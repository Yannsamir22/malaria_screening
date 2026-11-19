from enum import StrEnum
from typing import Annotated
from pydantic import BaseModel, EmailStr, Field, ConfigDict, field_validator, model_validator

class Role(StrEnum):
    ADMINISTRATOR = "administrator"
    CLINICIAN = "clinician"
    TECHNICIAN = "technician"
    PUBLIC_HEALTH_OFFICER = "public_health_officer"

class UserStatus(StrEnum):
    ACTIVE = "active"
    DEACTIVATED = "deactivated"

FullName = Annotated[str, Field(min_length=1, max_length=120)]
Facility = Annotated[str, Field(min_length=1, max_length=120)]
Email = Annotated[EmailStr, Field(max_length=254)]

class RegisterRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: Email
    full_name: FullName
    password: str = Field(min_length=12, max_length=128)
    role: Role
    facility: Facility | None = None

    @field_validator("facility", mode="before")
    @classmethod
    def reject_null_facility(cls, value):
        if value is None:
            raise ValueError("Facility cannot be null.")
        return value

class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: Email
    password: str = Field(min_length=12, max_length=128)

class RefreshRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    refresh_token: str

class UserPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    full_name: FullName | None = None
    facility: Facility | None = None
    role: Role | None = None

    @field_validator("full_name", "facility", "role", mode="before")
    @classmethod
    def reject_null_fields(cls, value):
        if value is None:
            raise ValueError("Fields cannot be null.")
        return value

    @model_validator(mode="after")
    def reject_empty_patch(self):
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided.")
        return self

class User(BaseModel):
    id: str
    created: str
    email: str
    full_name: str
    role: Role
    status: UserStatus
    facility: str | None = None

class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int

class UserList(BaseModel):
    users: list[User]

class Health(BaseModel):
    status: str
    service: str