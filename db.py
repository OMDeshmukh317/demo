import sqlite3
from datetime import datetime
import os

DB_DIR = "databases"
ANPR_DB = os.path.join(DB_DIR, "anpr.db")
PPE_DB = os.path.join(DB_DIR, "ppe.db")
AUTH_DB = os.path.join(DB_DIR, "auth.db")  
WATCHLIST_DB = os.path.join(DB_DIR, "vehicle_watchlist.db")

def init_databases():
    os.makedirs(DB_DIR, exist_ok=True)

    # ---------------- AUTH DATABASE ----------------
    conn = sqlite3.connect(AUTH_DB)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT
        )
    """)
    conn.commit()
    conn.close()

    create_default_admin()

    # ---------------- ANPR DATABASE ----------------
    conn = sqlite3.connect(ANPR_DB)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS anpr_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            track_id INTEGER,
            plate_number TEXT,
            vehicle_image TEXT,
            plate_image TEXT,
            timestamp TEXT,
            camera_id INTEGER
        )
    """)
    conn.commit()
    conn.close()

    # ---------------- PPE DATABASE ----------------
    conn = sqlite3.connect(PPE_DB)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS ppe_violations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            person_id INTEGER UNIQUE,
            violations TEXT,
            person_image TEXT,
            timestamp TEXT,
            camera_id INTEGER
        )
    """)
    conn.commit()
    conn.close()


# ---------------- DEFAULT USER ----------------
def create_default_admin():
    conn = sqlite3.connect(AUTH_DB)
    cur = conn.cursor()

    cur.execute("SELECT * FROM users WHERE username=?", ("admin",))
    if not cur.fetchone():
        cur.execute(
            "INSERT INTO users (username, password) VALUES (?, ?)",
            ("admin", "admin")
        )
        conn.commit()

    conn.close()


# ---------------- VERIFY LOGIN ----------------
def verify_user(username, password):
    conn = sqlite3.connect(AUTH_DB)
    cur = conn.cursor()

    cur.execute(
        "SELECT * FROM users WHERE username=? AND password=?",
        (username, password)
    )
    user = cur.fetchone()
    conn.close()

    return user is not None


# ---------------- ANPR INSERT ----------------
def insert_anpr_event(track_id, plate_number, vehicle_image, plate_image, camera_id):
    conn = sqlite3.connect(ANPR_DB)
    cursor = conn.cursor()

    timestamp = datetime.now().strftime("%d-%m-%Y %H:%M:%S")

    cursor.execute("""
        INSERT INTO anpr_events
        (track_id, plate_number, vehicle_image, plate_image, timestamp, camera_id)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (track_id, plate_number, vehicle_image, plate_image, timestamp, camera_id))

    conn.commit()
    conn.close()


# ---------------- PPE UPSERT ----------------
def upsert_ppe_violation(person_id, violation, person_image, camera_id=1):
    conn = sqlite3.connect(PPE_DB)
    cur = conn.cursor()

    timestamp = datetime.now().strftime("%d-%m-%Y %H:%M:%S")

    cur.execute("SELECT violations FROM ppe_violations WHERE person_id=?", (person_id,))
    row = cur.fetchone()

    if row:
        existing = set(row[0].split(", "))
        existing.add(violation)
        merged = ", ".join(sorted(existing))

        cur.execute("""
            UPDATE ppe_violations
            SET violations=?, timestamp=?
            WHERE person_id=?
        """, (merged, timestamp, person_id))
    else:
        cur.execute("""
            INSERT INTO ppe_violations 
            (person_id, violations, person_image, timestamp, camera_id)
            VALUES (?, ?, ?, ?, ?)
        """, (person_id, violation, person_image, timestamp, camera_id))

    conn.commit()
    conn.close()


# ---------------- FETCH FUNCTIONS ----------------
def get_all_anpr_events():
    conn = sqlite3.connect(ANPR_DB)
    cur = conn.cursor()
    cur.execute("SELECT * FROM anpr_events ORDER BY id DESC")
    rows = cur.fetchall()
    conn.close()
    return rows


def get_all_ppe_violations():
    conn = sqlite3.connect(PPE_DB)
    cur = conn.cursor()
    cur.execute("SELECT * FROM ppe_violations ORDER BY id DESC")
    rows = cur.fetchall()
    conn.close()
    return rows