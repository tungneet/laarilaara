"""Authentication and account endpoints (catalog §4)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, status

from app.core.dependencies import CurrentSession, get_current_session
from app.core.errors import ApiError
from app.repositories import challenges as challenges_repo
from app.repositories import sessions as sessions_repo
from app.schemas.auth import (
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    LoginRequest,
    LoginResponse,
    LogoutAllResponse,
    LogoutResponse,
    RefreshRequest,
    RefreshResponse,
    RegisterRequest,
    RegisterResponse,
    ResetPasswordRequest,
    ResetPasswordResponse,
    VerifyChallengeRequest,
    VerifyChallengeResponse,
)
from app.services import auth as auth_service

router = APIRouter(prefix="/v1/auth", tags=["auth"])

_INVALID_CHALLENGE_ERROR = ApiError(
    status=status.HTTP_400_BAD_REQUEST,
    code="CHALLENGE_INVALID",
    title="Invalid or expired verification code",
)

_INVALID_CREDENTIALS_ERROR = ApiError(
    status=status.HTTP_401_UNAUTHORIZED,
    code="INVALID_CREDENTIALS",
    title="Invalid email or password",
)

_ACCOUNT_NOT_VERIFIED_ERROR = ApiError(
    status=status.HTTP_403_FORBIDDEN,
    code="ACCOUNT_NOT_VERIFIED",
    title="Account email is not verified yet",
)

_INVALID_REFRESH_TOKEN_ERROR = ApiError(
    status=status.HTTP_401_UNAUTHORIZED,
    code="INVALID_REFRESH_TOKEN",
    title="Invalid, expired, or revoked refresh token",
)

_INVALID_RESET_ERROR = ApiError(
    status=status.HTTP_400_BAD_REQUEST,
    code="CHALLENGE_INVALID",
    title="Invalid or expired reset code",
)


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def register(payload: RegisterRequest) -> RegisterResponse:
    auth_service.register_account(
        email=str(payload.email),
        password=payload.password,
        locale=payload.locale,
        display_name=payload.display_name,
        gender=payload.gender,
    )
    # Generic response regardless of whether the email was new.
    return RegisterResponse()


@router.post(
    "/challenges/{challenge_id}/verify",
    response_model=VerifyChallengeResponse,
    status_code=status.HTTP_200_OK,
)
async def verify_challenge(
    challenge_id: str, payload: VerifyChallengeRequest
) -> VerifyChallengeResponse:
    try:
        auth_service.verify_challenge(challenge_id, payload.code)
    except (
        challenges_repo.ChallengeNotFoundError,
        challenges_repo.ChallengeInvalidError,
    ) as exc:
        raise _INVALID_CHALLENGE_ERROR from exc
    return VerifyChallengeResponse()


@router.post(
    "/login",
    response_model=LoginResponse,
    status_code=status.HTTP_200_OK,
)
async def login(payload: LoginRequest) -> LoginResponse:
    try:
        access_token, refresh_token, expires_in = auth_service.login(
            email=str(payload.email), password=payload.password
        )
    except auth_service.InvalidCredentialsError as exc:
        raise _INVALID_CREDENTIALS_ERROR from exc
    except auth_service.AccountNotVerifiedError as exc:
        raise _ACCOUNT_NOT_VERIFIED_ERROR from exc

    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=expires_in,
    )


@router.post(
    "/refresh",
    response_model=RefreshResponse,
    status_code=status.HTTP_200_OK,
)
async def refresh(payload: RefreshRequest) -> RefreshResponse:
    try:
        access_token, new_refresh_token, expires_in = auth_service.refresh(
            payload.refresh_token
        )
    except sessions_repo.RefreshTokenInvalidError as exc:
        raise _INVALID_REFRESH_TOKEN_ERROR from exc

    return RefreshResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        expires_in=expires_in,
    )


@router.post(
    "/logout",
    response_model=LogoutResponse,
    status_code=status.HTTP_200_OK,
)
async def logout(
    current: CurrentSession = Depends(get_current_session),
) -> LogoutResponse:
    auth_service.logout(current.account_id, current.session_id)
    return LogoutResponse()


@router.post(
    "/logout-all",
    response_model=LogoutAllResponse,
    status_code=status.HTTP_200_OK,
)
async def logout_all(
    current: CurrentSession = Depends(get_current_session),
) -> LogoutAllResponse:
    auth_service.logout_all(current.account_id)
    return LogoutAllResponse()


@router.post(
    "/password/forgot",
    response_model=ForgotPasswordResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def forgot_password(payload: ForgotPasswordRequest) -> ForgotPasswordResponse:
    auth_service.request_password_reset(str(payload.email))
    # Generic response regardless of whether the email exists.
    return ForgotPasswordResponse()


@router.post(
    "/password/reset",
    response_model=ResetPasswordResponse,
    status_code=status.HTTP_200_OK,
)
async def reset_password(payload: ResetPasswordRequest) -> ResetPasswordResponse:
    try:
        auth_service.reset_password(
            payload.challenge_id, payload.code, payload.new_password
        )
    except (
        challenges_repo.ChallengeNotFoundError,
        challenges_repo.ChallengeInvalidError,
    ) as exc:
        raise _INVALID_RESET_ERROR from exc
    return ResetPasswordResponse()
