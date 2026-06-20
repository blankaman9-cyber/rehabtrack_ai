"""
train.py — LSTM Exercise Classifier Training Script
=====================================================
Trains RehabLSTM on the dataset produced by collect_data.py and saves
a checkpoint that server.py / app.py can load directly.

Usage
-----
    python train.py                          # uses exercise_dataset.npz
    python train.py --data my_dataset.npz   # custom dataset path
    python train.py --epochs 60 --lr 1e-3   # override hyperparameters

Output
------
    checkpoint_best.pt   — best validation-accuracy weights  (use this)
    checkpoint_last.pt   — weights at final epoch
    training_log.json    — full per-epoch history for plotting
"""

import os, sys, json, argparse, time
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
os.environ["PYTHONUTF8"] = "1"
from datetime import datetime

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader, random_split
from sklearn.metrics import classification_report, confusion_matrix

# ── Local imports ─────────────────────────────────────────────────────────────
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lstm_model import RehabLSTM, build_scoring_engine, CONFIDENCE_THRESHOLD
from pose_processor import EXERCISE_LABELS, NUM_ANGLES, WINDOW_SIZE

# ── Defaults (overridable via argparse) ───────────────────────────────────────
DEFAULTS = dict(
    data         = "exercise_dataset.npz",
    epochs       = 80,
    batch_size   = 64,
    lr           = 3e-4,
    weight_decay = 1e-4,
    val_split    = 0.2,
    patience     = 15,           # early-stopping patience (epochs)
    hidden_dim   = 128,
    num_layers   = 2,
    dropout      = 0.3,
    seed         = 42,
    checkpoint   = "checkpoint_best.pt",
    log          = "training_log.json",
)


# ── Dataset ───────────────────────────────────────────────────────────────────

class ExerciseDataset(Dataset):
    """
    Wraps the .npz file produced by collect_data.py.

    Each item is:
        x : float32 tensor  (WINDOW_SIZE, NUM_ANGLES)
        y : int64 tensor    scalar class index
    """

    def __init__(self, npz_path: str, augment: bool = False):
        data = np.load(npz_path)
        self.X = torch.from_numpy(data["X"].astype(np.float32))  # (N, 30, 16)
        self.y = torch.from_numpy(data["y"].astype(np.int64))    # (N,)
        self.augment = augment
        print(f"  Loaded {len(self.X)} windows from {npz_path}")
        for i, ex in enumerate(EXERCISE_LABELS):
            n = int((self.y == i).sum())
            print(f"    {ex:<14}: {n:>4} windows")

    def __len__(self):
        return len(self.X)

    def __getitem__(self, idx):
        x = self.X[idx].clone()
        y = self.y[idx]
        if self.augment:
            x = self._augment(x)
        return x, y

    @staticmethod
    def _augment(x: torch.Tensor) -> torch.Tensor:
        """
        Light augmentations applied per-sample during training.

        1. Gaussian noise   — simulates MediaPipe jitter
        2. Time-shift       — shifts the window start by up to 3 frames
        3. Amplitude scale  — ±10% global angle scale
        """
        # 1. Gaussian jitter (σ = 2–5°)
        noise_std = torch.empty(1).uniform_(2.0, 5.0).item()
        x = x + torch.randn_like(x) * noise_std

        # 2. Random time-shift (roll along time axis)
        shift = torch.randint(-3, 4, (1,)).item()
        if shift != 0:
            x = torch.roll(x, shift, dims=0)

        # 3. Amplitude scale (0.9 – 1.1)
        scale = torch.empty(1).uniform_(0.90, 1.10).item()
        x = x * scale

        # Clip to valid degree range
        x = torch.clamp(x, 0.0, 180.0)
        return x


# ── Training utilities ────────────────────────────────────────────────────────

def compute_class_weights(y: torch.Tensor, num_classes: int) -> torch.Tensor:
    """Inverse-frequency class weights to handle imbalanced datasets."""
    counts = torch.bincount(y, minlength=num_classes).float()
    counts = torch.clamp(counts, min=1)
    weights = 1.0 / counts
    weights = weights / weights.sum() * num_classes   # normalise
    return weights


def evaluate(model, loader, criterion, device):
    """Run one evaluation pass. Returns (loss, accuracy, all_preds, all_targets)."""
    model.eval()
    total_loss, correct, total = 0.0, 0, 0
    all_preds, all_targets = [], []

    with torch.no_grad():
        for x, y in loader:
            x, y = x.to(device), y.to(device)
            probs  = model(x)
            loss   = criterion(torch.log(probs + 1e-9), y)   # NLLLoss
            preds  = probs.argmax(dim=1)

            total_loss += loss.item() * len(y)
            correct    += (preds == y).sum().item()
            total      += len(y)
            all_preds.extend(preds.cpu().tolist())
            all_targets.extend(y.cpu().tolist())

    return total_loss / total, correct / total, all_preds, all_targets


