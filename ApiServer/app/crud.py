import random
import string
from typing import List, Optional, Any
import snowflake.connector

from app.auth import get_password_hash


def _row_to_dict(cursor, row) -> dict:
    columns = [desc[0].lower() for desc in cursor.description]
    return dict(zip(columns, row))


def _fetchone_dict(cursor) -> Optional[dict]:
    row = cursor.fetchone()
    if row is None:
        return None
    return _row_to_dict(cursor, row)


def _fetchall_dict(cursor) -> List[dict]:
    rows = cursor.fetchall()
    return [_row_to_dict(cursor, row) for row in rows]


# ==========================
# User CRUD
# ==========================
def get_user(conn, user_id: int) -> Optional[dict]:
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM USERS WHERE ID = %s", (user_id,))
    return _fetchone_dict(cursor)


def get_user_by_email(conn, email: str) -> Optional[dict]:
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM USERS WHERE EMAIL = %s", (email,))
    return _fetchone_dict(cursor)


def create_user(conn, email: str, full_name: str, password: str, role: str = "user") -> dict:
    hashed_pw = get_password_hash(password)
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO USERS (ID, EMAIL, FULL_NAME, HASHED_PASSWORD, ROLE, KYC_STATUS, WALLET_BALANCE, WALLET_FROZEN, CREATED_AT, UPDATED_AT)
        VALUES (SNOWFLAKE_LEARNING_DB.FDS.USERS_SEQ.NEXTVAL, %s, %s, %s, %s, 'PENDING_SUBMISSION', 0.0, 'ACTIVE', CURRENT_TIMESTAMP(), CURRENT_TIMESTAMP())""",
        (email, full_name, hashed_pw, role),
    )
    cursor.execute("SELECT * FROM USERS WHERE EMAIL = %s", (email,))
    return _fetchone_dict(cursor)


def update_user_kyc(conn, user_id: int, doc_type: str, doc_number: str) -> Optional[dict]:
    cursor = conn.cursor()
    cursor.execute(
        """UPDATE USERS SET KYC_DOCUMENT_TYPE = %s, KYC_DOCUMENT_NUMBER = %s, 
        KYC_STATUS = 'PENDING_APPROVAL', UPDATED_AT = CURRENT_TIMESTAMP() WHERE ID = %s""",
        (doc_type, doc_number, user_id),
    )
    return get_user(conn, user_id)


def approve_user_kyc(conn, user_id: int, approve: bool) -> Optional[dict]:
    status = "APPROVED" if approve else "REJECTED"
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE USERS SET KYC_STATUS = %s, UPDATED_AT = CURRENT_TIMESTAMP() WHERE ID = %s",
        (status, user_id),
    )
    return get_user(conn, user_id)


def update_user_balance(conn, user_id: int, amount: float) -> Optional[dict]:
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE USERS SET WALLET_BALANCE = WALLET_BALANCE + %s, UPDATED_AT = CURRENT_TIMESTAMP() WHERE ID = %s",
        (amount, user_id),
    )
    return get_user(conn, user_id)


def get_pending_kyc_users(conn) -> List[dict]:
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM USERS WHERE KYC_STATUS = 'PENDING_APPROVAL'")
    return _fetchall_dict(cursor)


def get_all_users(conn) -> List[dict]:
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM USERS ORDER BY ID")
    return _fetchall_dict(cursor)


def freeze_user_wallet(conn, user_id: int, reason: str = "Fraud risk detected") -> Optional[dict]:
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE USERS SET WALLET_FROZEN = 'FROZEN', KYC_STATUS = 'FROZEN', UPDATED_AT = CURRENT_TIMESTAMP() WHERE ID = %s",
        (user_id,),
    )
    return get_user(conn, user_id)


def unfreeze_user_wallet(conn, user_id: int) -> Optional[dict]:
    cursor = conn.cursor()
    cursor.execute(
        """UPDATE USERS SET WALLET_FROZEN = 'ACTIVE', 
        KYC_STATUS = CASE WHEN KYC_STATUS = 'FROZEN' THEN 'PENDING_SUBMISSION' ELSE KYC_STATUS END,
        UPDATED_AT = CURRENT_TIMESTAMP() WHERE ID = %s""",
        (user_id,),
    )
    return get_user(conn, user_id)


def reset_user_kyc(conn, user_id: int) -> Optional[dict]:
    cursor = conn.cursor()
    cursor.execute(
        """UPDATE USERS SET KYC_STATUS = 'PENDING_SUBMISSION', KYC_DOCUMENT_TYPE = NULL, 
        KYC_DOCUMENT_NUMBER = NULL, UPDATED_AT = CURRENT_TIMESTAMP() WHERE ID = %s""",
        (user_id,),
    )
    return get_user(conn, user_id)


# ==========================
# Recipient CRUD
# ==========================
def create_recipient(conn, sender_id: int, name: str, bank_name: str, account_number: str,
                     routing_number: Optional[str], country: str, currency: str) -> dict:
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO RECIPIENTS (ID, SENDER_ID, NAME, BANK_NAME, ACCOUNT_NUMBER, ROUTING_NUMBER, COUNTRY, CURRENCY, CREATED_AT)
        VALUES (SNOWFLAKE_LEARNING_DB.FDS.RECIPIENTS_SEQ.NEXTVAL, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP())""",
        (sender_id, name, bank_name, account_number, routing_number, country, currency.upper()),
    )
    cursor.execute(
        "SELECT * FROM RECIPIENTS WHERE SENDER_ID = %s AND ACCOUNT_NUMBER = %s ORDER BY ID DESC LIMIT 1",
        (sender_id, account_number),
    )
    return _fetchone_dict(cursor)


