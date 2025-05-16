from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session
from .database import SessionLocal
from .config import settings
from . import crud, schemas


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    x_remote_user: str = Header(None),
    auth:          str = Header(None, alias="Auth"),
    x_dev_user:    str = Header(None, alias="X-Dev-User"),
    db: Session = Depends(get_db)
) -> schemas.UserRead:

    # -- Local development fallback (only when debug=True) --
    if settings.debug and x_dev_user:
        user = crud.get_user(db, x_dev_user)
        if not user:
            user = crud.create_user(
                db,
                schemas.UserCreate(username=x_dev_user, name=x_dev_user, email=f"{x_dev_user}@example.com"),
                is_admin=True
            )
        return user

    # -- Production path: require static header, then remote-user --
    if auth != settings.auth_token:
        raise HTTPException(401, "Invalid auth token")

    if not x_remote_user:
        raise HTTPException(401, "Authentication required")

    user = crud.get_user(db, x_remote_user)
    if not user:
        raise HTTPException(403, "User not provisioned")
    return user
