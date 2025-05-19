from typing import Optional
from pydantic import BaseModel, ConfigDict


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
