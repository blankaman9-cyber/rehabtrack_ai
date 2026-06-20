"""
collect_data.py — Exercise Data Collection Tool
================================================
Records labelled pose windows from your webcam and saves them as a .npz
dataset file ready for train.py.

How to use
----------
    python collect_data.py

Controls during recording:
    SPACE  — start / stop recording for the current exercise
    N      — next exercise
    Q      — quit and save dataset

Output
------
    exercise_dataset.npz  — contains arrays  X (N, 30, 16) and y (N,)
    exercise_dataset_meta.json — label mapping and collection stats

Tips for good data
------------------
- Aim for at least 200 windows per exercise (the script shows a live count).
- Vary your speed: slow reps, normal reps, partial reps.
- Different body positions: closer/further from camera, slightly off-centre.
- Rest between exercises so the buffer resets cleanly.
"""

import os, sys, time, json
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
os.environ["PYTHONUTF8"] = "1"
import cv2
import numpy as np
from collections import deque
from datetime import datetime

# ── Add parent dir to path if running from a subfolder ───────────────────────
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pose_processor import PoseProcessor, EXERCISE_LABELS, NUM_ANGLES, WINDOW_SIZE

# ── Config ────────────────────────────────────────────────────────────────────
OUTPUT_PATH      = "exercise_dataset.npz"
META_PATH        = "exercise_dataset_meta.json"
MIN_WINDOWS      = 200     # warn if fewer than this per class
TARGET_WINDOWS   = 300     # shown as the target in the UI
FONT             = cv2.FONT_HERSHEY_SIMPLEX

# ── Colours (BGR) ─────────────────────────────────────────────────────────────
C_WHITE  = (255, 255, 255)
C_GREEN  = (100, 220, 100)
C_RED    = (80,  80,  220)
C_YELLOW = (80,  220, 220)
C_GRAY   = (140, 140, 140)
C_BG     = (20,  20,  20)


def draw_ui(frame: np.ndarray, exercise: str, ex_idx: int,
            recording: bool, count: int, buffer_fill: float,
            all_counts: dict) -> np.ndarray:
    """Overlay status HUD onto the frame."""
    h, w = frame.shape[:2]
    overlay = frame.copy()

    # Semi-transparent top bar
    cv2.rectangle(overlay, (0, 0), (w, 110), C_BG, -1)
    cv2.addWeighted(overlay, 0.75, frame, 0.25, 0, frame)

    # Exercise name + index
    color = C_GREEN if recording else C_WHITE
    cv2.putText(frame, f"Exercise: {exercise}  ({ex_idx+1}/{len(EXERCISE_LABELS)})",
                (14, 34), FONT, 0.8, color, 2, cv2.LINE_AA)

    # Recording state
    state = "● RECORDING" if recording else "○ PAUSED  (SPACE to start)"
    cv2.putText(frame, state, (14, 66), FONT, 0.55,
                C_RED if recording else C_GRAY, 1, cv2.LINE_AA)

    # Window count for current class
    cv2.putText(frame, f"Windows this class: {count} / {TARGET_WINDOWS}",
                (14, 92), FONT, 0.5, C_YELLOW, 1, cv2.LINE_AA)

    # Buffer fill bar
    bar_x, bar_y, bar_w, bar_h = 14, 118, 220, 10
    cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_w, bar_y + bar_h), C_GRAY, 1)
    filled = int(bar_w * buffer_fill)
    if filled > 0:
        cv2.rectangle(frame, (bar_x, bar_y),
                      (bar_x + filled, bar_y + bar_h), C_GREEN, -1)
    cv2.putText(frame, "Buffer", (bar_x + bar_w + 6, bar_y + 9),
                FONT, 0.38, C_GRAY, 1, cv2.LINE_AA)

    # All-class summary (bottom-left)
    y_start = h - 20 - len(EXERCISE_LABELS) * 22
    cv2.putText(frame, "Dataset so far:", (14, y_start - 8),
                FONT, 0.42, C_GRAY, 1, cv2.LINE_AA)
    for i, ex in enumerate(EXERCISE_LABELS):
        n = all_counts.get(ex, 0)
        bar_len = min(int(n / TARGET_WINDOWS * 120), 120)
        y = y_start + i * 22
        cv2.rectangle(frame, (14, y), (14 + bar_len, y + 14),
                      C_GREEN if n >= MIN_WINDOWS else C_YELLOW, -1)
        cv2.putText(frame, f"{ex}: {n}", (140, y + 11),
                    FONT, 0.38, C_WHITE, 1, cv2.LINE_AA)

    # Controls (bottom-right)
    controls = ["SPACE: record/pause", "N: next exercise", "Q: quit & save"]
    for i, txt in enumerate(controls):
        cv2.putText(frame, txt, (w - 220, h - 70 + i * 22),
                    FONT, 0.38, C_GRAY, 1, cv2.LINE_AA)

    return frame


