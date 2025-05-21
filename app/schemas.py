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
    model_config = ConfigDict(from_attributes=True)


class CourseUpdate(BaseModel):
    title:                      Optional[str] = None
    course_term_id:             Optional[int] = None
    grad_school_activity_id:    Optional[int] = None
    credit_points:              Optional[int] = None
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


# --- Course ↔ DecisionLetters ---
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
