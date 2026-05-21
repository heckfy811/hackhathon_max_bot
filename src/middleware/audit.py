from typing import Callable, Awaitable
from maxapi.types import Update, CallbackQuery

from src.repositories.clarification_repo import ClarificationRepository
from src.services.audit_service import AuditService
from src.repositories.audit_repo import AuditRepository
from src.repositories.request_repo import RequestRepository
from sqlalchemy.ext.asyncio import AsyncSession
import re


class AuditMiddleware:
    AUDITABLE_ACTIONS = {
        r'^approve:(.+)$': 'approved',
        r'^reject:(.+)$': 'rejected',
        r'^clarify:(.+)$': 'clarification_requested',
        r'^answer_clarification:(.+)$': 'clarification_answered',
        r'^cancel:(.+)$': 'cancelled',
        r'^submit:(.+)$': 'submitted',
    }

    def __init__(self, session_factory):
        self.session_factory = session_factory

    async def __call__(
            self,
            update: Update,
            handler: Callable[[Update], Awaitable[None]]
    ):
        result = await handler(update)
        if update.callback_query:
            await self._audit_callback(update.callback_query)

        return result

    async def _audit_callback(self, callback: CallbackQuery):
        data = callback.data

        for pattern, action in self.AUDITABLE_ACTIONS.items():
            match = re.match(pattern, data)
            if match:
                request_id = match.group(1)
                user_id = str(callback.from_user.id)
                details = None
                if action == "clarification_requested":
                    details = await self._get_clarification_question(request_id)
                elif action == "clarification_answered":
                    details = await self._get_clarification_answer(request_id)
                elif action == "rejected":
                    details = await self._get_rejection_details(request_id)
                async with self.session_factory() as session:
                    audit_service = AuditService(AuditRepository(session))
                    await audit_service.log(
                        request_id=request_id,
                        action=action,
                        actor_id=user_id,
                        details=details
                    )
                break

    async def _get_clarification_question(self, request_id: str) -> str | None:
        async with self.session_factory() as session:
            repo = ClarificationRepository(session)
            active = await repo.get_active_by_request(request_id)
            return active.question if active else None

    async def _get_clarification_answer(self, request_id: str) -> str | None:
        async with self.session_factory() as session:
            repo = ClarificationRepository(session)
            active = await repo.get_active_by_request(request_id)
            return active.answer if active else None

    async def _get_rejection_details(self, request_id: str) -> str | None:
        async with self.session_factory() as session:
            repo = RequestRepository(session)
            request = await repo.get(request_id)
            if request and request.rejection_reason:
                details = f"Причина: {request.rejection_reason}"
                if request.admin_comment:
                    details += f"\nКомментарий: {request.admin_comment}"
                return details
            return None