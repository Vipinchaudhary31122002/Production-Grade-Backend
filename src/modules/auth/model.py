"""
auth/model.py — RefreshToken ORM model.

OOP concepts applied:
- Inheritance: ``RefreshToken`` extends ``Base``, inheriting the mapper
  instrumentation and ``metadata`` registration from SQLAlchemy's
  ``DeclarativeBase``.
- Encapsulation: All column definitions, default factories, and the
  ``is_expired`` / ``is_valid`` helper properties are contained inside the
  class.  External code reads intent-revealing properties rather than
  comparing raw column values.
- Abstraction: ``is_valid`` abstracts the combination of revocation and
  expiry checks, so callers don't repeat that logic.
"""

from datetime import datetime, timezone
from sqlalchemy import String, Boolean, DateTime, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


class RefreshToken(Base):
    """Stores refresh token hashes so they can be individually revoked.

    The raw token value is never persisted — only its SHA-256 hash.
    This means a leaked database does not expose usable tokens.

    Linked to the ``users`` table via a CASCADE-deleting foreign key so that
    all tokens for a user are automatically removed when the user is deleted.
    """

    __tablename__ = "refresh_tokens"

    # ── Primary key ───────────────────────────────────────────────────────
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # ── Relationship ──────────────────────────────────────────────────────
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── Token data ────────────────────────────────────────────────────────
    token_hash: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False
    )
    is_revoked: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    # ── Audit timestamp ───────────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # ── Computed properties (abstraction over raw column values) ──────────

    @property
    def is_expired(self) -> bool:
        """Return True if the token's expiry timestamp has passed."""
        return datetime.now(timezone.utc) > self.expires_at.replace(
            tzinfo=timezone.utc
        )

    @property
    def is_valid(self) -> bool:
        """Return True if the token is neither revoked nor expired."""
        return not self.is_revoked and not self.is_expired

    # ── Dunder methods ────────────────────────────────────────────────────

    def __repr__(self) -> str:
        return (
            f"<RefreshToken id={self.id} user_id={self.user_id} "
            f"revoked={self.is_revoked}>"
        )
