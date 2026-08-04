from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app import crud, schemas, auth, models
from app.database import get_db

router = APIRouter(
    prefix="/admin",
    tags=["Admin Management"],
    dependencies=[Depends(auth.get_current_admin)]
)

@router.get("/kyc", response_model=List[schemas.UserResponse])
def get_pending_kyc(db: Session = Depends(get_db)):
    return crud.get_pending_kyc_users(db)


@router.post("/kyc/{user_id}/approve", response_model=schemas.UserResponse)
def approve_kyc(
    user_id: int,
    approve: bool,
    db: Session = Depends(get_db)
):
    user = crud.get_user(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    if user.kyc_status != "PENDING_APPROVAL":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"KYC status is '{user.kyc_status}'. Can only approve/reject users with 'PENDING_APPROVAL' status."
        )
    return crud.approve_user_kyc(db=db, user_id=user_id, approve=approve)


@router.get("/transactions", response_model=List[schemas.TransactionResponse])
def list_all_transactions(db: Session = Depends(get_db)):
    return crud.get_all_transactions(db)


@router.post("/transactions/{txn_id}/status", response_model=schemas.TransactionResponse)
def update_transaction_status(
    txn_id: int,
    status_value: str,
    db: Session = Depends(get_db)
):
    txn = crud.get_transaction(db, txn_id)
    if not txn:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found"
        )
        
    allowed_statuses = ["PENDING", "FUNDED", "PROCESSING", "COMPLETED", "CANCELLED", "FAILED"]
    if status_value.upper() not in allowed_statuses:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid status. Allowed statuses: {', '.join(allowed_statuses)}"
        )
        
    return crud.update_transaction_status(db=db, txn_id=txn_id, new_status=status_value.upper())


@router.post("/rates", response_model=schemas.ExchangeRateResponse)
def create_or_update_rate(
    rate_data: schemas.ExchangeRateBase,
    db: Session = Depends(get_db)
):
    if rate_data.rate <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Exchange rate must be greater than zero"
        )
    if not (0 <= rate_data.fee_percentage <= 1):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Fee percentage must be between 0.0 and 1.0"
        )
        
    return crud.create_or_update_exchange_rate(
        db=db,
        source=rate_data.source_currency,
        target=rate_data.target_currency,
        rate=rate_data.rate,
        fee_percentage=rate_data.fee_percentage
    )
