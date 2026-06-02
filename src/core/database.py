"""
core/database.py — Async SQLAlchemy engine, session factory, and Base model.

OOP concepts applied:
- Encapsulation: ``DatabaseManager`` owns the engine, session factory, and all
  lifecycle operations (``get_session``, ``init_db``).  External code never
  touches the engine or factory directly.
- Abstraction: Callers use ``get_session`` (a generator-dependency) and
  ``init_db`` without knowing which database backend or pool settings are in
  play.
- Inheritance: ``Base`` (``DeclarativeBase``) is the root of the ORM model
  hierarchy.  Every model inherits from it, gaining the ``metadata`` registry
  and the mapper instrumentation.
- Single-Responsibility: ``DatabaseManager`` is the single owner of connection
  logic; model classes own only their own table mapping.
"""

import logging
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
    AsyncEngine,
)
from sqlalchemy.orm import DeclarativeBase

from src.config import settings

logger = logging.getLogger(__name__)


# ── ORM base ──────────────────────────────────────────────────────────────────

class Base(DeclarativeBase):
    """Root of the ORM model hierarchy.

    All domain models inherit from this class so they are visible to Alembic
    and participate in the shared ``metadata`` registry.
    """


# ── Database manager (encapsulation) ─────────────────────────────────────────

class DatabaseManager:
    """Owns the engine and session factory for the application database.

    Encapsulates:
    - Engine creation and its backend-specific quirks (e.g. SQLite thread check).
    - Session factory configuration (``expire_on_commit``, ``autoflush``, etc.).
    - Session lifecycle: commit on success, rollback on error, always close.
    - Table creation for development / testing.

    Attributes are private; the public surface is ``get_session`` and
    ``init_db``.
    """

    def __init__(self) -> None:
        self._engine: AsyncEngine = self._create_engine()
        self._session_factory: async_sessionmaker[AsyncSession] = (
            self._create_session_factory()
        )

    # ── Private factory helpers ───────────────────────────────────────────

    def _create_engine(self) -> AsyncEngine:
        """Build the async engine with appropriate connection args."""
        connect_args = (
            {"check_same_thread": False} if settings.is_sqlite else {}
        )
        return create_async_engine(
            settings.DATABASE_URL,
            echo=settings.DEBUG,
            connect_args=connect_args,
        )

    def _create_session_factory(self) -> async_sessionmaker[AsyncSession]:
        """Build the async session factory bound to the engine."""
        return async_sessionmaker(
            bind=self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
            autocommit=False,
        )

    # ── Public API ────────────────────────────────────────────────────────

    async def get_session(self) -> AsyncSession:
        """FastAPI dependency — yields a DB session per request.

        Commits on success, rolls back on any exception, and always closes
        the session.
        """
        async with self._session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    async def init_db(self) -> None:
        """Create all tables on startup (development / testing).

        Import models here so ``Base.metadata`` knows about them before
        ``create_all`` is called.  In production, prefer Alembic migrations.
        """
        # Importing here avoids circular imports at module load time
        from src.modules.users.model import User          # noqa: F401
        from src.modules.auth.model import RefreshToken   # noqa: F401

        try:
            async with self._engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logger.info("Database connection completed.")
        except Exception as exc:
            logger.error("Database connection rejected: %s", exc)
            raise


# ── Module-level singleton ────────────────────────────────────────────────────

_db_manager = DatabaseManager()


# ── Public helpers (preserve existing call-sites) ─────────────────────────────

async def get_session() -> AsyncSession:
    """FastAPI dependency yielding a managed ``AsyncSession``."""
    async for session in _db_manager.get_session():
        yield session


async def init_db() -> None:
    """Create all ORM tables (dev / test shortcut)."""
    await _db_manager.init_db()
