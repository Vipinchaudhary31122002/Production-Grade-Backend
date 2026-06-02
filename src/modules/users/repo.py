"""
users/repo.py — Data access layer for the users table.

OOP concepts applied:
- Encapsulation: The ``AsyncSession`` is a private instance attribute.
  All SQL lives inside the class; nothing outside constructs queries directly.
- Abstraction: ``UserRepo`` presents a clean domain-level API (``get_by_id``,
  ``create``, ``list_users``, etc.) that hides SQLAlchemy's ``select``,
  ``func.count``, and session management from the service layer.
- Single-Responsibility: This class only touches the ``users`` table.
  Cross-table operations belong in services or separate repos.
- Open/Closed: New query methods can be added without modifying existing ones.
"""

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.users.model import User


class UserRepo:
    """Data access object for the ``users`` table.

    Accepts an ``AsyncSession`` at construction time so it can be created
    inside a FastAPI dependency and reuse the per-request session.

    All methods are ``async`` and return fully-loaded ``User`` instances
    (or ``None`` / lists thereof).
    """

    def __init__(self, db: AsyncSession) -> None:
        self._db = db   # private — callers never touch the session directly

    # ── Read operations ───────────────────────────────────────────────────

    async def get_by_id(self, user_id: int) -> User | None:
        """Fetch a single user by primary key, or ``None`` if not found."""
        result = await self._db.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        """Fetch a user by email address (case-sensitive), or ``None``."""
        result = await self._db.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()

    async def get_by_username(self, username: str) -> User | None:
        """Fetch a user by username, or ``None`` if not found."""
        result = await self._db.execute(
            select(User).where(User.username == username)
        )
        return result.scalar_one_or_none()

    async def list_users(self, offset: int = 0, limit: int = 10) -> list[User]:
        """Return a page of users ordered by insertion (primary key)."""
        result = await self._db.execute(
            select(User).offset(offset).limit(limit)
        )
        return list(result.scalars().all())

    async def count(self) -> int:
        """Return the total number of users in the table."""
        result = await self._db.execute(select(func.count(User.id)))
        return result.scalar_one()

    # ── Write operations ──────────────────────────────────────────────────

    async def create(self, user: User) -> User:
        """Persist a new ``User`` and return it with its generated ``id``."""
        self._db.add(user)
        await self._db.flush()
        await self._db.refresh(user)
        return user

    async def update(self, user: User) -> User:
        """Flush pending changes to *user* and return the refreshed instance."""
        await self._db.flush()
        await self._db.refresh(user)
        return user
