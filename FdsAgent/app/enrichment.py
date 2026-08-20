import os
import base64
import snowflake.connector
from cryptography.hazmat.primitives import serialization
from dotenv import load_dotenv

load_dotenv()


def _load_private_key():
    key_b64 = os.getenv("SNOWFLAKE_PRIVATE_KEY", "")
    key_bytes = base64.b64decode(key_b64)
    private_key = serialization.load_pem_private_key(key_bytes, password=None)
    return private_key.private_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )


def _get_connection():
    return snowflake.connector.connect(
        account=os.getenv("SNOWFLAKE_ACCOUNT"),
        user=os.getenv("SNOWFLAKE_USER"),
        private_key=_load_private_key(),
        warehouse=os.getenv("SNOWFLAKE_WAREHOUSE"),
        database=os.getenv("SNOWFLAKE_DATABASE", "SNOWFLAKE_LEARNING_DB"),
        schema=os.getenv("SNOWFLAKE_SCHEMA", "FDS"),
        role=os.getenv("SNOWFLAKE_ROLE"),
    )


def get_sender_profile(sender_id: int) -> dict:
    conn = _get_connection()
    cursor = conn.cursor(snowflake.connector.DictCursor)
    cursor.execute("SELECT * FROM USERS WHERE ID = %s", (sender_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else {}


def get_recipient_profile(recipient_id: int) -> dict:
    conn = _get_connection()
    cursor = conn.cursor(snowflake.connector.DictCursor)
    cursor.execute("SELECT * FROM RECIPIENTS WHERE ID = %s", (recipient_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else {}


def get_sender_transaction_history(sender_id: int) -> list[dict]:
    conn = _get_connection()
    cursor = conn.cursor(snowflake.connector.DictCursor)
    cursor.execute("""
        SELECT T.*, R.NAME as RECIPIENT_NAME
        FROM TRANSACTIONS T
        LEFT JOIN RECIPIENTS R ON T.RECIPIENT_ID = R.ID
        WHERE T.SENDER_ID = %s
        ORDER BY T.CREATED_AT DESC
        LIMIT 20
    """, (sender_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_recipient_transaction_history(recipient_id: int) -> list[dict]:
    conn = _get_connection()
    cursor = conn.cursor(snowflake.connector.DictCursor)
    cursor.execute("""
        SELECT T.*, U.FULL_NAME as SENDER_NAME
        FROM TRANSACTIONS T
        LEFT JOIN USERS U ON T.SENDER_ID = U.ID
        WHERE T.RECIPIENT_ID = %s
        ORDER BY T.CREATED_AT DESC
        LIMIT 20
    """, (recipient_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def enrich_transaction(txn_data: dict) -> dict:
    sender_id = txn_data.get("sender_id")
    recipient_id = txn_data.get("recipient_id")

    sender_profile = get_sender_profile(sender_id) if sender_id else {}
    recipient_profile = get_recipient_profile(recipient_id) if recipient_id else {}

    sender_history = get_sender_transaction_history(sender_id) if sender_id else []
    recipient_history = get_recipient_transaction_history(recipient_id) if recipient_id else []

    if sender_profile:
        sender_profile.pop("HASHED_PASSWORD", None)

    return {
        "transaction": txn_data,
        "sender": sender_profile,
        "recipient": recipient_profile,
        "sender_history": sender_history,
        "recipient_history": recipient_history
    }
