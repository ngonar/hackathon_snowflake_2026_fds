import os
import base64
import snowflake.connector
from cryptography.hazmat.primitives import serialization
from dotenv import load_dotenv

from app.skill_loader import get_sql

load_dotenv()


def _get_connection():
    token_path = "/snowflake/session/token"
    if os.path.exists(token_path):
        with open(token_path, "r") as f:
            token = f.read().strip()
        return snowflake.connector.connect(
            host=os.getenv("SNOWFLAKE_HOST"),
            account=os.getenv("SNOWFLAKE_ACCOUNT"),
            authenticator="oauth",
            token=token,
            warehouse=os.getenv("SNOWFLAKE_WAREHOUSE"),
            database=os.getenv("SNOWFLAKE_DATABASE", "SNOWFLAKE_LEARNING_DB"),
            schema=os.getenv("SNOWFLAKE_SCHEMA", "FDS"),
        )
    key_b64 = os.getenv("SNOWFLAKE_PRIVATE_KEY", "")
    if key_b64:
        key_bytes = base64.b64decode(key_b64)
        pk = serialization.load_pem_private_key(key_bytes, password=None)
        pk_der = pk.private_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
        return snowflake.connector.connect(
            account=os.getenv("SNOWFLAKE_ACCOUNT"),
            user=os.getenv("SNOWFLAKE_USER"),
            private_key=pk_der,
            warehouse=os.getenv("SNOWFLAKE_WAREHOUSE"),
            database=os.getenv("SNOWFLAKE_DATABASE", "SNOWFLAKE_LEARNING_DB"),
            schema=os.getenv("SNOWFLAKE_SCHEMA", "FDS"),
            role=os.getenv("SNOWFLAKE_ROLE"),
        )
    return snowflake.connector.connect(
        account=os.getenv("SNOWFLAKE_ACCOUNT"),
        user=os.getenv("SNOWFLAKE_USER"),
        password=os.getenv("SNOWFLAKE_PASSWORD"),
        warehouse=os.getenv("SNOWFLAKE_WAREHOUSE"),
        database=os.getenv("SNOWFLAKE_DATABASE", "SNOWFLAKE_LEARNING_DB"),
        schema=os.getenv("SNOWFLAKE_SCHEMA", "FDS"),
        role=os.getenv("SNOWFLAKE_ROLE"),
    )


def _execute_skill_query(script_key: str, params: dict) -> dict | None:
    """Execute a skill SQL template and return the first row as a dict."""
    sql = get_sql("fds-transaction-profiling", script_key)
    conn = _get_connection()
    try:
        cursor = conn.cursor(snowflake.connector.DictCursor)
        cursor.execute(sql, params)
        row = cursor.fetchone()
        return dict(row) if row else {}
    finally:
        conn.close()


def get_sender_profile(sender_id: int) -> dict:
    return _execute_skill_query("sender_profile.sql", {"sender_id": sender_id})


def get_sender_behavior(sender_id: int) -> dict:
    return _execute_skill_query("sender_behavior.sql", {"sender_id": sender_id})


def get_recipient_profile(recipient_id: int) -> dict:
    return _execute_skill_query("recipient_profile.sql", {"recipient_id": recipient_id})


def get_recipient_inflow(recipient_id: int) -> dict:
    return _execute_skill_query("recipient_inflow.sql", {"recipient_id": recipient_id})


def enrich_transaction(txn_data: dict) -> dict:
    sender_id = txn_data.get("sender_id")
    recipient_id = txn_data.get("recipient_id")

    sender_profile = get_sender_profile(sender_id) if sender_id else {}
    sender_behavior = get_sender_behavior(sender_id) if sender_id else {}
    recipient_profile = get_recipient_profile(recipient_id) if recipient_id else {}
    recipient_inflow = get_recipient_inflow(recipient_id) if recipient_id else {}

    if sender_profile:
        sender_profile.pop("HASHED_PASSWORD", None)

    return {
        "transaction": txn_data,
        "sender": sender_profile,
        "sender_behavior": sender_behavior,
        "recipient": recipient_profile,
        "recipient_inflow": recipient_inflow,
    }
