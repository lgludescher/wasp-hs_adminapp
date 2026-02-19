from datetime import datetime, timezone
from enum import Enum as PyEnum
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime,
    ForeignKey, UniqueConstraint, CheckConstraint,
    Numeric
)
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import relationship, foreign
from sqlalchemy import and_
from .database import Base


# ---------- Enums ----------
class EntityType(PyEnum):
    PERSON_ROLE = "person_role"
    PROJECT = "project"
    COURSE = "course"


class RoleType(PyEnum):
    RESEARCHER = "researcher"
    PHD_STUDENT = "phd_student"
    POSTDOC = "postdoc"


class Season(PyEnum):
    SPRING = "spring"
    SUMMER = "summer"
    FALL = "fall"
    WINTER = "winter"


class GradeType(PyEnum):
    PASS = "pass"
    FAIL = "fail"


class ActivityType(PyEnum):
    GRAD_SCHOOL = "grad_school"
    ABROAD = "abroad"


# ---------- Models ----------

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    is_admin = Column(Boolean, default=False)


# Lookup tables
class ResearcherTitle(Base):
    __tablename__ = "researcher_titles"
    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    researchers = relationship("Researcher", back_populates="title",
                               cascade="all, delete-orphan", foreign_keys="Researcher.title_id")
    original_researchers = relationship("Researcher", back_populates="original_title",
                                        cascade="all, delete-orphan", foreign_keys="Researcher.original_title_id")
    postdocs_as_current = relationship("Postdoc", back_populates="current_title",
                                       foreign_keys="Postdoc.current_title_id")


class Institution(Base):
    __tablename__ = "institutions"
    id = Column(Integer, primary_key=True)
    institution = Column(String, nullable=False)
    person_institutions = relationship("PersonInstitution", back_populates="institution",
                                       cascade="all, delete-orphan")
    course_institutions = relationship("CourseInstitution", back_populates="institution",
                                       cascade="all, delete-orphan")
    postdocs_as_current = relationship("Postdoc", back_populates="current_institution",
                                       foreign_keys="Postdoc.current_institution_id")


class AcademicBranch(Base):
    __tablename__ = "academic_branches"
    id = Column(Integer, primary_key=True)
    branch = Column(String, nullable=False)
    fields = relationship("AcademicField", back_populates="branch", cascade="all, delete-orphan")


class AcademicField(Base):
    __tablename__ = "academic_fields"
    id = Column(Integer, primary_key=True)
    field = Column(String, nullable=False)
    branch_id = Column(Integer, ForeignKey("academic_branches.id"), nullable=False)
    branch = relationship("AcademicBranch", back_populates="fields")
    person_fields = relationship("PersonField", back_populates="field", cascade="all, delete-orphan")
    project_fields = relationship("ProjectField", back_populates="field", cascade="all, delete-orphan")


class ProjectCallType(Base):
    __tablename__ = "project_call_types"
    id = Column(Integer, primary_key=True)
    type = Column(String, nullable=False)
    projects = relationship("Project", back_populates="call_type", cascade="all, delete-orphan")


class Role(Base):
    __tablename__ = "roles"
    id = Column(Integer, primary_key=True)
    role = Column(SQLEnum(RoleType, name="role_type_enum"), nullable=False, unique=True)
    person_roles = relationship("PersonRole", back_populates="role", cascade="all, delete-orphan")


class Course(Base):
    __tablename__ = "courses"
    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    # terms_offered = Column(String, nullable=True)

    # ← either a generic CourseTerm …
    course_term_id = Column(Integer, ForeignKey("course_terms.id"), nullable=True)
    # ← … or linked to a GradSchoolActivity
    grad_school_activity_id = Column(Integer, ForeignKey("grad_school_activities.id"), nullable=True)

    # contact_teachers = Column(String, nullable=True)
    credit_points = Column(Numeric(precision=4, scale=1), nullable=True)
    notes = Column(String, nullable=True)

    # ensure **exactly one** of the two is set
    __table_args__ = (
        CheckConstraint(
            "(course_term_id IS NOT NULL) != (grad_school_activity_id IS NOT NULL)",
            name="ck_course_term_xor_grad_activity"
        ),
    )

    # either a generic term…
    course_term = relationship("CourseTerm", back_populates="courses", foreign_keys="Course.course_term_id")
    # … or a linked grad‐school activity
    grad_school_activity = relationship("GradSchoolActivity", back_populates="courses",
                                        foreign_keys="Course.grad_school_activity_id")

    student_courses = relationship("PhDStudentCourse", back_populates="course",
                                   cascade="all, delete-orphan")
    course_institutions = relationship("CourseInstitution", back_populates="course",
                                       cascade="all, delete-orphan")
    teachers = relationship("CourseTeacher", back_populates="course", cascade="all, delete-orphan")
    decision_letters = relationship(
        "DecisionLetter",
        primaryjoin=lambda: and_(
            DecisionLetter.entity_type == EntityType.COURSE,
            foreign(DecisionLetter.entity_id) == Course.id
        ),
        viewonly=True
    )


