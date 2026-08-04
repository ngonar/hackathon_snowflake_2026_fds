import os
import sqlite3
from dotenv import load_dotenv

load_dotenv()

REMIT_DB_PATH = os.getenv("REMIT_DB_PATH")

def _get_connection():
    conn = sqlite3.connect(REMIT_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def get_sender_profile(sender_id: int) -> dict:
    """Retrieves user profile details from the main database."""
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (sender_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return dict(row)
    return {}

def get_recipient_profile(recipient_id: int) -> dict:
    """Retrieves recipient details from the main database."""
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM recipients WHERE id = ?", (recipient_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return dict(row)
    return {}

def get_sender_transaction_history(sender_id: int) -> list[dict]:
    """Retrieves transaction history for a sender from the main database."""
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT t.*, r.name as recipient_name 
        FROM transactions t
        LEFT JOIN recipients r ON t.recipient_id = r.id
        WHERE t.sender_id = ? 
        ORDER BY t.created_at DESC
    """, (sender_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_recipient_transaction_history(recipient_id: int) -> list[dict]:
    """Retrieves transaction history for a recipient from the main database."""
    conn = _get_connection()
    cursor = conn.cursor()
    # Note: recipients are linked to transactions via recipient_id
    cursor.execute("""
        SELECT t.*, u.full_name as sender_name 
        FROM transactions t
        LEFT JOIN users u ON t.sender_id = u.id
        WHERE t.recipient_id = ? 
        ORDER BY t.created_at DESC
    """, (recipient_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def enrich_transaction(txn_data: dict) -> dict:
    """Enriches the transaction details with sender, recipient, and transaction history."""
    sender_id = txn_data.get("sender_id")
    recipient_id = txn_data.get("recipient_id")
    
    sender_profile = get_sender_profile(sender_id) if sender_id else {}
    recipient_profile = get_recipient_profile(recipient_id) if recipient_id else {}
    
    sender_history = get_sender_transaction_history(sender_id) if sender_id else []
    recipient_history = get_recipient_transaction_history(recipient_id) if recipient_id else []
    
    # We remove hashed_password from user profile to prevent sending it to the LLM (security best practice)
    if sender_profile:
        sender_profile.pop("hashed_password", None)
        
    enriched_data = {
        "transaction": txn_data,
        "sender": sender_profile,
        "recipient": recipient_profile,
        "sender_history": sender_history,
        "recipient_history": recipient_history
    }
    return enriched_data
