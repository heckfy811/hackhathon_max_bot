from sqlalchemy import select, update, delete
from src.models.request import Request
from src.repositories.base import BaseRepository


class RequestRepository(BaseRepository):
    async def get(self, request_id: str) -> Request | None:
        result = await self.session.execute(
            select(Request).where(Request.id == request_id)
        )
        return result.scalar_one_or_none()

    async def get_by_short_id(self, short_id: str) -> Request | None:
        result = await self.session.execute(
            select(Request).where(Request.short_id == short_id)
        )
        return result.scalar_one_or_none()

    async def get_by_initiator(self, user_id: str) -> list[Request]:
        result = await self.session.execute(
            select(Request).where(Request.initiator_id == user_id)
        )
        return result.scalars().all()

    async def get_by_user_and_status(self, user_id: str, status: str) -> list[Request]:
        result = await self.session.execute(
            select(Request)
            .where(Request.initiator_id == user_id)
            .where(Request.status == status)
            .order_by(Request.created_at.desc())
        )
        return result.scalars().all()

    async def get_by_status(self, status: str) -> list[Request]:
        result = await self.session.execute(
            select(Request).where(Request.status == status)
        )
        return result.scalars().all()

    async def get_by_statuses(self, statuses: list[str]) -> list[Request]:
        result = await self.session.execute(
            select(Request)
            .where(Request.status.in_(statuses))
            .order_by(Request.created_at)
        )
        return result.scalars().all()

    async def get_pending_queue(self) -> list[Request]:
        result = await self.session.execute(
            select(Request)
            .where(Request.status.in_(["pending", "need_clarification"]))
            .order_by(Request.created_at)
        )
        return result.scalars().all()

    async def create(self, request: Request) -> Request:
        self.session.add(request)
        await self.session.commit()
        await self.session.refresh(request)
        return request

    async def update(self, request: Request) -> Request:
        await self.session.commit()
        await self.session.refresh(request)
        return request

    async def update_status(self, request_id: str, status: str) -> None:
        await self.session.execute(
            update(Request)
            .where(Request.id == request_id)
            .values(status=status)
        )
        await self.session.commit()

    async def delete(self, request_id: str) -> None:
        await self.session.execute(
            delete(Request).where(Request.id == request_id)
        )
        await self.session.commit()