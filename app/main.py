from contextlib import asynccontextmanager
from fastapi import FastAPI


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
        # await init_db()

        yield  # application is running

        # ── Shutdown ─────────────────────────────────────────────────────
        # Close DB connections, flush caches, etc. as needed.

    @classmethod
    def create(cls) -> FastAPI:
        """Build and return the fully-configured ``FastAPI`` application."""
        app = FastAPI(
            # title=settings.APP_NAME,
            # version="0.1.0",
            # debug=settings.DEBUG,
            # # Hide interactive docs in production to reduce attack surface
            # docs_url="/docs" if settings.DEBUG else None,
            # redoc_url="/redoc" if settings.DEBUG else None,
            # lifespan=cls._lifespan,
        )

        # register_middleware(app)
        # register_exception_handlers(app)
        # app.include_router(router)

        return app


# Entry point used by uvicorn: uvicorn src.main:app
app: FastAPI = AppFactory.create()

