from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session, selectinload
from . import models, schemas
from typing import Optional, List, Union
from sqlalchemy import case, desc, and_, or_, select
from sqlalchemy import cast, String
from .models import Season, CourseTerm, GradSchoolActivity, EntityType, GradeType, ActivityType
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
    Season.WINTER: -1, # Deprecated, but kept for sorting legacy data
    Season.SPRING: 0,
    Season.SUMMER: 1,
    Season.FALL:   2,
}

# A strict list of what creates a valid *new* term
ACTIVE_SEASONS = [Season.SPRING, Season.SUMMER, Season.FALL]

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
        last = existing[0]  # This is the most recent term

        # Scenario A: The DB ends with a "Winter" term (Legacy Data)
        # "Jumps" from the deprecated Winter to the new start: Spring of the SAME year.
        if last.season == Season.WINTER:
            next_season = Season.SPRING
            next_year = last.year

        # Scenario B: The DB ends with Spring, Summer, or Fall (Standard Cycle)
        else:
            # Find where it is in the ACTIVE list (0, 1, or 2)
            try:
                current_idx = ACTIVE_SEASONS.index(last.season)

                if current_idx < len(ACTIVE_SEASONS) - 1:
                    # Spring -> Summer, or Summer -> Fall
                    next_season = ACTIVE_SEASONS[current_idx + 1]
                    next_year = last.year
                else:
                    # Fall -> Spring (Next Year)
                    next_season = ACTIVE_SEASONS[0]
                    next_year = last.year + 1

            except ValueError:
                # Failsafe: If for some reason the season is not in ACTIVE_SEASONS
                # and not caught by the Winter check (shouldn't happen), default to Spring next year.
                next_season = ACTIVE_SEASONS[0]
                next_year = last.year + 1

        # --- LOGIC CHANGE END ---

    else:
        # Very first term for a NEW database (Spring 2019)
        next_season, next_year = Season.SPRING, 2019

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
                 activity_id: Optional[int] = None, is_active_term: Optional[bool] = None,
                 teacher_role_id: Optional[int] = None,
                 search: Optional[str] = None):

    q = db.query(models.Course)

    if title is not None:
        q = q.filter_by(title=title)
    if term_id is not None:
        q = q.filter_by(course_term_id=term_id)
    if activity_id is not None:
        q = q.filter_by(grad_school_activity_id=activity_id)

    # --- filter by teacher role ---
    if teacher_role_id is not None:
        q = (
            q.join(
                models.CourseTeacher,
                models.Course.id == models.CourseTeacher.course_id
            )
            .filter_by(person_role_id=teacher_role_id)
        )

    if search:
        term = f"%{search}%"
        q = q.filter(models.Course.title.ilike(term))

    if is_active_term is not None:
        # outer-join so term-less (i.e. grad-school) courses remain in the result,
        # then keep either “has a grad_school_activity” OR “term matches active flag”
        q = (
            q.outerjoin(
                models.CourseTerm,
                models.Course.course_term_id == models.CourseTerm.id
            )
            .filter(
                or_(
                    models.Course.grad_school_activity_id.isnot(None),
                    models.CourseTerm.is_active == is_active_term
                )
            )
        )
    else:
        q = (
            q.outerjoin(
                models.CourseTerm,
                models.Course.course_term_id == models.CourseTerm.id
            )
        )

    # always also outer‐join the grad‐school activity for ordering
    q = q.outerjoin(
        models.GradSchoolActivity,
        models.Course.grad_school_activity_id == models.GradSchoolActivity.id
    )

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

    q = q.order_by(
        desc(case(year_cases, else_=0)),
        desc(season_ordering)
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


def list_project_call_types(db: Session, search: Optional[str] = None) -> list[models.ProjectCallType]:
    q = db.query(models.ProjectCallType)

    if search:
        term = f"%{search}%"
        q = q.filter(models.ProjectCallType.type.ilike(term))

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
                  project_number: Optional[str] = None, final_report_submitted: Optional[bool] = None,
                  # is_affiliated: Optional[bool] = None,
                  is_extended: Optional[bool] = None,
                  # is_active: Optional[bool] = None,
                  project_status: Optional[str] = None,
                  field_id: Optional[int] = None,
                  branch_id: Optional[int] = None,
                  search: Optional[str] = None):
    q = db.query(models.Project)

    if call_type_id is not None:
        q = q.filter_by(call_type_id=call_type_id)
    if title is not None:
        q = q.filter_by(title=title)
    if project_number is not None:
        q = q.filter_by(project_number=project_number)
    # if is_affiliated is not None:
    #     q = q.filter_by(is_affiliated=is_affiliated)
    if final_report_submitted is not None:
        q = q.filter_by(final_report_submitted=final_report_submitted)
    if is_extended is not None:
        q = q.filter_by(is_extended=is_extended)

    # if is_active is not None:
    #     if is_active:
    #         q = q.filter(models.Project.end_date.is_(None))
    #     else:
    #         q = q.filter(models.Project.end_date.is_not(None))

    # project status
    if project_status is not None:

        start_of_today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

        if project_status.lower() == 'ongoing':
            q = q.filter(
                or_(
                    models.Project.end_date.is_(None),
                    models.Project.end_date >= start_of_today
                )
            )
        elif project_status.lower() == 'awaiting_report':
            q = q.filter(
                and_(
                    models.Project.end_date.is_not(None),
                    models.Project.end_date < start_of_today,
                    models.Project.final_report_submitted.is_(False)
                )
            )
        elif project_status.lower() == 'completed':
            q = q.filter(
                and_(
                    models.Project.end_date.is_not(None),
                    models.Project.end_date < start_of_today,
                    models.Project.final_report_submitted.is_(True)
                )
            )

    # filter by exact field link
    if field_id is not None:
        q = (
            q.join(
                models.ProjectField,
                models.Project.id == models.ProjectField.project_id
            )
            .filter_by(field_id=field_id)
        )

    # filter by branch via the AcademicField join
    if branch_id is not None:
        if field_id is None:  # not joined with ProjectField yet
            q = (
                q.join(
                    models.ProjectField,
                    models.Project.id == models.ProjectField.project_id
                )
            )

        q = (
            q.join(
                models.AcademicField,
                models.ProjectField.field_id == models.AcademicField.id
            )
            .filter_by(branch_id=branch_id)
        )

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

    # for field in ("call_type_id", "title", "project_number", "is_affiliated",
    #               "is_extended", "start_date", "notes"):
    for field in ("call_type_id", "title", "project_number", "final_report_submitted",
                  "is_extended", "start_date", "notes"):
        val = getattr(p_in, field)
        if val is not None:
            setattr(p, field, val)

    # allows for resetting end_date, in case end_date is None
    p.end_date = p_in.end_date

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

# <editor-fold desc="Person-related functions">
# ---------- Role ----------

def get_role(db: Session, role_id: int) -> Optional[models.Role]:
    return db.query(models.Role).filter_by(id=role_id).first()


def list_roles(db: Session) -> List[models.Role]:
    q = db.query(models.Role)
    return q.order_by(models.Role.id).all()  # type: ignore


# ---------- Person ----------

def get_person(db: Session, person_id: int) -> Optional[models.Person]:
    return db.query(models.Person).filter_by(id=person_id).first()


