"""
lstm_model.py — Real-Time LSTM Classification & Scoring Network

Architecture:
    Input  : (batch, window_size, num_angles)  e.g. (1, 30, 16)
               ↓
    LSTM   : hidden_dim=128, num_layers=2, batch_first=True
               ↓  takes final hidden state → shape (batch, hidden_dim)
    Dropout: 0.3  (regularisation)
               ↓
    FC     : hidden_dim → num_classes
               ↓
    Softmax: probability distribution over exercise classes

Scoring Engine:
    The max class probability (confidence) is mapped linearly to a
    0–100 score, with a dead-zone below CONFIDENCE_THRESHOLD treated
    as "uncertain / not performing exercise".

Mock weights:
    The model is initialised with random weights so it runs end-to-end
    immediately without needing pre-trained checkpoint files.
    Replace `model.load_state_dict(torch.load("checkpoint.pt"))` when
    real trained weights become available.
"""

import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
import numpy as np
import torch
import torch.nn as nn
from typing import Tuple, List, Dict

from pose_processor import EXERCISE_LABELS, NUM_ANGLES, WINDOW_SIZE

# ── Hyper-parameters ──────────────────────────────────────────────────────────
HIDDEN_DIM         = 128
NUM_LAYERS         = 2
DROPOUT            = 0.3
NUM_CLASSES        = len(EXERCISE_LABELS)       # 4
CONFIDENCE_THRESHOLD = 0.40   # below this → score treated as 0 (no clear motion)
SEED               = 42


