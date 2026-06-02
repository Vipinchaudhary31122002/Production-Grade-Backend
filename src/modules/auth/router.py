"""
auth/router.py — HTTP layer for authentication endpoints.

OOP concepts applied:
- Encapsulation: ``AuthServiceDep`` hides the construction of ``AuthService``
  (and its two repo dependencies) behind a single injected type alias.
  Route handlers never instantiate services directly.
- Abstraction: Route handlers call ``service.register``, ``service.login``,
  and ``service.refresh_tokens`` without knowing anything about JWTs,
  password hashing, or database sessions.
- Single-Responsibility: This file only handles HTTP concerns — HTTP verbs,
  status codes, request parsing, and response shaping.

All dependencies are imported from the module-local dependencies file:
    from src.modules.auth.dependencies import AuthServiceDep
"""

from fastapi import APIRouter, status

from src.modules.auth.dependencies import AuthServiceDep
from src.modules.auth.schema import (
    LoginRequest,
    RegisterRequest,
    RefreshTokenRequest,
    TokenResponse,
)

router = APIRouter()


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    response_model=TokenResponse,
    summary="Register a new user account",
)
async def register(body: RegisterRequest, service: AuthServiceDep) -> TokenResponse:
    """Create a new user and return an access + refresh token pair."""
    return await service.register(body)


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Authenticate with email and password",
)
async def login(body: LoginRequest, service: AuthServiceDep) -> TokenResponse:
    """Verify credentials and return an access + refresh token pair."""
    return await service.login(body)


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Rotate the refresh token",
)
async def refresh_tokens(
    body: RefreshTokenRequest, service: AuthServiceDep
) -> TokenResponse:
    """Revoke the supplied refresh token and issue a new token pair."""
    return await service.refresh_tokens(body.refresh_token)

