"""
pose_processor.py — Time-Series Feature Extraction Engine

Handles MediaPipe PoseLandmarker (Tasks API) initialization, frame-by-frame
joint coordinate extraction, 16-angle feature vector computation, and a
sliding-window deque buffer to feed the LSTM.

Frame data flow:
    BGR frame (H×W×3)
      → MediaPipe PoseLandmarker → 33 landmarks (x, y, z, visibility)
      → 16 skeletal joint angles (float32 vector)
      → deque buffer (window_size × 16)  ← shape fed to LSTM: (1, window_size, 16)
"""

import os
import time
import cv2
import mediapipe as mp
import numpy as np
from collections import deque
from typing import Optional, Tuple, List

from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision


# ── Joint angle definitions ────────────────────────────────────────────────────
# Each tuple = (landmark_A, vertex_landmark, landmark_B)
# The angle at the VERTEX is computed via the dot-product formula.
#
# MediaPipe Pose landmark indices (subset used here):
#   11=left_shoulder  12=right_shoulder
#   13=left_elbow     14=right_elbow
#   15=left_wrist     16=right_wrist
#   23=left_hip       24=right_hip
#   25=left_knee      26=right_knee
#   27=left_ankle     28=right_ankle
#   29=left_heel      30=right_heel
#   0=nose            7=left_ear   8=right_ear

ANGLE_TRIPLETS = [
    # Upper-body
    (13, 11, 23),   # 0  Left shoulder (elbow–shoulder–hip)
    (14, 12, 24),   # 1  Right shoulder
    (11, 13, 15),   # 2  Left elbow
    (12, 14, 16),   # 3  Right elbow
    (13, 15, 11),   # 4  Left wrist flex (elbow–wrist–shoulder proxy)
    (14, 16, 12),   # 5  Right wrist flex
    # Core / trunk
    (11, 23, 25),   # 6  Left hip
    (12, 24, 26),   # 7  Right hip
    (11, 23, 24),   # 8  Left lateral trunk tilt
    (12, 24, 23),   # 9  Right lateral trunk tilt
    # Lower-body
    (23, 25, 27),   # 10 Left knee
    (24, 26, 28),   # 11 Right knee
    (25, 27, 29),   # 12 Left ankle
    (26, 28, 30),   # 13 Right ankle
    # Shoulder-to-shoulder / cross angles
    (11, 12, 24),   # 14 Shoulder–hip cross (right side)
    (12, 11, 23),   # 15 Shoulder–hip cross (left side)
]

NUM_ANGLES = len(ANGLE_TRIPLETS)   # 16
WINDOW_SIZE = 30                   # temporal history fed to LSTM (frames)

# ── Pose connections for skeleton drawing ──────────────────────────────────────
# Pairs of landmark indices that should be connected with lines
POSE_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 7),
    (0, 4), (4, 5), (5, 6), (6, 8),
    (9, 10),
    (11, 12), (11, 13), (13, 15), (15, 17), (15, 19), (15, 21),
    (12, 14), (14, 16), (16, 18), (16, 20), (16, 22),
    (11, 23), (12, 24), (23, 24),
    (23, 25), (25, 27), (27, 29), (27, 31), (29, 31),
    (24, 26), (26, 28), (28, 30), (28, 32), (30, 32),
]

# Model path — expected next to this file
_MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pose_landmarker.task")


def _angle_between(a: np.ndarray, vertex: np.ndarray, b: np.ndarray) -> float:
    """
    Compute the angle (degrees) at `vertex` formed by rays vertex→a and vertex→b.

    Uses the dot-product formula:
        cos(θ) = (v1 · v2) / (|v1| |v2|)
    Clipped to [-1, 1] to guard against floating-point noise before arccos.

    Args:
        a, vertex, b: 3-D (x, y, z) coordinate arrays.

    Returns:
        Angle in degrees [0°, 180°].
    """
    v1 = a - vertex
    v2 = b - vertex
    norm1 = np.linalg.norm(v1)
    norm2 = np.linalg.norm(v2)
    if norm1 < 1e-6 or norm2 < 1e-6:
        return 0.0
    cos_theta = np.dot(v1, v2) / (norm1 * norm2)
    cos_theta = float(np.clip(cos_theta, -1.0, 1.0))
    return float(np.degrees(np.arccos(cos_theta)))


def _draw_landmarks_on_frame(frame: np.ndarray, landmarks, connections=POSE_CONNECTIONS):
    """
    Draw pose landmarks and connections on a BGR frame.
    Replaces the removed mp.solutions.drawing_utils functionality.

    Args:
        frame: BGR image (H × W × 3, uint8).
        landmarks: List of NormalizedLandmark from PoseLandmarkerResult.
    """
    h, w = frame.shape[:2]

    # Draw connections first (behind the dots)
    for idx_a, idx_b in connections:
        if idx_a < len(landmarks) and idx_b < len(landmarks):
            lm_a = landmarks[idx_a]
            lm_b = landmarks[idx_b]
            pt_a = (int(lm_a.x * w), int(lm_a.y * h))
            pt_b = (int(lm_b.x * w), int(lm_b.y * h))
            cv2.line(frame, pt_a, pt_b, (240, 240, 240), 2, cv2.LINE_AA)

    # Draw landmark dots
    for lm in landmarks:
        cx = int(lm.x * w)
        cy = int(lm.y * h)
        cv2.circle(frame, (cx, cy), 4, (180, 180, 180), -1, cv2.LINE_AA)
        cv2.circle(frame, (cx, cy), 5, (255, 255, 255), 1, cv2.LINE_AA)


