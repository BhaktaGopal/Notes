from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models import Role


class UserRegister(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    username: str = Field(
        min_length=3,
        max_length=50,
        pattern=r"^[a-zA-Z0-9_.-]+$",
    )
    email: EmailStr
    password: str = Field(
        min_length=12,
        max_length=128,
    )


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: str
    role: str
    department: str
    clearance: int
    is_active: bool


class UserAccessUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: Role
    department: str = Field(min_length=1, max_length=100)
    clearance: int = Field(ge=0, le=10)
    is_active: bool


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class DocumentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=200)
    content: str
    classification: int = Field(default=0, ge=0, le=10)


class DocumentPut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=200)
    content: str
    classification: int = Field(ge=0, le=10)


class DocumentPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(
        default=None,
        min_length=1,
        max_length=200,
    )
    content: str | None = None
    classification: int | None = Field(
        default=None,
        ge=0,
        le=10,
    )


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    content: str
    owner_id: int
    department: str
    classification: int