"""
alembic/env.py — Alembic migration environment.

OOP concepts applied:
- Encapsulation: ``MigrationRunner`` owns every Alembic configuration and
  execution detail.  The module-level entry point simply calls
  ``MigrationRunner.run()``, keeping the script body clean.
- Abstraction: Alembic internals (offline vs online mode, async engine setup,
  connection synchronisation) are hidden behind two private class methods.
- Single-Responsibility: This module is responsible only for configuring and
  running migrations; it does not import application business logic.
"""

import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# ── Import all models so Alembic can detect them ──────────────────────────────
from src.core.database import Base
from src.modules.users.model import User          # noqa: F401
from src.modules.auth.model import RefreshToken   # noqa: F401
# Add new models here as you create them


# ── Migration runner (encapsulation) ─────────────────────────────────────────

class MigrationRunner:
    """Encapsulates Alembic's offline and online migration flows.

    Provides a single ``run`` entry point; the caller does not need to know
    which mode Alembic is operating in.
    """

    _config = context.config
    _target_metadata = Base.metadata

    @classmethod
    def _get_url(cls) -> str:
        """Read the database URL from application settings at migration time."""
        from src.config import settings
        return settings.DATABASE_URL

    # ── Offline migration (generates SQL scripts) ─────────────────────────

    @classmethod
    def _run_offline(cls) -> None:
        """Configure Alembic for offline mode and run all pending migrations."""
        context.configure(
            url=cls._get_url(),
            target_metadata=cls._target_metadata,
            literal_binds=True,
            dialect_opts={"paramstyle": "named"},
        )
        with context.begin_transaction():
            context.run_migrations()

    # ── Online migration (runs against a live database) ───────────────────

    @staticmethod
    def _do_run_migrations(connection: Connection) -> None:
        context.configure(connection=connection, target_metadata=Base.metadata)
        with context.begin_transaction():
            context.run_migrations()

    @classmethod
    async def _run_async_migrations(cls) -> None:
        """Create an async engine and run migrations via a sync wrapper."""
        configuration = cls._config.get_section(cls._config.config_ini_section, {})
        configuration["sqlalchemy.url"] = cls._get_url()

        connectable = async_engine_from_config(
            configuration,
            prefix="sqlalchemy.",
            poolclass=pool.NullPool,
        )
        async with connectable.connect() as connection:
            await connection.run_sync(cls._do_run_migrations)
        await connectable.dispose()

    @classmethod
    def _run_online(cls) -> None:
        asyncio.run(cls._run_async_migrations())

    # ── Public entry point ────────────────────────────────────────────────

    @classmethod
    def run(cls) -> None:
        """Run migrations in whichever mode Alembic is currently configured for."""
        if context.is_offline_mode():
            cls._run_offline()
        else:
            cls._run_online()


# ── Module-level setup ────────────────────────────────────────────────────────

config = MigrationRunner._config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

MigrationRunner.run()