class GradSchoolActivity(Base):
    __tablename__ = "grad_school_activities"
    id = Column(Integer, primary_key=True)
    # type = Column(String, nullable=False)
    activity_type_id = Column(Integer, ForeignKey("grad_school_activity_types.id"), nullable=False)
    description = Column(String, nullable=True)
    year = Column(Integer, nullable=True)

    activity_type = relationship("GradSchoolActivityType", back_populates="activities",
                                 foreign_keys="GradSchoolActivity.activity_type_id")

    student_activities = relationship(
        "GradSchoolStudentActivity",
        back_populates="activity",
        viewonly=True,
        primaryjoin=lambda: and_(
            StudentActivity.activity_type == ActivityType.GRAD_SCHOOL,
            foreign(StudentActivity.activity_id) == GradSchoolActivity.id
        )
    )

    # back‐reference: all courses linked to this grad‐school activity
    courses = relationship("Course", back_populates="grad_school_activity",
                           foreign_keys="Course.grad_school_activity_id")


# Core domain entities
class Person(Base):
    __tablename__ = "people"
    id = Column(Integer, primary_key=True)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    roles = relationship("PersonRole", back_populates="person", cascade="all, delete-orphan")


class PersonRole(Base):
    __tablename__ = "people_roles"
    id = Column(Integer, primary_key=True)
    person_id = Column(Integer, ForeignKey("people.id"), nullable=False)
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=False)
    start_date = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    end_date = Column(DateTime, nullable=True)
    notes = Column(String, nullable=True)

    # --- IS_ACTIVE PROPERTY ---
    @property
    def is_active(self) -> bool:
        # 1. If no end_date, they are active
        if self.end_date is None:
            return True

        # 2. Get "Start of Today" in UTC (matching CRUD logic)
        start_of_today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

        # 3. Prepare end_date for comparison
        # (SQLite might return a naive datetime; force it to UTC to match start_of_today)
        end_date_checked = self.end_date
        if end_date_checked.tzinfo is None:
            end_date_checked = end_date_checked.replace(tzinfo=timezone.utc)
        else:
            end_date_checked = end_date_checked.astimezone(timezone.utc)

        # 4. Compare
        return end_date_checked >= start_of_today

    # -------------------------------

    person = relationship("Person", back_populates="roles")
    role = relationship("Role", back_populates="person_roles")
    researcher = relationship("Researcher", back_populates="person_role", uselist=False)
    phd_student = relationship("PhDStudent", back_populates="person_role", uselist=False)
    postdoc = relationship("Postdoc", back_populates="person_role", uselist=False)
    institutions = relationship("PersonInstitution", back_populates="person_role",
                                cascade="all, delete-orphan")
    fields = relationship("PersonField", back_populates="person_role", cascade="all, delete-orphan")
    projects = relationship("PersonProject", back_populates="person_role", cascade="all, delete-orphan")
    supervised_students = relationship(
        "SupervisorPhDStudent",
        back_populates="supervisor",
        foreign_keys="SupervisorPhDStudent.supervisor_role_id",
        cascade="all, delete-orphan"
    )
    student_supervisors = relationship(
        "SupervisorPhDStudent",
        back_populates="student",
        foreign_keys="SupervisorPhDStudent.student_role_id",
        cascade="all, delete-orphan"
    )
    courses_teaching = relationship(
        "CourseTeacher",
        back_populates="person_role",
        cascade="all, delete-orphan"
    )
    decision_letters = relationship(
        "DecisionLetter",
        primaryjoin=lambda: and_(
            DecisionLetter.entity_type == EntityType.PERSON_ROLE,
            foreign(DecisionLetter.entity_id) == PersonRole.id
        ),
        viewonly=True
    )


