"""
users/model.py — User ORM model.

OOP concepts applied:
- Inheritance: ``User`` extends ``Base`` (SQLAlchemy's ``DeclarativeBase``),
  inheriting the mapper instrumentation and ``metadata`` registration without
  any boilerplate.
- Encapsulation: Column definitions, default factories, and the ``__repr__``
  helper are all contained inside the class.  External code reads attributes,
  never SQL column objects.
- Abstraction: The ``is_active``, ``is_admin``, and ``display_name`` properties
  abstract away the raw string comparisons and conditional logic that would
  otherwise be scattered across services.
"""

from datetime import datetime, timezone
from sqlalchemy import String, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base
from src.constants.enums import UserRole, UserStatus


class User(Base):
    """ORM representation of the ``users`` table.

    Stores authentication credentials, profile data, and account metadata.
    Password is stored as a bcrypt hash — never in plaintext.
    """

    __tablename__ = "users"

    # ── Primary key ───────────────────────────────────────────────────────
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # ── Identity / credentials ────────────────────────────────────────────
    email: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )
    username: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, index=True
    )
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)

    # ── Profile ───────────────────────────────────────────────────────────
    full_name: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # ── Access control ────────────────────────────────────────────────────
    role: Mapped[str] = mapped_column(
        String(20), default=UserRole.USER, nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(20), default=UserStatus.ACTIVE, nullable=False
    )

    # ── Audit timestamps ──────────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # ── Computed properties (abstraction over raw column values) ──────────

    @property
    def is_active(self) -> bool:
        """Return True when the account is in the ACTIVE state."""
        return self.status == UserStatus.ACTIVE

    @property
    def is_admin(self) -> bool:
        """Return True when the user holds an admin or moderator role."""
        return UserRole(self.role).is_privileged()

    @property
    def display_name(self) -> str:
        """Return the best available human-readable name for this user."""
        return self.full_name or self.username

    # ── Dunder methods ────────────────────────────────────────────────────

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email!r} role={self.role!r}>"