def list_persons(db: Session, search: Optional[str] = None) -> List[models.Person]:
    q = db.query(models.Person)
    if search:
        term = f"%{search}%"
        q = q.filter(
            or_(
                models.Person.first_name.ilike(term),
                models.Person.last_name.ilike(term),
                models.Person.email.ilike(term),
            )
        )
    return q.order_by(models.Person.first_name, models.Person.last_name).all()  # type: ignore


def create_person(db: Session, p_in: schemas.PersonCreate) -> models.Person:
    db_obj = models.Person(
        first_name=p_in.first_name,
        last_name=p_in.last_name,
        email=p_in.email
    )
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


def update_person(db: Session, person_id: int, p_in: schemas.PersonUpdate) -> models.Person:
    db_obj = get_person(db, person_id)
    if not db_obj:
        raise EntityNotFoundError(f"Person #{person_id} not found")
    if p_in.first_name is not None:
        db_obj.first_name = p_in.first_name
    if p_in.last_name is not None:
        db_obj.last_name = p_in.last_name
    if p_in.email is not None:
        db_obj.email = p_in.email
    db.commit()
    db.refresh(db_obj)
    return db_obj


def delete_person(db: Session, person_id: int) -> None:
    db_obj = get_person(db, person_id)
    if not db_obj:
        raise EntityNotFoundError(f"Person #{person_id} not found")

    # only if no related sub-entities
    if db_obj.roles:
        raise Exception("Cannot delete person with linked entities")

    db.delete(db_obj)
    db.commit()


# </editor-fold>

# <editor-fold desc="Person Role-related functions">
# ---------- Person Role ----------

def get_person_role(db: Session, person_role_id: int) -> Optional[models.PersonRole]:
    return db.query(models.PersonRole).filter_by(id=person_role_id).first()


def list_person_roles(
    db: Session,
    person_id: Optional[int] = None,
    role_id: Optional[int] = None,
    active: Optional[bool] = None,
) -> List[models.PersonRole]:
    q = db.query(models.PersonRole)
    if person_id is not None:
        q = q.filter_by(person_id=person_id)
    if role_id is not None:
        q = q.filter_by(role_id=role_id)

    # ACTIVE
    if active is not None:
        start_of_today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        if active:
            # q = q.filter(models.PersonRole.end_date.is_(None))
            q = q.filter(
                or_(
                    models.PersonRole.end_date.is_(None),
                    models.PersonRole.end_date >= start_of_today
                )
            )
        else:
            # q = q.filter(models.PersonRole.end_date.isnot(None))
            q = q.filter(
                and_(
                    models.PersonRole.end_date.isnot(None),
                    models.PersonRole.end_date < start_of_today
                )
            )

    return q.order_by(models.PersonRole.start_date.desc()).all()  # type: ignore


def create_person_role(db: Session, pr_in: schemas.PersonRoleCreate) -> models.PersonRole:
    db_obj = models.PersonRole(
        person_id=pr_in.person_id,
        role_id=pr_in.role_id,
        start_date=pr_in.start_date or datetime.now(timezone.utc),
        end_date=pr_in.end_date,
        notes=pr_in.notes
    )
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


def update_person_role(db: Session, person_role_id: int, pr_in: schemas.PersonRoleUpdate) -> models.PersonRole:
    db_obj = get_person_role(db, person_role_id)
    if not db_obj:
        raise EntityNotFoundError(f"PersonRole #{person_role_id} not found")
    if pr_in.start_date is not None:
        db_obj.start_date = pr_in.start_date
    # if pr_in.end_date is not None:
    #     db_obj.end_date = pr_in.end_date
    if pr_in.notes is not None:
        db_obj.notes = pr_in.notes

    # allows for resetting end_date, in case end_date is None
    db_obj.end_date = pr_in.end_date

    db.commit()
    db.refresh(db_obj)
    return db_obj


def delete_person_role(db: Session, person_role_id: int) -> None:
    db_obj = get_person_role(db, person_role_id)
    if not db_obj:
        raise EntityNotFoundError(f"PersonRole #{person_role_id} not found")

    # only if no related sub-entities
    if (db_obj.researcher or db_obj.phd_student or db_obj.postdoc or
            db_obj.projects or db_obj.supervised_students or db_obj.student_supervisors or
            db_obj.courses_teaching or db_obj.decision_letters or
            db_obj.institutions or db_obj.fields):
        raise Exception("Cannot delete person role with linked entities")

    db.delete(db_obj)
    db.commit()


# </editor-fold>

# <editor-fold desc="Researcher-related functions">
# ---------- Researcher ----------

# Researcher Title
def get_researcher_title(db: Session, rt_id: int):
    return db.query(models.ResearcherTitle).filter_by(id=rt_id).first()


def list_researcher_titles(db: Session, search: Optional[str] = None) -> list[models.ResearcherTitle]:
    q = db.query(models.ResearcherTitle)

    if search:
        term = f"%{search}%"
        q = q.filter(models.ResearcherTitle.title.ilike(term))

    return q.order_by(models.ResearcherTitle.title).all()  # type: ignore


def create_researcher_title(db: Session, rt_in: schemas.ResearcherTitleCreate):
    db_rt = models.ResearcherTitle(title=rt_in.title)
    db.add(db_rt)
    db.commit()
    db.refresh(db_rt)
    return db_rt


def update_researcher_title(db: Session, rt_id: int, rt_in: schemas.ResearcherTitleUpdate):
    db_rt = get_researcher_title(db, rt_id)
    if not db_rt:
        raise EntityNotFoundError(f"Researcher Title #{rt_id} not found")
    if rt_in.title is not None:
        db_rt.title = rt_in.title
    db.commit()
    db.refresh(db_rt)
    return db_rt


def delete_researcher_title(db: Session, rt_id: int):
    db_rt = get_researcher_title(db, rt_id)
    if not db_rt:
        raise EntityNotFoundError(f"Researcher Title #{rt_id} not found")

    # only if no related sub-entities
    if db_rt.researchers or db_rt.original_researchers or db_rt.postdocs_as_current:
        raise Exception("Cannot delete researcher title with linked entities")

    db.delete(db_rt)
    db.commit()


# Researcher
def get_researcher(db: Session, researcher_id: int) -> Optional[models.Researcher]:
    return db.query(models.Researcher).filter_by(id=researcher_id).first()


def list_researchers(
    db: Session,
    person_role_id:   Optional[int] = None,
    is_active:        Optional[bool] = None,
    title_id:         Optional[int] = None,
    institution_id:   Optional[int] = None,
    field_id:         Optional[int] = None,
    branch_id:        Optional[int] = None,
    search:           Optional[str] = None,
) -> List[models.Researcher]:

    q = db.query(models.Researcher)
    seen = set()

    # 1) simple equality filters
    if person_role_id is not None:
        q = q.filter_by(person_role_id=person_role_id)
    if title_id is not None:
        q = q.filter_by(title_id=title_id)

    # 2) active/inactive via PersonRole.end_date
    if is_active is not None:
        if "pr" not in seen:
            q = q.join(models.PersonRole,
                       models.Researcher.person_role_id == models.PersonRole.id)
            seen.add("pr")

        start_of_today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        if is_active:
            # q = q.filter(models.PersonRole.end_date.is_(None))
            q = q.filter(
                or_(
                    models.PersonRole.end_date.is_(None),
                    models.PersonRole.end_date >= start_of_today
                )
            )
        else:
            # q = q.filter(models.PersonRole.end_date.isnot(None))
            q = q.filter(
                and_(
                    models.PersonRole.end_date.isnot(None),
                    models.PersonRole.end_date < start_of_today
                )
            )

    # 3) institution filter (only active links)
    if institution_id is not None:
        if "pr" not in seen:
            q = q.join(models.PersonRole,
                       models.Researcher.person_role_id == models.PersonRole.id)
            seen.add("pr")
        if "pi" not in seen:
            q = q.join(models.PersonInstitution,
                       models.PersonRole.id == models.PersonInstitution.person_role_id)
            seen.add("pi")
        q = q.filter_by(institution_id=institution_id).filter(
            models.PersonInstitution.end_date.is_(None)
        )

    # 4) field/branch filter
    if field_id is not None or branch_id is not None:
        if "pr" not in seen:
            q = q.join(models.PersonRole,
                       models.Researcher.person_role_id == models.PersonRole.id)
            seen.add("pr")
        if "pf" not in seen:
            q = q.join(models.PersonField,
                       models.PersonRole.id == models.PersonField.person_role_id)
            seen.add("pf")
        if field_id is not None:
            q = q.filter_by(field_id=field_id)
        if branch_id is not None:
            if "af" not in seen:
                q = q.join(models.AcademicField,
                           models.PersonField.field_id == models.AcademicField.id)
                seen.add("af")
            q = q.filter_by(branch_id=branch_id)

    # 5) substring search on name
    if search:
        if "pr" not in seen:
            q = q.join(models.PersonRole,
                       models.Researcher.person_role_id == models.PersonRole.id)
            seen.add("pr")
        if "p" not in seen:
            q = q.join(models.Person,
                       models.PersonRole.person_id == models.Person.id)
            seen.add("p")
        term = f"%{search}%"
        q = q.filter(
            or_(
                models.Person.first_name.ilike(term),
                models.Person.last_name.ilike(term),
            )
        )

    # 6) ordering by last_name, first_name
    if "pr" not in seen:
        q = q.join(models.PersonRole,
                   models.Researcher.person_role_id == models.PersonRole.id)
        seen.add("pr")
    if "p" not in seen:
        q = q.join(models.Person,
                   models.PersonRole.person_id == models.Person.id)
        seen.add("p")

    q = q.order_by(models.Person.first_name, models.Person.last_name)

    return q.all()  # type: ignore


def create_researcher(db: Session, r_in: schemas.ResearcherCreate) -> models.Researcher:
    db_obj = models.Researcher(
        person_role_id=r_in.person_role_id,
        title_id=r_in.title_id,
        original_title_id=r_in.original_title_id,
        link=r_in.link,
        notes=r_in.notes
    )
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


def update_researcher(db: Session, researcher_id: int, r_in: schemas.ResearcherUpdate) -> models.Researcher:
    db_obj = get_researcher(db, researcher_id)
    if not db_obj:
        raise EntityNotFoundError(f"Researcher #{researcher_id} not found")
    if r_in.title_id is not None:
        db_obj.title_id = r_in.title_id
    if r_in.original_title_id is not None:
        db_obj.original_title_id = r_in.original_title_id
    if r_in.link is not None:
        db_obj.link = r_in.link
    if r_in.notes is not None:
        db_obj.notes = r_in.notes
    db.commit()
    db.refresh(db_obj)
    return db_obj


def delete_researcher(db: Session, researcher_id: int) -> None:
    db_obj = get_researcher(db, researcher_id)
    if not db_obj:
        raise EntityNotFoundError(f"Researcher #{researcher_id} not found")
    db.delete(db_obj)
    db.commit()


# </editor-fold>

# <editor-fold desc="PhD Student-related functions">
# ---------- PhD Student ----------

def get_phd_student(db: Session, student_id: int) -> Optional[models.PhDStudent]:
    return db.query(models.PhDStudent).filter_by(id=student_id).first()


def list_phd_students(
    db: Session,
    person_role_id:   Optional[int] = None,
    is_active:        Optional[bool] = None,
    cohort_number:    Optional[int] = None,
    is_affiliated:    Optional[bool] = None,
    is_graduated:     Optional[bool] = None,
    institution_id:   Optional[int] = None,
    field_id:         Optional[int] = None,
    branch_id:        Optional[int] = None,
    search:           Optional[str] = None,
) -> list[models.PhDStudent]:

    q = db.query(models.PhDStudent)
    seen = set()

    # 1) filter by person_role_id
    if person_role_id is not None:
        q = q.filter_by(person_role_id=person_role_id)

    # 2) active/inactive via PersonRole.end_date
    if is_active is not None:
        if "pr" not in seen:
            q = q.join(models.PersonRole,
                       models.PhDStudent.person_role_id == models.PersonRole.id)
            seen.add("pr")

        start_of_today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        if is_active:
            # q = q.filter(models.PersonRole.end_date.is_(None))
            q = q.filter(
                or_(
                    models.PersonRole.end_date.is_(None),
                    models.PersonRole.end_date >= start_of_today
                )
            )
        else:
            # q = q.filter(models.PersonRole.end_date.isnot(None))
            q = q.filter(
                and_(
                    models.PersonRole.end_date.isnot(None),
                    models.PersonRole.end_date < start_of_today
                )
            )

    # 3) cohort_number, is_affiliated, is_graduated
    if cohort_number is not None:
        q = q.filter(models.PhDStudent.cohort_number == cohort_number)
    if is_affiliated is not None:
        q = q.filter(models.PhDStudent.is_affiliated == is_affiliated)
    if is_graduated is not None:
        q = q.filter(models.PhDStudent.is_graduated == is_graduated)

    # 4) institution filter (only active PersonInstitution)
    if institution_id is not None:
        if "pr" not in seen:
            q = q.join(models.PersonRole,
                       models.PhDStudent.person_role_id == models.PersonRole.id)
            seen.add("pr")
        if "pi" not in seen:
            q = q.join(models.PersonInstitution,
                       models.PersonRole.id == models.PersonInstitution.person_role_id)
            seen.add("pi")
        q = q.filter_by(institution_id=institution_id).filter(
            models.PersonInstitution.end_date.is_(None)
        )

    # 5) field/branch filter
    if field_id is not None or branch_id is not None:
        if "pr" not in seen:
            q = q.join(models.PersonRole,
                       models.PhDStudent.person_role_id == models.PersonRole.id)
            seen.add("pr")
        if "pf" not in seen:
            q = q.join(models.PersonField,
                       models.PersonRole.id == models.PersonField.person_role_id)
            seen.add("pf")
        if field_id is not None:
            q = q.filter_by(field_id=field_id)
        if branch_id is not None:
            if "af" not in seen:
                q = q.join(models.AcademicField,
                           models.PersonField.field_id == models.AcademicField.id)
                seen.add("af")
            q = q.filter_by(branch_id=branch_id)

    # 6) substring search on name
    if search:
        if "pr" not in seen:
            q = q.join(models.PersonRole,
                       models.PhDStudent.person_role_id == models.PersonRole.id)
            seen.add("pr")
        if "p" not in seen:
            q = q.join(models.Person,
                       models.PersonRole.person_id == models.Person.id)
            seen.add("p")
        term = f"%{search}%"
        q = q.filter(
            or_(
                models.Person.first_name.ilike(term),
                models.Person.last_name.ilike(term),
            )
        )

    # 7) order by person’s last_name, first_name
    if "pr" not in seen:
        q = q.join(models.PersonRole,
                   models.PhDStudent.person_role_id == models.PersonRole.id)
        seen.add("pr")
    if "p" not in seen:
        q = q.join(models.Person,
                   models.PersonRole.person_id == models.Person.id)
        seen.add("p")

    q = q.order_by(models.Person.first_name, models.Person.last_name)

    return q.all()  # type: ignore


def create_phd_student(db: Session, s_in: schemas.PhDStudentCreate) -> models.PhDStudent:
    db_obj = models.PhDStudent(**s_in.model_dump())
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


def update_phd_student(db: Session, student_id: int, s_in: schemas.PhDStudentUpdate) -> models.PhDStudent:
    db_obj = get_phd_student(db, student_id)
    if not db_obj:
        raise EntityNotFoundError(f"PhDStudent #{student_id} not found")
    for attr, val in s_in.model_dump(exclude_none=True).items():
        setattr(db_obj, attr, val)
    db.commit()
    db.refresh(db_obj)
    return db_obj


def delete_phd_student(db: Session, student_id: int) -> None:
    db_obj = get_phd_student(db, student_id)
    if not db_obj:
        raise EntityNotFoundError(f"PhDStudent #{student_id} not found")
    db.delete(db_obj)
    db.commit()


# </editor-fold>

# <editor-fold desc="Postdoc-related functions">
# ---------- Postdoc ----------

def get_postdoc(db: Session, postdoc_id: int) -> Optional[models.Postdoc]:
    return db.query(models.Postdoc).filter_by(id=postdoc_id).first()


def list_postdocs(
    db: Session,
    person_role_id:   Optional[int] = None,
    is_active:        Optional[bool] = None,
    cohort_number:    Optional[int] = None,
    is_incoming:      Optional[bool] = None,
    is_graduated:     Optional[bool] = None,
    institution_id:   Optional[int] = None,
    field_id:         Optional[int] = None,
    branch_id:        Optional[int] = None,
    search:           Optional[str] = None,
) -> List[models.Postdoc]:

    q = db.query(models.Postdoc)
    seen = set()

    # 1) person_role filter
    if person_role_id is not None:
        q = q.filter_by(person_role_id=person_role_id)

    # 2) active/inactive via PersonRole.end_date
    if is_active is not None:
        if "pr" not in seen:
            q = q.join(models.PersonRole,
                       models.Postdoc.person_role_id == models.PersonRole.id)
            seen.add("pr")

        start_of_today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        if is_active:
            # q = q.filter(models.PersonRole.end_date.is_(None))
            q = q.filter(
                or_(
                    models.PersonRole.end_date.is_(None),
                    models.PersonRole.end_date >= start_of_today
                )
            )
        else:
            # q = q.filter(models.PersonRole.end_date.isnot(None))
            q = q.filter(
                and_(
                    models.PersonRole.end_date.isnot(None),
                    models.PersonRole.end_date < start_of_today
                )
            )

    # 3) cohort_number
    if cohort_number is not None:
        # q = q.filter_by(cohort_number=cohort_number)
        q = q.filter(models.Postdoc.cohort_number == cohort_number)

    # 4) is_outgoing / is_graduated
    if is_incoming is not None:
        # q = q.filter_by(is_outgoing=is_outgoing)
        q = q.filter(models.Postdoc.is_incoming == is_incoming)

    if is_graduated is not None:
        q = q.filter(models.Postdoc.is_graduated == is_graduated)

    # 5) institution (active assignments only)
    if institution_id is not None:
        if "pr" not in seen:
            q = q.join(models.PersonRole,
                       models.Postdoc.person_role_id == models.PersonRole.id)
            seen.add("pr")
        if "pi" not in seen:
            q = q.join(models.PersonInstitution,
                       models.PersonRole.id == models.PersonInstitution.person_role_id)
            seen.add("pi")
        q = q.filter_by(institution_id=institution_id).filter(
            models.PersonInstitution.end_date.is_(None)
        )

    # 6) field and branch
    if field_id is not None or branch_id is not None:
        if "pr" not in seen:
            q = q.join(models.PersonRole,
                       models.Postdoc.person_role_id == models.PersonRole.id)
            seen.add("pr")
        if "pf" not in seen:
            q = q.join(models.PersonField,
                       models.PersonRole.id == models.PersonField.person_role_id)
            seen.add("pf")
        if field_id is not None:
            q = q.filter_by(field_id=field_id)
        if branch_id is not None:
            if "af" not in seen:
                q = q.join(models.AcademicField,
                           models.PersonField.field_id == models.AcademicField.id)
                seen.add("af")
            q = q.filter_by(branch_id=branch_id)

    # 7) name‐search on Person
    if search:
        term = f"%{search}%"
        if "pr" not in seen:
            q = q.join(models.PersonRole,
                       models.Postdoc.person_role_id == models.PersonRole.id)
            seen.add("pr")
        if "p" not in seen:
            q = q.join(models.Person,
                       models.PersonRole.person_id == models.Person.id)
            seen.add("p")
        q = q.filter(
            or_(
                models.Person.first_name.ilike(term),
                models.Person.last_name.ilike(term),
            )
        )

    # 8) ordering by last_name, first_name
    if "pr" not in seen:
        q = q.join(models.PersonRole,
                   models.Postdoc.person_role_id == models.PersonRole.id)
        seen.add("pr")
    if "p" not in seen:
        q = q.join(models.Person,
                   models.PersonRole.person_id == models.Person.id)
        seen.add("p")

    q = q.order_by(models.Person.first_name, models.Person.last_name)

    return q.all()  # type: ignore


def create_postdoc(db: Session, p_in: schemas.PostdocCreate) -> models.Postdoc:
    db_obj = models.Postdoc(**p_in.model_dump())
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


def update_postdoc(db: Session, postdoc_id: int, p_in: schemas.PostdocUpdate) -> models.Postdoc:
    db_obj = get_postdoc(db, postdoc_id)
    if not db_obj:
        raise EntityNotFoundError(f"Postdoc #{postdoc_id} not found")
    # for attr, val in p_in.model_dump(exclude_none=True).items():
    # "exclude_unset" includes the fields that were actually sent even if they are null
    # this allows the fields "current_title_id", "current_title_other", "current_institution_id"
    # and "current_institution_other" to be set back to null
    for attr, val in p_in.model_dump(exclude_unset=True).items():
        setattr(db_obj, attr, val)
    db.commit()
    db.refresh(db_obj)
    return db_obj


def delete_postdoc(db: Session, postdoc_id: int) -> None:
    db_obj = get_postdoc(db, postdoc_id)
    if not db_obj:
        raise EntityNotFoundError(f"Postdoc #{postdoc_id} not found")
    db.delete(db_obj)
    db.commit()


# </editor-fold>

# <editor-fold desc="Student Activity-related functions">
# ---------- Student Activity ----------

class StudentActivityNotFound(Exception):
    pass


def get_student_activity(db: Session, student_activity_id: int) -> Optional[models.StudentActivity]:
    return db.query(models.StudentActivity).filter_by(id=student_activity_id).first()


def list_student_activities(
    db: Session,
    phd_student_id: int,
    activity_type:  Optional[ActivityType] = None
) -> List[models.StudentActivity]:
    # 1) ensure the student exists
    student = get_phd_student(db, phd_student_id)
    if not student:
        raise EntityNotFoundError(f"PhD student #{phd_student_id} not found")

    # 2) start base query and optional filter by type
    q = db.query(models.StudentActivity).filter_by(phd_student_id=phd_student_id)
    if activity_type is not None:
        q = q.filter_by(activity_type=activity_type)

    # 3) join to the two subclass tables so we can sort by their columns
    q = (
        q
        # grad‐school years
        .outerjoin(
            models.GradSchoolActivity,
            and_(
                models.StudentActivity.activity_type == ActivityType.GRAD_SCHOOL,
                models.StudentActivity.activity_id == models.GradSchoolActivity.id
            )
        )
        # # abroad start dates
        # .outerjoin(
        #     models.AbroadStudentActivity,
        #     and_(
        #         models.StudentActivity.activity_type == ActivityType.ABROAD,
        #         models.StudentActivity.activity_id == models.AbroadStudentActivity.id
        #     )
        # )
    )

    # 4) build a discriminator to put grad‐school first, abroad next
    type_order = case(
        {
            models.StudentActivity.activity_type == ActivityType.GRAD_SCHOOL: 0,
            models.StudentActivity.activity_type == ActivityType.ABROAD: 1,
        },
        else_=2
    )

    # 5) order by: grad‐school year desc, abroad start_date desc
    q = q.order_by(
        type_order,
        desc(models.GradSchoolActivity.year),
        desc(models.AbroadStudentActivity.start_date),
    )

    # 6) execute
    return q.all()  # type: ignore


def create_grad_school_student_activity(
    db: Session,
    stu_id: int,
    in_data: schemas.GradSchoolStudentActivityCreate
) -> models.GradSchoolStudentActivity:
    """
    1) Verify the target PhD student exists.
    2) Verify the referenced GradSchoolActivity exists.
    3) Enforce the unique‐together constraint on (phd_student_id, activity_type, activity_id).
    4) Create & return.
    """
    # 1) PhD student must exist
    # from .crud import get_phd_student, EntityNotFoundError
    student = get_phd_student(db, stu_id)
    if not student:
        raise EntityNotFoundError(f"PhDStudent #{stu_id} not found")

    # 2) Grad school activity must exist
    gsa = db.query(models.GradSchoolActivity).filter_by(id=in_data.activity_id).first()
    if not gsa:
        raise EntityNotFoundError(f"GradSchoolActivity #{in_data.activity_id} not found")

    # 3) Check unique constraint
    existing = (
        db.query(models.GradSchoolStudentActivity)
          .filter_by(
              phd_student_id=stu_id,
              # activity_type=in_data.activity_type,
              activity_type=ActivityType.GRAD_SCHOOL,
              activity_id=in_data.activity_id
          )
        .first()
    )
    if existing:
        raise Exception(f"StudentActivity for student {stu_id} & grad‐activity {in_data.activity_id} already exists")

    # 4) Create
    db_obj = models.GradSchoolStudentActivity(
        phd_student_id=stu_id,
        # activity_type=in_data.activity_type,
        activity_type=ActivityType.GRAD_SCHOOL,
        activity_id=in_data.activity_id,
        is_completed=in_data.is_completed,
        grade=in_data.grade
    )
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


def create_abroad_student_activity(
    db: Session,
    stu_id: int,
    in_data: schemas.AbroadStudentActivityCreate
) -> models.AbroadStudentActivity:
    """
    1) Verify the target PhD student exists.
    2) Enforce the unique‐together constraint on (phd_student_id, activity_type, activity_id).
       For an AbroadActivity, we do not reference another table, so we auto‐assign activity_id = id of this row.
    3) Create & return.
    """
    # from .crud import get_phd_student, EntityNotFoundError
    student = get_phd_student(db, stu_id)
    if not student:
        raise EntityNotFoundError(f"PhDStudent #{stu_id} not found")

    # We pick activity_id = a new placeholder, but actually,
    # with our inheritance setup, the `id` column will get filled after insert.
    # However, to satisfy the unique constraint, we must delay commit until after id is known.
    # A simpler workaround: assign activity_id = some sentinel (0) at first, then update.
    db_obj = models.AbroadStudentActivity(
        phd_student_id=stu_id,
        # activity_type=in_data.activity_type,
        activity_type=ActivityType.ABROAD,
        activity_id=0,  # temporary
        description=in_data.description,
        start_date=in_data.start_date,
        end_date=in_data.end_date,
        city=in_data.city,
        country=in_data.country,
        host_institution=in_data.host_institution
    )
    db.add(db_obj)
    db.flush()  # assign db_obj.id
    db_obj.activity_id = db_obj.id

    # Now check uniqueness manually:
    conflict = (db.query(models.AbroadStudentActivity).filter_by(phd_student_id=stu_id,
                                                                 # activity_type=in_data.activity_type,
                                                                 activity_type=ActivityType.ABROAD,
                                                                 activity_id=db_obj.activity_id)
                .first())
    if conflict and conflict.id != db_obj.id:
        raise Exception(f"Duplicate AbroadActivity for student {stu_id} & activity_id {db_obj.activity_id}")

    db.commit()
    db.refresh(db_obj)
    return db_obj


def update_student_activity(
    db: Session,
    stu_act_id: int,
    stu_id: int,
    in_data: Union[schemas.GradSchoolStudentActivityCreate, schemas.AbroadStudentActivityCreate]
) -> models.StudentActivity:
    """
    1) Fetch the StudentActivity by id.
    2) If not found or `phd_student_id` mismatch, 404.
    3) Branch on `activity_type` rather than isinstance(...).
    4) Re‐query the proper subclass so SQLAlchemy gives us a subclass instance.
    5) Update only the fields relevant to that subclass.
    """
    sa = get_student_activity(db, stu_act_id)
    if not sa or sa.phd_student_id != stu_id:
        raise StudentActivityNotFound(f"Student activity #{stu_act_id} for student {stu_id} not found")

    # If the row’s discriminator says “GRAD_SCHOOL”, re‐load as GradSchoolStudentActivity
    if sa.activity_type == models.ActivityType.GRAD_SCHOOL:
        gss = db.query(models.GradSchoolStudentActivity).filter_by(id=stu_act_id).first()
        if not gss:
            # Shouldn’t happen if the data is consistent, but just in case:
            raise EntityNotFoundError(f"GradSchoolStudentActivity #{stu_act_id} not found")

        # Update the optional activity_id (must point to a real GradSchoolActivity)
        if getattr(in_data, "activity_id", None) is not None and in_data.activity_id != gss.activity_id:
            new_gsa = db.query(models.GradSchoolActivity).filter_by(id=in_data.activity_id).first()
            if not new_gsa:
                raise EntityNotFoundError(f"GradSchoolActivity #{in_data.activity_id} not found")
            gss.activity_id = in_data.activity_id

        # Update is_completed / grade if provided
        if getattr(in_data, "is_completed", None) is not None:
            gss.is_completed = in_data.is_completed
        # if getattr(in_data, "grade", None) is not None:
        #     gss.grade = in_data.grade
        # Check if 'grade' was actually included in the request payload (ALLOW SETTING TO NULL)
        if "grade" in in_data.model_dump(exclude_unset=True):
            gss.grade = in_data.grade

        db.commit()
        db.refresh(gss)
        return gss  # type: ignore

    # If the row’s discriminator says “ABROAD”, re‐load as AbroadStudentActivity
    elif sa.activity_type == models.ActivityType.ABROAD:
        abs_row = db.query(models.AbroadStudentActivity).filter_by(id=stu_act_id).first()
        if not abs_row:
            raise EntityNotFoundError(f"AbroadStudentActivity #{stu_act_id} not found")

        # Only update whichever fields the payload provided
        if getattr(in_data, "description", None) is not None:
            abs_row.description = in_data.description
        if getattr(in_data, "start_date", None) is not None:
            abs_row.start_date = in_data.start_date
        if getattr(in_data, "end_date", None) is not None:
            abs_row.end_date = in_data.end_date
        if getattr(in_data, "city", None) is not None:
            abs_row.city = in_data.city
        if getattr(in_data, "country", None) is not None:
            abs_row.country = in_data.country
        if getattr(in_data, "host_institution", None) is not None:
            abs_row.host_institution = in_data.host_institution

        db.commit()
        db.refresh(abs_row)
        return abs_row  # type: ignore

    else:
        # Should never happen, but guard against unknown discriminator values
        raise Exception(f"Unknown activity_type {sa.activity_type!r} for StudentActivity #{stu_act_id}")


