import logging

import snowflake.connector

from app.config import settings

logger = logging.getLogger("uvicorn.error")


def publish_transaction_message(transaction_data: dict):
    """
    Inserts transaction details into Snowflake table REMITTANCE_TRX.
    A stream and task on the Snowflake side handle downstream processing.
    """
    conn = None
    try:
        conn = snowflake.connector.connect(
            account=settings.SNOWFLAKE_ACCOUNT,
            user=settings.SNOWFLAKE_USER,
            password=settings.SNOWFLAKE_PASSWORD,
            warehouse=settings.SNOWFLAKE_WAREHOUSE,
            database=settings.SNOWFLAKE_DATABASE,
            schema=settings.SNOWFLAKE_SCHEMA,
        )
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO REMITTANCE_TRX
                (ID, REFERENCE_NUMBER, SENDER_ID, RECIPIENT_ID,
                 SOURCE_CURRENCY, TARGET_CURRENCY, SOURCE_AMOUNT, TARGET_AMOUNT,
                 EXCHANGE_RATE, FEE, STATUS, CREATED_AT, UPDATED_AT)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
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
                transaction_data.get("status"),
                transaction_data.get("created_at"),
                transaction_data.get("updated_at"),
            ),
        )
        cursor.close()

        logger.info(
            f"Successfully inserted transaction {transaction_data.get('reference_number')} "
            f"into Snowflake table {settings.SNOWFLAKE_DATABASE}.{settings.SNOWFLAKE_SCHEMA}.REMITTANCE_TRX"
        )

    except Exception as e:
        logger.error(f"Failed to insert transaction into Snowflake: {str(e)}")
        print(f"Failed to insert transaction into Snowflake: {str(e)}")
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass
