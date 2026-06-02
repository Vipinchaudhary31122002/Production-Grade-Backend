"""
tests/conftest.py — Shared test fixtures.

OOP concepts applied:
- Encapsulation: ``TestDatabaseManager`` owns every detail of the in-memory
  test database (URL, engine, session factory) as private class attributes.
  Fixtures read from it via class-level helpers; tests never reference
  SQLAlchemy internals directly.
- Abstraction: The ``client`` fixture provides an ``AsyncClient`` ready to
  use — tests don't know about ``ASGITransport``, dependency overrides, or
  session cleanup.
- Single-Responsibility: ``TestDatabaseManager`` handles the DB; individual
  pytest fixtures handle their own lifecycle (scope, teardown).
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from src.main import app
from src.core.database import Base, get_session


# ── In-memory test database manager ──────────────────────────────────────────

class TestDatabaseManager:
    """Encapsulates the in-memory SQLite database used by the test suite.

    Using an in-memory database means:
    - No file I/O — tests run fast.
    - No shared state between test runs — each session starts clean.
    - No risk of polluting the development ``dev.db`` file.
    """

    _URL: str = "sqlite+aiosqlite:///:memory:"

    # Class-level singletons — created once per process
    engine = create_async_engine(_URL, echo=False)
    session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    @classmethod
    async def create_all_tables(cls) -> None:
        """Create every ORM table in the in-memory database."""
        async with cls.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    @classmethod
    async def drop_all_tables(cls) -> None:
        """Drop every ORM table (called at session teardown)."""
        async with cls.engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest_asyncio.fixture(scope="session", autouse=True)
async def create_test_tables():
    """Create all tables once before the test session starts, drop them at the end."""
    await TestDatabaseManager.create_all_tables()
    yield
    await TestDatabaseManager.drop_all_tables()


@pytest_asyncio.fixture
async def db_session():
    """Yield a fresh ``AsyncSession`` per test, rolled back after each test.

    Rolling back instead of committing keeps tests isolated — no test can
    affect the data seen by another.
    """
    async with TestDatabaseManager.session_factory() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession):
    """Yield an async HTTP test client wired to the real application.

    The real ``get_session`` dependency is overridden with a factory that
    yields the test session, so every request goes through the same
    rolled-back transaction.
    """
    async def override_get_session():
        yield db_session

    app.dependency_overrides[get_session] = override_get_session

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac

    app.dependency_overrides.clear()
