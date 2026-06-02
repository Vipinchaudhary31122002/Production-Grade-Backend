"""
router.py — Root API router.

OOP concepts applied:
- Encapsulation: ``RouterRegistry`` owns the sub-router mounting logic.
  ``main.py`` only calls ``RouterRegistry.build()``; it never touches
  individual sub-routers directly.
- Abstraction: Adding a new module requires one line in ``RouterRegistry``
  — the caller doesn't know which routers exist or what prefixes they use.
- Single-Responsibility: This module mounts routers and defines the two
  system-level endpoints (root and health check).
"""

from fastapi import APIRouter
from sqlalchemy import text

from src.modules.auth.router import router as auth_router
from src.modules.users.router import router as users_router
from src.config import settings
from src.dependencies import DBSession


# ── Router registry (encapsulation) ──────────────────────────────────────────

class RouterRegistry:
    """Builds and returns the root APIRouter with all module routers mounted.

    To add a new module:
    1. Import its router.
    2. Add one ``_root.include_router(...)`` call in ``_mount_modules``.
    That's it — ``main.py`` never changes.
    """

    @classmethod
    def _mount_modules(cls, root: APIRouter) -> None:
        """Mount every module router onto *root* with its prefix and tags."""
        root.include_router(auth_router, prefix="/auth", tags=["Auth"])
        root.include_router(users_router, prefix="/users", tags=["Users"])

    @classmethod
    def build(cls) -> APIRouter:
        """Return the assembled root router."""
        root = APIRouter(prefix="")
        cls._mount_modules(root)
        return root


# ── Root router instance ──────────────────────────────────────────────────────

router = RouterRegistry.build()


# ── System endpoints ──────────────────────────────────────────────────────────

@router.get("/", tags=["System"], summary="Welcome message")
async def root(db: DBSession):
    """Minimal liveness endpoint — confirms the app is up."""
    return {"message": "Welcome to the backend"}


@router.get("/health", tags=["System"], summary="Health check")
async def health_check(db: DBSession):
    """Health check endpoint for load balancers and monitoring.

    Runs a trivial SQL query to verify the database connection is alive.
    """
    await db.execute(text("SELECT 1"))
    return {"status": "ok", "env": settings.APP_ENV}