class Researcher(Base):
    __tablename__ = "researchers"
    id = Column(Integer, primary_key=True)
    person_role_id = Column(Integer, ForeignKey("people_roles.id"), nullable=False)
    title_id = Column(Integer, ForeignKey("researcher_titles.id"), nullable=True)
    original_title_id = Column(Integer, ForeignKey("researcher_titles.id"), nullable=True)
    link = Column(String, nullable=True)
    notes = Column(String, nullable=True)

    person_role = relationship("PersonRole", back_populates="researcher")
    title = relationship("ResearcherTitle", back_populates="researchers",
                         foreign_keys="Researcher.title_id")
    original_title = relationship("ResearcherTitle", back_populates="original_researchers",
                                  foreign_keys="Researcher.original_title_id")


class PhDStudent(Base):
    __tablename__ = "phd_students"
    id = Column(Integer, primary_key=True)
    person_role_id = Column(Integer, ForeignKey("people_roles.id"), nullable=False)
    cohort_number = Column(Integer, nullable=True)
    is_affiliated = Column(Boolean, default=False)
    department = Column(String, nullable=True)
    discipline = Column(String, nullable=True)
    phd_project_title = Column(String, nullable=True)
    planned_defense_date = Column(DateTime, nullable=True)
    is_graduated = Column(Boolean, default=False)
    current_title = Column(String, nullable=True)
    current_organization = Column(String, nullable=True)
    link = Column(String, nullable=True)
    notes = Column(String, nullable=True)

    person_role = relationship("PersonRole", back_populates="phd_student")
    courses = relationship("PhDStudentCourse", back_populates="student", cascade="all, delete-orphan")
    activities = relationship(
        "StudentActivity",
        back_populates="student",
        cascade="all, delete-orphan"
    )


class Postdoc(Base):
    __tablename__ = "postdocs"
    id = Column(Integer, primary_key=True)
    person_role_id = Column(Integer, ForeignKey("people_roles.id"), nullable=False)
    cohort_number = Column(Integer, nullable=True)
    department = Column(String, nullable=True)
    discipline = Column(String, nullable=True)
    postdoc_project_title = Column(String, nullable=True)
    # is_repatriated = Column(Boolean, default=False)
    is_incoming = Column(Boolean, default=False)
    is_graduated = Column(Boolean, default=False)

    # Either point to a known title, or fill in free-text if the title is “Other”
    current_title_id = Column(Integer, ForeignKey("researcher_titles.id"), nullable=True)
    current_title_other = Column(String, nullable=True)

    # Same pattern for institution
    current_institution_id = Column(Integer, ForeignKey("institutions.id"), nullable=True)
    current_institution_other = Column(String, nullable=True)

    # current_department = Column(String, nullable=True)
    link = Column(String, nullable=True)
    notes = Column(String, nullable=True)

    person_role = relationship("PersonRole", back_populates="postdoc")
    current_title = relationship("ResearcherTitle", back_populates="postdocs_as_current",
                                 foreign_keys="Postdoc.current_title_id")
    current_institution = relationship("Institution", back_populates="postdocs_as_current",
                                       foreign_keys="Postdoc.current_institution_id")


class Project(Base):
    __tablename__ = "projects"
    id = Column(Integer, primary_key=True)
    call_type_id = Column(Integer, ForeignKey("project_call_types.id"), nullable=False)
    title = Column(String, nullable=False)
    project_number = Column(String, nullable=False)
    # is_affiliated = Column(Boolean, default=False)
    final_report_submitted = Column(Boolean, default=False)
    is_extended = Column(Boolean, default=False)
    start_date = Column(DateTime, nullable=True)
    end_date = Column(DateTime, nullable=True)
    notes = Column(String, nullable=True)

    call_type = relationship("ProjectCallType", back_populates="projects")
    person_projects = relationship("PersonProject", back_populates="project", cascade="all, delete-orphan")
    fields = relationship("ProjectField", back_populates="project", cascade="all, delete-orphan")
    research_output_reports = relationship("ResearchOutputReport", back_populates="project",
                                           cascade="all, delete-orphan")
    decision_letters = relationship(
        "DecisionLetter",
        primaryjoin=lambda: and_(
            DecisionLetter.entity_type == EntityType.PROJECT,
            foreign(DecisionLetter.entity_id) == Project.id
        ),
        viewonly=True
    )


