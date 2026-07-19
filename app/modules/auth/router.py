from fastapi import APIRouter

router = APIRouter(
    prefix="/auth",
    tags=["auth"],
)

@router.post("/login")
async def login() -> None:
    pass

@router.post("/signup")
async def signup() -> None:
    pass

@router.post("/logout")
async def logout() -> None:
    pass

@router.get("/send-otp")
async def send_otp() -> None:
    pass

@router.post("/verify-otp")
async def verify_otp() -> None:
    pass

@router.post("/change-password")
async def change_password() -> None:
    pass