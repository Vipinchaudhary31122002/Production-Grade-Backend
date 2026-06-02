"""
core/security.py — Password hashing and JWT utilities.

OOP concepts applied:
- Encapsulation: ``PasswordHasher`` owns the ``CryptContext`` instance and
  exposes only two methods — ``hash`` and ``verify``.  The bcrypt scheme
  selection is a private detail hidden from callers.
- Abstraction: ``JWTManager`` presents ``create_access_token``,
  ``create_refresh_token``, and ``decode`` as a clean interface; the raw
  ``jwt.encode / jwt.decode`` calls and payload assembly are hidden inside.
- Single-Responsibility: Each class has exactly one concern — password
  hashing or JWT management — making them independently testable.
- Module-level helpers are thin wrappers that delegate to the singletons,
  preserving the existing call-sites throughout the codebase.
"""

from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from passlib.context import CryptContext

from src.config import settings
from src.constants.enums import TokenType


# ── Password hashing ──────────────────────────────────────────────────────────

class PasswordHasher:
    """Thin wrapper around passlib's CryptContext.

    Encapsulates the choice of hashing scheme (bcrypt) and the
    ``CryptContext`` lifecycle so callers work with a simple two-method API.
    """

    def __init__(self) -> None:
        # bcrypt is intentionally slow — that's the point for password storage
        self._context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    def hash(self, plain: str) -> str:
        """Return the bcrypt hash of *plain*."""
        return self._context.hash(plain)

    def verify(self, plain: str, hashed: str) -> bool:
        """Return True if *plain* matches the previously hashed value."""
        return self._context.verify(plain, hashed)


# ── JWT management ────────────────────────────────────────────────────────────

class JWTManager:
    """Creates and validates JWTs for the application.

    Encapsulates the algorithm, secret, and expiry logic so that none of
    those implementation details leak into service or router layers.
    """

    def __init__(
        self,
        secret_key: str,
        algorithm: str,
        access_expire_minutes: int,
        refresh_expire_days: int,
    ) -> None:
        self._secret = secret_key
        self._algorithm = algorithm
        self._access_expire = timedelta(minutes=access_expire_minutes)
        self._refresh_expire = timedelta(days=refresh_expire_days)

    # ── Internal helpers (encapsulation) ──────────────────────────────────

    def _encode(self, payload: dict[str, Any]) -> str:
        return jwt.encode(payload, self._secret, algorithm=self._algorithm)

    def _build_payload(
        self,
        subject: str | int,
        token_type: TokenType,
        expires_delta: timedelta,
        extra: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        expire = datetime.now(timezone.utc) + expires_delta
        payload: dict[str, Any] = {
            "sub": str(subject),
            "exp": expire,
            "type": token_type.value,
        }
        if extra:
            payload.update(extra)
        return payload

    # ── Public API ────────────────────────────────────────────────────────

    def create_access_token(
        self,
        subject: str | int,
        extra_claims: dict[str, Any] | None = None,
    ) -> str:
        """Issue a short-lived access token for *subject*."""
        payload = self._build_payload(
            subject, TokenType.ACCESS, self._access_expire, extra_claims
        )
        return self._encode(payload)

    def create_refresh_token(self, subject: str | int) -> str:
        """Issue a long-lived refresh token for *subject*."""
        payload = self._build_payload(
            subject, TokenType.REFRESH, self._refresh_expire
        )
        return self._encode(payload)

    def decode(self, token: str) -> dict[str, Any] | None:
        """Decode *token* and return its payload, or ``None`` if invalid/expired."""
        try:
            return jwt.decode(token, self._secret, algorithms=[self._algorithm])
        except jwt.PyJWTError:
            return None


# ── Singletons ────────────────────────────────────────────────────────────────

_password_hasher = PasswordHasher()

_jwt_manager = JWTManager(
    secret_key=settings.SECRET_KEY,
    algorithm=settings.JWT_ALGORITHM,
    access_expire_minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES,
    refresh_expire_days=settings.REFRESH_TOKEN_EXPIRE_DAYS,
)


# ── Module-level helpers (preserve existing call-sites) ───────────────────────

def hash_password(plain: str) -> str:
    """Hash a plain-text password using bcrypt."""
    return _password_hasher.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """Return True if *plain* matches *hashed*."""
    return _password_hasher.verify(plain, hashed)


def create_access_token(
    subject: str | int,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    """Issue a JWT access token for *subject*."""
    return _jwt_manager.create_access_token(subject, extra_claims)


def create_refresh_token(subject: str | int) -> str:
    """Issue a JWT refresh token for *subject*."""
    return _jwt_manager.create_refresh_token(subject)


def decode_access_token(token: str) -> dict[str, Any] | None:
    """Decode a JWT and return its payload, or ``None`` on failure."""
    return _jwt_manager.decode(token)
