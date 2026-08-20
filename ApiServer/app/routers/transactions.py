import csv
import io

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, UploadFile, File
from sqlalchemy.orm import Session
from typing import List

from app import crud, schemas, auth, models
from app.database import get_db
from app.queue import publish_transaction_message

router = APIRouter(
    prefix="/transactions",
    tags=["Transactions"]
)

@router.post("", response_model=schemas.TransactionResponse, status_code=status.HTTP_201_CREATED)
def create_remittance_transaction(
    payload: schemas.TransactionCreate,
    background_tasks: BackgroundTasks,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    # 1. Verify KYC status is APPROVED
    if current_user.kyc_status != "APPROVED":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"KYC approval is required to perform transfers. Current status: {current_user.kyc_status}"
        )
        
    # 2. Verify recipient exists and belongs to current user
    recipient = crud.get_recipient(db, payload.recipient_id)
    if not recipient or recipient.sender_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recipient not found"
        )
        
    source_currency = "USD"  # Wallet currency is anchored in USD
    target_currency = recipient.currency.upper()
    
    # 3. Retrieve rate and calculate fee
    if source_currency == target_currency:
        rate = 1.0
        fee_percentage = 0.005  # 0.5% internal transfer fee
    else:
        rate_record = crud.get_exchange_rate(db, source_currency, target_currency)
        if not rate_record:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Remittance to currency {target_currency} is not currently supported"
            )
        rate = rate_record.rate
        fee_percentage = rate_record.fee_percentage
        
    fee = round(payload.source_amount * fee_percentage, 2)
    target_amount = round(payload.source_amount * rate, 2)
    
    # 4. Create database transaction (Status: PENDING)
    db_txn = crud.create_transaction(
        db=db,
        sender_id=current_user.id,
        recipient_id=recipient.id,
        source_currency=source_currency,
        target_currency=target_currency,
        source_amount=payload.source_amount,
        target_amount=target_amount,
        exchange_rate=rate,
        fee=fee
    )
    
    # 5. Publish details to RabbitMQ in the background
    txn_dict = schemas.TransactionResponse.model_validate(db_txn).model_dump(mode="json")
    background_tasks.add_task(publish_transaction_message, txn_dict)
    
    return db_txn


@router.post("/{txn_id}/fund", response_model=schemas.TransactionResponse)
def fund_transaction(
    txn_id: int,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    # 1. Fetch transaction
    txn = crud.get_transaction(db, txn_id)
    if not txn or txn.sender_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found"
        )
        
    # 2. Check transaction status
    if txn.status != "PENDING":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Transaction cannot be funded because it is in status: {txn.status}"
        )
        
    # 3. Calculate total cost
    total_cost = txn.source_amount + txn.fee
    
    # 4. Check user balance
    if current_user.wallet_balance < total_cost:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Insufficient wallet balance. Required: {total_cost} USD, Available: {current_user.wallet_balance} USD"
        )
        
    # 5. Deduct balance and update transaction status to FUNDED
    crud.update_user_balance(db=db, user_id=current_user.id, amount=-total_cost)
    updated_txn = crud.update_transaction_status(db=db, txn_id=txn.id, new_status="FUNDED")
    
    return updated_txn


@router.get("", response_model=List[schemas.TransactionResponse])
def list_my_transactions(
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    return crud.get_transactions_by_sender(db=db, sender_id=current_user.id)


@router.post("/bulk", response_model=schemas.BulkTransferResult)
async def bulk_transfer(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.kyc_status != "APPROVED":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="KYC approval is required to perform transfers"
        )

    if not file.filename.endswith('.csv'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only CSV files are accepted"
        )

    content = await file.read()
    try:
        text = content.decode('utf-8')
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be UTF-8 encoded"
        )

    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames or 'recipient_id' not in reader.fieldnames or 'source_amount' not in reader.fieldnames:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="CSV must contain 'recipient_id' and 'source_amount' columns"
        )

    successful = []
    failed = []
    source_currency = "USD"

    for row_num, row in enumerate(reader, start=1):
        try:
            recipient_id = int(row['recipient_id'])
            source_amount = float(row['source_amount'])
        except (ValueError, TypeError):
            failed.append(schemas.BulkTransferRowError(
                row=row_num,
                recipient_id=None,
                source_amount=None,
                error="Invalid recipient_id or source_amount value"
            ))
            continue

        if source_amount <= 0:
            failed.append(schemas.BulkTransferRowError(
                row=row_num, recipient_id=recipient_id, source_amount=source_amount,
                error="source_amount must be greater than 0"
            ))
            continue

        recipient = crud.get_recipient(db, recipient_id)
        if not recipient or recipient.sender_id != current_user.id:
            failed.append(schemas.BulkTransferRowError(
                row=row_num, recipient_id=recipient_id, source_amount=source_amount,
                error="Recipient not found or does not belong to you"
            ))
            continue

        target_currency = recipient.currency.upper()
        if source_currency == target_currency:
            rate = 1.0
            fee_percentage = 0.005
        else:
            rate_record = crud.get_exchange_rate(db, source_currency, target_currency)
            if not rate_record:
                failed.append(schemas.BulkTransferRowError(
                    row=row_num, recipient_id=recipient_id, source_amount=source_amount,
                    error=f"Currency {target_currency} not supported"
                ))
                continue
            rate = rate_record.rate
            fee_percentage = rate_record.fee_percentage

        fee = round(source_amount * fee_percentage, 2)
        target_amount = round(source_amount * rate, 2)

        db_txn = crud.create_transaction(
            db=db,
            sender_id=current_user.id,
            recipient_id=recipient.id,
            source_currency=source_currency,
            target_currency=target_currency,
            source_amount=source_amount,
            target_amount=target_amount,
            exchange_rate=rate,
            fee=fee
        )

        txn_dict = schemas.TransactionResponse.model_validate(db_txn).model_dump(mode="json")
        background_tasks.add_task(publish_transaction_message, txn_dict)
        successful.append(db_txn)

    return schemas.BulkTransferResult(
        total=len(successful) + len(failed),
        successful=[schemas.TransactionResponse.model_validate(t) for t in successful],
        failed=failed
    )


@router.get("/{txn_id}", response_model=schemas.TransactionResponse)
def get_transaction_details(
    txn_id: int,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    txn = crud.get_transaction(db, txn_id)
    if not txn or txn.sender_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found"
        )
    return txn
