from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional
from pydantic import BaseModel

from app import crud, schemas, auth
from app.database import get_db
from app.nl_query import translate_and_execute

router = APIRouter(
    prefix="/admin",
    tags=["Admin Management"],
    dependencies=[Depends(auth.get_current_admin)]
)


@router.get("/kyc", response_model=List[schemas.UserResponse])
def get_pending_kyc(conn=Depends(get_db)):
    return crud.get_pending_kyc_users(conn)


@router.get("/users", response_model=List[schemas.UserResponse])
def list_all_users(conn=Depends(get_db)):
    return crud.get_all_users(conn)


@router.post("/kyc/{user_id}/approve", response_model=schemas.UserResponse)
def approve_kyc(user_id: int, approve: bool, conn=Depends(get_db)):
    user = crud.get_user(conn, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if user.get("kyc_status") != "PENDING_APPROVAL":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"KYC status is '{user.get('kyc_status')}'. Can only approve/reject users with 'PENDING_APPROVAL' status."
        )
    return crud.approve_user_kyc(conn, user_id=user_id, approve=approve)


@router.get("/transactions", response_model=List[schemas.TransactionResponse])
def list_all_transactions(conn=Depends(get_db)):
    return crud.get_all_transactions(conn)


@router.post("/transactions/{txn_id}/status", response_model=schemas.TransactionResponse)
def update_transaction_status(
    txn_id: int,
    status_value: str,
    anomaly_score: Optional[float] = None,
    velocity_flags: Optional[str] = None,
    fraud_explanation: Optional[str] = None,
    fraud_evidence: Optional[str] = None,
    conn=Depends(get_db)
):
    txn = crud.get_transaction(conn, txn_id)
    if not txn:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")

    allowed_statuses = ["PENDING", "FUNDED", "PROCESSING", "COMPLETED", "CANCELLED", "FAILED", "SUSPICIOUS"]
    if status_value.upper() not in allowed_statuses:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid status. Allowed statuses: {', '.join(allowed_statuses)}"
        )

    return crud.update_transaction_status(
        conn, txn_id=txn_id, new_status=status_value.upper(),
        anomaly_score=anomaly_score, velocity_flags=velocity_flags,
        fraud_explanation=fraud_explanation, fraud_evidence=fraud_evidence
    )


@router.post("/rates", response_model=schemas.ExchangeRateResponse)
def create_or_update_rate(rate_data: schemas.ExchangeRateBase, conn=Depends(get_db)):
    if rate_data.rate <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Exchange rate must be greater than zero")
    if not (0 <= rate_data.fee_percentage <= 1):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Fee percentage must be between 0.0 and 1.0")

    return crud.create_or_update_exchange_rate(
        conn, source=rate_data.source_currency, target=rate_data.target_currency,
        rate=rate_data.rate, fee_percentage=rate_data.fee_percentage
    )


@router.post("/users/{user_id}/freeze", response_model=schemas.UserResponse)
def freeze_user_wallet(user_id: int, reason: str = "Fraud risk detected by FDS", conn=Depends(get_db)):
    user = crud.get_user(conn, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if user.get("wallet_frozen") == "FROZEN":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Wallet is already frozen")
    return crud.freeze_user_wallet(conn, user_id=user_id, reason=reason)


@router.post("/users/{user_id}/unfreeze", response_model=schemas.UserResponse)
def unfreeze_user_wallet(user_id: int, conn=Depends(get_db)):
    user = crud.get_user(conn, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if user.get("wallet_frozen") != "FROZEN":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Wallet is not frozen")
    return crud.unfreeze_user_wallet(conn, user_id=user_id)


@router.post("/users/{user_id}/kyc-reverify", response_model=schemas.UserResponse)
def dispatch_kyc_reverification(user_id: int, conn=Depends(get_db)):
    user = crud.get_user(conn, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return crud.reset_user_kyc(conn, user_id=user_id)


@router.post("/users/{user_id}/kyc-status", response_model=schemas.UserResponse)
def update_kyc_status(user_id: int, status_value: str, conn=Depends(get_db)):
    allowed = ["PENDING_SUBMISSION", "PENDING_APPROVAL", "APPROVED", "REJECTED", "FROZEN"]
    if status_value.upper() not in allowed:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid KYC status. Allowed: {', '.join(allowed)}"
        )
    user = crud.get_user(conn, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE USERS SET KYC_STATUS = %s, UPDATED_AT = CURRENT_TIMESTAMP() WHERE ID = %s",
        (status_value.upper(), user_id)
    )
    return crud.get_user(conn, user_id)


class InvestigateRequest(BaseModel):
    query: str


@router.post("/investigate")
def investigate_fraud(req: InvestigateRequest):
    if not req.query or len(req.query.strip()) < 3:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Query must be at least 3 characters"
        )

    result = translate_and_execute(req.query.strip())

    if not result.get("success"):
        return {
            "success": False,
            "error": result.get("error", "Unknown error"),
            "sql": result.get("sql"),
            "results": [],
            "columns": [],
            "row_count": 0
        }

    return result
