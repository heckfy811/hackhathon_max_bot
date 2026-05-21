from sqlalchemy import select

from src.models.audit_log import AuditLog
from src.repositories.base import BaseRepository


class AuditRepository(BaseRepository):
    async def create(self, audit: AuditLog) -> AuditLog:
        self.session.add(audit)
        await self.session.commit()
        await self.session.refresh(audit)
        return audit

    async def get_by_request(self, request_id: str) -> list[AuditLog]:
        result = await self.session.execute(
            select(AuditLog)
            .where(AuditLog.request_id == request_id)
            .order_by(AuditLog.created_at.desc())
        )
        return result.scalars().all()

    async def get_by_actor(self, actor_id: str) -> list[AuditLog]:
        result = await self.session.execute(
            select(AuditLog)
            .where(AuditLog.actor_id == actor_id)
            .order_by(AuditLog.created_at.desc())
        )
        return result.scalars().all()