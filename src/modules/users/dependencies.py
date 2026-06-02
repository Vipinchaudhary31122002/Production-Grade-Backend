"""
users/dependencies.py — FastAPI dependency wiring for the users module.

Everything a router inside the users module needs can be imported from here:

    from src.modules.users.dependencies import UserServiceDep, CurrentUser

No need to reach into core, the root dependencies file, or other modules
directly — this file is the single import point for the users router.

OOP concepts applied:
- Encapsulation: Service construction (UserRepo wiring) is hidden inside
  ``get_user_service``. Routers declare ``UserServiceDep`` and never
  instantiate anything manually.
- Abstraction: ``CurrentUser`` is re-exported here so the users router
  imports everything from one place, hiding where the auth logic actually
  lives.
- Single-Responsibility: This file owns only the dependency-wiring for the
  users module.
"""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_session
from src.dependencies import CurrentUser, DBSession  # re-export for convenience
from src.modules.users.repo import UserRepo
from src.modules.users.service import UserService
from src.utils.pagination import PaginationParams

# ── Re-exports (so routers import only from this file) ────────────────────────

__all__ = [
    "DBSession",
    "CurrentUser",
    "UserServiceDep",
    "PaginationDep",
    "get_user_service",
]


# ── Service factory ───────────────────────────────────────────────────────────

def get_user_service(db: DBSession) -> UserService:
    """Construct a ``UserService`` wired to the per-request DB session.

    Composes UserRepo internally so the router never references the repo.
    """
    return UserService(UserRepo(db))


#: Inject this type into any user route handler to get a ready-to-use UserService.
UserServiceDep = Annotated[UserService, Depends(get_user_service)]

#: Inject this type into any route handler that needs pagination query params.
PaginationDep = Annotated[PaginationParams, Depends()]
