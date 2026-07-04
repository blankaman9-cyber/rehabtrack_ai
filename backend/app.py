"""
app.py — Dual-Interface Telerehabilitation Tracker (Streamlit)

Run with:
    streamlit run app.py

Tabs:
    🏃 Patient  — live webcam pose tracking, LSTM scoring, session logging
    🩺 Doctor   — longitudinal analytics dashboard, prescription management
"""

import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
os.environ["PYTHONUTF8"] = "1"

import time
import threading
from collections import deque
from datetime import datetime
from typing import Dict, List, Optional

import cv2
import numpy as np
import pandas as pd
import streamlit as st

# Local modules
import database as db
from pose_processor import PoseProcessor, EXERCISE_LABELS, NUM_ANGLES, WINDOW_SIZE
from lstm_model import build_scoring_engine

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="RehabTrack AI",
    page_icon="🏃",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Styling ────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@0;1&family=Barlow:wght@300;400;500;600&display=swap');

    /* Global fonts and overrides */
    html, body, [class*="css"], .stMarkdown, p, div, span, label, input, select, textarea {
        font-family: 'Barlow', sans-serif !important;
        color: #ffffff !important;
    }

    .main, .stApp {
        background-color: #000000 !important;
    }

    h1, h2, h3, .font-heading {
        font-family: 'Instrument Serif', serif !important;
        font-style: italic !important;
        color: #ffffff !important;
    }
    
    h1 { font-size: 3.5rem !important; }
    h2 { font-size: 2.8rem !important; }
    h3 { font-size: 2rem !important; }

    /* Liquid-glass variant 1 (subtle) */
    .liquid-glass {
        background: rgba(255, 255, 255, 0.01) !important;
        backdrop-filter: blur(4px) !important;
        -webkit-backdrop-filter: blur(4px) !important;
        border: none !important;
        box-shadow: inset 0 1px 1px rgba(255, 255, 255, 0.1) !important;
        position: relative !important;
        overflow: hidden !important;
    }
    .liquid-glass::before {
        content: "";
        position: absolute; inset: 0;
        border-radius: inherit;
        padding: 1.4px;
        background: linear-gradient(180deg,
          rgba(255, 255, 255, 0.45) 0%,
          rgba(255, 255, 255, 0.15) 20%,
          rgba(255, 255, 255, 0) 40%,
          rgba(255, 255, 255, 0) 60%,
          rgba(255, 255, 255, 0.15) 80%,
          rgba(255, 255, 255, 0.45) 100%);
        -webkit-mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
        -webkit-mask-composite: xor;
        mask-composite: exclude;
        pointer-events: none;
    }

    /* Liquid-glass variant 2 (strong) */
    .liquid-glass-strong {
        background: rgba(255, 255, 255, 0.01) !important;
        backdrop-filter: blur(50px) !important;
        -webkit-backdrop-filter: blur(50px) !important;
        border: none !important;
        box-shadow: 4px 4px 4px rgba(0, 0, 0, 0.05), inset 0 1px 1px rgba(255, 255, 255, 0.15) !important;
        position: relative !important;
        overflow: hidden !important;
    }
    .liquid-glass-strong::before {
        content: "";
        position: absolute; inset: 0;
        border-radius: inherit;
        padding: 1.4px;
        background: linear-gradient(180deg,
          rgba(255, 255, 255, 0.5) 0%,
          rgba(255, 255, 255, 0.2) 20%,
          rgba(255, 255, 255, 0) 40%,
          rgba(255, 255, 255, 0) 60%,
          rgba(255, 255, 255, 0.2) 80%,
          rgba(255, 255, 255, 0.5) 100%);
        -webkit-mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
        -webkit-mask-composite: xor;
        mask-composite: exclude;
        pointer-events: none;
    }

    /* Score ring using liquid-glass-strong style */
    .score-ring {
        display: flex; align-items: center; justify-content: center;
        width: 110px; height: 110px;
        border-radius: 50%;
        font-size: 2.2rem; font-weight: 700;
        font-family: 'Instrument Serif', serif !important;
        font-style: italic !important;
        margin: auto;
        
        background: rgba(255, 255, 255, 0.01);
        backdrop-filter: blur(50px);
        -webkit-backdrop-filter: blur(50px);
        border: none;
        box-shadow: 4px 4px 4px rgba(0, 0, 0, 0.05), inset 0 1px 1px rgba(255, 255, 255, 0.15);
        position: relative;
        overflow: hidden;
    }
    .score-ring::before {
        content: "";
        position: absolute; inset: 0;
        border-radius: inherit;
        padding: 1.4px;
        background: linear-gradient(180deg,
          rgba(255, 255, 255, 0.5) 0%,
          rgba(255, 255, 255, 0.2) 20%,
          rgba(255, 255, 255, 0) 40%,
          rgba(255, 255, 255, 0) 60%,
          rgba(255, 255, 255, 0.2) 80%,
          rgba(255, 255, 255, 0.5) 100%);
        -webkit-mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
        -webkit-mask-composite: xor;
        mask-composite: exclude;
        pointer-events: none;
    }
    .score-high   { color: #ffffff !important; text-shadow: 0 0 10px rgba(255, 255, 255, 0.5); }
    .score-mid    { color: rgba(255, 255, 255, 0.85) !important; }
    .score-low    { color: rgba(255, 255, 255, 0.5) !important; }

    /* Metric cards */
    .metric-card {
        background: rgba(255, 255, 255, 0.01);
        backdrop-filter: blur(4px);
        -webkit-backdrop-filter: blur(4px);
        border: none;
        box-shadow: inset 0 1px 1px rgba(255, 255, 255, 0.1);
        position: relative;
        overflow: hidden;
        border-radius: 1.25rem;
        padding: 1.2rem 1.4rem;
        text-align: center;
        margin-bottom: 1rem;
    }
    .metric-card::before {
        content: "";
        position: absolute; inset: 0;
        border-radius: inherit;
        padding: 1.4px;
        background: linear-gradient(180deg,
          rgba(255, 255, 255, 0.45) 0%,
          rgba(255, 255, 255, 0.15) 20%,
          rgba(255, 255, 255, 0) 40%,
          rgba(255, 255, 255, 0) 60%,
          rgba(255, 255, 255, 0.15) 80%,
          rgba(255, 255, 255, 0.45) 100%);
        -webkit-mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
        -webkit-mask-composite: xor;
        mask-composite: exclude;
        pointer-events: none;
    }
    .metric-label { font-size: 0.75rem; color: rgba(255, 255, 255, 0.65); text-transform: uppercase; letter-spacing: 0.08em; }
    .metric-value {
        font-size: 1.8rem;
        font-weight: 700;
        color: #ffffff;
        font-family: 'Instrument Serif', serif !important;
        font-style: italic !important;
        margin-top: 0.25rem;
    }

    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: #050505 !important;
        border-right: 1px solid rgba(255, 255, 255, 0.08) !important;
    }

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background: transparent !important;
    }
    .stTabs [data-baseweb="tab"] {
        background: rgba(255, 255, 255, 0.01) !important;
        border-radius: 8px 8px 0 0 !important;
        border: 1px solid rgba(255, 255, 255, 0.05) !important;
        border-bottom: none !important;
        color: rgba(255, 255, 255, 0.6) !important;
        font-weight: 500;
        padding: 8px 20px;
        backdrop-filter: blur(4px);
    }
    .stTabs [aria-selected="true"] {
        background: rgba(255, 255, 255, 0.04) !important;
        color: #ffffff !important;
        border-color: rgba(255, 255, 255, 0.15) !important;
        border-bottom: 2px solid #ffffff !important;
    }

    /* Buttons with liquid-glass logic */
    .stButton > button {
        background: rgba(255, 255, 255, 0.01) !important;
        color: #ffffff !important;
        border: none !important;
        border-radius: 9999px !important;
        box-shadow: inset 0 1px 1px rgba(255, 255, 255, 0.15) !important;
        position: relative !important;
        overflow: hidden !important;
        backdrop-filter: blur(4px) !important;
        -webkit-backdrop-filter: blur(4px) !important;
        font-family: 'Barlow', sans-serif !important;
        font-weight: 500 !important;
        padding: 0.5rem 1.5rem !important;
        transition: all 0.3s ease !important;
    }
    .stButton > button::before {
        content: "";
        position: absolute; inset: 0;
        border-radius: inherit;
        padding: 1.4px;
        background: linear-gradient(180deg,
          rgba(255, 255, 255, 0.45) 0%,
          rgba(255, 255, 255, 0.15) 20%,
          rgba(255, 255, 255, 0) 40%,
          rgba(255, 255, 255, 0) 60%,
          rgba(255, 255, 255, 0.15) 80%,
          rgba(255, 255, 255, 0.45) 100%);
        -webkit-mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
        -webkit-mask-composite: xor;
        mask-composite: exclude;
        pointer-events: none;
    }
    .stButton > button:hover {
        background: rgba(255, 255, 255, 0.04) !important;
        box-shadow: inset 0 1px 1px rgba(255, 255, 255, 0.25) !important;
        opacity: 0.95 !important;
    }

    /* Form elements & input field overrides */
    div[data-baseweb="select"], div[data-baseweb="input"], input, select, textarea {
        background: rgba(255, 255, 255, 0.02) !important;
        color: #ffffff !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 8px !important;
    }
    
    div[data-baseweb="select"]:hover, div[data-baseweb="input"]:hover {
        border-color: rgba(255, 255, 255, 0.2) !important;
    }

    /* Role selection screen styles */
    .role-landing {
        display: flex; flex-direction: column; align-items: center;
        justify-content: center; min-height: 45vh; text-align: center;
    }
    .role-title {
        font-size: 4rem; font-weight: 700; color: #ffffff;
        font-family: 'Instrument Serif', serif !important;
        font-style: italic !important;
        letter-spacing: -0.03em; margin-bottom: 0.3rem;
    }
    .role-title span {
        color: #ffffff;
        text-shadow: 0 0 10px rgba(255, 255, 255, 0.4);
    }
    .role-subtitle {
        font-size: 1.1rem; color: rgba(255, 255, 255, 0.7); margin-bottom: 2rem;
        max-width: 460px;
        font-family: 'Barlow', sans-serif !important;
        font-weight: 300;
        line-height: 1.4;
    }
    .role-card {
        background: rgba(255, 255, 255, 0.01);
        backdrop-filter: blur(4px);
        -webkit-backdrop-filter: blur(4px);
        border: none;
        box-shadow: inset 0 1px 1px rgba(255, 255, 255, 0.1);
        position: relative;
        overflow: hidden;
        border-radius: 1.25rem;
        padding: 2.2rem 1.8rem;
        text-align: center;
        transition: all 0.3s ease;
        cursor: pointer;
        min-height: 220px;
        display: flex; flex-direction: column;
        align-items: center; justify-content: center;
        margin-bottom: 1rem;
    }
    .role-card::before {
        content: "";
        position: absolute; inset: 0;
        border-radius: inherit;
        padding: 1.4px;
        background: linear-gradient(180deg,
          rgba(255, 255, 255, 0.45) 0%,
          rgba(255, 255, 255, 0.15) 20%,
          rgba(255, 255, 255, 0) 40%,
          rgba(255, 255, 255, 0) 60%,
          rgba(255, 255, 255, 0.15) 80%,
          rgba(255, 255, 255, 0.45) 100%);
        -webkit-mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
        -webkit-mask-composite: xor;
        mask-composite: exclude;
        pointer-events: none;
    }
    .role-card:hover {
        background: rgba(255, 255, 255, 0.03);
        box-shadow: 0 8px 30px rgba(255, 255, 255, 0.05), inset 0 1px 1px rgba(255, 255, 255, 0.2);
        transform: translateY(-4px);
    }
    .role-icon { font-size: 3.2rem; margin-bottom: 0.8rem; }
    .role-name {
        font-size: 1.6rem; font-weight: 600; color: #ffffff;
        font-family: 'Instrument Serif', serif !important;
        font-style: italic !important;
        margin-bottom: 0.4rem;
    }
    .role-desc {
        font-size: 0.85rem; color: rgba(255, 255, 255, 0.7); line-height: 1.5;
        font-family: 'Barlow', sans-serif !important;
    }

    /* Hide Streamlit branding */
    #MainMenu, footer, header { visibility: hidden; }
    .block-container { padding-top: 1.5rem; }
