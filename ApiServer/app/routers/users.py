from fastapi import APIRouter, Depends, HTTPException, status

from app import crud, schemas, auth
from app.database import get_db

router = APIRouter(
    prefix="/users",
    tags=["Users"]
)


@router.get("/me", response_model=schemas.UserResponse)
def read_user_me(current_user: dict = Depends(auth.get_current_user)):
    return current_user


@router.post("/me/kyc", response_model=schemas.UserResponse)
def submit_kyc(
    kyc_data: schemas.KycSubmission,
    current_user: dict = Depends(auth.get_current_user),
    conn=Depends(get_db)
):
    if current_user.get("kyc_status") == "APPROVED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="KYC is already approved"
        )

    allowed_types = ["passport", "national_id", "drivers_license"]
    if kyc_data.kyc_document_type.lower() not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid document type. Allowed types are: {', '.join(allowed_types)}"
        )

    return crud.update_user_kyc(
        conn,
        user_id=current_user["id"],
        doc_type=kyc_data.kyc_document_type.lower(),
        doc_number=kyc_data.kyc_document_number
    )


@router.put("/me/settings", response_model=schemas.UserResponse)
def update_user_settings(
    settings: schemas.BaseCurrencyUpdate,
    current_user: dict = Depends(auth.get_current_user),
    conn=Depends(get_db)
):
    allowed_currencies = ["USD", "EUR", "GBP", "KES", "INR", "PHP", "MXN"]
    currency = settings.base_currency.upper()
    if currency not in allowed_currencies:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported currency. Allowed: {', '.join(allowed_currencies)}"
        )
    return crud.update_user_base_currency(conn, user_id=current_user["id"], currency=currency)


@router.post("/me/deposit", response_model=schemas.WalletResponse)
def deposit_funds(
    deposit: schemas.WalletDeposit,
    current_user: dict = Depends(auth.get_current_user),
    conn=Depends(get_db)
):
    updated_user = crud.update_user_balance(conn, user_id=current_user["id"], amount=deposit.amount)
    return schemas.WalletResponse(wallet_balance=updated_user["wallet_balance"])
