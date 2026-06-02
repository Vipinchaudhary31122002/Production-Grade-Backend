"""
users/schema.py — Pydantic schemas for the users module.

OOP concepts applied:
- Inheritance: ``UserUpdateRequest`` inherits from ``UserCreateRequest``'s
  sibling class through the shared Pydantic ``BaseModel`` base.  Each schema
  inherits field validation, serialisation, and ``model_dump`` for free.
- Encapsulation: ``UserResponse`` exposes only the fields that are safe to
  send over the wire — ``hashed_password`` is never included.
- Abstraction: The annotated types ``StrongPassword`` and ``ValidUsername``
  hide their validation rules behind a simple type alias; the schema doesn't
  repeat any regex logic.
- Single-Responsibility: Request schemas validate input; the response schema
  shapes output.  They have different purposes and can evolve independently.
"""

from datetime import datetime
from pydantic import BaseModel, EmailStr, ConfigDict

from src.utils.validators import StrongPassword, ValidUsername


# ── Request schemas ───────────────────────────────────────────────────────────

class UserCreateRequest(BaseModel):
    """Validates the payload for creating a new user account.

    ``password`` is validated against the strong-password rules via the
    ``StrongPassword`` annotated type.  ``username`` is validated by
    ``ValidUsername``.  Neither raw value is stored; the service layer
    hashes the password before persistence.
    """

    email: EmailStr
    username: ValidUsername
    password: StrongPassword
    full_name: str | None = None


class UserUpdateRequest(BaseModel):
    """Validates the payload for updating an existing user's profile.

    All fields are optional — only fields that are explicitly provided will
    be written to the database (``exclude_unset=True`` pattern in the
    service).
    """

    full_name: str | None = None
    username: ValidUsername | None = None


# ── Response schema ───────────────────────────────────────────────────────────

class UserResponse(BaseModel):
    """Public-facing representation of a user — safe to serialise to JSON.

    ``model_config = ConfigDict(from_attributes=True)`` enables
    ``UserResponse.model_validate(user_orm_instance)`` so conversion from the
    SQLAlchemy model is a one-liner.

    ``hashed_password`` is deliberately excluded; it must never appear in
    API responses.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    username: str
    full_name: str | None = None
    role: str
    status: str
    created_at: datetime
    updated_at: datetime