</style>
""", unsafe_allow_html=True)


# ── Initialise DB (idempotent) ─────────────────────────────────────────────────
db.initialise_db()


# ── Session state defaults ─────────────────────────────────────────────────────
def _init_state():
    defaults = {
        "user_role": None,   # None = show role picker, "patient" or "doctor"
        "patient_id": 1,
        "tracking_active": False,
        "session_scores": [],
        "session_roms": [],
        "session_labels": [],
        "session_reps": 0,
        "last_label": "—",
        "last_score": 0.0,
        "angle_history": deque(maxlen=WINDOW_SIZE),
        "prob_history": {lbl: deque(maxlen=WINDOW_SIZE) for lbl in EXERCISE_LABELS},
        "frame_placeholder": None,
        "scoring_engine": None,
        "pose_processor": None,
        # Cooldown: timestamp (monotonic) after which the next rep can be counted
        "rep_cooldown_until": 0.0,
        # How many seconds to lock out after a rep is counted
        "rep_cooldown_secs": 5.0,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

_init_state()


# ── Lazy-load heavy models ─────────────────────────────────────────────────────
@st.cache_resource(show_spinner="Loading LSTM model…")
def load_scoring_engine(checkpoint_path=None):
    return build_scoring_engine(checkpoint_path=checkpoint_path)

def _create_pose_processor():
    """Create a fresh PoseProcessor (new landmarker = fresh timestamp state)."""
    return PoseProcessor(window_size=WINDOW_SIZE)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — PATIENT INTERFACE
# ══════════════════════════════════════════════════════════════════════════════

def render_patient_tab():
    st.markdown("## 🏃 Patient Live Session")

    # ── Sidebar: patient & prescription selection ──────────────────────────
    with st.sidebar:
        st.markdown("### 👤 Patient Profile")
        patients = db.get_all_patients()
        if not patients:
            st.warning("No patients currently registered in the database.")
            return
        patient_names = {p["name"]: p["id"] for p in patients}
        selected_name = st.selectbox("Select Patient", list(patient_names.keys()))
        st.session_state.patient_id = patient_names[selected_name]
        patient = db.get_patient(st.session_state.patient_id)

        st.markdown(f"""
        <div class='metric-card'>
            <div class='metric-label'>Condition</div>
            <div style='color:#a0b4cc;font-size:0.9rem;margin-top:4px'>{patient['condition']}</div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("")

        prescriptions = db.get_prescriptions(st.session_state.patient_id)
        presc_options = {f"{p['exercise']} (×{p['target_reps']} reps)": p for p in prescriptions}
        selected_presc_key = st.selectbox("📋 Active Prescription", list(presc_options.keys()) or ["No prescriptions"])
        selected_presc = presc_options.get(selected_presc_key)

        if selected_presc:
            st.markdown(f"""
            <div class='metric-card'>
                <div class='metric-label'>Target ROM</div>
                <div class='metric-value'>{selected_presc['target_rom']}°</div>
            </div>
            """, unsafe_allow_html=True)
            if selected_presc.get("notes"):
                st.info(f"📝 {selected_presc['notes']}")

    # ── Main layout ────────────────────────────────────────────────────────
    left_col, right_col = st.columns([3, 2], gap="large")

    with left_col:
        st.markdown("### 📹 Live Feed")

        # Camera frame placeholder
        frame_ph = st.empty()

        # Control buttons
        btn_col1, btn_col2, btn_col3 = st.columns(3)
        with btn_col1:
            start_btn = st.button("▶ Start Tracking", use_container_width=True)
        with btn_col2:
            stop_btn  = st.button("⏹ Stop",           use_container_width=True)
        with btn_col3:
            log_btn   = st.button("💾 Log Session",    use_container_width=True)

        if start_btn:
            st.session_state.tracking_active    = True
            st.session_state.session_scores     = []
            st.session_state.session_roms       = []
            st.session_state.session_labels     = []
            st.session_state.session_reps       = 0
            st.session_state.rep_cooldown_until = 0.0   # reset cooldown
            # Create a fresh processor each session (fresh MediaPipe timestamps)
            st.session_state.pose_processor = _create_pose_processor()

        if stop_btn:
            st.session_state.tracking_active = False

        if log_btn and st.session_state.session_scores:
            peak_rom   = float(np.max(st.session_state.session_roms)) if st.session_state.session_roms else 0.0
            mean_score = float(np.mean(st.session_state.session_scores))
            exercise   = (
                max(set(st.session_state.session_labels), key=st.session_state.session_labels.count)
                if st.session_state.session_labels else "Unknown"
            )
            db.log_session(
                patient_id=st.session_state.patient_id,
                exercise=exercise,
                peak_rom=peak_rom,
                mean_score=mean_score,
                reps=st.session_state.session_reps,
            )
            st.success(f"✅ Session logged — {exercise}, score {mean_score:.1f}/100, ROM {peak_rom:.1f}°")

        # Buffer fill progress bar
        if st.session_state.tracking_active and st.session_state.pose_processor:
            processor = st.session_state.pose_processor
            st.progress(processor.get_buffer_fill(), text="Building temporal window…")

        # ── Live tracking loop ─────────────────────────────────────────────
        if st.session_state.tracking_active and st.session_state.pose_processor:
            checkpoint_file = "checkpoint_best.pt"
            path_to_load = checkpoint_file if os.path.exists(checkpoint_file) else None
            engine    = load_scoring_engine(checkpoint_path=path_to_load)
            processor = st.session_state.pose_processor
            cap = cv2.VideoCapture(0)

            if not cap.isOpened():
                st.error("⚠️ Webcam not accessible. Using synthetic demo mode.")
                _run_demo_mode(frame_ph, right_col, engine, processor)
                st.session_state.tracking_active = False
            else:
                try:
                    _run_webcam_loop(cap, frame_ph, right_col, engine, processor)
                finally:
                    cap.release()
        else:
            # Static placeholder frame
            placeholder_img = np.zeros((480, 640, 3), dtype=np.uint8)
            cv2.putText(placeholder_img, "Press  Start Tracking",
                        (120, 240), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)
            frame_ph.image(placeholder_img, channels="BGR", width="stretch")

    with right_col:
        _render_metrics_panel()

    # ── Exercise tutorial section ──────────────────────────────────────────
    _render_exercise_tutorials()


