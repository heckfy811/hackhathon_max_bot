from src.repositories.user_repo import UserRepository
from src.models.user import User
from datetime import datetime


class UserService:
    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo

    async def get_or_create(self, user_id: str, display_name: str) -> User:
        user = await self.user_repo.get(user_id)
        if not user:
            user = User(
                max_user_id=user_id,
                display_name=display_name,
                consent_given=False,
                role="user"
            )
            user = await self.user_repo.create(user)
        return user

    async def get(self, user_id: str) -> User | None:
        return await self.user_repo.get(user_id)

    async def is_admin(self, user_id: str) -> bool:
        user = await self.user_repo.get(user_id)
        return user is not None and user.role == "admin"

    async def give_consent(self, user_id: str, consent_version: str) -> User:
        user = await self.user_repo.get(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")

        user.consent_given = True
        user.consent_version = consent_version
        user.consent_timestamp = datetime.now()
        return await self.user_repo.update(user)

    async def update_role(self, user_id: str, role: str) -> User:
        user = await self.user_repo.get(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")

        user.role = role
        return await self.user_repo.update(user)