def get_recipients_by_sender(conn, sender_id: int) -> List[dict]:
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM RECIPIENTS WHERE SENDER_ID = %s ORDER BY ID", (sender_id,))
    return _fetchall_dict(cursor)


def get_recipient(conn, recipient_id: int) -> Optional[dict]:
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM RECIPIENTS WHERE ID = %s", (recipient_id,))
    return _fetchone_dict(cursor)


# ==========================
# Exchange Rate CRUD
# ==========================
def get_exchange_rate(conn, source: str, target: str) -> Optional[dict]:
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM EXCHANGE_RATES WHERE SOURCE_CURRENCY = %s AND TARGET_CURRENCY = %s",
        (source.upper(), target.upper()),
    )
    return _fetchone_dict(cursor)


def get_all_exchange_rates(conn) -> List[dict]:
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM EXCHANGE_RATES ORDER BY SOURCE_CURRENCY, TARGET_CURRENCY")
    return _fetchall_dict(cursor)


def create_or_update_exchange_rate(conn, source: str, target: str, rate: float, fee_percentage: float) -> dict:
    cursor = conn.cursor()
    existing = get_exchange_rate(conn, source, target)
    if existing:
        cursor.execute(
            """UPDATE EXCHANGE_RATES SET RATE = %s, FEE_PERCENTAGE = %s, UPDATED_AT = CURRENT_TIMESTAMP()
            WHERE SOURCE_CURRENCY = %s AND TARGET_CURRENCY = %s""",
            (rate, fee_percentage, source.upper(), target.upper()),
        )
    else:
        cursor.execute(
            """INSERT INTO EXCHANGE_RATES (SOURCE_CURRENCY, TARGET_CURRENCY, RATE, FEE_PERCENTAGE, CREATED_AT, UPDATED_AT)
            VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP(), CURRENT_TIMESTAMP())""",
            (source.upper(), target.upper(), rate, fee_percentage),
        )
    return get_exchange_rate(conn, source, target)


# ==========================
# Transaction CRUD
# ==========================
def generate_reference_number() -> str:
    digits = ''.join(random.choices(string.digits, k=8))
    return f"REMIT-{digits}"


def create_transaction(conn, sender_id: int, recipient_id: int, source_currency: str,
                       target_currency: str, source_amount: float, target_amount: float,
                       exchange_rate: float, fee: float) -> dict:
    ref = generate_reference_number()
    cursor = conn.cursor()
    # Ensure unique reference
    cursor.execute("SELECT 1 FROM TRANSACTIONS WHERE REFERENCE_NUMBER = %s", (ref,))
    while cursor.fetchone():
        ref = generate_reference_number()
        cursor.execute("SELECT 1 FROM TRANSACTIONS WHERE REFERENCE_NUMBER = %s", (ref,))

    cursor.execute(
        """INSERT INTO TRANSACTIONS (ID, REFERENCE_NUMBER, SENDER_ID, RECIPIENT_ID,
        SOURCE_CURRENCY, TARGET_CURRENCY, SOURCE_AMOUNT, TARGET_AMOUNT,
        EXCHANGE_RATE, FEE, STATUS, CREATED_AT, UPDATED_AT)
        VALUES (SNOWFLAKE_LEARNING_DB.FDS.TRANSACTIONS_SEQ.NEXTVAL, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'PENDING', CURRENT_TIMESTAMP(), CURRENT_TIMESTAMP())""",
        (ref, sender_id, recipient_id, source_currency.upper(), target_currency.upper(),
         source_amount, target_amount, exchange_rate, fee),
    )
    cursor.execute("SELECT * FROM TRANSACTIONS WHERE REFERENCE_NUMBER = %s", (ref,))
    return _fetchone_dict(cursor)


def get_transaction(conn, txn_id: int) -> Optional[dict]:
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM TRANSACTIONS WHERE ID = %s", (txn_id,))
    return _fetchone_dict(cursor)


def get_transaction_by_ref(conn, ref: str) -> Optional[dict]:
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM TRANSACTIONS WHERE REFERENCE_NUMBER = %s", (ref,))
    return _fetchone_dict(cursor)


def get_transactions_by_sender(conn, sender_id: int) -> List[dict]:
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM TRANSACTIONS WHERE SENDER_ID = %s ORDER BY CREATED_AT DESC", (sender_id,))
    return _fetchall_dict(cursor)


def get_all_transactions(conn) -> List[dict]:
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM TRANSACTIONS ORDER BY CREATED_AT DESC")
    return _fetchall_dict(cursor)


def update_transaction_status(conn, txn_id: int, new_status: str,
                              anomaly_score: Optional[float] = None,
                              velocity_flags: Optional[str] = None,
                              fraud_explanation: Optional[str] = None,
                              fraud_evidence: Optional[str] = None) -> Optional[dict]:
    cursor = conn.cursor()
    sets = ["STATUS = %s", "UPDATED_AT = CURRENT_TIMESTAMP()"]
    params = [new_status]

    if anomaly_score is not None:
        sets.append("ANOMALY_SCORE = %s")
        params.append(anomaly_score)
    if velocity_flags is not None:
        sets.append("VELOCITY_FLAGS = %s")
        params.append(velocity_flags)
    if fraud_explanation is not None:
        sets.append("FRAUD_EXPLANATION = %s")
        params.append(fraud_explanation)
    if fraud_evidence is not None:
        sets.append("FRAUD_EVIDENCE = %s")
        params.append(fraud_evidence)

    params.append(txn_id)
    cursor.execute(f"UPDATE TRANSACTIONS SET {', '.join(sets)} WHERE ID = %s", params)
    return get_transaction(conn, txn_id)
