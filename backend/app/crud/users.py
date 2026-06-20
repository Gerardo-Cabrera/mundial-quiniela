from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.user import User


class UserCRUD:
    async def get_by_email(self, db: AsyncSession, email: str) -> User | None:
        result = await db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def get_by_team(self, db: AsyncSession, team_name: str) -> User | None:
        result = await db.execute(select(User).where(User.team_name == team_name))
        return result.scalar_one_or_none()

    async def get_by_email_or_team(self, db: AsyncSession, email: str, team_name: str) -> User | None:
        result = await db.execute(
            select(User).where(
                (User.email == email) | (User.team_name == team_name)
            )
        )
        return result.scalar_one_or_none()

    async def create(self, db: AsyncSession, *, team_name: str, email: str, hashed_password: str) -> User:
        user = User(
            team_name=team_name,
            email=email,
            hashed_password=hashed_password,
        )
        db.add(user)
        await db.flush()
        await db.refresh(user)
        return user


user_crud = UserCRUD()
