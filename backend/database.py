"""
database.py — SQLite persistence layer for the Telerehabilitation Tracker.

Tables
------
patients        : registered patient records
sessions        : logged exercise session summaries
prescriptions   : clinician-assigned exercise protocols
"""

import sqlite3
import os
from datetime import datetime
from typing import List, Dict, Optional, Tuple

DB_PATH = os.environ.get("REHAB_DB_PATH", "rehab_system.db")

# Ensure parent directory of DB_PATH exists if a directory path is provided
db_dir = os.path.dirname(DB_PATH)
if db_dir:
    os.makedirs(db_dir, exist_ok=True)


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn


def initialise_db() -> None:
    """Create all tables if they don't exist and seed demo data."""
    with get_connection() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS patients (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT    NOT NULL,
            age         INTEGER,
            condition   TEXT,
            password    TEXT    DEFAULT 'password',
            created_at  TEXT    DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS doctors (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT    NOT NULL,
            password    TEXT    NOT NULL,
            specialty   TEXT,
            created_at  TEXT    DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS prescriptions (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id  INTEGER REFERENCES patients(id),
            exercise    TEXT    NOT NULL,
            target_reps INTEGER DEFAULT 10,
            target_rom  REAL    DEFAULT 90.0,
            notes       TEXT,
            assigned_at TEXT    DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS sessions (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id   INTEGER REFERENCES patients(id),
            exercise     TEXT    NOT NULL,
            peak_rom     REAL,
            mean_score   REAL,
            reps         INTEGER DEFAULT 0,
            session_date TEXT    DEFAULT (datetime('now'))
        );
        """)

        # Migration: Check and add password column to patients if not present
        cursor = conn.execute("PRAGMA table_info(patients)")
        columns = [row['name'] for row in cursor.fetchall()]
        if 'password' not in columns:
            conn.execute("ALTER TABLE patients ADD COLUMN password TEXT DEFAULT 'password';")

        # Seed demo patients only if table is empty
        count = conn.execute("SELECT COUNT(*) FROM patients").fetchone()[0]
        if count == 0:
            demo_patients = [
                ("Arjun Sharma",   42, "Knee osteoarthritis", "password"),
                ("Priya Nair",     35, "Post-ACL reconstruction", "password"),
                ("Ramesh Iyer",    58, "Lower-back rehabilitation", "password"),
                ("Deepa Menon",    29, "Shoulder impingement", "password"),
            ]
            conn.executemany(
                "INSERT INTO patients (name, age, condition, password) VALUES (?,?,?,?)",
                demo_patients,
            )

            # Seed prescriptions
            presc = [
                (1, "Squat",       12, 80.0,  "Start shallow, 3 sets"),
                (1, "Step Jack",   15, 70.0,  "Low impact"),
                (2, "Squat",       10, 90.0,  "Full depth if comfortable"),
                (3, "Body Twist",  12, 60.0,  "Keep hips fixed"),
                (4, "Arm Cross",   15, 120.0, "Full shoulder flexion"),
            ]
            conn.executemany(
                "INSERT INTO prescriptions (patient_id,exercise,target_reps,target_rom,notes) VALUES (?,?,?,?,?)",
                presc,
            )

            # Seed historical sessions (8 weeks × 2 exercises × 2 patients)
            import random
            random.seed(0)
            for week in range(1, 9):
                for day in range(1, 4):
                    date_str = f"2024-{week:02d}-{day * 6:02d} 10:00:00"
                    for pid, ex in [(1, "Squat"), (2, "Squat"), (3, "Body Twist"), (4, "Arm Cross")]:
                        conn.execute(
                            "INSERT INTO sessions (patient_id,exercise,peak_rom,mean_score,reps,session_date) VALUES (?,?,?,?,?,?)",
                            (
                                pid, ex,
                                round(45 + week * 4 + random.uniform(-3, 3), 1),
                                round(40 + week * 5 + random.uniform(-5, 5), 1),
                                random.randint(8, 15),
                                date_str,
                            ),
                        )

        # Seed demo doctors only if table is empty
        doc_count = conn.execute("SELECT COUNT(*) FROM doctors").fetchone()[0]
        if doc_count == 0:
            demo_doctors = [
                ("Dr. Sarah Jenkins", "password", "Orthopedic Specialist"),
                ("Dr. Amit Patel",    "password", "Physical Therapist"),
            ]
            conn.executemany(
                "INSERT INTO doctors (name, password, specialty) VALUES (?,?,?)",
                demo_doctors,
            )

        conn.commit()


# ── Patient CRUD ──────────────────────────────────────────────────────────────

def get_all_patients() -> List[Dict]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT id, name, age, condition FROM patients ORDER BY name"
        ).fetchall()
    return [dict(r) for r in rows]


def get_patient(patient_id: int) -> Optional[Dict]:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM patients WHERE id=?", (patient_id,)
        ).fetchone()
    return dict(row) if row else None


def add_patient(name: str, age: int, condition: str, password: str = "password") -> int:
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO patients (name, age, condition, password) VALUES (?,?,?,?)",
            (name, age, condition, password),
        )
        conn.commit()
    return cur.lastrowid


def delete_patient(patient_id: int) -> None:
    with get_connection() as conn:
        conn.execute("DELETE FROM prescriptions WHERE patient_id=?", (patient_id,))
        conn.execute("DELETE FROM sessions WHERE patient_id=?", (patient_id,))
        conn.execute("DELETE FROM patients WHERE id=?", (patient_id,))
        conn.commit()


def authenticate_patient(name: str, password: str) -> Optional[Dict]:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id, name, age, condition FROM patients WHERE name=? AND password=?",
            (name, password)
        ).fetchone()
    return dict(row) if row else None


def authenticate_doctor(name: str, password: str) -> Optional[Dict]:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id, name, specialty FROM doctors WHERE name=? AND password=?",
            (name, password)
        ).fetchone()
    return dict(row) if row else None


def add_doctor(name: str, password: str, specialty: str) -> int:
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO doctors (name, password, specialty) VALUES (?,?,?)",
            (name, password, specialty),
        )
        conn.commit()
    return cur.lastrowid


# ── Prescription CRUD ─────────────────────────────────────────────────────────

def get_prescriptions(patient_id: int) -> List[Dict]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM prescriptions WHERE patient_id=? ORDER BY assigned_at DESC",
            (patient_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def add_prescription(
    patient_id: int,
    exercise: str,
    target_reps: int,
    target_rom: float,
    notes: str,
) -> int:
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO prescriptions (patient_id,exercise,target_reps,target_rom,notes) VALUES (?,?,?,?,?)",
            (patient_id, exercise, target_reps, target_rom, notes),
        )
        conn.commit()
    return cur.lastrowid


# ── Session logging ───────────────────────────────────────────────────────────

def log_session(
    patient_id: int,
    exercise: str,
    peak_rom: float,
    mean_score: float,
    reps: int,
) -> int:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO sessions (patient_id,exercise,peak_rom,mean_score,reps,session_date) VALUES (?,?,?,?,?,?)",
            (patient_id, exercise, round(peak_rom, 2), round(mean_score, 2), reps, now),
        )
        conn.commit()
    return cur.lastrowid


def get_sessions(patient_id: int, limit: int = 200) -> List[Dict]:
    with get_connection() as conn:
        rows = conn.execute(
            """SELECT * FROM sessions WHERE patient_id=?
               ORDER BY session_date DESC LIMIT ?""",
            (patient_id, limit),
        ).fetchall()
    return [dict(r) for r in rows]


def get_rom_trend(patient_id: int) -> Tuple[List[str], List[float]]:
    """Returns (dates, peak_rom_values) for sparkline charts."""
    rows = get_sessions(patient_id)
    rows.reverse()  # oldest first
    dates  = [r["session_date"][:10] for r in rows]
    values = [r["peak_rom"] for r in rows]
    return dates, values


def get_score_trend(patient_id: int) -> Tuple[List[str], List[float]]:
    """Returns (dates, mean_score_values) for accuracy trend chart."""
    rows = get_sessions(patient_id)
    rows.reverse()
    dates  = [r["session_date"][:10] for r in rows]
    values = [r["mean_score"] for r in rows]
    return dates, values