def _render_exercise_tutorials():
    """Renders exercise tutorial section with embedded YouTube videos and form tips."""

    # Tutorial styling
    st.markdown("""
    <style>
        .tutorial-section {
            margin-top: 2.5rem;
            padding-top: 1.5rem;
            border-top: 1px solid rgba(255, 255, 255, 0.08);
        }
        .tutorial-header {
            font-size: 2.2rem;
            font-family: 'Instrument Serif', serif !important;
            font-style: italic !important;
            color: #ffffff;
            margin-bottom: 0.3rem;
        }
        .tutorial-subheader {
            font-size: 0.95rem;
            color: rgba(255, 255, 255, 0.65);
            margin-bottom: 1.5rem;
        }
        .tutorial-card {
            background: rgba(255, 255, 255, 0.01);
            backdrop-filter: blur(4px);
            -webkit-backdrop-filter: blur(4px);
            border: none;
            box-shadow: inset 0 1px 1px rgba(255, 255, 255, 0.1);
            position: relative;
            overflow: hidden;
            border-radius: 1.25rem;
            padding: 1.2rem;
            margin-bottom: 0.8rem;
            transition: all 0.3s ease;
        }
        .tutorial-card::before {
            content: "";
            position: absolute; inset: 0;
            border-radius: inherit;
            padding: 1.4px;
            background: linear-gradient(180deg,
              rgba(255, 255, 255, 0.45) 0%,
              rgba(255, 255, 255, 0.15) 20%,
              rgba(255, 255, 255, 0) 40%,
              rgba(255, 255, 255, 0) 60%,
              rgba(255, 255, 255, 0.15) 80%,
              rgba(255, 255, 255, 0.45) 100%);
            -webkit-mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
            -webkit-mask-composite: xor;
            mask-composite: exclude;
            pointer-events: none;
        }
        .tutorial-card:hover {
            background: rgba(255, 255, 255, 0.03);
        }
        .exercise-name {
            font-size: 1.4rem;
            font-family: 'Instrument Serif', serif !important;
            font-style: italic !important;
            color: #ffffff;
            margin-bottom: 0.5rem;
        }
        .exercise-name span {
            display: inline-block;
            color: #ffffff;
            text-shadow: 0 0 8px rgba(255,255,255,0.4);
        }
        .form-tips {
            font-size: 0.82rem;
            color: rgba(255, 255, 255, 0.7);
            line-height: 1.65;
            margin-top: 0.6rem;
        }
        .form-tips strong {
            color: #ffffff;
        }
        .muscle-tag {
            display: inline-block;
            background: rgba(255, 255, 255, 0.05);
            color: #ffffff;
            border: 1px solid rgba(255, 255, 255, 0.2);
            border-radius: 20px;
            padding: 2px 10px;
            font-size: 0.72rem;
            font-weight: 500;
            margin-right: 4px;
            margin-top: 6px;
        }
    </style>

    <div class='tutorial-section'>
        <div class='tutorial-header'>📖 Exercise Tutorials</div>
        <div class='tutorial-subheader'>
            Watch these videos to learn proper form before starting your session
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Exercise tutorial data
    tutorials = [
        {
            "name": "Squat",
            "icon": "🏋️",
            "video_id": "YaXPRqUwItQ",
            "tips": [
                "Stand with feet shoulder-width apart, toes slightly out",
                "Hinge at hips first — push them back like sitting into a chair",
                "Keep knees aligned over toes, don't let them cave inward",
                "Maintain a neutral spine with chest lifted throughout",
                "Squat only to a pain-free depth; increase gradually",
            ],
            "muscles": ["Quadriceps", "Glutes", "Hamstrings", "Core"],
        },
        {
            "name": "Arm Cross",
            "icon": "💪",
            "video_id": "-1K0m5ywRcY",
            "tips": [
                "Stand tall, extend arms to sides at shoulder height (T position)",
                "Sweep arms forward across your body, crossing one over the other",
                "Alternate which arm is on top with each repetition",
                "Keep shoulders down — avoid shrugging toward ears",
                "Use smooth, controlled motion; avoid jerky swings",
            ],
            "muscles": ["Shoulders", "Chest", "Upper Back", "Deltoids"],
        },
        {
            "name": "Body Twist",
            "icon": "🔄",
            "video_id": "f4Qah0bQTIo",
            "tips": [
                "Stand with feet shoulder-width apart, knees slightly bent",
                "Raise arms to chest height with elbows bent at 90 degrees",
                "Initiate the twist from your core, not your arms",
                "Allow the back foot to pivot naturally to protect knees",
                "Move in a controlled, rhythmic manner — avoid swinging",
            ],
            "muscles": ["Obliques", "Core", "Lower Back", "Hip Flexors"],
        },
        {
            "name": "Step Jack",
            "icon": "⭐",
            "video_id": "JHdVMkRBuRA",
            "tips": [
                "Stand tall with feet together and arms at your sides",
                "Step right foot out while raising arms overhead",
                "Return to start, then repeat with left foot",
                "Maintain an engaged core for stability and balance",
                "Low-impact alternative to jumping jacks — gentle on joints",
            ],
            "muscles": ["Full Body", "Calves", "Shoulders", "Cardio"],
        },
    ]

    # Render 2 tutorials per row
    for i in range(0, len(tutorials), 2):
        cols = st.columns(2, gap="large")
        for j, col in enumerate(cols):
            if i + j < len(tutorials):
                tut = tutorials[i + j]
                with col:
                    st.markdown(f"""
                    <div class='tutorial-card'>
                        <div class='exercise-name'>{tut['icon']} <span>{tut['name']}</span></div>
                    </div>
                    """, unsafe_allow_html=True)

                    # Embed YouTube video
                    st.video(f"https://www.youtube.com/watch?v={tut['video_id']}")

                    # Form tips
                    tips_html = "".join(
                        f"<div style='margin-bottom:3px'>• {tip}</div>"
                        for tip in tut["tips"]
                    )
                    muscles_html = "".join(
                        f"<span class='muscle-tag'>{m}</span>"
                        for m in tut["muscles"]
                    )
                    st.markdown(f"""
                    <div class='form-tips'>
                        <strong>✅ Proper Form Tips</strong>
                        {tips_html}
                        <div style='margin-top:8px'>
                            <strong>🎯 Target Muscles</strong><br>
                            {muscles_html}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

def _run_webcam_loop(cap, frame_ph, right_col, engine, processor):
    """Single-threaded webcam capture + inference loop (runs until stop pressed)."""
    MAX_FRAMES = 300   # safety limit; user can restart

    for _ in range(MAX_FRAMES):
        if not st.session_state.tracking_active:
            break

        ret, frame = cap.read()
        if not ret:
            break

        annotated, feat_vec, window_ready, window_tensor = processor.process(frame)

        if feat_vec is not None:
            # Track raw angle for waveform chart (use left knee angle index 10)
            st.session_state.angle_history.append(float(feat_vec[10]))

        if window_ready and window_tensor is not None:
            probs_dict, label, score = engine.score(window_tensor)
            st.session_state.last_label = label
            st.session_state.last_score = score
            st.session_state.session_scores.append(score)
            st.session_state.session_roms.append(float(feat_vec[10]) if feat_vec is not None else 0.0)
            st.session_state.session_labels.append(label)
            for lbl in EXERCISE_LABELS:
                st.session_state.prob_history[lbl].append(probs_dict[lbl])

            # ── Rep counter with 5-second cooldown ────────────────────────
            # A rep is counted only when:
            #   1. Score crosses the 60 threshold (low→high)
            #   2. The cooldown has fully expired since the last counted rep
            now = time.monotonic()
            cooldown_remaining = max(0.0, st.session_state.rep_cooldown_until - now)
            score_crossed_threshold = (
                len(st.session_state.session_scores) >= 2
                and st.session_state.session_scores[-2] < 60 <= score
            )
            if score_crossed_threshold and cooldown_remaining == 0.0:
                st.session_state.session_reps += 1
                st.session_state.rep_cooldown_until = (
                    now + st.session_state.rep_cooldown_secs
                )
                cooldown_remaining = st.session_state.rep_cooldown_secs  # for overlay

            # Overlay score on frame (shows cooldown timer when active)
            _draw_score_overlay(annotated, label, score, cooldown_remaining)

        frame_ph.image(annotated, channels="BGR", width="stretch")

        with right_col:
            _render_metrics_panel()

        time.sleep(0.03)  # ~30 fps cap


def _run_demo_mode(frame_ph, right_col, engine, processor):
    """
    Demo mode: generates synthetic joint-angle sequences to demonstrate
    the full pipeline when no webcam is available.
    """
    st.info("🤖 Demo mode — synthetic motion data.")
    t = 0
    for _ in range(150):
        if not st.session_state.tracking_active:
            break

        # Generate a plausible synthetic angle sequence (sinusoidal knee flex)
        angle_vec = np.ones(NUM_ANGLES, dtype=np.float32) * 90.0
        angle_vec[10] = 90 + 50 * np.sin(t * 0.3)  # left knee oscillation
        angle_vec[11] = 90 + 50 * np.sin(t * 0.3)  # right knee
        angle_vec[6]  = 80 + 30 * np.sin(t * 0.3)  # left hip
        angle_vec[7]  = 80 + 30 * np.sin(t * 0.3)  # right hip
        t += 1

        processor._buffer.append(angle_vec)
        st.session_state.angle_history.append(float(angle_vec[10]))

        if len(processor._buffer) == WINDOW_SIZE:
            window_tensor = np.stack(list(processor._buffer), axis=0)[np.newaxis].astype(np.float32)
            probs_dict, label, score = engine.score(window_tensor)
            st.session_state.last_label = label
            st.session_state.last_score = score
            st.session_state.session_scores.append(score)
            st.session_state.session_roms.append(float(angle_vec[10]))
            st.session_state.session_labels.append(label)
            for lbl in EXERCISE_LABELS:
                st.session_state.prob_history[lbl].append(probs_dict[lbl])

        # Synthetic video frame
        now_demo = time.monotonic()
        cooldown_remaining_demo = max(0.0, st.session_state.rep_cooldown_until - now_demo)
        demo_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        _draw_skeleton_stub(demo_frame, t)
        _draw_score_overlay(demo_frame, st.session_state.last_label, st.session_state.last_score, cooldown_remaining_demo)
        frame_ph.image(demo_frame, channels="BGR", width="stretch")

        with right_col:
            _render_metrics_panel()

        time.sleep(0.05)


def _draw_score_overlay(frame, label, score, cooldown_remaining: float = 0.0):
    """Burn label + score onto frame. Shows a cooldown bar when locked out."""
    h, w = frame.shape[:2]
    cv2.rectangle(frame, (0, 0), (360, 70), (15, 15, 15), -1)
    color = (255, 255, 255) if score >= 70 else (200, 200, 200) if score >= 40 else (128, 128, 128)
    cv2.putText(frame, f"{label}  {score:.0f}/100",
                (10, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.0, color, 2)

    if cooldown_remaining > 0.0:
        # Draw a shrinking cooldown bar below the score text
        bar_total_w = 340
        elapsed_frac = 1.0 - (cooldown_remaining / 5.0)   # 5 s = full cooldown
        filled_w = int(bar_total_w * elapsed_frac)
        cv2.rectangle(frame, (10, 50), (10 + bar_total_w, 62), (60, 60, 60), -1)
        cv2.rectangle(frame, (10, 50), (10 + filled_w,    62), (200, 200, 200), -1)
        cv2.putText(frame, f"cooldown {cooldown_remaining:.1f}s",
                    (10, 78), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (160, 160, 160), 1)


def _draw_skeleton_stub(frame, t):
    """Draws a rudimentary animated stick figure for demo mode."""
    cx, cy = 320, 240
    knee_y = cy + 60 + int(40 * np.sin(t * 0.3))
    joints = {
        "head":  (cx, cy - 110),
        "ls":    (cx - 60, cy - 60), "rs": (cx + 60, cy - 60),
        "lh":    (cx - 40, cy),      "rh": (cx + 40, cy),
        "lk":    (cx - 40, knee_y),  "rk": (cx + 40, knee_y),
        "la":    (cx - 40, knee_y + 60), "ra": (cx + 40, knee_y + 60),
    }
    bones = [("head","ls"),("head","rs"),("ls","lh"),("rs","rh"),
             ("lh","rh"),("lh","lk"),("rh","rk"),("lk","la"),("rk","ra")]
    for a, b in bones:
        cv2.line(frame, joints[a], joints[b], (240, 240, 240), 2)
    for pt in joints.values():
        cv2.circle(frame, pt, 5, (180, 180, 180), -1)


def _render_metrics_panel():
    """Right column: score ring, live charts."""
    score = st.session_state.last_score
    label = st.session_state.last_label

    ring_class = "score-high" if score >= 70 else "score-mid" if score >= 40 else "score-low"
    st.markdown(f"""
    <div class='score-ring {ring_class}'>{score:.0f}</div>
    <p style='text-align:center;color:rgba(255,255,255,0.65);margin-top:6px;font-size:0.85rem'>
        Accuracy Score
    </p>
    """, unsafe_allow_html=True)

    m1, m2 = st.columns(2)
    with m1:
        reps = st.session_state.session_reps
        st.markdown(f"""
        <div class='metric-card'>
            <div class='metric-label'>Reps</div>
            <div class='metric-value'>{reps}</div>
        </div>""", unsafe_allow_html=True)
    with m2:
        mean_s = (np.mean(st.session_state.session_scores)
                  if st.session_state.session_scores else 0.0)
        st.markdown(f"""
        <div class='metric-card'>
            <div class='metric-label'>Session Avg</div>
            <div class='metric-value'>{mean_s:.0f}</div>
        </div>""", unsafe_allow_html=True)

    # ── Cooldown indicator ─────────────────────────────────────────────────
    now = time.monotonic()
    cooldown_remaining = max(0.0, st.session_state.get("rep_cooldown_until", 0.0) - now)
    if cooldown_remaining > 0.0:
        cooldown_pct = int((1.0 - cooldown_remaining / st.session_state.rep_cooldown_secs) * 100)
        st.markdown(f"""
        <div style='text-align:center;margin-bottom:0.4rem'>
            <span style='font-size:0.75rem;color:rgba(255,255,255,0.5);
                         text-transform:uppercase;letter-spacing:0.08em'>
                ⏳ Rep cooldown — {cooldown_remaining:.1f}s
            </span>
        </div>""", unsafe_allow_html=True)
        st.progress(cooldown_pct, text="")
    else:
        st.markdown("""
        <div style='text-align:center;margin-bottom:0.4rem'>
            <span style='font-size:0.75rem;color:rgba(100,220,100,0.8);
                         text-transform:uppercase;letter-spacing:0.08em'>
                ✅ Ready to count
            </span>
        </div>""", unsafe_allow_html=True)

    st.markdown("#### Exercise Probabilities")
    # Build live bar chart from latest prob history
    if st.session_state.prob_history[EXERCISE_LABELS[0]]:
        bar_data = {
            lbl: list(st.session_state.prob_history[lbl])[-1]
            for lbl in EXERCISE_LABELS
        }
        bar_df = pd.DataFrame({
            "Exercise": list(bar_data.keys()),
            "Probability (%)": list(bar_data.values()),
        }).set_index("Exercise")
        st.bar_chart(bar_df, color="#ffffff", height=200)

    st.markdown("#### Joint Angle Waveform (Left Knee)")
    if st.session_state.angle_history:
        waveform_df = pd.DataFrame(
            {"Angle (°)": list(st.session_state.angle_history)}
        )
        st.line_chart(waveform_df, color="#b0b0b0", height=180)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — DOCTOR INTERFACE
# ══════════════════════════════════════════════════════════════════════════════

def render_doctor_tab():
    st.markdown("## 🩺 Clinical Dashboard")

    patients = db.get_all_patients()
    if not patients:
        st.info("No patients currently registered in the database.")
        with st.expander("➕ Register First Patient"):
            with st.form("patient_form_empty"):
                p1, p2, p3 = st.columns(3)
                with p1:
                    new_name = st.text_input("Full Name")
                with p2:
                    new_age = st.number_input("Age", min_value=5, max_value=100, value=30)
                with p3:
                    new_cond = st.text_input("Diagnosis / Condition")
                if st.form_submit_button("Register Patient"):
                    if new_name:
                        db.add_patient(new_name, new_age, new_cond)
                        st.success(f"Patient '{new_name}' registered.")
                        st.rerun()
        return

    with st.sidebar:
        st.markdown("### 🏥 Patient Directory")
        selected_name = st.radio(
            "Select Patient",
            [p["name"] for p in patients],
            label_visibility="collapsed",
        )

    patient = next(p for p in patients if p["name"] == selected_name)
    pid = patient["id"]

    # ── Patient header ─────────────────────────────────────────────────────
    st.markdown(f"""
    <h3 style='margin-bottom:0'>{patient['name']}</h3>
    <p style='color:#6b7fa3;margin-top:2px'>Age {patient['age']} · {patient['condition']}</p>
    """, unsafe_allow_html=True)

    sessions = db.get_sessions(pid)
    dates_rom,  values_rom   = db.get_rom_trend(pid)
    dates_score, values_score = db.get_score_trend(pid)

    # ── KPI row ────────────────────────────────────────────────────────────
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    with kpi1:
        st.markdown(f"""
        <div class='metric-card'>
            <div class='metric-label'>Total Sessions</div>
            <div class='metric-value'>{len(sessions)}</div>
        </div>""", unsafe_allow_html=True)
    with kpi2:
        avg_score = np.mean(values_score) if values_score else 0
        st.markdown(f"""
        <div class='metric-card'>
            <div class='metric-label'>Avg Accuracy</div>
            <div class='metric-value'>{avg_score:.1f}</div>
        </div>""", unsafe_allow_html=True)
    with kpi3:
        peak = max(values_rom) if values_rom else 0
        st.markdown(f"""
        <div class='metric-card'>
            <div class='metric-label'>Peak ROM</div>
            <div class='metric-value'>{peak:.1f}°</div>
        </div>""", unsafe_allow_html=True)
    with kpi4:
        last_date = sessions[0]["session_date"][:10] if sessions else "—"
        st.markdown(f"""
        <div class='metric-card'>
            <div class='metric-label'>Last Session</div>
            <div class='metric-value' style='font-size:1.1rem'>{last_date}</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("")

    # ── Charts ─────────────────────────────────────────────────────────────
    chart_left, chart_right = st.columns(2, gap="large")

    with chart_left:
        st.markdown("#### 📐 Range of Motion Progress")
        if dates_rom:
            rom_df = pd.DataFrame({"Date": dates_rom, "ROM (°)": values_rom}).set_index("Date")
            st.line_chart(rom_df, color="#ffffff", height=250)
        else:
            st.info("No session data yet.")

    with chart_right:
        st.markdown("#### 🎯 Session Accuracy Trend")
        if dates_score:
            score_df = pd.DataFrame({"Date": dates_score, "Score": values_score}).set_index("Date")
            st.line_chart(score_df, color="#b0b0b0", height=250)
        else:
            st.info("No session data yet.")

    # ── Sessions table ─────────────────────────────────────────────────────
    st.markdown("#### 📋 Session History")
    if sessions:
        df = pd.DataFrame(sessions)[["session_date", "exercise", "peak_rom", "mean_score", "reps"]]
        df.columns = ["Date", "Exercise", "Peak ROM (°)", "Score", "Reps"]
        df["Date"] = df["Date"].str[:16]
        st.dataframe(df, width="stretch", height=220)
    else:
        st.info("No sessions logged for this patient.")

    # ── Prescription management ────────────────────────────────────────────
    st.markdown("---")
    st.markdown("#### ➕ Update Prescription")

    prescriptions = db.get_prescriptions(pid)
    if prescriptions:
        presc_df = pd.DataFrame(prescriptions)[["exercise", "target_reps", "target_rom", "notes", "assigned_at"]]
        presc_df.columns = ["Exercise", "Target Reps", "Target ROM", "Notes", "Assigned"]
        presc_df["Assigned"] = presc_df["Assigned"].str[:10]
        st.dataframe(presc_df, width="stretch", height=160)

    with st.expander("📝 Add New Prescription"):
        with st.form("presc_form"):
            f1, f2 = st.columns(2)
            with f1:
                ex = st.selectbox("Exercise", EXERCISE_LABELS)
                reps = st.number_input("Target Reps", min_value=1, max_value=50, value=10)
            with f2:
                rom = st.number_input("Target ROM (°)", min_value=10.0, max_value=180.0, value=90.0)
                notes = st.text_input("Clinical Notes")
            submitted = st.form_submit_button("Assign Protocol")
            if submitted:
                db.add_prescription(pid, ex, reps, rom, notes)
                st.success(f"✅ Protocol '{ex}' assigned to {patient['name']}")
                st.rerun()

    # ── Add new patient ────────────────────────────────────────────────────
    with st.expander("➕ Register New Patient"):
        with st.form("patient_form"):
            p1, p2, p3 = st.columns(3)
            with p1:
                new_name = st.text_input("Full Name")
            with p2:
                new_age = st.number_input("Age", min_value=5, max_value=100, value=30)
            with p3:
                new_cond = st.text_input("Diagnosis / Condition")
            if st.form_submit_button("Register Patient"):
                if new_name:
                    db.add_patient(new_name, new_age, new_cond)
                    st.success(f"Patient '{new_name}' registered.")
                    st.rerun()

    # ── Remove Patient Profile (Danger Zone) ───────────────────────────────
    with st.expander("⚠️ Danger Zone"):
        st.write(f"Are you sure you want to permanently delete patient profile: **{patient['name']}**?")
        st.write("This will delete all their historical session records and prescriptions. This action cannot be undone.")
        if st.button("Confirm: Delete Patient Profile", type="primary"):
            db.delete_patient(pid)
            st.success(f"Successfully deleted {patient['name']}.")
            st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# ROLE SELECTION — Landing page
# ══════════════════════════════════════════════════════════════════════════════

def render_role_selection():
    """Full-screen role selection landing page."""
    st.markdown("""
    <div class='role-landing'>
        <div>
            <span style='font-size:3.5rem'>🦴</span>
        </div>
        <div class='role-title'>RehabTrack <span>AI</span></div>
        <div class='role-subtitle'>
            AI-powered telerehabilitation with real-time pose tracking
            and clinical analytics
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Role selection cards
    spacer_l, col_patient, col_doctor, spacer_r = st.columns([1, 2, 2, 1], gap="large")

    with col_patient:
        st.markdown("""
        <div class='role-card'>
            <div class='role-icon'>🏃</div>
            <div class='role-name'>Patient</div>
            <div class='role-desc'>
                Start your exercise session with<br>
                live webcam pose tracking &amp; scoring
            </div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Enter as Patient", use_container_width=True, key="btn_patient"):
            st.session_state.user_role = "patient"
            st.rerun()

    with col_doctor:
        st.markdown("""
        <div class='role-card'>
            <div class='role-icon'>🩺</div>
            <div class='role-name'>Doctor</div>
            <div class='role-desc'>
                View patient analytics, session<br>
                history &amp; manage prescriptions
            </div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Enter as Doctor", use_container_width=True, key="btn_doctor"):
            st.session_state.user_role = "doctor"
            st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# MAIN — Role-based routing
# ══════════════════════════════════════════════════════════════════════════════

def _render_header():
    """Top header bar with logo and switch-role button."""
    st.markdown("""
    <div style='display:flex;align-items:center;gap:12px;margin-bottom:0.5rem'>
        <span style='font-size:2rem'>🦴</span>
        <span style='font-size:2rem;font-family:"Instrument Serif", serif;font-style:italic;color:#ffffff;letter-spacing:-0.02em'>
            RehabTrack <span style='text-shadow: 0 0 8px rgba(255,255,255,0.4)'>AI</span>
        </span>
        <span style='margin-left:auto;font-size:0.8rem;color:rgba(255,255,255,0.6);font-family:"Barlow",sans-serif'>
            Telerehabilitation · LSTM Motion Analysis
        </span>
    </div>
    """, unsafe_allow_html=True)


def main():
    role = st.session_state.get("user_role")

    if role is None:
        # Show landing page
        render_role_selection()
    else:
        _render_header()

        # Switch role button in sidebar
        with st.sidebar:
            st.markdown("---")
            if st.button("🔄 Switch Role", use_container_width=True):
                st.session_state.user_role = None
                st.session_state.tracking_active = False
                st.rerun()

        if role == "patient":
            render_patient_tab()
        elif role == "doctor":
            render_doctor_tab()


if __name__ == "__main__":
    main()
