"""
auth/service.py — Authentication business logic.

OOP concepts applied:
- Encapsulation: ``AuthService`` owns ``UserRepo``, ``AuthRepo``, and
  ``UserService`` references as private attributes.  Token creation and
  storage details are hidden inside private helpers (``_issue_token_pair``).
- Abstraction: Routers call ``login``, ``register``, and ``refresh_tokens``
  — they never build JWTs, hash tokens, or compute expiry timestamps.
- Composition: ``AuthService`` reuses ``UserService.create_user`` rather than
  duplicating user-creation logic (composition over duplication).
- Single-Responsibility: This class handles only authentication flows; user
  CRUD belongs in ``UserService``.
- Open/Closed: Adding a new auth flow (e.g. OAuth2 exchange) means adding a
  new method, not changing existing ones.
"""

from datetime import datetime, timedelta, timezone

from src.modules.auth.schema import LoginRequest, RegisterRequest, TokenResponse
from src.modules.auth.repo import AuthRepo
from src.modules.users.repo import UserRepo
from src.modules.users.schema import UserCreateRequest
from src.modules.users.service import UserService
from src.core.security import (
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_access_token,
)
from src.config import settings
from src.exceptions import UnauthorizedException
from src.constants.enums import TokenType


class AuthService:
    """Orchestrates login, registration, and token-refresh flows.

    Uses composition: an instance of ``UserService`` is constructed
    internally so that user-creation rules are enforced consistently
    regardless of the entry point (direct registration vs. OAuth, etc.).
    """

    def __init__(self, user_repo: UserRepo, auth_repo: AuthRepo) -> None:
        self._user_repo = user_repo      # private — callers don't touch repos
        self._auth_repo = auth_repo
        self._user_service = UserService(user_repo)   # composition

    # ── Private helpers (encapsulation) ───────────────────────────────────

    async def _issue_token_pair(
        self, user_id: int, role: str
    ) -> TokenResponse:
        """Create an access + refresh token pair and persist the refresh token.

        Encapsulates the expiry calculation and storage in one place so
        ``login`` and ``register`` don't duplicate this logic.
        """
        access_token = create_access_token(
            subject=user_id, extra_claims={"role": role}
        )
        refresh_token = create_refresh_token(subject=user_id)

        expires_at = datetime.now(timezone.utc) + timedelta(
            days=settings.REFRESH_TOKEN_EXPIRE_DAYS
        )
        await self._auth_repo.store_refresh_token(user_id, refresh_token, expires_at)

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
        )

    # ── Public API ────────────────────────────────────────────────────────

    async def login(self, data: LoginRequest) -> TokenResponse:
        """Authenticate a user by email + password and return a token pair.

        Uses the same error message for "not found" and "wrong password" to
        prevent user-enumeration attacks.
        """
        user = await self._user_repo.get_by_email(data.email)
        if not user or not verify_password(data.password, user.hashed_password):
            raise UnauthorizedException("Invalid email or password")

        return await self._issue_token_pair(user.id, user.role)

    async def register(self, data: RegisterRequest) -> TokenResponse:
        """Create a new user account and return a token pair.

        Delegates uniqueness checks and password hashing to ``UserService``.
        """
        user = await self._user_service.create_user(
            UserCreateRequest(
                email=data.email,
                username=data.username,
                password=data.password,
                full_name=data.full_name,
            )
        )
        return await self._issue_token_pair(user.id, user.role)

    async def refresh_tokens(self, refresh_token: str) -> TokenResponse:
        """Rotate the refresh token: revoke the old one, issue a new pair.

        Validates the token signature, type claim, DB record existence, and
        user existence before issuing new credentials.
        """
        payload = decode_access_token(refresh_token)

        if not payload or payload.get("type") != TokenType.REFRESH:
            raise UnauthorizedException("Invalid or expired refresh token")

        # Verify the token exists in the DB and has not been revoked
        stored = await self._auth_repo.find_refresh_token(refresh_token)
        if not stored:
            raise UnauthorizedException(
                "Refresh token has been revoked or does not exist"
            )

        user_id = payload.get("sub")
        user = await self._user_repo.get_by_id(int(user_id))
        if not user:
            raise UnauthorizedException("User no longer exists")

        # Rotate: revoke old, issue new pair
        await self._auth_repo.revoke_token(refresh_token)
        return await self._issue_token_pair(user.id, user.role)

