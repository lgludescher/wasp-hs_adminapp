from fastapi import APIRouter, Depends, HTTPException, Response
from typing import List
from sqlalchemy.orm import Session
from .. import crud, schemas, dependencies
from ..crud import EntityNotFoundError

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

    # Check for existing user
    existing = crud.get_user(db, user_in.username)
    if existing:
        raise HTTPException(status_code=400, detail=f"User '{user_in.username}' already exists")

    return crud.create_user(db, user_in)


@router.put("/{username}", response_model=schemas.UserRead)
async def update_user(
    username: str,
    user_in: schemas.UserUpdate,
    current_user: schemas.UserRead = Depends(dependencies.get_current_user),
    db: Session = Depends(dependencies.get_db),
):
    if not current_user.is_admin:
        raise HTTPException(403, "Only admins can update users")
    try:
        return crud.update_user(db, username, user_in)
    except EntityNotFoundError as e:
        raise HTTPException(404, str(e))


@router.delete("/{username}", status_code=204)
async def delete_user(
    username: str,
    current_user: schemas.UserRead = Depends(dependencies.get_current_user),
    db: Session = Depends(dependencies.get_db),
):
    if not current_user.is_admin:
        raise HTTPException(403, "Only admins can delete users")
    try:
        crud.delete_user(db, username)
    except EntityNotFoundError as e:
        raise HTTPException(404, str(e))
    return Response(status_code=204)
