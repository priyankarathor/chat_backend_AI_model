import os
import jwt

from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials


load_dotenv()


SECRET_KEY = os.getenv("JWT_SECRET_KEY")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")

def get_int_env(*names: str, default: int) -> int:
    for name in names:
        value = os.getenv(name)

        if value is None:
            continue

        try:
            return int(value)
        except ValueError as exc:
            raise RuntimeError(
                f"{name} must be a whole number of minutes"
            ) from exc

    return default


ACCESS_TOKEN_EXPIRE_MINUTES = get_int_env(
    "JWT_ACCESS_TOKEN_EXPIRE_MINUTES",
    "ACCESS_TOKEN_EXPIRE_MINUTES",
    default=60,
)


security = HTTPBearer()


def get_jwt_secret_key():
    if not SECRET_KEY:
        raise HTTPException(
            status_code=500,
            detail="JWT_SECRET_KEY environment variable is missing"
        )

    return SECRET_KEY


# ==========================
# CREATE TOKEN
# ==========================

def create_access_token(data: dict):

    payload = data.copy()

    expire = datetime.now(timezone.utc) + timedelta(
        minutes=ACCESS_TOKEN_EXPIRE_MINUTES
    )

    payload["exp"] = expire

    return jwt.encode(
        payload,
        get_jwt_secret_key(),
        algorithm=ALGORITHM
    )


# ==========================
# GET CURRENT USER
# ==========================

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):

    token = credentials.credentials

    try:

        payload = jwt.decode(
            token,
            get_jwt_secret_key(),
            algorithms=[ALGORITHM]
        )

        user_id = payload.get("sub")

        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )

        return {
            "user_id": user_id,
            "email": payload.get("email")
        }

    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=401,
            detail="Session expired. Please sign in again.",
            headers={
                "WWW-Authenticate": (
                    'Bearer error="invalid_token", '
                    'error_description="The access token expired"'
                )
            },
        )

    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=401,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )
