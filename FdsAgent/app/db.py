import os
import sqlite3
import datetime
from dotenv import load_dotenv

load_dotenv()

FDS_DB_PATH = os.getenv("FDS_DB_PATH", "fds.db")

def init_db():
    """Initializes the SQLite database and creates the necessary tables."""
    conn = sqlite3.connect(FDS_DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transactions_analysis (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            txn_id INTEGER,
            reference_number TEXT,
            sender_id INTEGER,
            recipient_id INTEGER,
            source_currency TEXT,
            target_currency TEXT,
            source_amount REAL,
            target_amount REAL,
            exchange_rate REAL,
            fee REAL,
            status TEXT,
            is_fraud INTEGER, -- 0 or 1
            fraud_type TEXT,
            explanation TEXT,
            decision TEXT, -- FAILED, SUSPICIOUS, or FUNDED
            anomaly_score REAL,
            velocity_flags TEXT,
            evidence TEXT,
            analyzed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    # Run migration in case columns don't exist yet
    for col, col_type in [
        ("anomaly_score", "REAL"),
        ("velocity_flags", "TEXT"),
        ("evidence", "TEXT"),
    ]:
        try:
            cursor.execute(f"ALTER TABLE transactions_analysis ADD COLUMN {col} {col_type}")
        except Exception:
            pass
    conn.commit()
    conn.close()

def save_analysis(
    txn_id: int,
    reference_number: str,
    sender_id: int,
    recipient_id: int,
    source_currency: str,
    target_currency: str,
    source_amount: float,
    target_amount: float,
    exchange_rate: float,
    fee: float,
    status: str,
    is_fraud: bool,
    fraud_type: str,
    explanation: str,
    decision: str,
    anomaly_score: float = 0.0,
    velocity_flags: str = "[]",
    evidence: str = "[]"
):
    """Saves a transaction analysis record into the database."""
    conn = sqlite3.connect(FDS_DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO transactions_analysis (
            txn_id, reference_number, sender_id, recipient_id,
            source_currency, target_currency, source_amount, target_amount,
            exchange_rate, fee, status, is_fraud, fraud_type, explanation,
            decision, anomaly_score, velocity_flags, evidence, analyzed_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        txn_id, reference_number, sender_id, recipient_id,
        source_currency, target_currency, source_amount, target_amount,
        exchange_rate, fee, status, 1 if is_fraud else 0, fraud_type, explanation,
        decision, anomaly_score, velocity_flags, evidence, datetime.datetime.now().isoformat()
    ))
    conn.commit()
    conn.close()
