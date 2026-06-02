"""
auth/dependencies.py — FastAPI dependency wiring for the auth module.

Everything a router inside the auth module needs can be imported from here:

    from src.modules.auth.dependencies import AuthServiceDep

No need to reach into core, repos, or the root dependencies file directly.

OOP concepts applied:
- Encapsulation: Service construction (UserRepo + AuthRepo wiring) is
  hidden inside ``get_auth_service``. Routers declare ``AuthServiceDep``
  and never instantiate anything manually.
- Single-Responsibility: This file owns only the dependency-wiring for the
  auth module. Business logic stays in AuthService; DB access stays in repos.
"""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_session
from src.modules.auth.repo import AuthRepo
from src.modules.auth.service import AuthService
from src.modules.users.repo import UserRepo


# ── Session alias (convenience re-export for auth routers) ────────────────────

DBSession = Annotated[AsyncSession, Depends(get_session)]


# ── Service factory ───────────────────────────────────────────────────────────

def get_auth_service(db: DBSession) -> AuthService:
    """Construct an ``AuthService`` wired to the per-request DB session.

    Composes UserRepo and AuthRepo internally so the router never touches
    either repo directly.
    """
    return AuthService(user_repo=UserRepo(db), auth_repo=AuthRepo(db))


#: Inject this type into any auth route handler to get a ready-to-use AuthService.
AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
