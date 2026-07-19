from fastapi import APIRouter

router = APIRouter(
    prefix="/user",
    tags=["user"],
)

@router.get("/me")
async def me() -> None:
    pass

@router.post("/edit-user-details")
async def edit_user_details() -> None:
    pass

@router.get("/all-users")
async def all_users() -> None:
    pass

@router.get("/user-details/{user_id}")
async def user_details() -> None:
    pass