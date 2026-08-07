"""Auth request/response schemas."""
from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=10, max_length=256)
    display_name: str | None = Field(default=None, max_length=120)
    gender: str | None = Field(default=None, max_length=20)
    locale: str = Field(default="en", max_length=10)


class RegisterResponse(BaseModel):
    """Deliberately generic: never reveals whether the email already exists.
    
    In production the frontend should store challenge_id and never show it to the
    user — it's passed hidden to the verify endpoint.
    """

    status: str = "verification_pending"
    challenge_id: str | None = None
    message: str = (
        "If this email can be registered, a verification code has been sent."
    )


class VerifyChallengeRequest(BaseModel):
    code: str = Field(min_length=4, max_length=16)


class VerifyChallengeResponse(BaseModel):
    status: str = "verified"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=256)


class GoogleAuthRequest(BaseModel):
    id_token: str = Field(min_length=1)


class PhoneStartRequest(BaseModel):
    phone: str = Field(min_length=8, max_length=20)


class PhoneStartResponse(BaseModel):
    """Deliberately generic: never reveals whether the phone is already registered.
    
    In production the frontend should store challenge_id and never show it to the
    user — it's passed hidden to the verify endpoint.
    """

    status: str = "verification_pending"
    challenge_id: str | None = None
    message: str = (
        "If this phone number can be registered, a verification code has been sent."
    )


class PhoneVerifyRequest(BaseModel):
    challenge_id: str = Field(min_length=1)
    code: str = Field(min_length=4, max_length=16)


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=1)


class RefreshResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int


class LogoutResponse(BaseModel):
    status: str = "logged_out"


class LogoutAllResponse(BaseModel):
    status: str = "logged_out_all"


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ForgotPasswordResponse(BaseModel):
    """Deliberately generic: never reveals whether the email exists."""

    status: str = "reset_pending"
    message: str = "If this email has an account, a reset code has been sent."


class ResetPasswordRequest(BaseModel):
    challenge_id: str = Field(min_length=1)
    code: str = Field(min_length=4, max_length=16)
    new_password: str = Field(min_length=10, max_length=256)


class ResetPasswordResponse(BaseModel):
    status: str = "password_reset"
