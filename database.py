import sqlite3
import hashlib
from datetime import datetime

DB_NAME = "school_fees.db"


def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def init_db():
    conn = get_connection()
    cur = conn.cursor()

    # 1. Users & Roles (Admin vs Bursar)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            full_name TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('ADMIN', 'BURSAR')),
            password_hash TEXT NOT NULL,
            is_active INTEGER DEFAULT 1
        )
    """)

    # 2. Admin-Customizable School Settings
    cur.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    """)

    # 3. Students (Secondary School Specific: S1-S6, Day/Boarding, Science/Arts)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_code TEXT UNIQUE NOT NULL,
            full_name TEXT NOT NULL,
            class_level TEXT NOT NULL,          -- S1, S2, S3, S4, S5, S6, ALUMNI
            stream TEXT DEFAULT 'A',
            residence TEXT NOT NULL CHECK(residence IN ('DAY', 'BOARDING')),
            track TEXT NOT NULL CHECK(track IN ('GENERAL', 'SCIENCE', 'ARTS')),
            guardian_name TEXT,
            guardian_phone TEXT,
            bursary_discount REAL DEFAULT 0.0,
            carried_forward_balance REAL DEFAULT 0.0,
            status TEXT DEFAULT 'ACTIVE' CHECK(status IN ('ACTIVE', 'ALUMNI', 'SUSPENDED'))
        )
    """)

    # 4. Fee Structures per Class, Residence, Track & Term
    cur.execute("""
        CREATE TABLE IF NOT EXISTS fee_structures (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            academic_year TEXT NOT NULL,
            term TEXT NOT NULL,
            class_level TEXT NOT NULL,
            residence TEXT NOT NULL,
            track TEXT NOT NULL,
            fee_item TEXT NOT NULL,             -- Tuition, Boarding, Lab, PTA, Uniform, Exams
            amount REAL NOT NULL
        )
    """)

    # 5. Payments & Receipts (Never deleted; only voided with reason)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            receipt_no TEXT UNIQUE NOT NULL,
            student_id INTEGER NOT NULL,
            academic_year TEXT NOT NULL,
            term TEXT NOT NULL,
            amount_paid REAL NOT NULL,
            payment_method TEXT NOT NULL,       -- CASH, MOBILE_MONEY, BANK_AGENT, BANK_TRANSFER
            external_ref TEXT,                  -- MoMo ID or Bank Slip Ref
            payment_date TEXT NOT NULL,
            recorded_by TEXT NOT NULL,
            is_voided INTEGER DEFAULT 0,
            void_reason TEXT,
            FOREIGN KEY (student_id) REFERENCES students(id)
        )
    """)

    # 6. Tamper-Proof Audit Trail
    cur.execute("""
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            username TEXT NOT NULL,
            action TEXT NOT NULL,
            details TEXT NOT NULL
        )
    """)

    # Seed Default Admin & Bursar if empty
    cur.execute("SELECT COUNT(*) FROM users")
    if cur.fetchone()[0] == 0:
        cur.execute(
            "INSERT INTO users (username, full_name, role, password_hash) VALUES (?, ?, ?, ?)",
            ("admin", "Headteacher / System Admin", "ADMIN", hash_password("admin123")),
        )
        cur.execute(
            "INSERT INTO users (username, full_name, role, password_hash) VALUES (?, ?, ?, ?)",
            ("bursar", "School Bursar", "BURSAR", hash_password("bursar123")),
        )

    # Seed Default School Settings if empty
    default_settings = {
        "school_name": "ST. MARY'S SECONDARY SCHOOL",
        "school_motto": "Excellence Through Discipline & Hard Work",
        "school_address": "P.O. Box 124, Kampala, Uganda",
        "school_phone": "+256 700 000 000",
        "currency": "UGX",
        "current_year": "2026",
        "current_term": "Term 1",
        "clearance_threshold_percent": "75",
        "receipt_footer": "Fees once paid are non-refundable. Keep this receipt safely.",
    }
    for k, v in default_settings.items():
        cur.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (k, v))

    conn.commit()
    conn.close()


def log_audit(username: str, action: str, details: str):
    conn = get_connection()
    conn.execute(
        "INSERT INTO audit_logs (timestamp, username, action, details) VALUES (?, ?, ?, ?)",
        (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), username, action, details),
    )
    conn.commit()
    conn.close()
  
