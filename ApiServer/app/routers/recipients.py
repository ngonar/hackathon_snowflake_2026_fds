from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app import crud, schemas, auth, models
from app.database import get_db

router = APIRouter(
    prefix="/recipients",
    tags=["Recipients"]
)

@router.post("", response_model=schemas.RecipientResponse, status_code=status.HTTP_201_CREATED)
def create_recipient(
    recipient: schemas.RecipientCreate,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    # Standard check: sender cannot add a recipient to a country with unsupported exchange rates if we want,
    # but let's allow it generally or just assume standard currencies.
    return crud.create_recipient(db=db, sender_id=current_user.id, recipient=recipient)


@router.get("", response_model=List[schemas.RecipientResponse])
def list_recipients(
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    return crud.get_recipients_by_sender(db=db, sender_id=current_user.id)
