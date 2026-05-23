from src.repositories.request_repo import RequestRepository
from src.models.request import Request
import uuid


class RequestService:
    def __init__(self, request_repo: RequestRepository):
        self.request_repo = request_repo

    async def create_draft(self, initiator_id: str) -> Request:
        draft = Request(
            id=uuid.uuid4(),
            status="draft",
            initiator_id=initiator_id
        )
        return await self.request_repo.create(draft)

    async def get_draft(self, user_id: str) -> Request | None:
        drafts = await self.request_repo.get_by_user_and_status(user_id, "draft")
        return drafts[0] if drafts else None

    async def update_draft(self, request_id: str, **kwargs) -> Request:
        request = await self.request_repo.get(request_id)
        if not request or request.status != "draft":
            raise ValueError("Only draft can be updated")

        for key, value in kwargs.items():
            if hasattr(request, key):
                setattr(request, key, value)

        return await self.request_repo.update(request)

    async def submit(self, request_id: str) -> Request:
        request = await self.request_repo.get(request_id)
        if not request or request.status != "draft":
            raise ValueError("Only draft can be submitted")

        required_fields = [request.guest_name, request.visit_date, request.location, request.purpose]
        if not all(required_fields):
            raise ValueError("All required fields must be filled")

        request.status = "pending"
        return await self.request_repo.update(request)

    async def get(self, request_id: str) -> Request | None:
        return await self.request_repo.get(request_id)

    async def get_by_short_id(self, short_id: str) -> Request | None:
        return await self.request_repo.get_by_short_id(short_id)

    async def get_by_user(self, user_id: str) -> list[Request]:
        return await self.request_repo.get_by_initiator(user_id)

    async def get_pending_queue(self) -> list[Request]:
        return await self.request_repo.get_by_statuses(["pending", "need_clarification"])

    async def approve(self, request_id: str, comment: str = None) -> Request:
        request = await self.request_repo.get(request_id)
        if not request or request.status != "pending":
            raise ValueError("Only pending request can be approved")

        request.status = "approved"
        if comment:
            request.admin_comment = comment

        return await self.request_repo.update(request)

    async def reject(self, request_id: str, reason: str, comment: str = None) -> Request:
        request = await self.request_repo.get(request_id)
        if not request or request.status != "pending":
            raise ValueError("Only pending request can be rejected")

        request.status = "rejected"
        request.rejection_reason = reason
        if comment:
            request.rejection_comment = comment

        return await self.request_repo.update(request)

    async def cancel(self, request_id: str) -> Request:
        request = await self.request_repo.get(request_id)
        if not request or request.status != "pending":
            raise ValueError("Only pending request can be cancelled")

        request.status = "closed"
        return await self.request_repo.update(request)

    async def delete_draft(self, request_id: str) -> None:
        request = await self.request_repo.get(request_id)
        if not request or request.status != "draft":
            raise ValueError("Only draft can be deleted")

        await self.request_repo.delete(request_id)