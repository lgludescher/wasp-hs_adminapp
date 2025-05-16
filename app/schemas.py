from pydantic import BaseModel, ConfigDict


class UserBase(BaseModel):
    username: str
    name: str
    email: str


class UserCreate(UserBase):
    pass


class UserRead(UserBase):
    id: int
    is_admin: bool

    # Pydantic v2: use ConfigDict(from_attributes=True) instead of orm_mode
    model_config = ConfigDict(from_attributes=True)
