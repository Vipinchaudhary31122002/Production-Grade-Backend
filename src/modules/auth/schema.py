"""
auth/schema.py — Pydantic schemas for the auth module.

OOP concepts applied:
- Inheritance: All schemas inherit from ``BaseModel``, reusing Pydantic's
  validation, serialisation, and JSON-schema generation.
- Encapsulation: Each schema class bundles only the fields relevant to its
  operation (registration, login, token refresh, token response).  A router
  never builds or validates these dicts manually.
- Abstraction: ``TokenResponse`` hides the fact that there are two separate
  tokens; callers just receive a ``TokenResponse`` object.
- Single-Responsibility: Request schemas validate inbound data; the response
  schema shapes outbound data.  They are allowed to diverge independently.
"""

from pydantic import BaseModel, EmailStr

from src.utils.validators import StrongPassword


# ── Request schemas ───────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    """Validates the payload for new user registration.

    ``password`` is validated against the strong-password policy via the
    ``StrongPassword`` annotated type.
    """

    email: EmailStr
    username: str
    password: StrongPassword
    full_name: str | None = None


class LoginRequest(BaseModel):
    """Validates the payload for an authentication attempt.

    The password is plain text here — it is compared against the stored hash
    in the service layer, never stored or logged.
    """

    email: EmailStr
    password: str   # plain text — verified against bcrypt hash in service


class RefreshTokenRequest(BaseModel):
    """Carries the refresh token for a token-rotation request."""

    refresh_token: str


# ── Response schema ───────────────────────────────────────────────────────────

class TokenResponse(BaseModel):
    """Returned to the client after successful authentication or token refresh.

    Encapsulates both token strings and their shared type so the client
    always receives a consistent shape.
    """

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
