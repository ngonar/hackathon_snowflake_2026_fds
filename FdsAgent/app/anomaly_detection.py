import os
import base64
import snowflake.connector
from cryptography.hazmat.primitives import serialization
from dotenv import load_dotenv

from app.skill_loader import get_sql

load_dotenv()

# Weighted scoring from the fds-anomaly-detection SKILL.md
FLAG_WEIGHTS = {
    "HIGH_FREQUENCY_24H": 20,
    "AMOUNT_SPIKE": 25,
    "NEW_RECIPIENT_BURST": 15,
    "UNUSUAL_HOURS": 10,
    "SMURFING": 30,
    "RAPID_ONBOARDING": 25,
    "CIRCULAR_TRANSFER": 35,
}


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


def _run_check(script_name: str, params: dict) -> dict:
    sql = get_sql("fds-anomaly-detection", script_name)
    conn = _get_connection()
    try:
        cursor = conn.cursor(snowflake.connector.DictCursor)
        cursor.execute(sql, params)
        row = cursor.fetchone()
        return dict(row) if row else {}
    except Exception as e:
        print(f"AnomalyDetection: {script_name} failed: {e}")
        return {}
    finally:
        conn.close()


def run_anomaly_detection(sender_id: int, recipient_id: int, source_amount: float, txn_hour: int = 0) -> dict:
    """Run all 5 anomaly detection scripts and compute a weighted composite score."""
    flags = []
    details = {}

    # 1. Velocity check
    velocity = _run_check("velocity_check.sql", {
        "sender_id": sender_id,
        "current_amount": source_amount,
    })
    details["velocity"] = velocity
    if velocity.get("HIGH_FREQUENCY_24H"):
        flags.append("HIGH_FREQUENCY_24H")
    if velocity.get("NEW_RECIPIENT_BURST"):
        flags.append("NEW_RECIPIENT_BURST")
    if velocity.get("AMOUNT_SPIKE"):
        flags.append("AMOUNT_SPIKE")

    # 2. Time-based evasion
    time_check = _run_check("time_evasion.sql", {
        "sender_id": sender_id,
        "txn_hour": txn_hour,
    })
    details["time_evasion"] = time_check
    if time_check.get("UNUSUAL_HOURS"):
        flags.append("UNUSUAL_HOURS")

    # 3. Smurfing detection
    smurfing = _run_check("smurfing_check.sql", {
        "sender_id": sender_id,
    })
    details["smurfing"] = smurfing
    if smurfing.get("SMURFING_DETECTED"):
        flags.append("SMURFING")

    # 4. Rapid onboarding
    rapid = _run_check("rapid_onboarding.sql", {
        "sender_id": sender_id,
        "current_amount": source_amount,
    })
    details["rapid_onboarding"] = rapid
    if rapid.get("RAPID_ONBOARDING_DETECTED"):
        flags.append("RAPID_ONBOARDING")

    # 5. Circular transfer detection
    circular = _run_check("circular_check.sql", {
        "sender_id": sender_id,
        "recipient_id": recipient_id,
    })
    details["circular"] = circular
    if circular.get("CIRCULAR_TRANSFER_DETECTED"):
        flags.append("CIRCULAR_TRANSFER")

    # Compute weighted anomaly score (capped at 100)
    anomaly_score = min(100.0, sum(FLAG_WEIGHTS.get(f, 0) for f in flags))

    return {
        "anomaly_score": anomaly_score,
        "velocity_flags": flags if flags else ["NONE"],
        "details": details,
    }
