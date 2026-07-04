import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
os.environ["PYTHONUTF8"] = "1"
import numpy as np
from flask import Flask, request, jsonify, send_from_directory
import database as db
from lstm_model import build_scoring_engine

# Initialize database schema and seeds
db.initialise_db()

app = Flask(__name__)

# Load PyTorch LSTM model
print("[Backend] Loading PyTorch LSTM Scoring Engine...")
checkpoint_file = "checkpoint_best.pt"
if os.path.exists(checkpoint_file):
    engine = build_scoring_engine(checkpoint_path=checkpoint_file)
    print(f"[Backend] Model loaded successfully from {checkpoint_file}.")
else:
    engine = build_scoring_engine(checkpoint_path=None)
    print("[Backend] Checkpoint not found. Loaded mock LSTM weights for demo mode.")

# Resolve the absolute path to the frontend/web directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WEB_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", "frontend", "web"))

# ── Serve Frontend ───────────────────────────────────────────────────────────

@app.route("/")
def serve_index():
    return send_from_directory(WEB_DIR, "index.html")

@app.route("/pose_landmarker.task")
def serve_pose_model():
    # Serve pose model from backend directory
    return send_from_directory(BASE_DIR, "pose_landmarker.task")

@app.route("/<path:path>")
def serve_static(path):
    # Serve static assets or JS component modules from the web folder
    if os.path.exists(os.path.join(WEB_DIR, path)):
        return send_from_directory(WEB_DIR, path)
    # Default fallback to index.html for React SPA routing
    return send_from_directory(WEB_DIR, "index.html")

# ── Authentication API ───────────────────────────────────────────────────────

@app.route("/api/auth/login", methods=["POST"])
def auth_login():
    try:
        data = request.json
        if not data:
            return jsonify({"error": "Missing JSON body"}), 400
        role = data.get("role")
        name = data.get("name")
        password = data.get("password")
        
        if not role or not name or not password:
            return jsonify({"error": "role, name, and password are required"}), 400
            
        if role == "patient":
            patient = db.authenticate_patient(name, password)
            if patient:
                return jsonify({"success": True, "user": {**patient, "role": "patient"}})
        elif role == "doctor":
            doctor = db.authenticate_doctor(name, password)
            if doctor:
                return jsonify({"success": True, "user": {**doctor, "role": "doctor"}})
                
        return jsonify({"error": "Invalid credentials"}), 401
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/doctors", methods=["POST"])
def register_doctor():
    try:
        data = request.json
        if not data:
            return jsonify({"error": "Missing JSON body"}), 400
        name = data.get("name")
        password = data.get("password")
        specialty = data.get("specialty", "")
        if not name or not password:
            return jsonify({"error": "Name and password are required"}), 400
        doc_id = db.add_doctor(name, password, specialty)
        return jsonify({"id": doc_id, "message": "Doctor registered successfully"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── Patients API ──────────────────────────────────────────────────────────────

@app.route("/api/patients", methods=["GET"])
def get_patients():
    try:
        patients = db.get_all_patients()
        return jsonify(patients)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/patients/<int:pid>", methods=["GET"])
def get_patient_by_id(pid):
    try:
        patient = db.get_patient(pid)
        if not patient:
            return jsonify({"error": "Patient not found"}), 404
        return jsonify(patient)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/patients/<int:pid>", methods=["DELETE"])
def remove_patient(pid):
    try:
        patient = db.get_patient(pid)
        if not patient:
            return jsonify({"error": "Patient not found"}), 404
        db.delete_patient(pid)
        return jsonify({"success": True, "message": "Patient removed successfully"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/patients", methods=["POST"])
def register_patient():
    try:
        data = request.json
        if not data:
            return jsonify({"error": "Missing JSON body"}), 400
        name = data.get("name")
        age = int(data.get("age", 30))
        condition = data.get("condition", "")
        password = data.get("password", "password")
        if not name:
            return jsonify({"error": "Name is required"}), 400
        pid = db.add_patient(name, age, condition, password)
        return jsonify({"id": pid, "message": "Patient registered successfully"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ── Prescriptions API ─────────────────────────────────────────────────────────

@app.route("/api/prescriptions/<int:pid>", methods=["GET"])
def get_patient_prescriptions(pid):
    try:
        presc = db.get_prescriptions(pid)
        return jsonify(presc)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/prescriptions", methods=["POST"])
def create_prescription():
    try:
        data = request.json
        if not data:
            return jsonify({"error": "Missing JSON body"}), 400
        pid = data.get("patient_id")
        exercise = data.get("exercise")
        reps = int(data.get("target_reps", 10))
        rom = float(data.get("target_rom", 90.0))
        notes = data.get("notes", "")
        if not pid or not exercise:
            return jsonify({"error": "patient_id and exercise are required"}), 400
        presc_id = db.add_prescription(pid, exercise, reps, rom, notes)
        return jsonify({"id": presc_id, "message": "Prescription assigned successfully"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ── Sessions API ──────────────────────────────────────────────────────────────

@app.route("/api/sessions/<int:pid>", methods=["GET"])
def get_patient_sessions(pid):
    try:
        sessions = db.get_sessions(pid)
        return jsonify(sessions)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/sessions", methods=["POST"])
def log_patient_session():
    try:
        data = request.json
        if not data:
            return jsonify({"error": "Missing JSON body"}), 400
        pid = data.get("patient_id")
        exercise = data.get("exercise")
        peak_rom = float(data.get("peak_rom", 0.0))
        mean_score = float(data.get("mean_score", 0.0))
        reps = int(data.get("reps", 0))
        if not pid or not exercise:
            return jsonify({"error": "patient_id and exercise are required"}), 400
        sess_id = db.log_session(pid, exercise, peak_rom, mean_score, reps)
        return jsonify({"id": sess_id, "message": "Session logged successfully"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/trends/<int:pid>", methods=["GET"])
def get_trends(pid):
    try:
        dates_rom, values_rom = db.get_rom_trend(pid)
        dates_score, values_score = db.get_score_trend(pid)
        return jsonify({
            "rom": {"dates": dates_rom, "values": values_rom},
            "score": {"dates": dates_score, "values": values_score}
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ── scoring API ───────────────────────────────────────────────────────────────

@app.route("/api/score", methods=["POST"])
def score_temporal_window():
    try:
        data = request.json
        if not data:
            return jsonify({"error": "Missing JSON body"}), 400
        window_list = data.get("window")
        if not window_list:
            return jsonify({"error": "No sliding window provided"}), 400
        
        # Convert to numpy array of float32
        window_np = np.array(window_list, dtype=np.float32)
        
        # Ensure shape is (1, 30, 16)
        if window_np.shape != (1, 30, 16):
            return jsonify({
                "error": f"Invalid shape {window_np.shape}, expected (1, 30, 16)"
            }), 400
            
        probs_dict, label, score = engine.score(window_np)
        return jsonify({
            "probs": probs_dict,
            "label": label,
            "score": score
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
