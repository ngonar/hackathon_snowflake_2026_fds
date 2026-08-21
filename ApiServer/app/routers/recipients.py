from fastapi import APIRouter, Depends, HTTPException, status
from typing import List

from app import crud, schemas, auth
from app.database import get_db

router = APIRouter(
    prefix="/recipients",
    tags=["Recipients"]
)


@router.post("", response_model=schemas.RecipientResponse, status_code=status.HTTP_201_CREATED)
def create_recipient(
    recipient: schemas.RecipientCreate,
    current_user: dict = Depends(auth.get_current_user),
    conn=Depends(get_db)
):
    return crud.create_recipient(
        conn,
        sender_id=current_user["id"],
        name=recipient.name,
        bank_name=recipient.bank_name,
        account_number=recipient.account_number,
        routing_number=recipient.routing_number,
        country=recipient.country,
        currency=recipient.currency,
    )


@router.get("", response_model=List[schemas.RecipientResponse])
def list_recipients(
    current_user: dict = Depends(auth.get_current_user),
    conn=Depends(get_db)
):
    return crud.get_recipients_by_sender(conn, sender_id=current_user["id"])
