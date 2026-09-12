from typing import Optional
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from backend.app.core.security import get_password_hash, verify_password
from backend.app.models.user import User
from backend.app.schemas.auth import UserRegister


class AuthService:
    @staticmethod
    async def register_user(db: AsyncSession, user_in: UserRegister) -> User:
        # Check duplicate email or username
        stmt = select(User).where(
            or_(User.email == user_in.email, User.username == user_in.username)
        )
        res = await db.execute(stmt)
        existing = res.scalars().first()
        if existing:
            if existing.email == user_in.email:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already registered",
                )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already taken",
            )

        hashed_pwd = get_password_hash(user_in.password)
        db_user = User(
            email=user_in.email,
            username=user_in.username,
            hashed_password=hashed_pwd,
            avatar_url=user_in.avatar_url,
        )
        db.add(db_user)
        await db.flush()
        await db.refresh(db_user)
        return db_user

    @staticmethod
    async def authenticate_user(
        db: AsyncSession, email_or_username: str, password: str
    ) -> Optional[User]:
        stmt = select(User).where(
            or_(User.email == email_or_username, User.username == email_or_username)
        )
        res = await db.execute(stmt)
        user = res.scalars().first()
        if not user:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user

    @staticmethod
    async def get_user_by_id(db: AsyncSession, user_id: str) -> Optional[User]:
        stmt = select(User).where(User.id == user_id)
        res = await db.execute(stmt)
        return res.scalars().first()

    @staticmethod
    async def get_user_by_email_or_username(
        db: AsyncSession, query: str
    ) -> Optional[User]:
        stmt = select(User).where(or_(User.email == query, User.username == query))
        res = await db.execute(stmt)
        return res.scalars().first()


auth_service = AuthService()
