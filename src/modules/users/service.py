"""
users/service.py — Business logic for user operations.

OOP concepts applied:
- Encapsulation: ``UserService`` owns the ``UserRepo`` reference and all
  duplicate-checking / hashing logic.  Routers call high-level methods and
  never touch the repo directly.
- Single-Responsibility: This class is responsible solely for user-related
  business rules.  Auth token issuance lives in ``AuthService``; database
  access lives in ``UserRepo``.
- Abstraction: Routers call ``create_user``, ``get_user_by_id``, and
  ``update_user`` without knowing about hashing, uniqueness queries, or the
  ``exclude_unset`` pattern.
- Open/Closed: New user operations (e.g. ``deactivate_user``) can be added as
  methods without modifying existing ones.
"""

from src.modules.users.model import User
from src.modules.users.repo import UserRepo
from src.modules.users.schema import UserCreateRequest, UserUpdateRequest
from src.core.security import hash_password
from src.exceptions import ConflictException, NotFoundException


class UserService:
    """Orchestrates user-related business operations.

    Receives a ``UserRepo`` at construction time (dependency injection), making
    the service independently testable by swapping in a mock repo.
    """

    def __init__(self, user_repo: UserRepo) -> None:
        self._user_repo = user_repo   # private — routers don't touch the repo

    # ── Private helpers (encapsulation) ──────────────────────────────────

    async def _assert_email_unique(self, email: str) -> None:
        """Raise ``ConflictException`` if the email is already registered."""
        if await self._user_repo.get_by_email(email):
            raise ConflictException("A user with this email already exists")

    async def _assert_username_unique(
        self, username: str, exclude_id: int | None = None
    ) -> None:
        """Raise ``ConflictException`` if the username is taken by another user."""
        existing = await self._user_repo.get_by_username(username)
        if existing and existing.id != exclude_id:
            raise ConflictException("A user with this username already exists")

    # ── Public API ────────────────────────────────────────────────────────

    async def create_user(self, data: UserCreateRequest) -> User:
        """Create and persist a new user after enforcing uniqueness constraints.

        The plaintext password is hashed here; it is never stored in plaintext.
        """
        await self._assert_email_unique(data.email)
        await self._assert_username_unique(data.username)

        user = User(
            email=data.email,
            username=data.username,
            hashed_password=hash_password(data.password),
            full_name=data.full_name,
        )
        return await self._user_repo.create(user)

    async def get_user_by_id(self, user_id: int) -> User:
        """Return the user with *user_id*, or raise ``NotFoundException``."""
        user = await self._user_repo.get_by_id(user_id)
        if not user:
            raise NotFoundException("User not found")
        return user

    async def update_user(self, user_id: int, data: UserUpdateRequest) -> User:
        """Apply the provided fields to the user, then persist the changes.

        Only fields explicitly set in the request are updated
        (``exclude_unset=True``), so omitted fields retain their current values.
        """
        user = await self.get_user_by_id(user_id)
        update_data = data.model_dump(exclude_unset=True)

        if "username" in update_data:
            await self._assert_username_unique(
                update_data["username"], exclude_id=user_id
            )

        for field, value in update_data.items():
            setattr(user, field, value)

        return await self._user_repo.update(user)

    # ── Expose the repo for routers that need direct list/count access ────
    # (kept as a property so it remains a controlled access point)

    @property
    def user_repo(self) -> UserRepo:
        """Read-only access to the underlying repo (used by list endpoints)."""
        return self._user_repo
