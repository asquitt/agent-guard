"""Pydantic schemas for authentication endpoints."""

import re
from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


def _validate_password_strength(v: str) -> str:
    """Shared password strength validation (12+ chars, upper, lower, digit, special)."""
    if len(v) < 12:
        raise ValueError("Password must be at least 12 characters long")
    if not re.search(r"[A-Z]", v):
        raise ValueError("Password must contain at least one uppercase letter")
    if not re.search(r"[a-z]", v):
        raise ValueError("Password must contain at least one lowercase letter")
    if not re.search(r"\d", v):
        raise ValueError("Password must contain at least one digit")
    if not re.search(r"[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>/?`~]", v):
        raise ValueError("Password must contain at least one special character")
    return v


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)
    full_name: str = Field(min_length=1, max_length=255)
    org_name: str = Field(min_length=1, max_length=255)
    controlled_evaluation_accepted: Literal[True]
    access_code: str | None = Field(default=None, max_length=512)

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        return _validate_password_strength(v)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID
    email: str
    full_name: str = Field(serialization_alias="name")
    role: str
    org_id: UUID = Field(serialization_alias="organizationId")
    is_active: bool = Field(serialization_alias="isActive")
    mfa_enabled: bool = Field(default=False, serialization_alias="mfaEnabled")
    created_at: datetime = Field(serialization_alias="createdAt")


class OrgResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID
    name: str
    slug: str
    plan_tier: str = Field(serialization_alias="planTier")
    settings: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(serialization_alias="createdAt")


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=12, max_length=128)

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        return _validate_password_strength(v)


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=12, max_length=128)

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        return _validate_password_strength(v)


class UpdateProfileRequest(BaseModel):
    full_name: str | None = Field(None, min_length=1, max_length=255)


class MeResponse(BaseModel):
    user: UserResponse
    organization: OrgResponse


# ---------------------------------------------------------------------------
# MFA schemas
# ---------------------------------------------------------------------------


class LoginResponse(BaseModel):
    """Login response — may include tokens or require MFA verification."""

    access_token: str | None = None
    refresh_token: str | None = None
    token_type: str = "bearer"
    mfa_required: bool = False
    mfa_token: str | None = None  # Temporary token for MFA verification step


class MfaSetupResponse(BaseModel):
    secret: str
    qr_code: str  # base64 PNG
    backup_codes: list[str]


class MfaVerifyRequest(BaseModel):
    code: str = Field(min_length=6, max_length=8)  # 6-digit TOTP or 8-char backup code


class MfaLoginVerifyRequest(BaseModel):
    mfa_token: str
    code: str = Field(min_length=6, max_length=8)
