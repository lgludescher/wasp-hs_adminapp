from sqlalchemy.orm import Session
from . import models, schemas
from typing import Optional, List
from sqlalchemy import case, desc, and_, or_
from .models import Season, CourseTerm, GradSchoolActivity


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


# ---------- Course ----------

# Course Term
SEASON_ORDER = {
    Season.WINTER: 0,
    Season.SPRING: 1,
    Season.SUMMER: 2,
    Season.FALL:   3,
}


def get_course_term(db: Session, term_id: int):
    return db.query(models.CourseTerm).filter_by(id=term_id).first()


def list_course_terms(db: Session, active: Optional[bool] = None) -> list[models.CourseTerm]:
    q = db.query(models.CourseTerm)
    if active is not None:
        q = q.filter_by(is_active=active)

    # build a *mapping* of condition → sort order so SQLAlchemy sees a Mapping
    season_cases = {
        models.CourseTerm.season == s: order
        for s, order in SEASON_ORDER.items()
    }
    season_ordering = case(season_cases, else_=0)

    terms = (
        q.order_by(
            desc(models.CourseTerm.year),
            desc(season_ordering)
        )
        .all()
    )
    return terms  # type: ignore


def create_next_course_term(db: Session) -> models.CourseTerm:
    existing = list_course_terms(db)
    if existing:
        last = existing[0]
        idx = SEASON_ORDER[last.season]
        if idx < len(SEASON_ORDER) - 1:
            next_season = list(SEASON_ORDER)[idx + 1]
            next_year = last.year
        else:
            next_season = list(SEASON_ORDER)[0]
            next_year = last.year + 1
    else:
        # very first term: WINTER 2019
        next_season, next_year = list(SEASON_ORDER)[0], 2019

    new = models.CourseTerm(season=next_season, year=next_year)
    db.add(new)
    db.commit()
    db.refresh(new)
    return new


def update_course_term(db: Session, term_id: int, term_in: schemas.CourseTermUpdate):
    term = get_course_term(db, term_id)
    if not term:
        raise EntityNotFoundError(f"CourseTerm #{term_id} not found")
    term.is_active = term_in.is_active
    db.commit()
    db.refresh(term)
    return term


def delete_course_term(db: Session, term_id: int):
    term = get_course_term(db, term_id)
    if not term:
        raise EntityNotFoundError(f"CourseTerm #{term_id} not found")

    # only the very latest can be deleted, and only if no courses use it
    latest = list_course_terms(db)[0]
    if term.id != latest.id:
        raise Exception("Only the most recent term may be deleted")
    if term.courses:
        raise Exception("Cannot delete term in use by courses")

    db.delete(term)
    db.commit()


# Course
def get_course(db: Session, course_id: int):
    return db.query(models.Course).filter_by(id=course_id).first()


def list_courses(db: Session, title: Optional[str] = None, term_id: Optional[int] = None,
                 activity_id: Optional[int] = None, search: Optional[str] = None):
    q = db.query(models.Course)

    if title is not None:
        q = q.filter_by(title=title)
    if term_id is not None:
        q = q.filter_by(course_term_id=term_id)
    if activity_id is not None:
        q = q.filter_by(grad_school_activity_id=activity_id)

    if search:
        term = f"%{search}%"
        q = q.filter(models.Course.title.ilike(term))

    # build a *mapping* of condition → sort order so SQLAlchemy sees a Mapping
    season_cases = {
        models.CourseTerm.season == s: order
        for s, order in SEASON_ORDER.items()
    }
    season_ordering = case(season_cases, else_=0)

    # join term and activity to extract year, then order by descending year/season
    year_cases = {
        models.CourseTerm.year.isnot(None): models.CourseTerm.year,
        models.GradSchoolActivity.year.isnot(None): models.GradSchoolActivity.year
    }

    q = (
        q.outerjoin(models.CourseTerm, models.Course.course_term_id == models.CourseTerm.id)
        .outerjoin(models.GradSchoolActivity,
                   models.Course.grad_school_activity_id == models.GradSchoolActivity.id)
        .order_by(
            desc(case(year_cases, else_=0)),
            desc(season_ordering)
        )
    )

    return q.all()  # type: ignore


def create_course(db: Session, c_in: schemas.CourseCreate):
    # guard duplicate within same term or same activity
    dup_q = db.query(models.Course).filter_by(title=c_in.title)
    if c_in.course_term_id:
        dup_q = dup_q.filter_by(course_term_id=c_in.course_term_id)
    if c_in.grad_school_activity_id:
        dup_q = dup_q.filter_by(grad_school_activity_id=c_in.grad_school_activity_id)
    if dup_q.first():
        raise Exception("Course with same title and same term/activity already exists")

    c = models.Course(**c_in.model_dump())
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


def update_course(
    db: Session,
    course_id: int,
    c_in: schemas.CourseUpdate
):
    c = get_course(db, course_id)
    if not c:
        raise EntityNotFoundError(f"Course #{course_id} not found")

    for field in ("title", "course_term_id", "grad_school_activity_id", "credit_points", "notes"):
        val = getattr(c_in, field)
        if val is not None:
            setattr(c, field, val)

    db.commit()
    db.refresh(c)
    return c


def delete_course(db: Session, course_id: int):
    c = get_course(db, course_id)
    if not c:
        raise EntityNotFoundError(f"Course #{course_id} not found")

    # only if no related sub-entities
    if c.student_courses or c.course_institutions or c.teachers or c.decision_letters:
        raise Exception("Cannot delete course with linked entities")

    db.delete(c)
    db.commit()
