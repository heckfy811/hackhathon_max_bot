from sqlalchemy import select, update, func
from src.models.clarification import Clarification
from src.repositories.base import BaseRepository


class ClarificationRepository(BaseRepository):
    async def create(self, clarification: Clarification) -> Clarification:
        self.session.add(clarification)
        await self.session.commit()
        await self.session.refresh(clarification)
        return clarification

    async def get(self, clarification_id: str) -> Clarification | None:
        result = await self.session.execute(
            select(Clarification).where(Clarification.id == clarification_id)
        )
        return result.scalar_one_or_none()

    async def update(self, clarification: Clarification) -> Clarification:
        await self.session.commit()
        await self.session.refresh(clarification)
        return clarification

    async def get_active_by_request(self, request_id: str) -> Clarification | None:
        result = await self.session.execute(
            select(Clarification)
            .where(Clarification.request_id == request_id)
            .where(Clarification.is_active == True)
        )
        return result.scalar_one_or_none()

    async def get_all_by_request(self, request_id: str) -> list[Clarification]:
        result = await self.session.execute(
            select(Clarification)
            .where(Clarification.request_id == request_id)
            .order_by(Clarification.asked_at)
        )
        return result.scalars().all()

    async def mark_answered(self, clarification_id: int, answer: str) -> None:
        await self.session.execute(
            update(Clarification)
            .where(Clarification.id == clarification_id)
            .values(answer=answer, answered_at=func.now(), is_active=False)
        )
        await self.session.commit()