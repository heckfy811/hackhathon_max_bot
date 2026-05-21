from src.repositories.clarification_repo import ClarificationRepository
from src.repositories.request_repo import RequestRepository
from src.models.clarification import Clarification
import uuid
from datetime import datetime


class ClarificationService:
    def __init__(
            self,
            clar_repo: ClarificationRepository,
            request_repo: RequestRepository
    ):
        self.clar_repo = clar_repo
        self.request_repo = request_repo

    async def ask(self, request_id: str, admin_id: str, question: str) -> Clarification:
        request = await self.request_repo.get(request_id)
        if not request or request.status != "pending":
            raise ValueError("Only pending request can be clarified")

        old_active = await self.clar_repo.get_active_by_request(request_id)
        if old_active:
            old_active.is_active = False
            await self.clar_repo.update(old_active)

        clarification = Clarification(
            id=uuid.uuid4(),
            request_id=request_id if isinstance(request_id, uuid.UUID) else uuid.UUID(request_id),
            question=question,
            asked_by=admin_id,
            is_active=True
        )
        clarification = await self.clar_repo.create(clarification)

        request.status = "need_clarification"
        await self.request_repo.update(request)

        return clarification

    async def answer(self, clarification_id: str, answer: str) -> None:
        clarification = await self.clar_repo.get(clarification_id)
        if not clarification or not clarification.is_active:
            raise ValueError("This clarification is not active")

        clarification.answer = answer
        clarification.answered_at = datetime.now()
        clarification.is_active = False
        await self.clar_repo.update(clarification)
        await self.request_repo.update_status(clarification.request_id, "pending")

    async def get_active_by_request(self, request_id: str) -> Clarification | None:
        return await self.clar_repo.get_active_by_request(request_id)

    async def get_history(self, request_id: str) -> list[Clarification]:
        return await self.clar_repo.get_all_by_request(request_id)