def main():
    print("=" * 60)
    print("  RehabTrack AI — Data Collection Tool")
    print("=" * 60)
    print(f"  Exercises  : {', '.join(EXERCISE_LABELS)}")
    print(f"  Target     : {TARGET_WINDOWS} windows per exercise")
    print(f"  Output     : {OUTPUT_PATH}")
    print("=" * 60)
    print("\nPress SPACE to start recording, N to skip exercise, Q to quit.\n")

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("ERROR: Could not open webcam.")
        sys.exit(1)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    processor = PoseProcessor(window_size=WINDOW_SIZE)

    # Storage
    all_X: list = []   # list of (WINDOW_SIZE, NUM_ANGLES) arrays
    all_y: list = []   # integer class labels
    all_counts = {ex: 0 for ex in EXERCISE_LABELS}

    ex_idx    = 0
    recording = False
    last_window_hash = None   # deduplicate identical windows from slow cameras

    print(f"\n→ Current exercise: {EXERCISE_LABELS[ex_idx]}")

    try:
        while ex_idx < len(EXERCISE_LABELS):
            exercise    = EXERCISE_LABELS[ex_idx]
            class_label = ex_idx

            ret, frame = cap.read()
            if not ret:
                print("WARNING: Failed to read frame.")
                continue

            frame = cv2.flip(frame, 1)   # mirror for intuitive view

            annotated, feat_vec, window_ready, window_tensor = processor.process(frame)

            if recording and window_ready and window_tensor is not None:
                # window_tensor shape: (1, WINDOW_SIZE, NUM_ANGLES)
                window_np = window_tensor[0]   # (WINDOW_SIZE, NUM_ANGLES)

                # Simple dedup: skip if this window is ~identical to the last saved
                w_hash = hash(window_np.tobytes())
                if w_hash != last_window_hash:
                    all_X.append(window_np.copy())
                    all_y.append(class_label)
                    all_counts[exercise] += 1
                    last_window_hash = w_hash

            # Draw UI
            ui_frame = draw_ui(
                annotated, exercise, ex_idx, recording,
                all_counts[exercise], processor.get_buffer_fill(), all_counts
            )
            cv2.imshow("RehabTrack — Data Collector", ui_frame)

            key = cv2.waitKey(1) & 0xFF

            if key == ord(' '):
                recording = not recording
                if recording:
                    processor.reset_buffer()
                    print(f"  [REC] Recording {exercise}…  ({all_counts[exercise]} windows so far)")
                else:
                    print(f"  [PAUSE] Paused.  ({all_counts[exercise]} windows for {exercise})")

            elif key == ord('n') or key == ord('N'):
                recording = False
                processor.reset_buffer()
                ex_idx += 1
                last_window_hash = None
                if ex_idx < len(EXERCISE_LABELS):
                    print(f"\n→ Next exercise: {EXERCISE_LABELS[ex_idx]}")
                else:
                    print("\n→ All exercises done!")
                    break

            elif key == ord('q') or key == ord('Q'):
                print("\n→ Quitting early and saving collected data…")
                break

    finally:
        cap.release()
        processor.close()
        cv2.destroyAllWindows()

    # ── Save dataset ──────────────────────────────────────────────────────────
    if len(all_X) == 0:
        print("\nNo data collected. Nothing saved.")
        return

    X = np.stack(all_X, axis=0).astype(np.float32)   # (N, WINDOW_SIZE, NUM_ANGLES)
    y = np.array(all_y, dtype=np.int64)               # (N,)

    np.savez_compressed(OUTPUT_PATH, X=X, y=y)
    print(f"\nDataset saved  →  {OUTPUT_PATH}")
    print(f"  Total windows : {len(X)}")
    print(f"  Shape X       : {X.shape}")
    print(f"  Shape y       : {y.shape}")
    for i, ex in enumerate(EXERCISE_LABELS):
        n = int((y == i).sum())
        status = "✓" if n >= MIN_WINDOWS else f"⚠ (need {MIN_WINDOWS - n} more)"
        print(f"  {ex:<14}: {n:>4} windows  {status}")

    # Save metadata
    meta = {
        "created_at"    : datetime.now().isoformat(),
        "exercise_labels": EXERCISE_LABELS,
        "label_to_idx"  : {ex: i for i, ex in enumerate(EXERCISE_LABELS)},
        "window_size"   : WINDOW_SIZE,
        "num_angles"    : NUM_ANGLES,
        "counts"        : {ex: int((y == i).sum()) for i, ex in enumerate(EXERCISE_LABELS)},
        "total_windows" : len(X),
    }
    with open(META_PATH, "w") as f:
        json.dump(meta, f, indent=2)
    print(f"Metadata saved →  {META_PATH}\n")

    under = [ex for ex in EXERCISE_LABELS if all_counts[ex] < MIN_WINDOWS]
    if under:
        print(f"⚠  These classes have fewer than {MIN_WINDOWS} windows: {under}")
        print("   Consider re-running collect_data.py to add more samples.\n")
    else:
        print("✓  All classes meet the minimum window target.")
        print("   Run  python train.py  to train the model.\n")


if __name__ == "__main__":
    main()
