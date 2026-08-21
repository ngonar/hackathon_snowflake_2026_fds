from fastapi import APIRouter, Depends, HTTPException, status
from typing import List

from app import crud, schemas
from app.database import get_db

router = APIRouter(
    prefix="/rates",
    tags=["Exchange Rates"]
)


@router.get("", response_model=List[schemas.ExchangeRateResponse])
def get_all_rates(conn=Depends(get_db)):
    return crud.get_all_exchange_rates(conn)


@router.get("/estimate", response_model=schemas.EstimateResponse)
def estimate_transfer(
    source_currency: str,
    target_currency: str,
    source_amount: float,
    conn=Depends(get_db)
):
    if source_amount <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Source amount must be greater than zero"
        )

    rate_record = crud.get_exchange_rate(conn, source_currency, target_currency)
    if not rate_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Exchange rate for {source_currency.upper()} to {target_currency.upper()} not found or not supported"
        )

    fee = round(source_amount * rate_record["fee_percentage"], 2)
    target_amount = round(source_amount * rate_record["rate"], 2)
    total_required = round(source_amount + fee, 2)

    return schemas.EstimateResponse(
        source_currency=source_currency.upper(),
        target_currency=target_currency.upper(),
        source_amount=source_amount,
        exchange_rate=rate_record["rate"],
        fee=fee,
        target_amount=target_amount,
        total_required=total_required
    )