def delete_student_activity(db: Session, stu_act_id: int, stu_id: int) -> None:
    """
    Delete only if the row exists and belongs to that student.
    """
    sa = get_student_activity(db, stu_act_id)
    if not sa or sa.phd_student_id != stu_id:
        raise StudentActivityNotFound(f"Student activity #{stu_act_id} for student {stu_id} not found")

    db.delete(sa)
    db.commit()


# </editor-fold>

# <editor-fold desc="Grad School Activity relationships functions">
# --- student activities for a grad school activity ---
def list_student_activities_for_grad_school(
    db: Session,
    grad_school_activity_id: int,
    search: Optional[str] = None
) -> List[models.StudentActivity]:
    # ensure grad school activity exists
    gsa = get_grad_school_activity(db, grad_school_activity_id)
    if not gsa:
        raise EntityNotFoundError(f"GradSchoolActivity #{grad_school_activity_id} not found")

    # base query: only GRAD_SCHOOL entries for this activity_id
    q = (
        db.query(models.StudentActivity)
        .filter_by(
              activity_type=ActivityType.GRAD_SCHOOL,
              activity_id=grad_school_activity_id
        )
        .join(
              models.PhDStudent,
              models.StudentActivity.phd_student_id == models.PhDStudent.id
        )
        .join(
              models.PersonRole,
              models.PhDStudent.person_role_id == models.PersonRole.id
        )
        .join(
              models.Person,
              models.PersonRole.person_id == models.Person.id
        )
    )

    # optional substring search on student name
    if search:
        term = f"%{search}%"
        q = q.filter(
            or_(
                models.Person.first_name.ilike(term),
                models.Person.last_name.ilike(term),
            )
        )

    # final ordering by first_name then last_name
    q = q.order_by(
        models.Person.first_name,
        models.Person.last_name
    )

    return q.all()  # type: ignore


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


# --- teachers for a course ---
def get_course_teachers(db: Session, course_id: int) -> list[models.PersonRole]:
    # ensure course exists
    course = get_course(db, course_id)
    if not course:
        raise EntityNotFoundError(f"Course #{course_id} not found")
    joins = db.query(models.CourseTeacher).filter_by(course_id=course_id).all()
    return [j.person_role for j in joins]


def add_teacher_to_course(db: Session, course_id: int, person_role_id: int) -> models.PersonRole:
    # look up both ends
    course = get_course(db, course_id)
    if not course:
        raise EntityNotFoundError(f"Course #{course_id} not found")
    pr = get_person_role(db, person_role_id)
    if not pr:
        raise EntityNotFoundError(f"Person role #{person_role_id} not found")
    # no dupes
    exists = db.query(models.CourseTeacher).filter_by(
        course_id=course_id, person_role_id=person_role_id
    ).first()
    if exists:
        raise Exception(f"Person role (teacher) #{person_role_id} already linked to Course #{course_id}")
    link = models.CourseTeacher(course_id=course_id, person_role_id=person_role_id)
    db.add(link)
    db.commit()
    return pr  # type: ignore


def remove_teacher_from_course(db: Session, course_id: int, person_role_id: int):
    link = db.query(models.CourseTeacher).filter_by(
        course_id=course_id, person_role_id=person_role_id
    ).first()
    if not link:
        raise EntityNotFoundError(
            f"Person role #{person_role_id} not linked to Course #{course_id}"
        )
    db.delete(link)
    db.commit()


# --- students for a course ---
def get_course_students(db: Session, course_id: int, search: Optional[str] = None) -> List[models.PhDStudentCourse]:
    # 1) verify course exists
    course = get_course(db, course_id)
    if not course:
        raise EntityNotFoundError(f"Course #{course_id} not found")

    # 2) start the query on the join‐table
    q = (
        db.query(models.PhDStudentCourse)
        .filter_by(course_id=course_id)
        .join(
              models.PhDStudent,
              models.PhDStudentCourse.phd_student_id == models.PhDStudent.id
        )
        .join(
              models.PersonRole,
              models.PhDStudent.person_role_id == models.PersonRole.id
        )
        .join(
              models.Person,
              models.PersonRole.person_id == models.Person.id
        )
    )

    # 3) optional substring filter on the person’s name
    if search:
        term = f"%{search}%"
        q = q.filter(
            or_(
                models.Person.first_name.ilike(term),
                models.Person.last_name.ilike(term),
            )
        )

    # 4) order alphabetically by first_name, then last_name
    q = q.order_by(
        models.Person.first_name,
        models.Person.last_name
    )

    # 5) return the list of link‐rows
    return q.all()  # type: ignore


def add_student_to_course(db: Session, course_id: int,
                          in_data: schemas.CourseStudentLink) -> models.PhDStudentCourse:
    # look up both ends
    course = get_course(db, course_id)
    if not course:
        raise EntityNotFoundError(f"Course #{course_id} not found")
    student = get_phd_student(db, in_data.phd_student_id)
    if not student:
        raise EntityNotFoundError(f"PhD Student #{in_data.phd_student_id} not found")
    # no dupes
    exists = db.query(models.PhDStudentCourse).filter_by(
        course_id=course_id, phd_student_id=in_data.phd_student_id
    ).first()
    if exists:
        raise Exception(f"PhD student #{in_data.phd_student_id} already linked to Course #{course_id}")
    link = models.PhDStudentCourse(course_id=course_id,
                                   phd_student_id=in_data.phd_student_id,
                                   is_completed=in_data.is_completed,
                                   grade=in_data.grade)
    db.add(link)
    db.commit()
    db.refresh(link)
    return link  # type: ignore


def update_student_course_link(db: Session, course_id: int, phd_student_id: int,
                               in_data: schemas.CourseStudentLink) -> models.PhDStudentCourse:
    # look up both ends
    course = get_course(db, course_id)
    if not course:
        raise EntityNotFoundError(f"Course #{course_id} not found")
    student = get_phd_student(db, phd_student_id)
    if not student:
        raise EntityNotFoundError(f"PhD Student #{phd_student_id} not found")

    psc = db.query(models.PhDStudentCourse).filter_by(course_id=course_id, phd_student_id=phd_student_id).first()
    if not psc:
        # Shouldn’t happen if the data is consistent, but just in case:
        raise EntityNotFoundError(f"PhDStudentCourse for course #{course_id} and "
                                  f"phd student {phd_student_id} not found")

    # Update is_completed / grade if provided
    if getattr(in_data, "is_completed", None) is not None:
        psc.is_completed = in_data.is_completed
    # if getattr(in_data, "grade", None) is not None:
    #     psc.grade = in_data.grade
    # Check if 'grade' was actually included in the request payload (ALLOW SETTING TO NULL)
    if "grade" in in_data.model_dump(exclude_unset=True):
        psc.grade = in_data.grade

    db.commit()
    db.refresh(psc)
    return psc  # type: ignore


