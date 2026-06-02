"""
users/router.py — HTTP layer for user endpoints.

OOP concepts applied:
- Encapsulation: ``UserServiceDep`` hides the ``UserService`` construction
  (and its ``UserRepo`` dependency) behind a single injected type alias.
  Route handlers never instantiate services directly.
- Abstraction: Route handlers call high-level service methods and never
  reference SQL or the ORM directly.
- Single-Responsibility: This file handles only HTTP concerns — parameter
  parsing, response shaping, and status codes.  Business logic lives in
  ``UserService``; data access lives in ``UserRepo``.

All dependencies are imported from the module-local dependencies file:
    from src.modules.users.dependencies import UserServiceDep, CurrentUser, PaginationDep
"""

from fastapi import APIRouter, status

from src.modules.users.dependencies import CurrentUser, PaginationDep, UserServiceDep
from src.modules.users.schema import UserCreateRequest, UserResponse, UserUpdateRequest
from src.utils.response import ApiResponse, PaginatedResponse

router = APIRouter()


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/", status_code=status.HTTP_201_CREATED, response_model=ApiResponse[UserResponse])
async def create_user(body: UserCreateRequest, service: UserServiceDep):
    """Register a new user account (public endpoint — no auth required)."""
    user = await service.create_user(body)
    return ApiResponse.ok(data=UserResponse.model_validate(user), message="User created")


@router.get("/", response_model=PaginatedResponse[UserResponse])
async def list_users(
    _: CurrentUser,   # requires authentication
    service: UserServiceDep,
    pagination: PaginationDep,
):
    """List users with pagination (requires authentication)."""
    repo = service.user_repo
    users = await repo.list_users(offset=pagination.offset, limit=pagination.limit)
    total = await repo.count()
    return PaginatedResponse.create(
        items=[UserResponse.model_validate(u) for u in users],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.get("/me", response_model=ApiResponse[UserResponse])
async def get_current_user_profile(current_user: CurrentUser):
    """Return the currently authenticated user's profile."""
    return ApiResponse.ok(data=UserResponse.model_validate(current_user))


@router.patch("/me", response_model=ApiResponse[UserResponse])
async def update_current_user(
    current_user: CurrentUser,
    body: UserUpdateRequest,
    service: UserServiceDep,
):
    """Update the currently authenticated user's profile."""
    updated = await service.update_user(current_user.id, body)
    return ApiResponse.ok(data=UserResponse.model_validate(updated), message="Profile updated")