def print_section(title: str):
    print(f"\n{'-' * 60}")
    print(f"  {title}")
    print(f"{'-' * 60}")


# ── Main training loop ────────────────────────────────────────────────────────

def train(args):
    torch.manual_seed(args.seed)
    np.random.seed(args.seed)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"\n  Device : {device}")
    print(f"  Epochs : {args.epochs}  |  Batch : {args.batch_size}  |  LR : {args.lr}")

    # ── Load data ─────────────────────────────────────────────────────────────
    print_section("Loading dataset")
    if not os.path.exists(args.data):
        print(f"\nERROR: Dataset not found at '{args.data}'")
        print("Run  python collect_data.py  first to record exercise data.\n")
        sys.exit(1)

    full_dataset = ExerciseDataset(args.data, augment=False)
    n_total  = len(full_dataset)
    n_val    = int(n_total * args.val_split)
    n_train  = n_total - n_val

    train_set, val_set = random_split(
        full_dataset, [n_train, n_val],
        generator=torch.Generator().manual_seed(args.seed)
    )

    # Enable augmentation only on the training subset
    train_set.dataset = ExerciseDataset(args.data, augment=True)

    train_loader = DataLoader(train_set, batch_size=args.batch_size,
                              shuffle=True,  num_workers=0, pin_memory=False)
    val_loader   = DataLoader(val_set,   batch_size=args.batch_size,
                              shuffle=False, num_workers=0, pin_memory=False)

    print(f"\n  Train : {n_train} samples  |  Val : {n_val} samples")

    # ── Model ─────────────────────────────────────────────────────────────────
    print_section("Building model")
    model = RehabLSTM(
        input_size    = NUM_ANGLES,
        hidden_dim    = args.hidden_dim,
        num_layers    = args.num_layers,
        num_classes   = len(EXERCISE_LABELS),
        dropout       = args.dropout,
        bidirectional = args.bidirectional,
    ).to(device)

    n_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    print(f"  Parameters : {n_params:,}")

    # Class-weighted NLL loss (handles imbalanced datasets)
    all_y     = full_dataset.y
    cw        = compute_class_weights(all_y, len(EXERCISE_LABELS)).to(device)
    criterion = nn.NLLLoss(weight=cw)

    optimiser = torch.optim.Adam(model.parameters(),
                                 lr=args.lr, weight_decay=args.weight_decay)

    # Cosine annealing LR schedule
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
        optimiser, T_max=args.epochs, eta_min=args.lr * 0.05
    )

    # ── Training loop ─────────────────────────────────────────────────────────
    print_section("Training")
    print(f"\n{'Epoch':>6}  {'Train loss':>11}  {'Train acc':>10}  "
          f"{'Val loss':>9}  {'Val acc':>8}  {'LR':>9}  {'Best?':>5}")
    print("-" * 72)

    best_val_acc  = 0.0
    patience_ctr  = 0
    log_history   = []

    for epoch in range(1, args.epochs + 1):
        model.train()
        t0 = time.time()
        train_loss, train_correct, train_total = 0.0, 0, 0

        for x, y in train_loader:
            x, y = x.to(device), y.to(device)
            optimiser.zero_grad()
            probs = model(x)
            loss  = criterion(torch.log(probs + 1e-9), y)
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimiser.step()

            train_loss    += loss.item() * len(y)
            train_correct += (probs.argmax(1) == y).sum().item()
            train_total   += len(y)

        scheduler.step()

        t_loss = train_loss / train_total
        t_acc  = train_correct / train_total
        v_loss, v_acc, _, _ = evaluate(model, val_loader, criterion, device)
        lr_now = optimiser.param_groups[0]["lr"]

        is_best = v_acc > best_val_acc
        if is_best:
            best_val_acc = v_acc
            # Save self-describing checkpoint
            torch.save({
                "state_dict": model.state_dict(),
                "hidden_dim": args.hidden_dim,
                "num_layers": args.num_layers,
                "dropout": args.dropout,
                "bidirectional": args.bidirectional
            }, args.checkpoint)
            patience_ctr = 0
            flag = "  [OK]"
        else:
            patience_ctr += 1
            flag = ""

        log_history.append({
            "epoch": epoch, "train_loss": round(t_loss, 5),
            "train_acc": round(t_acc, 5), "val_loss": round(v_loss, 5),
            "val_acc": round(v_acc, 5), "lr": round(lr_now, 8),
        })

        print(f"{epoch:>6}  {t_loss:>11.4f}  {t_acc*100:>9.2f}%  "
              f"{v_loss:>9.4f}  {v_acc*100:>7.2f}%  {lr_now:>9.2e}{flag}")

        if patience_ctr >= args.patience:
            print(f"\n  Early stopping triggered after {epoch} epochs "
                  f"(no improvement for {args.patience} epochs).")
            break

    # Save last checkpoint with metadata
    torch.save({
        "state_dict": model.state_dict(),
        "hidden_dim": args.hidden_dim,
        "num_layers": args.num_layers,
        "dropout": args.dropout,
        "bidirectional": args.bidirectional
    }, "checkpoint_last.pt")

    # Save training log
    with open(args.log, "w") as f:
        json.dump({"history": log_history, "best_val_acc": best_val_acc,
                   "args": vars(args), "created_at": datetime.now().isoformat()}, f, indent=2)

    # ── Final evaluation on val set (best weights) ────────────────────────────
    print_section(f"Final evaluation  (best val acc = {best_val_acc*100:.2f}%)")
    checkpoint_data = torch.load(args.checkpoint, map_location=device, weights_only=False)
    if isinstance(checkpoint_data, dict) and "state_dict" in checkpoint_data:
        model.load_state_dict(checkpoint_data["state_dict"])
    else:
        model.load_state_dict(checkpoint_data)
    _, _, preds, targets = evaluate(model, val_loader, criterion, device)

    print("\n  Classification report:")
    print(classification_report(targets, preds, target_names=EXERCISE_LABELS, digits=3))

    print("  Confusion matrix (rows = true, cols = predicted):")
    cm = confusion_matrix(targets, preds)
    header = f"{'':>14}" + "".join(f"{ex:>12}" for ex in EXERCISE_LABELS)
    print(header)
    for i, row in enumerate(cm):
        print(f"  {EXERCISE_LABELS[i]:>12}" + "".join(f"{v:>12}" for v in row))

    # ── Sanity check via ScoringEngine ────────────────────────────────────────
    print_section("ScoringEngine sanity check  (checkpoint loaded)")
    engine = build_scoring_engine(checkpoint_path=args.checkpoint)
    print("  Running 10 val samples through engine.score()…\n")
    val_data = val_set.dataset
    sample_indices = torch.randperm(len(val_data))[:10].tolist()

    for idx in sample_indices:
        x, true_y = val_data[idx]
        window_np = x.unsqueeze(0).numpy()   # (1, 30, 16)
        probs_dict, pred_label, score = engine.score(window_np)
        true_label = EXERCISE_LABELS[true_y.item()]
        match = " [OK]" if pred_label == true_label else "[ERR]"
        print(f"  {match} true={true_label:<14} pred={pred_label:<14} score={score:>5.1f}  "
              f"conf={max(probs_dict.values()):.1f}%")

    print(f"\n  Best checkpoint saved to : {args.checkpoint}")
    print(f"  Training log saved to    : {args.log}")
    print("\n  To use in your app / server, load with:")
    print(f"    engine = build_scoring_engine(checkpoint_path='{args.checkpoint}')")
    print(f"  or in server.py:")
    print(f"    engine = build_scoring_engine(checkpoint_path='{args.checkpoint}')\n")


