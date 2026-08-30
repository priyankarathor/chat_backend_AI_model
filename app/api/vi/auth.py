from fastapi import APIRouter, HTTPException

from schemas.auth_schema import (
    RegisterUser,
    LoginUser
)

from services.auth_service import AuthService


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)


# =========================
# REGISTER
# =========================

@router.post("/register")
async def register(user: RegisterUser):

    result = await AuthService.register_user(user)

    if not result["success"]:
        raise HTTPException(
            status_code=400,
            detail=result["message"]
        )

    return result


# =========================
# LOGIN
# =========================

@router.post("/login")
async def login(user: LoginUser):

    result = await AuthService.login_user(user)

    if not result["success"]:
        raise HTTPException(
            status_code=401,
            detail=result["message"]
        )

    return result