def remove_student_from_course(db: Session, course_id: int, phd_student_id: int):
    link = db.query(models.PhDStudentCourse).filter_by(
        course_id=course_id, phd_student_id=phd_student_id
    ).first()
    if not link:
        raise EntityNotFoundError(
            f"PhD student #{phd_student_id} not linked to Course #{course_id}"
        )
    db.delete(link)
    db.commit()


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


# --- people roles for a project ---
def get_project_people_roles(db: Session, project_id: int) -> list[models.PersonProject]:
    # ensure project exists
    project = get_project(db, project_id)
    if not project:
        raise EntityNotFoundError(f"Project #{project_id} not found")

    q = (
        db.query(models.PersonProject)
        .filter_by(project_id=project_id)
        .join(
              models.PersonRole,
              models.PersonProject.person_role_id == models.PersonRole.id
        )
        .join(
              models.Person,
              models.PersonRole.person_id == models.Person.id
        )
        .order_by(
              models.PersonProject.is_active.desc(),
              # principal investigators first
              models.PersonProject.is_principal_investigator.desc(),
              # then leaders
              # models.PersonProject.is_leader.desc(),
              # then contact persons
              models.PersonProject.is_contact_person.desc(),
              # then alphabetical by person name
              models.Person.first_name,
              models.Person.last_name,
        )
    )
    return q.all()  # type: ignore


def add_person_role_to_project(db: Session, project_id: int,
                               in_data: schemas.ProjectPersonRoleLink) -> models.PersonProject:
    # look up both ends
    project = get_project(db, project_id)
    if not project:
        raise EntityNotFoundError(f"Project #{project_id} not found")
    person_role = get_person_role(db, in_data.person_role_id)
    if not person_role:
        raise EntityNotFoundError(f"Person role #{in_data.person_role_id} not found")
    # no dupes
    exists = db.query(models.PersonProject).filter_by(
        project_id=project_id, person_role_id=in_data.person_role_id
    ).first()
    if exists:
        raise Exception(f"Person role #{in_data.person_role_id} already linked to Project #{project_id}")
    link = models.PersonProject(project_id=project_id,
                                person_role_id=in_data.person_role_id,
                                is_principal_investigator=in_data.is_principal_investigator,
                                # is_leader=in_data.is_leader,
                                is_contact_person=in_data.is_contact_person,
                                is_active=in_data.is_active)
    db.add(link)
    db.commit()
    db.refresh(link)
    return link  # type: ignore


def update_person_role_project_link(db: Session, project_id: int, person_role_id: int,
                                    in_data: schemas.ProjectPersonRoleLink) -> models.PersonProject:
    # look up both ends
    project = get_project(db, project_id)
    if not project:
        raise EntityNotFoundError(f"Project #{project_id} not found")
    person_role = get_person_role(db, person_role_id)
    if not person_role:
        raise EntityNotFoundError(f"Person role #{person_role_id} not found")

    pp = db.query(models.PersonProject).filter_by(project_id=project_id, person_role_id=person_role_id).first()
    if not pp:
        # Shouldn’t happen if the data is consistent, but just in case:
        raise EntityNotFoundError(f"PersonProject for project #{project_id} and "
                                  f"person role {person_role_id} not found")

    # Update is_principal_investigator / is_contact_person / is_active if provided
    if getattr(in_data, "is_principal_investigator", None) is not None:
        pp.is_principal_investigator = in_data.is_principal_investigator
    # if getattr(in_data, "is_leader", None) is not None:
    #     pp.is_leader = in_data.is_leader
    if getattr(in_data, "is_contact_person", None) is not None:
        pp.is_contact_person = in_data.is_contact_person
    if getattr(in_data, "is_active", None) is not None:
        pp.is_active = in_data.is_active

    db.commit()
    db.refresh(pp)
    return pp  # type: ignore


def remove_person_role_from_project(db: Session, project_id: int, person_role_id: int):
    link = db.query(models.PersonProject).filter_by(
        project_id=project_id, person_role_id=person_role_id
    ).first()
    if not link:
        raise EntityNotFoundError(
            f"Person role #{person_role_id} not linked to Project #{project_id}"
        )
    db.delete(link)
    db.commit()


# </editor-fold>

# <editor-fold desc="Person Role relationships functions">
# --- institutions for a person role ---

def get_person_role_institutions(db: Session, person_role_id: int) -> list[models.PersonInstitution]:
    # ensure person role exists
    person_role = get_person_role(db, person_role_id)
    if not person_role:
        raise EntityNotFoundError(f"Person role #{person_role_id} not found")
    person_role_institutions = db.query(models.PersonInstitution).filter_by(person_role_id=person_role_id).all()
    return person_role_institutions  # type: ignore


def add_institution_to_person_role(db: Session, person_role_id: int,
                                   in_data: schemas.PersonRoleInstitutionLink) -> models.PersonInstitution:
    # look up both ends
    person_role = get_person_role(db, person_role_id)
    if not person_role:
        raise EntityNotFoundError(f"Person role #{person_role_id} not found")
    institution = get_institution(db, in_data.institution_id)
    if not institution:
        raise EntityNotFoundError(f"Institution #{in_data.institution_id} not found")
    # no dupes
    exists = db.query(models.PersonInstitution).filter_by(
        person_role_id=person_role_id, institution_id=in_data.institution_id
    ).first()
    if exists:
        raise Exception(f"Institution #{in_data.institution_id} already linked to Person Role #{person_role_id}")
    link = models.PersonInstitution(person_role_id=person_role_id,
                                    institution_id=in_data.institution_id,
                                    start_date=in_data.start_date,
                                    end_date=in_data.end_date)
    db.add(link)
    db.commit()
    db.refresh(link)
    return link  # type: ignore


def update_institution_person_role_link(db: Session, person_role_id: int, institution_id: int,
                                        in_data: schemas.PersonRoleInstitutionLink) -> models.PersonInstitution:
    # look up both ends
    person_role = get_person_role(db, person_role_id)
    if not person_role:
        raise EntityNotFoundError(f"Person role #{person_role_id} not found")
    institution = get_institution(db, institution_id)
    if not institution:
        raise EntityNotFoundError(f"Institution #{institution_id} not found")

    pi_row = db.query(models.PersonInstitution).filter_by(person_role_id=person_role_id,
                                                          institution_id=institution_id).first()
    if not pi_row:
        # Shouldn’t happen if the data is consistent, but just in case:
        raise EntityNotFoundError(f"Institution for person role #{person_role_id} and "
                                  f"institution {institution_id} not found")

    # # Update start_date / end_date if provided
    # if getattr(in_data, "start_date", None) is not None:
    #     pi_row.start_date = in_data.start_date
    # if getattr(in_data, "end_date", None) is not None:
    #     pi_row.end_date = in_data.end_date

    # Allows for resetting the dates to null
    # Check if the 'start_date' field was included in the incoming data
    if hasattr(in_data, "start_date"):
        # If it was, update the row's value, even if it's None
        pi_row.start_date = in_data.start_date

    # Do the same for the 'end_date' field
    if hasattr(in_data, "end_date"):
        pi_row.end_date = in_data.end_date

    db.commit()
    db.refresh(pi_row)
    return pi_row  # type: ignore


