from datetime import datetime
from sqlalchemy.orm import Session, selectinload
from . import models, schemas
from typing import Optional, List
from sqlalchemy import case, desc, and_, or_, select
from sqlalchemy import cast, String
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

# <editor-fold desc="Decision Letter-related functions">
# ---------- Decision Letter ----------

def get_decision_letter(db: Session, letter_id: int):
    return db.query(models.DecisionLetter).filter_by(id=letter_id).one()


def list_decision_letters(db: Session,
                          entity_type: EntityType,
                          entity_id: int) -> list[models.DecisionLetter]:
    q = (db.query(models.DecisionLetter).filter_by(entity_type=entity_type, entity_id=entity_id).all())
    return q  # type: ignore


def add_decision_letter(db: Session,
                        entity_type: EntityType,
                        entity_id: int,
                        link: str) -> models.DecisionLetter:
    obj = models.DecisionLetter(
        entity_type=entity_type,
        entity_id=entity_id,
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


def remove_decision_letter(db: Session, letter_id: int) -> None:
    db_letter = get_decision_letter(db, letter_id)
    if not db_letter:
        raise EntityNotFoundError(f"Decision letter #{letter_id} not found")
    db.delete(db_letter)
    db.commit()


# </editor-fold>

# <editor-fold desc="Grad School Activity-related functions">
# ---------- Grad School Activity ----------

# Grad School Activity Type
def get_grad_school_activity_type(db: Session, gsat_id: int):
    return db.query(models.GradSchoolActivityType).filter_by(id=gsat_id).first()


def list_grad_school_activity_types(db: Session) -> list[models.GradSchoolActivityType]:
    q = db.query(models.GradSchoolActivityType)
    return q.order_by(models.GradSchoolActivityType.type).all()  # type: ignore


def create_grad_school_activity_type(db: Session, gsat_in: schemas.GradSchoolActivityTypeCreate):
    db_gsat = models.GradSchoolActivityType(type=gsat_in.type)
    db.add(db_gsat)
    db.commit()
    db.refresh(db_gsat)
    return db_gsat


def update_grad_school_activity_type(db: Session, gsat_id: int, gsat_in: schemas.GradSchoolActivityTypeUpdate):
    db_gsat = get_grad_school_activity_type(db, gsat_id)
    if not db_gsat:
        raise EntityNotFoundError(f"Grad School Activity Type #{gsat_id} not found")
    if gsat_in.type is not None:
        db_gsat.type = gsat_in.type
    db.commit()
    db.refresh(db_gsat)
    return db_gsat


def delete_grad_school_activity_type(db: Session, gsat_id: int):
    db_gsat = get_grad_school_activity_type(db, gsat_id)
    if not db_gsat:
        raise EntityNotFoundError(f"Grad School Activity Type #{gsat_id} not found")

    # only if no related sub-entities
    if db_gsat.activities:
        raise Exception("Cannot delete grad school activity type with linked entities")

    db.delete(db_gsat)
    db.commit()


# Grad School Activity
def get_grad_school_activity(db: Session, gsa_id: int):
    return db.query(models.GradSchoolActivity).filter_by(id=gsa_id).first()


def list_grad_school_activities(
    db: Session,
    activity_type_id: Optional[int] = None,
    description:      Optional[str] = None,
    year:             Optional[int] = None,
    search:           Optional[str] = None
) -> list[models.GradSchoolActivity]:
    q = (
        db
        .query(models.GradSchoolActivity)
        # tell SQLAlchemy to eager‐load the .activity_type relationship in one go:
        .options(selectinload(models.GradSchoolActivity.activity_type))
    )

    if activity_type_id is not None:
        q = q.filter_by(activity_type_id=activity_type_id)
    if description is not None:
        q = q.filter_by(description=description)
    if year is not None:
        q = q.filter_by(year=year)

    if search:
        term = f"%{search}%"
        q = q.filter(
            or_(
                # note: .has(...) allows for searching across the FK‐relationship
                models.GradSchoolActivity.activity_type.has(
                    models.GradSchoolActivityType.type.ilike(term)
                ),
                models.GradSchoolActivity.description.ilike(term),
                # cast year to string for substring matches
                cast(models.GradSchoolActivity.year, String).ilike(term),
            )
        )

    q = (
        q.outerjoin(
            models.GradSchoolActivityType,
            models.GradSchoolActivity.activity_type_id == models.GradSchoolActivityType.id
        )
        .order_by(
            desc(models.GradSchoolActivity.year),
            models.GradSchoolActivityType.type
        )
    )

    return q.all()  # type: ignore


def create_grad_school_activity(db: Session, gsa_in: schemas.GradSchoolActivityCreate):
    # guard duplicate
    dup_q = db.query(models.GradSchoolActivity).filter_by(activity_type_id=gsa_in.activity_type_id)
    if gsa_in.description is not None:
        dup_q = dup_q.filter_by(description=gsa_in.description)
    if gsa_in.year is not None:
        dup_q = dup_q.filter_by(year=gsa_in.year)
    else:
        raise Exception("Grad school activity must have a year")
    if dup_q.first():
        raise Exception("Grad school activity with same activity type, description and year already exists")

    gsa = models.GradSchoolActivity(**gsa_in.model_dump())
    db.add(gsa)
    db.commit()
    db.refresh(gsa)
    return gsa


def update_grad_school_activity(
    db: Session,
    gsa_id: int,
    gsa_in: schemas.GradSchoolActivityUpdate
):
    gsa = get_grad_school_activity(db, gsa_id)
    if not gsa:
        raise EntityNotFoundError(f"Grad school activity #{gsa_id} not found")

    for field in ("activity_type_id", "description", "year"):
        val = getattr(gsa_in, field)
        if val is not None:
            setattr(gsa, field, val)

    db.commit()
    db.refresh(gsa)
    return gsa


def delete_grad_school_activity(db: Session, gsa_id: int):
    gsa = get_grad_school_activity(db, gsa_id)
    if not gsa_id:
        raise EntityNotFoundError(f"Grad school activity #{gsa_id} not found")

    # only if no related sub-entities
    if gsa.student_activities or gsa.courses:
        raise Exception("Cannot delete grad school activity with linked entities")

    db.delete(gsa)
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

# <editor-fold desc="Project-related functions">
# ---------- Project ----------

# Project Call Type
def get_project_call_type(db: Session, pct_id: int):
    return db.query(models.ProjectCallType).filter_by(id=pct_id).first()


def list_project_call_types(db: Session) -> list[models.ProjectCallType]:
    q = db.query(models.ProjectCallType)
    return q.order_by(models.ProjectCallType.type).all()  # type: ignore


def create_project_call_type(db: Session, pct_in: schemas.ProjectCallTypeCreate):
    db_pct = models.ProjectCallType(type=pct_in.type)
    db.add(db_pct)
    db.commit()
    db.refresh(db_pct)
    return db_pct


def update_project_call_type(db: Session, pct_id: int, pct_in: schemas.ProjectCallTypeUpdate):
    db_pct = get_project_call_type(db, pct_id)
    if not db_pct:
        raise EntityNotFoundError(f"Project Call Type #{pct_id} not found")
    if pct_in.type is not None:
        db_pct.type = pct_in.type
    db.commit()
    db.refresh(db_pct)
    return db_pct


def delete_project_call_type(db: Session, pct_id: int):
    db_pct = get_project_call_type(db, pct_id)
    if not db_pct:
        raise EntityNotFoundError(f"Project Call Type #{pct_id} not found")

    # only if no related sub-entities
    if db_pct.projects:
        raise Exception("Cannot delete project call type with linked entities")

    db.delete(db_pct)
    db.commit()


# Research output report
def get_research_output_report(db: Session, report_id: int):
    return db.query(models.ResearchOutputReport).filter_by(id=report_id).one()


def list_research_output_reports(db: Session, project_id: int) -> list[models.ResearchOutputReport]:
    q = (db.query(models.ResearchOutputReport).filter_by(project_id=project_id).all())
    return q  # type: ignore


def add_research_output_report(db: Session, project_id: int, link: str) -> models.ResearchOutputReport:
    obj = models.ResearchOutputReport(
        project_id=project_id,
        link=link
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def update_research_output_report(db: Session, report_id: int, report_in: schemas.ResearchOutputReportUpdate):
    db_report = get_research_output_report(db, report_id)
    if not db_report:
        raise EntityNotFoundError(f"Research output report #{report_id} not found")
    if report_in.link is not None:
        db_report.link = report_in.link
    db.commit()
    db.refresh(db_report)
    return db_report


def remove_research_output_report(db: Session, report_id: int) -> None:
    db_report = get_research_output_report(db, report_id)
    if not db_report:
        raise EntityNotFoundError(f"Research output report #{report_id} not found")
    db.delete(db_report)
    db.commit()


# Project
def get_project(db: Session, project_id: int):
    return db.query(models.Project).filter_by(id=project_id).first()


def list_projects(db: Session, call_type_id: Optional[int] = None, title: Optional[str] = None,
                  project_number: Optional[str] = None, is_affiliated: Optional[bool] = None,
                  is_extended: Optional[bool] = None,
                  is_active: Optional[bool] = None,
                  search: Optional[str] = None):
    q = db.query(models.Project)

    if call_type_id is not None:
        q = q.filter_by(call_type_id=call_type_id)
    if title is not None:
        q = q.filter_by(title=title)
    if project_number is not None:
        q = q.filter_by(project_number=project_number)
    if is_affiliated is not None:
        q = q.filter_by(is_affiliated=is_affiliated)
    if is_extended is not None:
        q = q.filter_by(is_extended=is_extended)

    if is_active is not None:
        if is_active:
            q = q.filter(models.Project.end_date.is_(None))
        else:
            q = q.filter(models.Project.end_date.is_not(None))

    # if start_date is not None:
    #     q = q.filter(models.Project.start_date >= start_date)
    # if end_date is not None:
    #     q = q.filter(models.Project.end_date <= end_date)

    if search:
        term = f"%{search}%"
        q = q.filter(
            or_(
                models.Project.title.ilike(term),
                models.Project.project_number.ilike(term),
            )
        )

    q = (
        q.outerjoin(models.ProjectCallType, models.Project.call_type_id == models.ProjectCallType.id)
        .order_by(desc(models.Project.start_date))
    )

    return q.all()  # type: ignore


def create_project(db: Session, p_in: schemas.ProjectCreate):
    # guard duplicate within same term or same activity
    dup_q = db.query(models.Project).filter_by(project_number=p_in.project_number)
    if dup_q.first():
        raise Exception("Project with same project number already exists")

    p = models.Project(**p_in.model_dump())
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


def update_project(db: Session, project_id: int, p_in: schemas.ProjectUpdate):
    p = get_project(db, project_id)
    if not p:
        raise EntityNotFoundError(f"Project #{project_id} not found")

    for field in ("call_type_id", "title", "project_number", "is_affiliated",
                  "is_extended", "start_date", "end_date", "notes"):
        val = getattr(p_in, field)
        if val is not None:
            setattr(p, field, val)

    db.commit()
    db.refresh(p)
    return p


def delete_project(db: Session, project_id: int):
    p = get_project(db, project_id)
    if not p:
        raise EntityNotFoundError(f"Project #{project_id} not found")

    # only if no related sub-entities
    if p.fields or p.person_projects or p.research_output_reports or p.decision_letters:
        raise Exception("Cannot delete project with linked entities")

    db.delete(p)
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

# <editor-fold desc="Project relationships functions">
# --- academic fields for a project ---
def get_project_fields(db: Session, project_id: int) -> list[models.AcademicField]:
    # ensure project exists
    project = get_project(db, project_id)
    if not project:
        raise EntityNotFoundError(f"Project #{project_id} not found")
    joins = db.query(models.ProjectField).filter_by(project_id=project_id).all()
    return [j.field for j in joins]


def add_field_to_project(db: Session, project_id: int, field_id: int) -> models.AcademicField:
    # look up both ends
    project = get_project(db, project_id)
    if not project:
        raise EntityNotFoundError(f"Project #{project_id} not found")
    field = get_field(db, field_id)
    if not field:
        raise EntityNotFoundError(f"Academic field #{field_id} not found")
    # no dupes
    exists = db.query(models.ProjectField).filter_by(
        project_id=project_id, field_id=field_id
    ).first()
    if exists:
        raise Exception(f"Academic field #{field_id} already linked to Project #{project_id}")
    link = models.ProjectField(project_id=project_id, field_id=field_id)
    db.add(link)
    db.commit()
    return field  # type: ignore


def remove_field_from_project(db: Session, project_id: int, field_id: int):
    link = db.query(models.ProjectField).filter_by(
        project_id=project_id, field_id=field_id
    ).first()
    if not link:
        raise EntityNotFoundError(
            f"Academic field #{field_id} not linked to Project #{project_id}"
        )
    db.delete(link)
    db.commit()


# </editor-fold>