class SupervisorPhDStudent(Base):
    __tablename__ = "supervisors_phd_students"
    id = Column(Integer, primary_key=True)
    supervisor_role_id = Column(Integer, ForeignKey("people_roles.id"), nullable=False)
    student_role_id = Column(Integer, ForeignKey("people_roles.id"), nullable=False)
    is_main = Column(Boolean, default=False)

    supervisor = relationship(
        "PersonRole",
        back_populates="supervised_students",
        foreign_keys=[supervisor_role_id]  # type: ignore
    )
    student = relationship(
        "PersonRole",
        back_populates="student_supervisors",
        foreign_keys=[student_role_id]  # type: ignore
    )


class PersonInstitution(Base):
    __tablename__ = "person_institutions"
    id = Column(Integer, primary_key=True)
    person_role_id = Column(Integer, ForeignKey("people_roles.id"), nullable=False)
    institution_id = Column(Integer, ForeignKey("institutions.id"), nullable=False)
    start_date = Column(DateTime, nullable=True)
    end_date = Column(DateTime, nullable=True)

    __table_args__ = (
        CheckConstraint("end_date IS NULL OR end_date >= start_date",
                        name="ck_person_institution_dates"),
    )

    person_role = relationship("PersonRole", back_populates="institutions")
    institution = relationship("Institution", back_populates="person_institutions")


class PersonField(Base):
    __tablename__ = "person_fields"
    id = Column(Integer, primary_key=True)
    person_role_id = Column(Integer, ForeignKey("people_roles.id"), nullable=False)
    field_id = Column(Integer, ForeignKey("academic_fields.id"), nullable=False)

    person_role = relationship("PersonRole", back_populates="fields")
    field = relationship("AcademicField", back_populates="person_fields")


class PersonProject(Base):
    __tablename__ = "person_projects"
    id = Column(Integer, primary_key=True)
    person_role_id = Column(Integer, ForeignKey("people_roles.id"), nullable=False)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    is_principal_investigator = Column(Boolean, default=False)
    # is_leader = Column(Boolean, default=False)
    is_contact_person = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True, nullable=False)

    person_role = relationship("PersonRole", back_populates="projects")
    project = relationship("Project", back_populates="person_projects")


