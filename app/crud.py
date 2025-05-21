from sqlalchemy.orm import Session
from . import models, schemas
from typing import Optional, List
from sqlalchemy import case, desc, and_, or_, select
from .models import Season, CourseTerm, GradSchoolActivity, EntityType, GradeType
from sqlalchemy.exc import NoResultFound


class EntityNotFoundError(Exception):
    pass


# <editor-fold desc="User-related functions">
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


# </editor-fold>

# <editor-fold desc="Institution-related functions">
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


# </editor-fold>

# <editor-fold desc="Domain-related functions">
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


# </editor-fold>

# <editor-fold desc="Course-related functions">
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


# </editor-fold>

# <editor-fold desc="Course relationships functions">
# --- institutions for a course ---
def get_course_institutions(db: Session, course_id: int) -> list[models.Institution]:
    # ensure course exists
    course = get_course(db, course_id)
    if not course:
        raise EntityNotFoundError(f"Course #{course_id} not found")
    joins = db.query(models.CourseInstitution).filter_by(course_id=course_id).all()
    return [j.institution for j in joins]


def add_institution_to_course(db: Session, course_id: int, institution_id: int) -> models.Institution:
    # look up both ends
    course = get_course(db, course_id)
    if not course:
        raise EntityNotFoundError(f"Course #{course_id} not found")
    inst = get_institution(db, institution_id)
    if not inst:
        raise EntityNotFoundError(f"Institution #{institution_id} not found")
    # no dupes
    exists = db.query(models.CourseInstitution).filter_by(
        course_id=course_id, institution_id=institution_id
    ).first()
    if exists:
        raise Exception(f"Institution #{institution_id} already linked to Course #{course_id}")
    link = models.CourseInstitution(course_id=course_id, institution_id=institution_id)
    db.add(link)
    db.commit()
    return inst  # type: ignore


def remove_institution_from_course(db: Session, course_id: int, institution_id: int):
    link = db.query(models.CourseInstitution).filter_by(
        course_id=course_id, institution_id=institution_id
    ).first()
    if not link:
        raise EntityNotFoundError(
            f"Institution #{institution_id} not linked to Course #{course_id}"
        )
    db.delete(link)
    db.commit()

# def list_course_institutions(db: Session, course_id: int) -> list[models.Institution]:
#     return (
#         db.query(models.Institution)
#         .join(models.CourseInstitution)
#         .filter(models.CourseInstitution.course_id == course_id)
#         .all()
#     )
#
#
# def add_course_institution(db: Session, course_id: int, inst_id: int) -> models.CourseInstitution:
#     obj = models.CourseInstitution(course_id=course_id, institution_id=inst_id)
#     db.add(obj)
#     db.commit()
#     db.refresh(obj)
#     return obj
#
#
# def remove_course_institution(db: Session, course_id: int, inst_id: int) -> None:
#     ci = (
#         db.query(models.CourseInstitution)
#         .filter_by(course_id=course_id, institution_id=inst_id)
#         .one()
#     )
#     db.delete(ci)
#     db.commit()


# --- students for a course ---
# def list_course_students(db: Session, course_id: int) -> list[models.PhDStudent]:
#     return (
#         db.query(models.PhDStudent)
#         .join(models.PhDStudentCourse)
#         .filter(models.PhDStudentCourse.course_id == course_id)
#         .all()
#     )
#
#
# def add_course_student(db: Session, course_id: int, s: schemas.CourseStudentCreate) -> models.PhDStudentCourse:
#     obj = models.PhDStudentCourse(
#         course_id=course_id,
#         phd_student_id=s.phd_student_id,
#         is_completed=s.is_completed,
#         grade=s.grade
#     )
#     db.add(obj)
#     db.commit()
#     db.refresh(obj)
#     return obj
#
#
# def remove_course_student(db: Session, course_id: int, phd_student_id: int) -> None:
#     sc = (
#         db.query(models.PhDStudentCourse)
#         .filter_by(course_id=course_id, phd_student_id=phd_student_id)
#         .one()
#     )
#     db.delete(sc)
#     db.commit()


# --- teachers for a course ---
# def list_course_teachers(db: Session, course_id: int) -> list[models.PersonRole]:
#     return (
#         db.query(models.PersonRole)
#         .join(models.CourseTeacher)
#         .filter(models.CourseTeacher.course_id == course_id)
#         .all()
#     )
#
#
# def add_course_teacher(db: Session, course_id: int, person_role_id: int) -> models.CourseTeacher:
#     obj = models.CourseTeacher(course_id=course_id, person_role_id=person_role_id)
#     db.add(obj)
#     db.commit()
#     db.refresh(obj)
#     return obj
#
#
# def remove_course_teacher(db: Session, course_id: int, person_role_id: int) -> None:
#     ct = (
#         db.query(models.CourseTeacher)
#         .filter_by(course_id=course_id, person_role_id=person_role_id)
#         .one()
#     )
#     db.delete(ct)
#     db.commit()


# --- decision letters for a course ---

def get_decision_letter(db: Session, letter_id: int):
    return db.query(models.DecisionLetter).filter_by(id=letter_id).one()


def list_course_decision_letters(db: Session, course_id: int) -> list[models.DecisionLetter]:
    q = (db.query(models.DecisionLetter).filter_by(entity_type=EntityType.COURSE, entity_id=course_id).all())
    return q  # type: ignore


def add_course_decision_letter(db: Session, course_id: int, link: str) -> models.DecisionLetter:
    obj = models.DecisionLetter(
        entity_type=EntityType.COURSE,
        entity_id=course_id,
        link=link
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def update_decision_letter(db: Session, letter_id: int, letter_in: schemas.DecisionLetterUpdate):
    db_letter = get_decision_letter(db, letter_id)
    if not db_letter:
        raise EntityNotFoundError(f"Decision letter #{letter_id} not found")
    if letter_in.link is not None:
        db_letter.link = letter_in.link
    db.commit()
    db.refresh(db_letter)
    return db_letter


def remove_course_decision_letter(db: Session, letter_id: int) -> None:
    db_letter = get_decision_letter(db, letter_id)
    if not db_letter:
        raise EntityNotFoundError(f"Decision letter #{letter_id} not found")
    db.delete(db_letter)
    db.commit()


# --- helpers to seed PhDStudent in tests ---
# def create_person(db: Session, first_name: str, last_name: str, email: str) -> models.Person:
#     p = models.Person(first_name=first_name, last_name=last_name, email=email)
#     db.add(p)
#     db.commit()
#     db.refresh(p)
#     return p
#
#
# def create_person_role(db: Session, person_id: int, role_name: schemas.PyEnum) -> models.PersonRole:
#     # assume role already exists
#     r = db.query(models.Role).filter_by(role=role_name).one()
#     pr = models.PersonRole(person_id=person_id, role_id=r.id)
#     db.add(pr)
#     db.commit()
#     db.refresh(pr)
#     return pr
#
#
# def create_phd_student(db: Session, person_role_id: int) -> models.PhDStudent:
#     s = models.PhDStudent(person_role_id=person_role_id)
#     db.add(s)
#     db.commit()
#     db.refresh(s)
#     return s


# </editor-fold>