# ── CLI ───────────────────────────────────────────────────────────────────────

def parse_args():
    p = argparse.ArgumentParser(description="Train RehabLSTM exercise classifier")
    p.add_argument("--data",         default=DEFAULTS["data"])
    p.add_argument("--epochs",       type=int,   default=DEFAULTS["epochs"])
    p.add_argument("--batch_size",   type=int,   default=DEFAULTS["batch_size"])
    p.add_argument("--lr",           type=float, default=DEFAULTS["lr"])
    p.add_argument("--weight_decay", type=float, default=DEFAULTS["weight_decay"])
    p.add_argument("--val_split",    type=float, default=DEFAULTS["val_split"])
    p.add_argument("--patience",     type=int,   default=DEFAULTS["patience"])
    p.add_argument("--hidden_dim",   type=int,   default=DEFAULTS["hidden_dim"])
    p.add_argument("--num_layers",   type=int,   default=DEFAULTS["num_layers"])
    p.add_argument("--dropout",      type=float, default=DEFAULTS["dropout"])
    p.add_argument("--bidirectional",action="store_true", help="Use bidirectional LSTM model")
    p.add_argument("--seed",         type=int,   default=DEFAULTS["seed"])
    p.add_argument("--checkpoint",   default=DEFAULTS["checkpoint"])
    p.add_argument("--log",          default=DEFAULTS["log"])
    return p.parse_args()


if __name__ == "__main__":
    train(parse_args())
