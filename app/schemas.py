from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict
from enum import Enum as PyEnum
from .models import GradeType, EntityType


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
    is_affiliated:  Optional[bool] = False
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
    is_affiliated:              Optional[bool] = None
    is_extended:                Optional[bool] = None
    start_date:                 Optional[datetime] = None
    end_date:                   Optional[datetime] = None
    notes:                      Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


# </editor-fold>

# <editor-fold desc="Course relationships entities">
# --- Course ↔ Institutions ---
class CourseInstitutionLink(BaseModel):
    institution_id: int

    model_config = ConfigDict(from_attributes=True)


# class CourseInstitutionCreate(BaseModel):
#     institution_id: int
#
#
# class CourseInstitutionRead(BaseModel):
#     id: int
#     institution: str
#
#     model_config = ConfigDict(from_attributes=True)


# --- Course ↔ Students ---
# class CourseStudentCreate(BaseModel):
#     phd_student_id: int
#     is_completed: Optional[bool] = False
#     grade: Optional[GradeType] = None
#
#
# class CourseStudentRead(BaseModel):
#     id: int
#     phd_student_id: int
#     is_completed: bool
#     grade: Optional[GradeType]
#
#     model_config = ConfigDict(from_attributes=True)


# --- Course ↔ Teachers ---
# class CourseTeacherCreate(BaseModel):
#     person_role_id: int
#
#
# class CourseTeacherRead(BaseModel):
#     id: int
#     person_role_id: int
#
#     model_config = ConfigDict(from_attributes=True)


# </editor-fold>

# <editor-fold desc="Project relationships entities">
# --- Project ↔ Fields ---
class ProjectFieldLink(BaseModel):
    field_id: int

    model_config = ConfigDict(from_attributes=True)


# </editor-fold>
