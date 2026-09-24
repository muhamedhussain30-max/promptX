"""
Auth routes — host registration and login.
Regular players don't need accounts; they use session tokens issued at /games/{code}/join.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database.base import get_db
from app.models.user import User
from app.schemas.auth import UserRegister, UserLogin, TokenResponse, UserOut
from app.schemas.common import APIResponse
from app.services.auth_service import (
    authenticate_user, create_user, create_access_token,
)

router = APIRouter()


@router.post("/register", response_model=APIResponse[UserOut], status_code=201)
async def register(body: UserRegister, db: AsyncSession = Depends(get_db)):
    try:
        # Check uniqueness
        existing = await db.execute(select(User).where(User.username == body.username))
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=409, detail="Username already taken")

        user = await create_user(
            db,
            username=body.username,
            email=body.email,
            password=body.password,
            display_name=body.display_name,
        )
        await db.commit()
        return APIResponse(data=UserOut.model_validate(user), message="Registration successful")
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        from app.config.logging import logger
        logger.error("registration_failed", error=str(e), username=body.username)
        raise HTTPException(
            status_code=500,
            detail=f"Registration failed: {str(e)}"
        )


@router.post("/login", response_model=APIResponse[TokenResponse])
async def login(body: UserLogin, db: AsyncSession = Depends(get_db)):
    try:
        user = await authenticate_user(db, body.username, body.password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
            )
        token = create_access_token({"sub": user.username, "display_name": user.display_name})
        return APIResponse(data=TokenResponse(
            access_token=token,
            user_id=user.id,
            display_name=user.display_name,
        ))
    except HTTPException:
        raise
    except Exception as e:
        from app.config.logging import logger
        logger.error("login_failed", error=str(e), username=body.username)
        raise HTTPException(
            status_code=500,
            detail=f"Login failed: {str(e)}"
        )
