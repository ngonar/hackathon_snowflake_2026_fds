from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional, List
from datetime import datetime

# ==========================
# Auth & User Schemas
# ==========================
class UserBase(BaseModel):
    email: EmailStr
    full_name: str

class UserCreate(UserBase):
    password: str = Field(..., min_length=6, description="Password must be at least 6 characters long")

class UserResponse(UserBase):
    id: int
    role: str
    kyc_status: str
    kyc_document_type: Optional[str] = None
    kyc_document_number: Optional[str] = None
    wallet_balance: float
    wallet_frozen: str = "ACTIVE"
    base_currency: str = "USD"
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None
    role: Optional[str] = None
    user_id: Optional[int] = None

# ==========================
# KYC Schemas
# ==========================
class KycSubmission(BaseModel):
    kyc_document_type: str = Field(..., description="Type of document: passport, national_id, or drivers_license")
    kyc_document_number: str = Field(..., min_length=4, description="ID or Document number")

# ==========================
# Recipient Schemas
# ==========================
class RecipientBase(BaseModel):
    name: str
    bank_name: str
    account_number: str
    routing_number: Optional[str] = None
    country: str
    currency: str

class RecipientCreate(RecipientBase):
    pass

class RecipientResponse(RecipientBase):
    id: int
    sender_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

# ==========================
# Exchange Rate & Estimation Schemas
# ==========================
class ExchangeRateBase(BaseModel):
    source_currency: str
    target_currency: str
    rate: float
    fee_percentage: float

class ExchangeRateResponse(ExchangeRateBase):
    id: int
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class EstimateRequest(BaseModel):
    source_currency: str = Field(..., description="Currency being sent (e.g. USD)")
    target_currency: str = Field(..., description="Currency to be received (e.g. EUR, KES, INR)")
    source_amount: float = Field(..., gt=0, description="Amount in source currency to be sent")

class EstimateResponse(BaseModel):
    source_currency: str
    target_currency: str
    source_amount: float
    exchange_rate: float
    fee: float
    target_amount: float
    total_required: float  # source_amount + fee

# ==========================
# Transaction Schemas
# ==========================
class TransactionCreate(BaseModel):
    recipient_id: int
    source_amount: float = Field(..., gt=0, description="Amount to transfer (excludes fee)")

class TransactionResponse(BaseModel):
    id: int
    reference_number: str
    sender_id: int
    recipient_id: int
    source_currency: str
    target_currency: str
    source_amount: float
    target_amount: float
    exchange_rate: float
    fee: float
    status: str
    created_at: datetime
    updated_at: datetime
    
    anomaly_score: Optional[float] = None
    velocity_flags: Optional[str] = None
    fraud_explanation: Optional[str] = None
    fraud_evidence: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

# ==========================
# Wallet Schemas
# ==========================
class WalletDeposit(BaseModel):
    amount: float = Field(..., gt=0, description="Amount to deposit in USD")

class WalletResponse(BaseModel):
    wallet_balance: float

# ==========================
# Bulk Transfer Schemas
# ==========================
class BulkTransferRowError(BaseModel):
    row: int
    recipient_id: Optional[int] = None
    source_amount: Optional[float] = None
    error: str

class BulkTransferResult(BaseModel):
    total: int
    successful: List[TransactionResponse]
    failed: List[BulkTransferRowError]

# ==========================
# Settings Schemas
# ==========================
class BaseCurrencyUpdate(BaseModel):
    base_currency: str = Field(..., description="User's preferred base currency (e.g. USD, EUR, GBP)")
