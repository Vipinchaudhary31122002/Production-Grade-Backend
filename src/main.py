"""
main.py — Application factory.

OOP concepts applied:
- Encapsulation: ``AppFactory`` owns the entire application-creation process.
  External code calls ``AppFactory.create()`` and gets a ready-to-use
  ``FastAPI`` instance — no setup details leak out.
- Abstraction: ``main.py`` delegates middleware registration, exception
  handling, and router mounting to dedicated classes/functions.
- Single-Responsibility: This module only assembles the application;
  each concern (middleware, logging, exceptions, routing) is handled by its
  own module.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI

from src.config import settings
from src.router import router
from src.core.database import init_db
from src.core.middleware import register_middleware
from src.core.logger import setup_logging
from src.exceptions import register_exception_handlers

# Configure logging before anything else runs
setup_logging()


class AppFactory:
    """Assembles and configures the FastAPI application.

    Encapsulates:
    - Lifespan management (startup / shutdown hooks).
    - Middleware registration order.
    - Exception handler registration.
    - Router mounting.
    - OpenAPI documentation visibility (hidden in production).

    Usage::

        app = AppFactory.create()
    """

    @staticmethod
    @asynccontextmanager
    async def _lifespan(app: FastAPI):
        """Async context manager: runs on startup (before ``yield``) and
        shutdown (after ``yield``)."""
        # ── Startup ──────────────────────────────────────────────────────
        await init_db()

        yield  # application is running

        # ── Shutdown ─────────────────────────────────────────────────────
        # Close DB connections, flush caches, etc. as needed.

    @classmethod
    def create(cls) -> FastAPI:
        """Build and return the fully-configured ``FastAPI`` application."""
        app = FastAPI(
            title=settings.APP_NAME,
            version="0.1.0",
            debug=settings.DEBUG,
            # Hide interactive docs in production to reduce attack surface
            docs_url="/docs" if settings.DEBUG else None,
            redoc_url="/redoc" if settings.DEBUG else None,
            lifespan=cls._lifespan,
        )

        register_middleware(app)
        register_exception_handlers(app)
        app.include_router(router)

        return app


# Entry point used by uvicorn: uvicorn src.main:app
app: FastAPI = AppFactory.create()

