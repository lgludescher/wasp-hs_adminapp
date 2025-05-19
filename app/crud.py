from sqlalchemy.orm import Session
from . import models, schemas
from typing import Optional
from sqlalchemy import or_


class EntityNotFoundError(Exception):
    pass


# ---------- User ----------

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


# ---------- Institution ----------

def get_institution(db: Session, institution_id: int):
    return db.query(models.Institution).filter_by(id=institution_id).first()


def get_institutions(db: Session, name: Optional[str] = None, search: Optional[str] = None):
    q = db.query(models.Institution)
    if name is not None:
        # exact‐match lookup for duplicate‐check
        return q.filter_by(institution=name).first()

    if search:
        term = f"%{search}%"
        q = q.filter(models.Institution.institution.ilike(term))

    return q.order_by(models.Institution.institution).all()


def create_institution(db: Session, inst_in: schemas.InstitutionCreate):
    db_inst = models.Institution(institution=inst_in.institution)
    db.add(db_inst)
    db.commit()
    db.refresh(db_inst)
    return db_inst


def update_institution(db: Session, institution_id: int, inst_in: schemas.InstitutionUpdate):
    db_inst = get_institution(db, institution_id)
    if not db_inst:
        raise EntityNotFoundError(f"Institution #{institution_id} not found")
    if inst_in.institution is not None:
        db_inst.institution = inst_in.institution
    db.commit()
    db.refresh(db_inst)
    return db_inst


def delete_institution(db: Session, institution_id: int):
    db_inst = get_institution(db, institution_id)
    if not db_inst:
        raise EntityNotFoundError(f"Institution #{institution_id} not found")
    db.delete(db_inst)
    db.commit()


# ---------- Domain ----------

# Academic Branch
def get_branch(db: Session, branch_id: int):
    return db.query(models.AcademicBranch).filter_by(id=branch_id).first()


def get_branches(db: Session, name: Optional[str] = None, search: Optional[str] = None):
    q = db.query(models.AcademicBranch)
    if name is not None:
        # exact-match lookup for duplicate check
        return q.filter_by(branch=name).first()

    if search:
        term = f"%{search}%"
        q = q.filter(models.AcademicBranch.branch.ilike(term))

    return q.order_by(models.AcademicBranch.branch).all()


def create_branch(db: Session, branch_in: schemas.BranchCreate):
    db_branch = models.AcademicBranch(branch=branch_in.branch)
    db.add(db_branch)
    db.commit()
    db.refresh(db_branch)
    return db_branch


def update_branch(db: Session, branch_id: int, branch_in: schemas.BranchUpdate):
    db_branch = get_branch(db, branch_id)
    if not db_branch:
        raise EntityNotFoundError(f"Branch #{branch_id} not found")
    if branch_in.branch is not None:
        db_branch.branch = branch_in.branch
    db.commit()
    db.refresh(db_branch)
    return db_branch


def delete_branch(db: Session, branch_id: int):
    db_branch = get_branch(db, branch_id)
    if not db_branch:
        raise EntityNotFoundError(f"Branch #{branch_id} not found")
    # prevent deletion if fields exist
    if db_branch.fields:
        raise Exception(f"Branch #{branch_id} has fields; cannot delete")
    db.delete(db_branch)
    db.commit()


# Academic Field
def get_field(db: Session, field_id: int):
    return db.query(models.AcademicField).filter_by(id=field_id).first()


def get_fields(db: Session, branch_id: Optional[int] = None,
               name: Optional[str] = None, search: Optional[str] = None):
    q = db.query(models.AcademicField)
    if branch_id is not None:
        q = q.filter_by(branch_id=branch_id)

    if name is not None:
        # exact-match within branch (if given)
        return q.filter_by(field=name).first()

    if search:
        term = f"%{search}%"
        q = q.filter(models.AcademicField.field.ilike(term))

    return q.order_by(models.AcademicField.field).all()


def create_field(db: Session, field_in: schemas.FieldCreate):
    db_field = models.AcademicField(field=field_in.field, branch_id=field_in.branch_id)
    db.add(db_field)
    db.commit()
    db.refresh(db_field)
    return db_field


def update_field(db: Session, field_id:  int, field_in:  schemas.FieldUpdate):
    db_field = get_field(db, field_id)
    if not db_field:
        raise EntityNotFoundError(f"Field #{field_id} not found")
    if field_in.field is not None:
        db_field.field = field_in.field
    if field_in.branch_id is not None:
        db_field.branch_id = field_in.branch_id
    db.commit()
    db.refresh(db_field)
    return db_field


def delete_field(db: Session, field_id: int):
    db_field = get_field(db, field_id)
    if not db_field:
        raise EntityNotFoundError(f"Field #{field_id} not found")
    db.delete(db_field)
    db.commit()
