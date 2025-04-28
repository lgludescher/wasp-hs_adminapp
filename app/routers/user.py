from fastapi import APIRouter, Depends, HTTPException
from typing import List
from sqlalchemy.orm import Session
from .. import crud, schemas, dependencies

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/", response_model=List[schemas.UserRead])
async def list_users(
    current_user: schemas.UserRead = Depends(dependencies.get_current_user),
    db: Session = Depends(dependencies.get_db)
):
    if not current_user.is_admin:
        raise HTTPException(403, "Only admins can list users")
    return crud.get_users(db)


@router.post("/", response_model=schemas.UserRead)
async def create_user(
    user_in: schemas.UserCreate,
    current_user: schemas.UserRead = Depends(dependencies.get_current_user),
    db: Session = Depends(dependencies.get_db)
):
    if not current_user.is_admin:
        raise HTTPException(403, "Only admins can create users")
    return crud.create_user(db, user_in)
