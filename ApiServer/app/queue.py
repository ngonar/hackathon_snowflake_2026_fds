import logging
import httpx
import snowflake.connector

from app.config import settings

logger = logging.getLogger("uvicorn.error")

FDS_AGENT_URL = "http://fds-agent-service.gxpx.svc.spcs.internal:8080/fds/invoke"


def _get_snowflake_connection():
    conn_params = {
        "account": settings.SNOWFLAKE_ACCOUNT,
        "user": settings.SNOWFLAKE_USER,
        "warehouse": settings.SNOWFLAKE_WAREHOUSE,
        "database": settings.SNOWFLAKE_DATABASE,
        "schema": settings.SNOWFLAKE_SCHEMA,
    }
    if settings.SNOWFLAKE_PASSWORD:
        conn_params["password"] = settings.SNOWFLAKE_PASSWORD
    return snowflake.connector.connect(**conn_params)


def _insert_pending_transaction(transaction_data: dict):
    """Insert transaction into PENDING_TRANSACTIONS for audit trail and fallback processing."""
    try:
        conn = _get_snowflake_connection()
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO SNOWFLAKE_LEARNING_DB.FDS.PENDING_TRANSACTIONS 
            (TXN_ID, REFERENCE_NUMBER, SENDER_ID, RECIPIENT_ID, 
             SOURCE_CURRENCY, TARGET_CURRENCY, SOURCE_AMOUNT, TARGET_AMOUNT,
             EXCHANGE_RATE, FEE, STATUS, PROCESSED)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, FALSE)""",
            (
                transaction_data.get("id"),
                transaction_data.get("reference_number"),
                transaction_data.get("sender_id"),
                transaction_data.get("recipient_id"),
                transaction_data.get("source_currency"),
                transaction_data.get("target_currency"),
                transaction_data.get("source_amount"),
                transaction_data.get("target_amount"),
                transaction_data.get("exchange_rate"),
                transaction_data.get("fee"),
                transaction_data.get("status", "PENDING"),
            ),
        )
        conn.close()
        logger.info(
            f"Inserted transaction {transaction_data.get('reference_number')} "
            f"into PENDING_TRANSACTIONS"
        )
    except Exception as e:
        logger.error(f"Failed to insert into PENDING_TRANSACTIONS: {str(e)}")


def publish_transaction_message(transaction_data: dict):
    """
    Sends transaction to the FDS Agent for fraud analysis via internal SPCS network,
    and inserts into PENDING_TRANSACTIONS for audit trail.
    """
    # Always insert into Snowflake PENDING_TRANSACTIONS for audit/fallback
    _insert_pending_transaction(transaction_data)

    try:
        response = httpx.post(
            FDS_AGENT_URL,
            json={"input": transaction_data},
            timeout=30.0,
        )
        if response.status_code == 200:
            logger.info(
                f"Successfully sent transaction {transaction_data.get('reference_number')} "
                f"to FDS Agent for processing"
            )
        else:
            logger.warning(
                f"FDS Agent returned status {response.status_code} for "
                f"transaction {transaction_data.get('reference_number')}: {response.text}"
            )
    except Exception as e:
        logger.error(f"Failed to send transaction to FDS Agent: {str(e)}")
        logger.info(
            f"Transaction {transaction_data.get('reference_number')} will be picked up "
            f"by the FDS Agent's polling consumer from PENDING_TRANSACTIONS"
        )