class PoseProcessor:
    """
    Wraps MediaPipe PoseLandmarker (Tasks API) and produces a sliding-window
    feature tensor ready for the LSTM classifier.

    Usage:
        processor = PoseProcessor()
        for frame in video_stream:
            annotated_frame, feature_vector, window_ready, window_tensor = processor.process(frame)
            if window_ready:
                logits = lstm_model(window_tensor)  # shape (1, WINDOW_SIZE, NUM_ANGLES)
    """

    def __init__(
        self,
        window_size: int = WINDOW_SIZE,
        model_path: str = _MODEL_PATH,
    ):
        self.window_size = window_size
        self._buffer: deque = deque(maxlen=window_size)
        self._last_timestamp_ms = 0  # ensure monotonically increasing timestamps

        # Auto-download model file if not present
        if not os.path.exists(model_path):
            import urllib.request
            print(f"[PoseProcessor] model_path {model_path} not found. Downloading from official MediaPipe CDN...")
            url = "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_full/float16/1/pose_landmarker_full.task"
            os.makedirs(os.path.dirname(model_path), exist_ok=True)
            urllib.request.urlretrieve(url, model_path)
            print("[PoseProcessor] Download complete!")

        # MediaPipe Tasks API initialisation
        base_options = mp_python.BaseOptions(model_asset_path=model_path)
        options = vision.PoseLandmarkerOptions(
            base_options=base_options,
            running_mode=vision.RunningMode.VIDEO,
            num_poses=1,
            output_segmentation_masks=False,
        )
        self._landmarker = vision.PoseLandmarker.create_from_options(options)

    # ── Public API ─────────────────────────────────────────────────────────────

    def process(
        self, bgr_frame: np.ndarray
    ) -> Tuple[np.ndarray, Optional[np.ndarray], bool, Optional[np.ndarray]]:
        """
        Process a single BGR video frame end-to-end.

        Args:
            bgr_frame: OpenCV BGR image (H × W × 3, uint8).

        Returns:
            annotated_frame : BGR image with skeleton overlay drawn.
            feature_vector  : float32 array of shape (NUM_ANGLES,) — current frame's
                              16 joint angles in degrees, or None if no pose detected.
            window_ready    : True once the deque has accumulated `window_size` frames.
            window_tensor   : float32 array of shape (1, window_size, NUM_ANGLES) —
                              the temporal batch ready to feed into the LSTM, or None.
        """
        # Convert BGR to RGB for MediaPipe
        rgb = cv2.cvtColor(bgr_frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)

        # Use real monotonic time to guarantee strictly increasing timestamps
        timestamp_ms = int(time.monotonic() * 1000)
        if timestamp_ms <= self._last_timestamp_ms:
            timestamp_ms = self._last_timestamp_ms + 1
        self._last_timestamp_ms = timestamp_ms
        result = self._landmarker.detect_for_video(mp_image, timestamp_ms)

        annotated = bgr_frame.copy()

        if not result.pose_landmarks or len(result.pose_landmarks) == 0:
            return annotated, None, False, None

        # Get the first (and only) detected pose
        pose_landmarks = result.pose_landmarks[0]       # normalized landmarks
        pose_world_landmarks = result.pose_world_landmarks[0] if result.pose_world_landmarks else None

        # Draw skeletal wireframe onto the frame
        _draw_landmarks_on_frame(annotated, pose_landmarks)

        # Extract raw landmark coordinates (world-space 3-D preferred for angle calc)
        landmarks = self._extract_landmarks(pose_landmarks, pose_world_landmarks)

        # Compute 16 joint angles
        feature_vector = self._compute_angles(landmarks)

        # Push into temporal buffer
        self._buffer.append(feature_vector.copy())

        window_ready = len(self._buffer) == self.window_size
        window_tensor = None
        if window_ready:
            # Stack → shape (window_size, NUM_ANGLES) → add batch dim → (1, window_size, NUM_ANGLES)
            window_tensor = np.stack(list(self._buffer), axis=0)[np.newaxis].astype(np.float32)

        return annotated, feature_vector, window_ready, window_tensor

    def get_buffer_fill(self) -> float:
        """Returns fraction [0, 1] of how full the sliding window is."""
        return len(self._buffer) / self.window_size

    def reset_buffer(self) -> None:
        """Clears the temporal window (call between exercise sets)."""
        self._buffer.clear()

    def close(self) -> None:
        """Release the landmarker resources."""
        self._landmarker.close()

    # ── Private helpers ────────────────────────────────────────────────────────

    def _extract_landmarks(self, pose_landmarks, pose_world_landmarks) -> np.ndarray:
        """
        Build a (33, 3) float32 array of (x, y, z) world coordinates.
        Falls back to normalised image-space landmarks if world coords unavailable.
        """
        if pose_world_landmarks and len(pose_world_landmarks) >= 33:
            lm_list = pose_world_landmarks
        else:
            lm_list = pose_landmarks

        coords = np.array(
            [[lm.x, lm.y, lm.z] for lm in lm_list], dtype=np.float32
        )  # shape (33, 3)
        return coords

    def _compute_angles(self, landmarks: np.ndarray) -> np.ndarray:
        """
        Evaluate all 16 skeletal angles defined in ANGLE_TRIPLETS.

        Args:
            landmarks: (33, 3) float32 world-coordinate array from MediaPipe.

        Returns:
            angles: float32 array of shape (NUM_ANGLES,) — values in [0°, 180°].
        """
        angles = np.zeros(NUM_ANGLES, dtype=np.float32)
        for i, (idx_a, idx_v, idx_b) in enumerate(ANGLE_TRIPLETS):
            angles[i] = _angle_between(
                landmarks[idx_a], landmarks[idx_v], landmarks[idx_b]
            )
        return angles


# ── Convenience label list (mirrors LSTM output classes) ──────────────────────
EXERCISE_LABELS: List[str] = ["Squat", "Arm Cross", "Body Twist", "Step Jack"]
