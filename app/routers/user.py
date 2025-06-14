from fastapi import APIRouter, Depends, HTTPException, Response, Query
from typing import List, Optional
from sqlalchemy.orm import Session
from .. import crud, schemas, dependencies
from ..crud import EntityNotFoundError
# from ..logger import logger
import logging

router = APIRouter(prefix="/users", tags=["users"])

logger = logging.getLogger(__name__)


# <editor-fold desc="User endpoints">

@router.get("/me", response_model=schemas.UserRead)
def read_current_user(
    current_user: schemas.UserRead = Depends(dependencies.get_current_user)
):
    """
    Return the currently authenticated user.
    - In DEBUG mode: X-Dev-User header
    - In PROD: Auth + X-Remote-User injected by Apache
    """
    return current_user


@router.get("/{username}", response_model=schemas.UserRead)
async def read_user(
    username: str,
    current_user: schemas.UserRead = Depends(dependencies.get_current_user),
    db: Session = Depends(dependencies.get_db)
):
    # allow admins to fetch anyone, non-admins only themselves
    if not current_user.is_admin and current_user.username != username:
        logger.warning(f"{current_user.username} forbidden from reading {username}")
        raise HTTPException(403, "Not allowed to fetch this user")

    user = crud.get_user(db, username)
    if not user:
        logger.warning(f"User '{username}' not found")
        raise HTTPException(404, f"User '{username}' not found")

    logger.info(f"{current_user.username} fetched user '{username}'")

    return user


@router.get("/", response_model=List[schemas.UserRead])
async def list_users(
    is_admin: Optional[bool] = Query(None, description="Filter by admin status"),
    search:   Optional[str] = Query(None, description="Substring search on username, name, or email"),
    current_user: schemas.UserRead = Depends(dependencies.get_current_user),
    db: Session = Depends(dependencies.get_db)
):
    if not current_user.is_admin:
        logger.warning(f"Unauthorized list_users attempt by {current_user.username}")
        raise HTTPException(403, "Only admins can list users")

    logger.info(f"{current_user.username} listed users (is_admin={is_admin}, search={search!r})")
    return crud.get_users(db, is_admin=is_admin, search=search)


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

    if username == current_user.username:
        logger.warning(f"Attempt by {current_user.username} to delete their own account denied")
        raise HTTPException(
            status_code=400,
            detail="Cannot delete your own account"
        )

    logger.info(f"{current_user.username} deleting user {username}")

    try:
        crud.delete_user(db, username)
    except EntityNotFoundError as e:
        logger.warning(f"Delete failed for {username}: {e}")
        raise HTTPException(404, str(e))
    return Response(status_code=204)


# </editor-fold>
