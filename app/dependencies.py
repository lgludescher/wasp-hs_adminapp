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
    x_dev_user:    str = Header(None, alias="X-Dev-User"),
    db: Session = Depends(get_db)
) -> schemas.UserRead:
    # 1) Production path: Apache will set X-Remote-User
    if x_remote_user:
        user = crud.get_user(db, x_remote_user)
        if not user:
            raise HTTPException(403, "User not provisioned")
        return user

    # 2) Local fallback: only when DEBUG is on
    if settings.debug and x_dev_user:
        user = crud.get_user(db, x_dev_user)
        if not user:
            # auto-create a dev admin so you can test
            user = crud.create_user(db,
                                    schemas.UserCreate(username=x_dev_user),
                                    is_admin=True)
        return user

    # 3) otherwise, block
    raise HTTPException(401, "Authentication required")
