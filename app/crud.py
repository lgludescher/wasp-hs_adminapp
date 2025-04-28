from sqlalchemy.orm import Session
from . import models, schemas


def get_user(db: Session, username: str):
    return db.query(models.User).filter(models.User.username == username).first()


def get_users(db: Session):
    return db.query(models.User).all()


def create_user(db: Session, user_in: schemas.UserCreate, is_admin: bool = False):
    db_user = models.User(username=user_in.username, is_admin=is_admin)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user
