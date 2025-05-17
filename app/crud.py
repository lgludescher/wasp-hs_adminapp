from sqlalchemy.orm import Session
from . import models, schemas
from typing import Optional
from sqlalchemy import or_


class EntityNotFoundError(Exception):
    pass


def get_user(db: Session, username: str):
    return db.query(models.User).filter_by(username=username).first()


def get_users(db: Session, is_admin: Optional[bool] = None, search: Optional[str] = None):
    q = db.query(models.User)
    if is_admin is not None:
        q = q.filter_by(is_admin=is_admin)

    if search:
        term = f"%{search}%"
        # case-insensitive substring match
        q = q.filter(
            or_(
                models.User.username.ilike(term),
                models.User.name.ilike(term),
                models.User.email.ilike(term),
            )
        )

    # always return in alphabetical order by username
    return q.order_by(models.User.username).all()


def create_user(db: Session, user_in: schemas.UserCreate, is_admin: bool = False):
    db_user = models.User(
        username=user_in.username,
        name=user_in.name,
        email=user_in.email,
        is_admin=user_in.is_admin
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def update_user(db: Session, username: str, user_in: schemas.UserUpdate):
    db_user = get_user(db, username)
    if not db_user:
        raise EntityNotFoundError(f"User '{username}' not found")
    if user_in.name is not None:
        db_user.name = user_in.name
    if user_in.email is not None:
        db_user.email = user_in.email
    if user_in.is_admin is not None:
        db_user.is_admin = user_in.is_admin
    db.commit()
    db.refresh(db_user)
    return db_user


def delete_user(db: Session, username: str):
    db_user = get_user(db, username)
    if not db_user:
        raise EntityNotFoundError(f"User '{username}' not found")
    db.delete(db_user)
    db.commit()