class RehabLSTM(nn.Module):
    """
    Lightweight bidirectional-optional LSTM for exercise sequence classification.

    Input tensor  : (batch_size, seq_len, input_size)
                     seq_len   = WINDOW_SIZE  (30 frames)
                     input_size = NUM_ANGLES  (16 joint angles)
    Output tensor : (batch_size, num_classes) — raw logits
    """

    def __init__(
        self,
        input_size: int = NUM_ANGLES,
        hidden_dim: int = HIDDEN_DIM,
        num_layers: int = NUM_LAYERS,
        num_classes: int = NUM_CLASSES,
        dropout: float = DROPOUT,
        bidirectional: bool = False,
    ):
        super().__init__()
        self.hidden_dim    = hidden_dim
        self.num_layers    = num_layers
        self.bidirectional = bidirectional
        self.num_directions = 2 if bidirectional else 1

        # ── Layer 1: LSTM ──────────────────────────────────────────────────
        # batch_first=True → input/output tensors shaped (batch, seq, feature)
        self.lstm = nn.LSTM(
            input_size=input_size,
            hidden_size=hidden_dim,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0.0,
            bidirectional=bidirectional,
        )

        # ── Layer 2: Regularisation ────────────────────────────────────────
        self.dropout = nn.Dropout(p=dropout)
        self.layer_norm = nn.LayerNorm(hidden_dim * self.num_directions)

        # ── Layer 3: Fully-Connected head ──────────────────────────────────
        self.fc = nn.Linear(hidden_dim * self.num_directions, num_classes)

        # ── Layer 4: Softmax (inference only — use CrossEntropy for training) ─
        self.softmax = nn.Softmax(dim=-1)

        # Initialise weights with Xavier uniform for stable mock runs
        self._init_weights()

    def _init_weights(self) -> None:
        """Xavier / orthogonal initialisation for LSTM and linear layers."""
        torch.manual_seed(SEED)
        for name, param in self.lstm.named_parameters():
            if "weight_ih" in name:
                nn.init.xavier_uniform_(param.data)
            elif "weight_hh" in name:
                nn.init.orthogonal_(param.data)
            elif "bias" in name:
                param.data.fill_(0.0)
                # Set forget-gate bias = 1 to prevent gradient vanishing
                n = param.size(0)
                param.data[n // 4: n // 2].fill_(1.0)
        nn.init.xavier_uniform_(self.fc.weight)
        nn.init.zeros_(self.fc.bias)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Forward pass.

        Args:
            x: float32 tensor of shape (batch, seq_len, input_size)
               Frames ordered oldest→newest in the sequence dimension.

        Returns:
            probs: float32 tensor of shape (batch, num_classes) — softmax probs.
        """
        # h0, c0 default to zeros (stateless inference)
        lstm_out, _ = self.lstm(x)            # (batch, seq_len, hidden_dim * num_directions)

        # Use the final time-step hidden state as the sequence summary
        # For bidirectional LSTM, forward LSTM's final state is at index -1,
        # backward LSTM's final state is at index 0.
        if self.bidirectional:
            forward_last = lstm_out[:, -1, :self.hidden_dim]
            backward_last = lstm_out[:, 0, self.hidden_dim:]
            last_hidden = torch.cat((forward_last, backward_last), dim=-1)
        else:
            last_hidden = lstm_out[:, -1, :]

        normed  = self.layer_norm(last_hidden)
        dropped = self.dropout(normed)
        logits  = self.fc(dropped)            # (batch, num_classes)
        probs   = self.softmax(logits)        # (batch, num_classes)
        return probs


# ── Scoring Engine ─────────────────────────────────────────────────────────────

class ScoringEngine:
    """
    Wraps RehabLSTM and converts raw probabilities into:
      - predicted exercise label
      - accuracy score 0–100
      - full probability dict for live bar chart

    Usage:
        engine = ScoringEngine()
        probs_dict, label, score = engine.score(window_tensor)
    """

    def __init__(self, model: RehabLSTM = None):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model  = (model or RehabLSTM()).to(self.device).eval()

    @torch.no_grad()
    def score(
        self, window_np: np.ndarray
    ) -> Tuple[Dict[str, float], str, float]:
        """
        Run one inference pass over the temporal window.

        Args:
            window_np : float32 numpy array of shape (1, window_size, num_angles).
                        Typically produced by PoseProcessor.process().

        Returns:
            probs_dict : {exercise_label: probability_percent}  (values sum ≈ 100)
            pred_label : The exercise with the highest probability.
            score      : Float in [0, 100] representing motion accuracy confidence.
                         Returns 0.0 when max confidence < CONFIDENCE_THRESHOLD.
        """
        x = torch.from_numpy(window_np).to(self.device)   # (1, 30, 16)
        probs = self.model(x).cpu().numpy()[0]             # (4,)

        probs_dict = {
            label: float(p * 100)
            for label, p in zip(EXERCISE_LABELS, probs)
        }

        max_idx   = int(np.argmax(probs))
        max_prob  = float(probs[max_idx])
        pred_label = EXERCISE_LABELS[max_idx]

        # Map confidence to score:
        #   below threshold → 0
        #   threshold..1.0  → linearly scaled to 0..100
        if max_prob < CONFIDENCE_THRESHOLD:
            score = 0.0
        else:
            score = round(
                (max_prob - CONFIDENCE_THRESHOLD)
                / (1.0 - CONFIDENCE_THRESHOLD)
                * 100.0,
                1,
            )

        return probs_dict, pred_label, score

    def load_checkpoint(self, path: str) -> None:
        """Load trained weights from a PyTorch checkpoint file."""
        checkpoint = torch.load(path, map_location=self.device, weights_only=False)
        
        # Support metadata-rich checkpoints
        if isinstance(checkpoint, dict) and "state_dict" in checkpoint:
            hidden_dim = checkpoint.get("hidden_dim", self.model.hidden_dim)
            num_layers = checkpoint.get("num_layers", self.model.num_layers)
            bidirectional = checkpoint.get("bidirectional", getattr(self.model, "bidirectional", False))
            
            # Reconstruct the model with the stored architecture parameters
            self.model = RehabLSTM(
                hidden_dim=hidden_dim,
                num_layers=num_layers,
                bidirectional=bidirectional
            ).to(self.device)
            state_dict = checkpoint["state_dict"]
        else:
            state_dict = checkpoint
            
        self.model.load_state_dict(state_dict)
        self.model.eval()
        print(f"[ScoringEngine] Loaded weights from {path} (bidirectional={getattr(self.model, 'bidirectional', False)})")


# ── Factory helper ────────────────────────────────────────────────────────────

def build_scoring_engine(checkpoint_path: str = None) -> ScoringEngine:
    """
    Convenience factory.  Builds a ScoringEngine with mock weights by default.
    Pass a valid checkpoint_path to load real trained weights.
    """
    engine = ScoringEngine()
    if checkpoint_path:
        engine.load_checkpoint(checkpoint_path)
    return engine


# ── Quick smoke-test ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    engine = build_scoring_engine()
    # Simulate a random sliding-window batch  (1 sample × 30 frames × 16 angles)
    dummy_window = np.random.rand(1, WINDOW_SIZE, NUM_ANGLES).astype(np.float32)
    dummy_window *= 180.0   # scale to realistic degree range

    probs_dict, label, score = engine.score(dummy_window)
    print("── Mock inference result ──────────────────────────")
    for lbl, pct in probs_dict.items():
        bar = "█" * int(pct / 5)
        print(f"  {lbl:<14} {pct:5.1f}%  {bar}")
    print(f"\n  Predicted: {label}   Score: {score}/100")
