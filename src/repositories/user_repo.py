from sqlalchemy import select
from src.models.user import User
from src.repositories.base import BaseRepository


class UserRepository(BaseRepository):
    async def get(self, user_id: str) -> User | None:
        result = await self.session.execute(
            select(User).where(User.max_user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def create(self, user: User) -> User:
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def update(self, user: User) -> User:
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def get_by_role(self, role: str) -> list[User]:
        result = await self.session.execute(
            select(User).where(User.role == role)
        )
        return result.scalars().all()