from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import datetime

from app.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=False)
    role = Column(String, default="user", nullable=False)  # "user", "admin"
    
    # KYC status
    kyc_status = Column(String, default="PENDING_SUBMISSION", nullable=False)  # "PENDING_SUBMISSION", "PENDING_APPROVAL", "APPROVED", "REJECTED"
    kyc_document_type = Column(String, nullable=True)  # "passport", "national_id", "drivers_license"
    kyc_document_number = Column(String, nullable=True)
    
    # Wallet
    wallet_balance = Column(Float, default=0.0, nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    # Relationships
    recipients = relationship("Recipient", back_populates="sender", cascade="all, delete-orphan")
    transactions = relationship("Transaction", back_populates="sender", cascade="all, delete-orphan")


class Recipient(Base):
    __tablename__ = "recipients"

    id = Column(Integer, primary_key=True, index=True)
    sender_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String, nullable=False)
    bank_name = Column(String, nullable=False)
    account_number = Column(String, nullable=False)
    routing_number = Column(String, nullable=True)
    country = Column(String, nullable=False)  # e.g., "Germany", "Kenya", "India"
    currency = Column(String, nullable=False)  # e.g., "EUR", "KES", "INR"
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    sender = relationship("User", back_populates="recipients")
    transactions = relationship("Transaction", back_populates="recipient", cascade="all, delete-orphan")


class ExchangeRate(Base):
    __tablename__ = "exchange_rates"

    id = Column(Integer, primary_key=True, index=True)
    source_currency = Column(String, nullable=False)  # e.g., "USD"
    target_currency = Column(String, nullable=False)  # e.g., "EUR"
    rate = Column(Float, nullable=False)              # e.g., 0.92
    fee_percentage = Column(Float, default=0.01, nullable=False) # e.g., 0.01 (1%)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    __table_args__ = (
        UniqueConstraint('source_currency', 'target_currency', name='uq_source_target_currency'),
    )


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    reference_number = Column(String, unique=True, index=True, nullable=False)
    sender_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    recipient_id = Column(Integer, ForeignKey("recipients.id", ondelete="CASCADE"), nullable=False)
    
    source_currency = Column(String, nullable=False)  # e.g., "USD"
    target_currency = Column(String, nullable=False)  # e.g., "EUR"
    source_amount = Column(Float, nullable=False)      # Amount sent (excludes fee)
    target_amount = Column(Float, nullable=False)      # Amount received (source_amount * exchange_rate)
    exchange_rate = Column(Float, nullable=False)      # Rate locked at transaction creation
    fee = Column(Float, nullable=False)                # Fee in source currency (source_amount * fee_percentage)
    
    status = Column(String, default="PENDING", nullable=False)  # "PENDING", "FUNDED", "PROCESSING", "COMPLETED", "CANCELLED", "FAILED"
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    # Relationships
    sender = relationship("User", back_populates="transactions")
    recipient = relationship("Recipient", back_populates="transactions")