def remove_institution_from_person_role(db: Session, person_role_id: int, institution_id: int):
    link = db.query(models.PersonInstitution).filter_by(
        person_role_id=person_role_id, institution_id=institution_id
    ).first()
    if not link:
        raise EntityNotFoundError(
            f"Institution #{institution_id} not linked to Person Role #{person_role_id}"
        )
    db.delete(link)
    db.commit()


# --- academic fields for a person role ---

def get_person_role_fields(db: Session, person_role_id: int) -> list[models.AcademicField]:
    # ensure person role exists
    person_role = get_person_role(db, person_role_id)
    if not person_role:
        raise EntityNotFoundError(f"Person role #{person_role_id} not found")
    joins = db.query(models.PersonField).filter_by(person_role_id=person_role_id).all()
    return [j.field for j in joins]


def add_field_to_person_role(db: Session, person_role_id: int, field_id: int) -> models.AcademicField:
    # look up both ends
    person_role = get_person_role(db, person_role_id)
    if not person_role:
        raise EntityNotFoundError(f"Person role #{person_role_id} not found")
    field = get_field(db, field_id)
    if not field:
        raise EntityNotFoundError(f"Academic field #{field_id} not found")
    # no dupes
    exists = db.query(models.PersonField).filter_by(
        person_role_id=person_role_id, field_id=field_id
    ).first()
    if exists:
        raise Exception(f"Academic field #{field_id} already linked to Person Role #{person_role_id}")
    link = models.PersonField(person_role_id=person_role_id, field_id=field_id)
    db.add(link)
    db.commit()
    return field  # type: ignore


def remove_field_from_person_role(db: Session, person_role_id: int, field_id: int):
    link = db.query(models.PersonField).filter_by(
        person_role_id=person_role_id, field_id=field_id
    ).first()
    if not link:
        raise EntityNotFoundError(
            f"Academic field #{field_id} not linked to Person Role #{person_role_id}"
        )
    db.delete(link)
    db.commit()


# --- projects for a person role ---

def get_person_role_projects(db: Session, person_role_id: int) -> List[models.PersonProject]:
    # 1) verify the person_role exists
    pr = get_person_role(db, person_role_id)
    if not pr:
        raise EntityNotFoundError(f"Person role #{person_role_id} not found")

    # 2) build the query with a join to Project for end_date and start_date
    q = (
        db.query(models.PersonProject)
          .filter_by(person_role_id=person_role_id)
          .join(models.Project, models.PersonProject.project_id == models.Project.id)
    )

    # 3) order by:
    #    a) active (end_date IS NULL) first
    #    b) then principal investigators
    #    c) then leaders
    #    d) then project.start_date descending
    q = q.order_by(
        models.PersonProject.is_active.desc(),
        # Boolean IS NULL becomes 1 for True, 0 for False, so desc() puts True first
        models.Project.end_date.is_(None).desc(),
        models.PersonProject.is_principal_investigator.desc(),
        # models.PersonProject.is_leader.desc(),
        models.PersonProject.is_contact_person.desc(),
        desc(models.Project.start_date),
    )

    return q.all()  # type: ignore


# --- supervision relationships ---

def get_supervision(db: Session, supervision_id: int) -> Optional[models.SupervisorPhDStudent]:
    return db.query(models.SupervisorPhDStudent).filter_by(id=supervision_id).first()


def list_supervisions(
    db: Session,
    *,
    student_role_id:   Optional[int] = None,
    supervisor_role_id: Optional[int] = None
) -> List[models.SupervisorPhDStudent]:
    q = db.query(models.SupervisorPhDStudent)
    if student_role_id is not None:
        q = q.filter_by(student_role_id=student_role_id)
    if supervisor_role_id is not None:
        q = q.filter_by(supervisor_role_id=supervisor_role_id)
    return q.order_by(models.SupervisorPhDStudent.id).all()  # type: ignore


def create_supervision(
    db: Session,
    sup_in: schemas.SupervisionCreate
) -> models.SupervisorPhDStudent:
    # ensure both person‐roles exist
    sup = get_person_role(db, sup_in.supervisor_role_id)
    if not sup:
        raise EntityNotFoundError(f"PersonRole #{sup_in.supervisor_role_id} not found")
    stu = get_person_role(db, sup_in.student_role_id)
    if not stu:
        raise EntityNotFoundError(f"PersonRole #{sup_in.student_role_id} not found")

    # prevent duplicates
    exists = db.query(models.SupervisorPhDStudent).filter_by(
        supervisor_role_id=sup_in.supervisor_role_id,
        student_role_id=sup_in.student_role_id
    ).first()
    if exists:
        raise Exception(
            f"Supervision link already exists "
            f"between supervisor {sup_in.supervisor_role_id} and student {sup_in.student_role_id}"
        )

    link = models.SupervisorPhDStudent(
        supervisor_role_id=sup_in.supervisor_role_id,
        student_role_id=sup_in.student_role_id,
        is_main=sup_in.is_main
    )
    db.add(link)
    db.commit()
    db.refresh(link)
    return link


def update_supervision(
    db: Session,
    supervision_id: int,
    sup_in: schemas.SupervisionUpdate
) -> models.SupervisorPhDStudent:
    link = get_supervision(db, supervision_id)
    if not link:
        raise EntityNotFoundError(f"Supervision #{supervision_id} not found")

    if sup_in.is_main is not None:
        link.is_main = sup_in.is_main

    db.commit()
    db.refresh(link)
    return link


def delete_supervision(db: Session, supervision_id: int) -> None:
    link = get_supervision(db, supervision_id)
    if not link:
        raise EntityNotFoundError(f"Supervision #{supervision_id} not found")
    db.delete(link)
    db.commit()


# </editor-fold>

# <editor-fold desc="PhD Student relationships functions">
# --- courses for a phd student ---
def get_student_courses(db: Session, phd_student_id: int) -> List[models.PhDStudentCourse]:
    # ensure PhDStudent exists
    student = get_phd_student(db, phd_student_id)
    if not student:
        raise EntityNotFoundError(f"PhD student #{phd_student_id} not found")

    # start query on the join‐table
    q = (
        db.query(models.PhDStudentCourse)
          .filter_by(phd_student_id=phd_student_id)
          .join(models.Course, models.PhDStudentCourse.course)
          .outerjoin(models.Course.course_term)
          .outerjoin(models.Course.grad_school_activity)
    )

    # build our CASE expressions for year and season
    season_cases = {
        models.CourseTerm.season == s: order
        for s, order in SEASON_ORDER.items()
    }
    season_ordering = case(season_cases, else_=0)

    year_cases = {
        models.CourseTerm.year.isnot(None):        models.CourseTerm.year,
        models.GradSchoolActivity.year.isnot(None): models.GradSchoolActivity.year,
    }

    # now apply the multi‐criteria ordering:
    # 1) not yet completed first → is_completed False (0) before True (1)
    # 2) descending by year (from term or activity)
    # 3) descending by season order
    q = q.order_by(
        models.PhDStudentCourse.is_completed,            # False first
        desc(case(year_cases, else_=0)),                  # newest year first
        desc(season_ordering)                             # season order
    )

    return q.all()  # type: ignore


# </editor-fold>
