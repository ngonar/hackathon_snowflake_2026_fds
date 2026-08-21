import random
import string
from sqlalchemy.orm import Session
from typing import List, Optional

from app import models, schemas
from app.auth import get_password_hash

# ==========================
# User CRUD
# ==========================
def get_user(db: Session, user_id: int) -> Optional[models.User]:
    return db.query(models.User).filter(models.User.id == user_id).first()

def get_user_by_email(db: Session, email: str) -> Optional[models.User]:
    return db.query(models.User).filter(models.User.email == email).first()

def create_user(db: Session, user: schemas.UserCreate, role: str = "user") -> models.User:
    hashed_pw = get_password_hash(user.password)
    db_user = models.User(
        email=user.email,
        full_name=user.full_name,
        hashed_password=hashed_pw,
        role=role,
        wallet_balance=0.0
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def update_user_kyc(db: Session, user_id: int, doc_type: str, doc_number: str) -> Optional[models.User]:
    db_user = get_user(db, user_id)
    if db_user:
        db_user.kyc_document_type = doc_type
        db_user.kyc_document_number = doc_number
        db_user.kyc_status = "PENDING_APPROVAL"
        db.commit()
        db.refresh(db_user)
    return db_user

def approve_user_kyc(db: Session, user_id: int, approve: bool) -> Optional[models.User]:
    db_user = get_user(db, user_id)
    if db_user:
        db_user.kyc_status = "APPROVED" if approve else "REJECTED"
        db.commit()
        db.refresh(db_user)
    return db_user

def update_user_balance(db: Session, user_id: int, amount: float) -> Optional[models.User]:
    db_user = get_user(db, user_id)
    if db_user:
        db_user.wallet_balance += amount
        db.commit()
        db.refresh(db_user)
    return db_user

def get_pending_kyc_users(db: Session) -> List[models.User]:
    return db.query(models.User).filter(models.User.kyc_status == "PENDING_APPROVAL").all()

def get_all_users(db: Session) -> List[models.User]:
    return db.query(models.User).all()

def freeze_user_wallet(db: Session, user_id: int, reason: str = "Fraud risk detected") -> Optional[models.User]:
    db_user = get_user(db, user_id)
    if db_user:
        db_user.wallet_frozen = "FROZEN"
        db_user.kyc_status = "FROZEN"
        db.commit()
        db.refresh(db_user)
    return db_user

def unfreeze_user_wallet(db: Session, user_id: int) -> Optional[models.User]:
    db_user = get_user(db, user_id)
    if db_user:
        db_user.wallet_frozen = "ACTIVE"
        if db_user.kyc_status == "FROZEN":
            db_user.kyc_status = "PENDING_SUBMISSION"
        db.commit()
        db.refresh(db_user)
    return db_user

def reset_user_kyc(db: Session, user_id: int) -> Optional[models.User]:
    db_user = get_user(db, user_id)
    if db_user:
        db_user.kyc_status = "PENDING_SUBMISSION"
        db_user.kyc_document_type = None
        db_user.kyc_document_number = None
        db.commit()
        db.refresh(db_user)
    return db_user

# ==========================
# Recipient CRUD
# ==========================
def create_recipient(db: Session, sender_id: int, recipient: schemas.RecipientCreate) -> models.Recipient:
    db_recipient = models.Recipient(
        sender_id=sender_id,
        name=recipient.name,
        bank_name=recipient.bank_name,
        account_number=recipient.account_number,
        routing_number=recipient.routing_number,
        country=recipient.country,
        currency=recipient.currency
    )
    db.add(db_recipient)
    db.commit()
    db.refresh(db_recipient)
    return db_recipient

def get_recipients_by_sender(db: Session, sender_id: int) -> List[models.Recipient]:
    return db.query(models.Recipient).filter(models.Recipient.sender_id == sender_id).all()

def get_recipient(db: Session, recipient_id: int) -> Optional[models.Recipient]:
    return db.query(models.Recipient).filter(models.Recipient.id == recipient_id).first()

# ==========================
# Exchange Rate CRUD
# ==========================
def get_exchange_rate(db: Session, source: str, target: str) -> Optional[models.ExchangeRate]:
    return db.query(models.ExchangeRate).filter(
        models.ExchangeRate.source_currency == source.upper(),
        models.ExchangeRate.target_currency == target.upper()
    ).first()

def get_all_exchange_rates(db: Session) -> List[models.ExchangeRate]:
    return db.query(models.ExchangeRate).all()

def create_or_update_exchange_rate(db: Session, source: str, target: str, rate: float, fee_percentage: float) -> models.ExchangeRate:
    db_rate = get_exchange_rate(db, source, target)
    if db_rate:
        db_rate.rate = rate
        db_rate.fee_percentage = fee_percentage
    else:
        db_rate = models.ExchangeRate(
            source_currency=source.upper(),
            target_currency=target.upper(),
            rate=rate,
            fee_percentage=fee_percentage
        )
        db.add(db_rate)
    db.commit()
    db.refresh(db_rate)
    return db_rate

# ==========================
# Transaction CRUD
# ==========================
def generate_reference_number() -> str:
    # Generates a code like REMIT-83749281
    digits = ''.join(random.choices(string.digits, k=8))
    return f"REMIT-{digits}"

def create_transaction(
    db: Session, 
    sender_id: int, 
    recipient_id: int, 
    source_currency: str, 
    target_currency: str, 
    source_amount: float, 
    target_amount: float, 
    exchange_rate: float, 
    fee: float
) -> models.Transaction:
    # Ensure reference number is unique
    while True:
        ref = generate_reference_number()
        exists = db.query(models.Transaction).filter(models.Transaction.reference_number == ref).first()
        if not exists:
            break
            
    db_txn = models.Transaction(
        reference_number=ref,
        sender_id=sender_id,
        recipient_id=recipient_id,
        source_currency=source_currency.upper(),
        target_currency=target_currency.upper(),
        source_amount=source_amount,
        target_amount=target_amount,
        exchange_rate=exchange_rate,
        fee=fee,
        status="PENDING"
    )
    db.add(db_txn)
    db.commit()
    db.refresh(db_txn)
    return db_txn

def get_transaction(db: Session, txn_id: int) -> Optional[models.Transaction]:
    return db.query(models.Transaction).filter(models.Transaction.id == txn_id).first()

def get_transaction_by_ref(db: Session, ref: str) -> Optional[models.Transaction]:
    return db.query(models.Transaction).filter(models.Transaction.reference_number == ref).first()

def get_transactions_by_sender(db: Session, sender_id: int) -> List[models.Transaction]:
    return db.query(models.Transaction).filter(models.Transaction.sender_id == sender_id).all()

def get_all_transactions(db: Session) -> List[models.Transaction]:
    return db.query(models.Transaction).all()

def update_transaction_status(
    db: Session, 
    txn_id: int, 
    new_status: str,
    anomaly_score: Optional[float] = None,
    velocity_flags: Optional[str] = None,
    fraud_explanation: Optional[str] = None,
    fraud_evidence: Optional[str] = None
) -> Optional[models.Transaction]:
    db_txn = get_transaction(db, txn_id)
    if db_txn:
        db_txn.status = new_status
        if anomaly_score is not None:
            db_txn.anomaly_score = anomaly_score
        if velocity_flags is not None:
            db_txn.velocity_flags = velocity_flags
        if fraud_explanation is not None:
            db_txn.fraud_explanation = fraud_explanation
        if fraud_evidence is not None:
            db_txn.fraud_evidence = fraud_evidence
        db.commit()
        db.refresh(db_txn)
    return db_txn
