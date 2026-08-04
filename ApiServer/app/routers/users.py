from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import crud, schemas, auth, models
from app.database import get_db

router = APIRouter(
    prefix="/users",
    tags=["Users"]
)

@router.get("/me", response_model=schemas.UserResponse)
def read_user_me(current_user: models.User = Depends(auth.get_current_user)):
    return current_user


@router.post("/me/kyc", response_model=schemas.UserResponse)
def submit_kyc(
    kyc_data: schemas.KycSubmission,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.kyc_status == "APPROVED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="KYC is already approved"
        )
    
    # Simple validation of document type
    allowed_types = ["passport", "national_id", "drivers_license"]
    if kyc_data.kyc_document_type.lower() not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid document type. Allowed types are: {', '.join(allowed_types)}"
        )
        
    return crud.update_user_kyc(
        db=db, 
        user_id=current_user.id, 
        doc_type=kyc_data.kyc_document_type.lower(), 
        doc_number=kyc_data.kyc_document_number
    )


@router.post("/me/deposit", response_model=schemas.WalletResponse)
def deposit_funds(
    deposit: schemas.WalletDeposit,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    # Deposit is mocked and assumed in USD (or base currency)
    updated_user = crud.update_user_balance(db=db, user_id=current_user.id, amount=deposit.amount)
    return schemas.WalletResponse(wallet_balance=updated_user.wallet_balance)
