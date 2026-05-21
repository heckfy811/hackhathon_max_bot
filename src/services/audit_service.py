from src.repositories.audit_repo import AuditRepository
from src.models.audit_log import AuditLog
import uuid


class AuditService:
    def __init__(self, audit_repo: AuditRepository):
        self.audit_repo = audit_repo

    async def log(
            self,
            request_id: uuid.UUID,
            action: str,
            actor_id: str,
            details: str = None
    ) -> AuditLog:
        audit = AuditLog(
            request_id=request_id,
            action=action,
            actor_id=actor_id,
            details=details
        )
        return await self.audit_repo.create(audit)

    async def get_by_request(self, request_id: str) -> list[AuditLog]:
        return await self.audit_repo.get_by_request(request_id)

    async def get_by_actor(self, actor_id: str) -> list[AuditLog]:
        return await self.audit_repo.get_by_actor(actor_id)