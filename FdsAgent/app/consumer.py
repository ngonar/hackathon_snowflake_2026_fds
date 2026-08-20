import os
import json
import time
import asyncio
import base64
import threading
import snowflake.connector
from cryptography.hazmat.primitives import serialization
from dotenv import load_dotenv

from app.agent import fds_process_chain

load_dotenv()

SNOWFLAKE_ACCOUNT = os.getenv("SNOWFLAKE_ACCOUNT")
SNOWFLAKE_USER = os.getenv("SNOWFLAKE_USER")
SNOWFLAKE_PRIVATE_KEY_B64 = os.getenv("SNOWFLAKE_PRIVATE_KEY")
SNOWFLAKE_PASSWORD = os.getenv("SNOWFLAKE_PASSWORD")
SNOWFLAKE_WAREHOUSE = os.getenv("SNOWFLAKE_WAREHOUSE")
SNOWFLAKE_DATABASE = os.getenv("SNOWFLAKE_DATABASE", "SNOWFLAKE_LEARNING_DB")
SNOWFLAKE_SCHEMA = os.getenv("SNOWFLAKE_SCHEMA", "FDS")
SNOWFLAKE_ROLE = os.getenv("SNOWFLAKE_ROLE")

POLL_INTERVAL = int(os.getenv("SF_POLL_INTERVAL", "5"))

_consumer_thread = None
_stop_event = threading.Event()


def _load_private_key():
    if not SNOWFLAKE_PRIVATE_KEY_B64:
        return None
    key_bytes = base64.b64decode(SNOWFLAKE_PRIVATE_KEY_B64)
    private_key = serialization.load_pem_private_key(key_bytes, password=None)
    return private_key.private_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )


def _get_connection():
    conn_params = {
        "account": SNOWFLAKE_ACCOUNT,
        "user": SNOWFLAKE_USER,
        "warehouse": SNOWFLAKE_WAREHOUSE,
        "database": SNOWFLAKE_DATABASE,
        "schema": SNOWFLAKE_SCHEMA,
        "role": SNOWFLAKE_ROLE,
    }
    private_key = _load_private_key()
    if private_key:
        conn_params["private_key"] = private_key
    else:
        conn_params["password"] = SNOWFLAKE_PASSWORD
    return snowflake.connector.connect(**conn_params)


def start_stream_consumer():
    """Starts a background thread that polls the Snowflake stream for new transactions."""
    global _consumer_thread, _stop_event
    _stop_event.clear()

    def run_consumer():
        while not _stop_event.is_set():
            try:
                conn = _get_connection()
                cursor = conn.cursor()

                # Fetch unprocessed rows
                cursor.execute(
                    "SELECT * FROM SNOWFLAKE_LEARNING_DB.FDS.PENDING_TRANSACTIONS "
                    "WHERE processed = FALSE ORDER BY created_at ASC"
                )
                columns = [desc[0].lower() for desc in cursor.description]
                rows = cursor.fetchall()

                for row in rows:
                    if _stop_event.is_set():
                        break

                    txn_data = dict(zip(columns, row))
                    row_id = txn_data.pop("id", None)
                    txn_data.pop("created_at", None)
                    txn_data.pop("processed", None)

                    # Convert txn_id back to 'id' key expected by the agent
                    txn_data["id"] = txn_data.pop("txn_id", None)

                    print(f"\nFDS Consumer: Received transaction from stream: {json.dumps(txn_data, default=str)}")

                    try:
                        result = asyncio.run(fds_process_chain.ainvoke(txn_data))
                        print(f"FDS Consumer: Processed transaction. Decision: {result['decision']}")
                    except Exception as e:
                        print(f"FDS Consumer: Error processing transaction: {e}")

                    # Mark as processed
                    cursor.execute(
                        "UPDATE SNOWFLAKE_LEARNING_DB.FDS.PENDING_TRANSACTIONS "
                        "SET processed = TRUE WHERE id = %s",
                        (row_id,)
                    )

                conn.close()

            except Exception as e:
                if _stop_event.is_set():
                    break
                print(f"FDS Consumer: Error polling Snowflake stream: {e}. Retrying in {POLL_INTERVAL}s...")

            # Wait for the next poll cycle
            _stop_event.wait(timeout=POLL_INTERVAL)

        print("FDS Consumer: Background thread stopped.")

    _consumer_thread = threading.Thread(target=run_consumer, daemon=True)
    _consumer_thread.start()
    print(f"FDS Consumer: Polling Snowflake stream every {POLL_INTERVAL}s...")
    return _consumer_thread


def stop_stream_consumer():
    """Stops the background Snowflake stream consumer thread."""
    global _stop_event
    print("FDS Consumer: Stopping background consumer...")
    _stop_event.set()
