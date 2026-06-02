"""
dependencies.py — Shared FastAPI dependency functions.

OOP concepts applied:
- Encapsulation: ``TokenAuthenticator`` owns the JWT-decoding and user-lookup
  logic.  Routers never call ``decode_access_token`` directly; they rely on
  the dependency injector to supply a fully validated ``User``.
- Abstraction: The ``CurrentUser`` type alias is the only thing routers
  need — they declare it as a parameter type and FastAPI handles the rest.
- Single-Responsibility: Authentication logic is isolated in
  ``TokenAuthenticator``; database access is delegated to ``UserRepo``.
"""

from typing import Annotated
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_session
from src.core.security import decode_access_token
from src.modules.users.model import User
from src.modules.users.repo import UserRepo

# Tells FastAPI where the login endpoint is (used in Swagger UI)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

# Type alias — use this in routers for clean signatures
DBSession = Annotated[AsyncSession, Depends(get_session)]


# ── Token authenticator (encapsulation) ──────────────────────────────────────

class TokenAuthenticator:
    """Resolves a raw Bearer token into an authenticated ``User`` instance.

    Encapsulates:
    - The ``HTTPException`` shape for credential failures.
    - JWT decoding via ``decode_access_token``.
    - The ``sub`` → ``user_id`` extraction and DB look-up.

    Used as an injectable callable by FastAPI's ``Depends()``.
    """

    # Encapsulate the error response so it is defined in one place
    _CREDENTIALS_EXCEPTION = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    async def __call__(
        self,
        token: Annotated[str, Depends(oauth2_scheme)],
        db: DBSession,
    ) -> User:
        """Decode *token* and return the matching user, or raise 401."""
        payload = decode_access_token(token)
        if payload is None:
            raise self._CREDENTIALS_EXCEPTION

        user_id: str | None = payload.get("sub")
        if user_id is None:
            raise self._CREDENTIALS_EXCEPTION

        repo = UserRepo(db)
        user = await repo.get_by_id(int(user_id))
        if user is None:
            raise self._CREDENTIALS_EXCEPTION

        return user


# ── Singleton dependency instance ─────────────────────────────────────────────

_authenticator = TokenAuthenticator()

# Preserved for backwards-compatibility with call-sites that use Depends(get_current_user)
async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: DBSession,
) -> User:
    """Decodes the JWT and returns the authenticated user (delegates to ``TokenAuthenticator``)."""
    return await _authenticator(token=token, db=db)


# Type alias for authenticated routes
CurrentUser = Annotated[User, Depends(get_current_user)]
