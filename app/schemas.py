from datetime import datetime
from typing import Optional, List, Union, Literal
from pydantic import BaseModel, ConfigDict
from enum import Enum as PyEnum
from .models import GradeType, EntityType, RoleType, ActivityType


# <editor-fold desc="User-related entities">
# ---------- User ----------

class UserBase(BaseModel):
    username: str
    name: str
    email: str


class UserCreate(UserBase):
    is_admin: bool = False


class UserRead(UserBase):
    id: int
    is_admin: bool

    # Pydantic v2: use ConfigDict(from_attributes=True) instead of orm_mode
    model_config = ConfigDict(from_attributes=True)


class UserUpdate(BaseModel):
    name:     Optional[str] = None
    email:    Optional[str] = None
    is_admin: Optional[bool] = None

    model_config = ConfigDict(from_attributes=True)


# </editor-fold>

# <editor-fold desc="Institution-related entities">
# ---------- Institution ----------

class InstitutionBase(BaseModel):
    institution: str


class InstitutionCreate(InstitutionBase):
    pass


class InstitutionRead(InstitutionBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


class InstitutionUpdate(BaseModel):
    institution: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# </editor-fold>

# <editor-fold desc="Domain-related entities">
# ---------- Domain ----------

# Academic Branch
class BranchBase(BaseModel):
    branch: str


class BranchCreate(BranchBase):
    pass


class BranchRead(BranchBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


class BranchUpdate(BaseModel):
    branch: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


# Academic Field
class FieldBase(BaseModel):
    field: str
    branch_id: int


class FieldCreate(FieldBase):
    pass


class FieldRead(FieldBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


class FieldUpdate(BaseModel):
    field: Optional[str] = None
    branch_id: Optional[int] = None
    model_config = ConfigDict(from_attributes=True)


# </editor-fold>

# <editor-fold desc="Decision Letter-related entities">
# ---------- Decision Letter ----------

class DecisionLetterCreate(BaseModel):
    link: str


class DecisionLetterRead(BaseModel):
    id:   int
    link: str

    model_config = ConfigDict(from_attributes=True)


class DecisionLetterUpdate(BaseModel):
    link: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# </editor-fold>

# <editor-fold desc="Grad School Activity-related entities">
# ---------- Grad School Activity ----------

# Grad School Activity Type
class GradSchoolActivityTypeBase(BaseModel):
    type: str


class GradSchoolActivityTypeCreate(GradSchoolActivityTypeBase):
    pass


class GradSchoolActivityTypeRead(GradSchoolActivityTypeBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


class GradSchoolActivityTypeUpdate(BaseModel):
    type: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# Grad School Activity
class GradSchoolActivityBase(BaseModel):
    activity_type_id:   Optional[int] = None
    description:        Optional[str] = None
    year:               Optional[int] = None


class GradSchoolActivityCreate(GradSchoolActivityBase):
    pass


class GradSchoolActivityRead(GradSchoolActivityBase):
    id:             int
    activity_type:  GradSchoolActivityTypeRead
    model_config = ConfigDict(from_attributes=True)


class GradSchoolActivityUpdate(BaseModel):
    activity_type_id:   Optional[int] = None
    description:        Optional[str] = None
    year:               Optional[int] = None
    model_config = ConfigDict(from_attributes=True)

# </editor-fold>

# <editor-fold desc="Course-related entities">
# ---------- Course ----------

# Course Term
class CourseTermRead(BaseModel):
    id:        int
    season:    PyEnum  # uses Season enum
    year:      int
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class CourseTermUpdate(BaseModel):
    is_active: bool
    model_config = ConfigDict(from_attributes=True)


# Course
class CourseBase(BaseModel):
    title:                      str
    course_term_id:             Optional[int] = None
    grad_school_activity_id:    Optional[int] = None
    credit_points:              Optional[int] = None
    notes:                      Optional[str] = None


class CourseCreate(CourseBase):
    pass  # no extra


class CourseRead(CourseBase):
    id:        int
    course_term: Optional[CourseTermRead] = None
    grad_school_activity: Optional[GradSchoolActivityRead] = None
    model_config = ConfigDict(from_attributes=True)


class CourseUpdate(BaseModel):
    title:                      Optional[str] = None
    course_term_id:             Optional[int] = None
    grad_school_activity_id:    Optional[int] = None
    credit_points:              Optional[int] = None
    notes:                      Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


# </editor-fold>

# <editor-fold desc="Project-related entities">
# ---------- Project ----------

# Project Call Type
class ProjectCallTypeBase(BaseModel):
    type: str


class ProjectCallTypeCreate(ProjectCallTypeBase):
    pass


class ProjectCallTypeRead(ProjectCallTypeBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


class ProjectCallTypeUpdate(BaseModel):
    type: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# Research output report
class ResearchOutputReportCreate(BaseModel):
    link: str


class ResearchOutputReportRead(BaseModel):
    id:   int
    link: str

    model_config = ConfigDict(from_attributes=True)


class ResearchOutputReportUpdate(BaseModel):
    link: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# Project
class ProjectBase(BaseModel):
    call_type_id:   int
    title:          str
    project_number: str
    # is_affiliated:  Optional[bool] = False
    final_report_submitted: Optional[bool] = False
    is_extended:    Optional[bool] = False
    start_date:     Optional[datetime] = None
    end_date:       Optional[datetime] = None
    notes:          Optional[str] = None


class ProjectCreate(ProjectBase):
    pass  # no extra


class ProjectRead(ProjectBase):
    id:         int
    call_type:  ProjectCallTypeRead
    model_config = ConfigDict(from_attributes=True)


class ProjectUpdate(BaseModel):
    call_type_id:               Optional[int] = None
    title:                      Optional[str] = None
    project_number:             Optional[str] = None
    # is_affiliated:              Optional[bool] = None
    final_report_submitted:     Optional[bool] = None
    is_extended:                Optional[bool] = None
    start_date:                 Optional[datetime] = None
    end_date:                   Optional[datetime] = None
    notes:                      Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


# </editor-fold>

# <editor-fold desc="Person-related entities">
# ---------- Person ----------

# Role
class RoleRead(BaseModel):
    id: int
    role: RoleType

    model_config = ConfigDict(from_attributes=True)


# Person
class PersonBase(BaseModel):
    first_name: str
    last_name: str
    email: str


class PersonCreate(PersonBase):
    pass


# This is just to nest a list of roles (and their respective start and end dates) in Person
class PersonRoleReadSlim(BaseModel):
    id:           int
    start_date:   datetime
    end_date:     Optional[datetime]
    notes:        Optional[str]
    role:         RoleRead

    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class PersonRead(PersonBase):
    id: int
    roles: List[PersonRoleReadSlim]

    model_config = ConfigDict(from_attributes=True)


class PersonUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# </editor-fold>

# <editor-fold desc="Person Role-related entities">
# ---------- Person Role ----------

class PersonRoleBase(BaseModel):
    person_id: int
    role_id:   int
    start_date: Optional[datetime] = None
    end_date:   Optional[datetime] = None
    notes: Optional[str] = None


class PersonRoleCreate(PersonRoleBase):
    pass


# This includes PersonRead
class PersonRoleReadFull(BaseModel):
    id:           int
    start_date:   datetime
    end_date:     Optional[datetime]
    notes:        Optional[str]
    role:         RoleRead
    person:       PersonRead

    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class PersonRoleUpdate(BaseModel):
    start_date: Optional[datetime] = None
    end_date:   Optional[datetime] = None
    notes:      Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


# </editor-fold>

# <editor-fold desc="Researcher-related entities">
# ---------- Researcher ----------

# Researcher Title
class ResearcherTitleBase(BaseModel):
    title: str


class ResearcherTitleCreate(ResearcherTitleBase):
    pass


class ResearcherTitleRead(ResearcherTitleBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


class ResearcherTitleUpdate(BaseModel):
    title: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# Researcher
class ResearcherBase(BaseModel):
    person_role_id:    int
    title_id:          Optional[int] = None
    original_title_id: Optional[int] = None
    link:              Optional[str] = None
    notes:             Optional[str] = None


class ResearcherCreate(ResearcherBase):
    pass


class ResearcherRead(ResearcherBase):
    id: int
    person_role: PersonRoleReadFull

    title:          Optional[ResearcherTitleRead]
    original_title: Optional[ResearcherTitleRead]

    model_config = ConfigDict(from_attributes=True)


class ResearcherUpdate(BaseModel):
    title_id:          Optional[int] = None
    original_title_id: Optional[int] = None
    link:              Optional[str] = None
    notes:             Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


# </editor-fold>

# <editor-fold desc="PhD Student-related entities">
# ---------- PhD Student ----------

class PhDStudentBase(BaseModel):
    person_role_id:      int
    cohort_number:       Optional[int] = None
    is_affiliated:       Optional[bool] = None
    department:          Optional[str] = None
    discipline:          Optional[str] = None
    phd_project_title:   Optional[str] = None
    planned_defense_date: Optional[datetime] = None
    is_graduated:        Optional[bool] = None
    current_title:       Optional[str] = None
    current_organization: Optional[str] = None
    link:                Optional[str] = None
    notes:               Optional[str] = None


class PhDStudentCreate(PhDStudentBase):
    pass


class PhDStudentRead(PhDStudentBase):
    id:          int
    person_role: PersonRoleReadFull

    model_config = ConfigDict(from_attributes=True)


class PhDStudentUpdate(BaseModel):
    cohort_number:        Optional[int] = None
    is_affiliated:        Optional[bool] = None
    department:           Optional[str] = None
    discipline:           Optional[str] = None
    phd_project_title:    Optional[str] = None
    planned_defense_date: Optional[datetime] = None
    is_graduated:         Optional[bool] = None
    current_title:        Optional[str] = None
    current_organization: Optional[str] = None
    link:                 Optional[str] = None
    notes:                Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


# </editor-fold>

# <editor-fold desc="Postdoc-related entities">
# ---------- Postdoc ----------

class PostdocBase(BaseModel):
    person_role_id:        int
    cohort_number:         Optional[int] = None
    department:            Optional[str] = None
    discipline:            Optional[str] = None
    postdoc_project_title: Optional[str] = None
    is_incoming:           Optional[bool] = False
    is_graduated:          Optional[bool] = False
    current_title_id:      Optional[int] = None
    current_title_other:   Optional[str] = None
    current_institution_id: Optional[int] = None
    current_institution_other: Optional[str] = None
    # current_department:    Optional[str] = None
    link:                  Optional[str] = None
    notes:                 Optional[str] = None


class PostdocCreate(PostdocBase):
    pass


class PostdocRead(PostdocBase):
    id:          int
    person_role: PersonRoleReadFull

    current_title: Optional[ResearcherTitleRead]
    current_institution: Optional[InstitutionRead]

    model_config = ConfigDict(from_attributes=True)


class PostdocUpdate(BaseModel):
    cohort_number:          Optional[int] = None
    department:             Optional[str] = None
    discipline:             Optional[str] = None
    postdoc_project_title:  Optional[str] = None
    is_incoming:            Optional[bool] = None
    is_graduated:           Optional[bool] = None
    current_title_id:       Optional[int] = None
    current_title_other:    Optional[str] = None
    current_institution_id: Optional[int] = None
    current_institution_other: Optional[str] = None
    # current_department:     Optional[str] = None
    link:                   Optional[str] = None
    notes:                  Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


# </editor-fold>

# <editor-fold desc="Student Activity-related entities">
# ---------- Student Activity ----------

class StudentActivityBase(BaseModel):
    phd_student_id: int
    # activity_type: PyEnum  # will be either ActivityType.GRAD_SCHOOL or ActivityType.ABROAD

    model_config = ConfigDict(from_attributes=True)


class GradSchoolActivityLinkBase(StudentActivityBase):
    # activity_type: PyEnum  # ActivityType.GRAD_SCHOOL
    activity_id: int  # FK → GradSchoolActivity.id
    is_completed: Optional[bool] = False
    grade: Optional[GradeType] = None

    model_config = ConfigDict(from_attributes=True)


class GradSchoolStudentActivityCreate(GradSchoolActivityLinkBase):
    # For creation, all fields except `id` come from client
    # activity_type: PyEnum  # must be ActivityType.GRAD_SCHOOL
    activity_type: Literal[ActivityType.GRAD_SCHOOL] = ActivityType.GRAD_SCHOOL
    activity_id: int
    is_completed: Optional[bool] = False
    grade: Optional[GradeType] = None

    model_config = ConfigDict(from_attributes=True)


class AbroadStudentActivityCreate(StudentActivityBase):
    # activity_type: PyEnum  # must be ActivityType.ABROAD
    activity_type: Literal[ActivityType.ABROAD] = ActivityType.ABROAD
    description: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    city: Optional[str] = None
    country: Optional[str] = None
    host_institution: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class StudentActivityRead(BaseModel):
    id: int
    phd_student_id: int
    activity_type: PyEnum  # ActivityType.GRAD_SCHOOL or ActivityType.ABROAD

    # fields present only when activity_type == GRAD_SCHOOL:
    # activity_id: Optional[int] = None
    activity: Optional[GradSchoolActivityRead] = None
    is_completed: Optional[bool] = None
    grade: Optional[PyEnum] = None  # GradeType

    # fields present only when activity_type == ABROAD:
    description: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    city: Optional[str] = None
    country: Optional[str] = None
    host_institution: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# </editor-fold>

# <editor-fold desc="Course relationships entities">
# --- Course ↔ Institutions ---
class CourseInstitutionLink(BaseModel):
    institution_id: int

    model_config = ConfigDict(from_attributes=True)


# --- Course ↔ Teachers ---
class CourseTeacherLink(BaseModel):
    person_role_id: int

    model_config = ConfigDict(from_attributes=True)


# --- Course ↔ Students ---
class CourseStudentLink(BaseModel):
    phd_student_id: int
    is_completed: Optional[bool] = False
    grade: Optional[GradeType] = None

    model_config = ConfigDict(from_attributes=True)


class CourseStudentRead(BaseModel):
    phd_student_id: int
    course_id: int
    is_completed: bool
    grade: Optional[GradeType]

    model_config = ConfigDict(from_attributes=True)


# </editor-fold>

# <editor-fold desc="Project relationships entities">
# --- Project ↔ Fields ---
class ProjectFieldLink(BaseModel):
    field_id: int

    model_config = ConfigDict(from_attributes=True)


# --- Project ↔ People Roles ---
class ProjectPersonRoleLink(BaseModel):
    person_role_id: int
    is_principal_investigator: Optional[bool] = False
    # is_leader: Optional[bool] = False
    is_contact_person: Optional[bool] = False
    is_active: Optional[bool] = True

    model_config = ConfigDict(from_attributes=True)


class ProjectPersonRoleRead(BaseModel):
    person_role_id: int
    project_id: int
    is_principal_investigator: bool
    # is_leader: bool
    is_contact_person: bool
    is_active: bool

    person_role: PersonRoleReadFull
    project: ProjectRead

    model_config = ConfigDict(from_attributes=True)


# </editor-fold>

# <editor-fold desc="Person Role relationships entities">
# --- Person Role ↔ Institutions ---
class PersonRoleInstitutionLink(BaseModel):
    institution_id: int
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class PersonRoleInstitutionRead(BaseModel):
    institution_id: int
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# --- Person Role ↔ Fields ---
class PersonRoleFieldLink(BaseModel):
    field_id: int

    model_config = ConfigDict(from_attributes=True)


# --- Students ↔ Supervisors ---
class SupervisionBase(BaseModel):
    supervisor_role_id: int
    student_role_id:    int
    is_main:            bool = False


class SupervisionCreate(SupervisionBase):
    pass


class SupervisionRead(SupervisionBase):
    id: int

    supervisor: PersonRoleReadFull
    student: PersonRoleReadFull

    model_config = ConfigDict(from_attributes=True)


class SupervisionUpdate(BaseModel):
    is_main: Optional[bool] = False

    model_config = ConfigDict(from_attributes=True)


# </editor-fold>
