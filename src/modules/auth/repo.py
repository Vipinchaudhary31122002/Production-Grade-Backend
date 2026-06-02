"""
auth/repo.py — Data access layer for auth-specific tables.

OOP concepts applied:
- Encapsulation: The ``AsyncSession`` is a private attribute; the SHA-256
  hashing helper is a private method.  Nothing outside the class touches the
  session or builds token hashes.
- Abstraction: Callers call ``store_refresh_token``, ``find_refresh_token``,
  and ``revoke_token`` — they never write SQL or construct hash hex-digests.
- Single-Responsibility: Only the ``refresh_tokens`` table is touched here.
  User lookups live in ``UserRepo``.
- Open/Closed: New token-revocation strategies (e.g. revoke-by-IP) can be
  added as new methods without changing existing ones.
"""

from datetime import datetime, timezone
import hashlib

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.auth.model import RefreshToken


class AuthRepo:
    """Data access object for the ``refresh_tokens`` table.

    Accepts an ``AsyncSession`` at construction time so it shares the
    per-request session with other repos in the same transaction.
    """

    def __init__(self, db: AsyncSession) -> None:
        self._db = db   # private — callers never touch the session directly

    # ── Private helpers (encapsulation) ───────────────────────────────────

    @staticmethod
    def _hash_token(token: str) -> str:
        """Return the SHA-256 hex-digest of *token*.

        We store hashes instead of raw tokens so a database dump cannot be
        used to forge sessions.
        """
        return hashlib.sha256(token.encode()).hexdigest()

    # ── Write operations ──────────────────────────────────────────────────

    async def store_refresh_token(
        self, user_id: int, token: str, expires_at: datetime
    ) -> RefreshToken:
        """Persist a new refresh-token record (stores the hash, not the token)."""
        record = RefreshToken(
            user_id=user_id,
            token_hash=self._hash_token(token),
            expires_at=expires_at,
        )
        self._db.add(record)
        await self._db.flush()
        return record

    async def revoke_token(self, token: str) -> None:
        """Mark the given token as revoked (no-op if not found)."""
        record = await self.find_refresh_token(token)
        if record:
            record.is_revoked = True

    async def revoke_all_user_tokens(self, user_id: int) -> None:
        """Revoke every active token for *user_id*.

        Call this on password change or a "logout from all devices" request.
        """
        result = await self._db.execute(
            select(RefreshToken).where(
                RefreshToken.user_id == user_id,
                RefreshToken.is_revoked == False,  # noqa: E712
            )
        )
        for token_record in result.scalars().all():
            token_record.is_revoked = True

    # ── Read operations ───────────────────────────────────────────────────

    async def find_refresh_token(self, token: str) -> RefreshToken | None:
        """Return the matching active, non-expired token record, or ``None``."""
        token_hash = self._hash_token(token)
        result = await self._db.execute(
            select(RefreshToken).where(
                RefreshToken.token_hash == token_hash,
                RefreshToken.is_revoked == False,  # noqa: E712
                RefreshToken.expires_at > datetime.now(timezone.utc),
            )
        )
        return result.scalar_one_or_none()