class PhDStudentCourse(Base):
    __tablename__ = "phd_students_courses"
    __table_args__ = (
        UniqueConstraint("phd_student_id", "course_id", name="uq_student_course"),
    )
    id = Column(Integer, primary_key=True)
    phd_student_id = Column(Integer, ForeignKey("phd_students.id"), nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    is_completed = Column(Boolean, default=False)
    grade = Column(SQLEnum(GradeType, name="grade_type_enum"), nullable=True)

    student = relationship("PhDStudent", back_populates="courses")
    course = relationship("Course", back_populates="student_courses")


class CourseTeacher(Base):
    __tablename__ = "courses_teachers"
    __table_args__ = (
        UniqueConstraint("course_id", "person_role_id", name="uq_course_teacher"),
    )

    id = Column(Integer, primary_key=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    person_role_id = Column(Integer, ForeignKey("people_roles.id"), nullable=False)

    course = relationship("Course", back_populates="teachers")
    person_role = relationship("PersonRole", back_populates="courses_teaching")


class CourseTerm(Base):
    __tablename__ = "course_terms"
    id = Column(Integer, primary_key=True)
    season = Column(SQLEnum(Season, name="season_enum"), nullable=False)
    year = Column(Integer, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    # back‐reference: all courses using this term
    courses = relationship("Course", back_populates="course_term", foreign_keys="Course.course_term_id")


class StudentActivity(Base):
    __tablename__ = "student_activities"
    __table_args__ = (
        UniqueConstraint("phd_student_id", "activity_type", "activity_id", name="uq_student_activity"),
    )
    id = Column(Integer, primary_key=True)
    phd_student_id = Column(Integer, ForeignKey("phd_students.id"), nullable=False)
    activity_type = Column(SQLEnum(ActivityType, name="activity_type_enum"), nullable=False)
    activity_id = Column(Integer, nullable=False)

    __mapper_args__ = {
        'polymorphic_on': activity_type,
        'polymorphic_identity': 'student_activity'
    }

    student = relationship("PhDStudent", back_populates="activities")


class GradSchoolStudentActivity(StudentActivity):
    __mapper_args__ = {'polymorphic_identity': ActivityType.GRAD_SCHOOL}

    is_completed = Column(Boolean, default=False)
    grade = Column(SQLEnum(GradeType, name="grade_type_enum"), nullable=True)

    activity = relationship(
        "GradSchoolActivity",
        back_populates="student_activities",
        viewonly=True,
        primaryjoin=lambda: and_(
            StudentActivity.activity_type == ActivityType.GRAD_SCHOOL,
            foreign(StudentActivity.activity_id) == GradSchoolActivity.id
        )
    )


class AbroadStudentActivity(StudentActivity):
    __mapper_args__ = {'polymorphic_identity': ActivityType.ABROAD}

    description = Column(String, nullable=True)
    start_date = Column(DateTime, nullable=True)
    end_date = Column(DateTime, nullable=True)
    city = Column(String, nullable=True)
    country = Column(String, nullable=True)
    host_institution = Column(String, nullable=True)


class GradSchoolActivityType(Base):
    __tablename__ = "grad_school_activity_types"
    id = Column(Integer, primary_key=True)
    type = Column(String, nullable=False)

    # back‐reference from activities
    activities = relationship("GradSchoolActivity", back_populates="activity_type",
                              cascade="all, delete-orphan")


class ProjectField(Base):
    __tablename__ = "project_fields"
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    field_id = Column(Integer, ForeignKey("academic_fields.id"), nullable=False)

    project = relationship("Project", back_populates="fields")
    field = relationship("AcademicField", back_populates="project_fields")


class ResearchOutputReport(Base):
    __tablename__ = "research_output_reports"
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    link = Column(String, nullable=True)

    project = relationship("Project", back_populates="research_output_reports")


class CourseInstitution(Base):
    __tablename__ = "courses_institutions"
    id = Column(Integer, primary_key=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    institution_id = Column(Integer, ForeignKey("institutions.id"), nullable=False)

    course = relationship("Course", back_populates="course_institutions")
    institution = relationship("Institution", back_populates="course_institutions")


class DecisionLetter(Base):
    __tablename__ = "decision_letters"
    id = Column(Integer, primary_key=True)
    entity_type = Column(SQLEnum(EntityType, name="entity_type_enum"), nullable=False)
    entity_id = Column(Integer, nullable=False)
    link = Column(String, nullable=True)

    __mapper_args__ = {
        'polymorphic_on': entity_type,
        'polymorphic_identity': 'decision_letter'
    }

    person_role = relationship(
        "PersonRole",
        primaryjoin=lambda: and_(
            DecisionLetter.entity_type == EntityType.PERSON_ROLE,
            foreign(DecisionLetter.entity_id) == PersonRole.id
        ),
        viewonly=True
    )
    project = relationship(
        "Project",
        primaryjoin=lambda: and_(
            DecisionLetter.entity_type == EntityType.PROJECT,
            foreign(DecisionLetter.entity_id) == Project.id
        ),
        viewonly=True
    )
    course = relationship(
        "Course",
        primaryjoin=lambda: and_(
            DecisionLetter.entity_type == EntityType.COURSE,
            foreign(DecisionLetter.entity_id) == Course.id
        ),
        viewonly=True
    )


class PersonRoleDecisionLetter(DecisionLetter):
    __mapper_args__ = {'polymorphic_identity': EntityType.PERSON_ROLE}


class ProjectDecisionLetter(DecisionLetter):
    __mapper_args__ = {'polymorphic_identity': EntityType.PROJECT}


class CourseDecisionLetter(DecisionLetter):
    __mapper_args__ = {'polymorphic_identity': EntityType.COURSE}
