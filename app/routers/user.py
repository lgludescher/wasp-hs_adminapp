from fastapi import APIRouter, Depends, HTTPException, Response
from typing import List
from sqlalchemy.orm import Session
from .. import crud, schemas, dependencies
from ..crud import EntityNotFoundError
# from ..logger import logger
import logging

router = APIRouter(prefix="/users", tags=["users"])

logger = logging.getLogger(__name__)


@router.get("/", response_model=List[schemas.UserRead])
async def list_users(
    current_user: schemas.UserRead = Depends(dependencies.get_current_user),
    db: Session = Depends(dependencies.get_db)
):
    if not current_user.is_admin:
        logger.warning(f"Unauthorized list_users attempt by {current_user.username}")
        raise HTTPException(403, "Only admins can list users")

    logger.info(f"{current_user.username} listed all users")
    return crud.get_users(db)


@router.post("/", response_model=schemas.UserRead)
async def create_user(
    user_in: schemas.UserCreate,
    current_user: schemas.UserRead = Depends(dependencies.get_current_user),
    db: Session = Depends(dependencies.get_db)
):
    if not current_user.is_admin:
        logger.warning(f"Unauthorized create_user attempt by {current_user.username}")
        raise HTTPException(403, "Only admins can create users")

    logger.info(f"{current_user.username} creating user {user_in.username}")

    # Check for existing user
    existing = crud.get_user(db, user_in.username)
    if existing:
        logger.warning(f"Attempt to create duplicate user {user_in.username} by {current_user.username}")
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
        logger.warning(f"Unauthorized update_user attempt by {current_user.username}")
        raise HTTPException(403, "Only admins can update users")

    logger.info(f"{current_user.username} updating user {username} → {user_in}")

    try:
        return crud.update_user(db, username, user_in)
    except EntityNotFoundError as e:
        logger.warning(f"Update failed for {username}: {e}")
        raise HTTPException(404, str(e))


@router.delete("/{username}", status_code=204)
async def delete_user(
    username: str,
    current_user: schemas.UserRead = Depends(dependencies.get_current_user),
    db: Session = Depends(dependencies.get_db),
):
    if not current_user.is_admin:
        logger.warning(f"Unauthorized delete_user attempt by {current_user.username}")
        raise HTTPException(403, "Only admins can delete users")

    logger.info(f"{current_user.username} deleting user {username}")

    try:
        crud.delete_user(db, username)
    except EntityNotFoundError as e:
        logger.warning(f"Delete failed for {username}: {e}")
        raise HTTPException(404, str(e))
    return Response(status_code=204)
