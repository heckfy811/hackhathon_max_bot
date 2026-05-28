import pytest
from unittest.mock import AsyncMock, MagicMock
from src.services.request_service import RequestService
from src.models.request import Request
import uuid


class TestRequestService:
    @pytest.fixture
    def mock_request_repo(self):
        repo = MagicMock()
        repo.get = AsyncMock()
        repo.create = AsyncMock()
        repo.update = AsyncMock()
        repo.delete = AsyncMock()
        repo.get_by_user_and_status = AsyncMock(return_value=[])
        repo.get_by_short_id = AsyncMock()
        repo.get_by_initiator = AsyncMock(return_value=[])
        repo.get_by_statuses = AsyncMock(return_value=[])
        return repo

    @pytest.fixture
    def service(self, mock_request_repo):
        return RequestService(mock_request_repo)

    @pytest.mark.asyncio
    async def test_create_draft(self, service, mock_request_repo):
        """Создание черновика"""
        mock_request_repo.create.return_value = Request(
            id=uuid.uuid4(),
            status="draft",
            initiator_id="user_123"
        )

        draft = await service.create_draft("user_123")

        assert draft.status == "draft"
        mock_request_repo.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_draft_exists(self, service, mock_request_repo, mock_request):
        """Черновик существует — возвращаем"""
        mock_request.status = "draft"
        mock_request_repo.get_by_user_and_status.return_value = [mock_request]

        draft = await service.get_draft("user_123")

        assert draft is not None
        assert draft.status == "draft"

    @pytest.mark.asyncio
    async def test_get_draft_not_exists(self, service, mock_request_repo):
        """Черновика нет — возвращаем None"""
        mock_request_repo.get_by_user_and_status.return_value = []

        draft = await service.get_draft("user_123")

        assert draft is None

    @pytest.mark.asyncio
    async def test_submit_success(self, service, mock_request_repo, mock_request):
        """Успешная отправка заявки"""
        mock_request.status = "draft"
        mock_request.guest_name = "Test Guest"
        mock_request.visit_date = "2025-12-31"
        mock_request.location = "Main Building"
        mock_request.purpose = "Meeting"
        mock_request_repo.get.return_value = mock_request
        mock_request_repo.update.return_value = mock_request

        result = await service.submit(str(mock_request.id))

        assert result.status == "pending"

    @pytest.mark.asyncio
    async def test_submit_not_draft(self, service, mock_request_repo, mock_request):
        """Попытка отправить не-черновик — ошибка"""
        mock_request.status = "pending"
        mock_request_repo.get.return_value = mock_request

        with pytest.raises(ValueError, match="Only draft can be submitted"):
            await service.submit(str(mock_request.id))

    @pytest.mark.asyncio
    async def test_submit_missing_fields(self, service, mock_request_repo, mock_request):
        """Не все поля заполнены — ошибка"""
        mock_request.status = "draft"
        mock_request.guest_name = None  # отсутствует
        mock_request_repo.get.return_value = mock_request

        with pytest.raises(ValueError, match="All required fields must be filled"):
            await service.submit(str(mock_request.id))

    @pytest.mark.asyncio
    async def test_approve_success(self, service, mock_request_repo, mock_request):
        """Успешное подтверждение заявки"""
        mock_request.status = "pending"
        mock_request_repo.get.return_value = mock_request
        mock_request_repo.update.return_value = mock_request

        result = await service.approve(str(mock_request.id), "Все ок")

        assert result.status == "approved"
        assert result.admin_comment == "Все ок"

    @pytest.mark.asyncio
    async def test_approve_wrong_status(self, service, mock_request_repo, mock_request):
        """Попытка подтвердить не-pending заявку — ошибка"""
        mock_request.status = "draft"
        mock_request_repo.get.return_value = mock_request

        with pytest.raises(ValueError, match="Only pending request can be approved"):
            await service.approve(str(mock_request.id))

    @pytest.mark.asyncio
    async def test_reject_success(self, service, mock_request_repo, mock_request):
        """Успешное отклонение заявки"""
        mock_request.status = "pending"
        mock_request_repo.get.return_value = mock_request
        mock_request_repo.update.return_value = mock_request

        result = await service.reject(str(mock_request.id), "Не та дата", "Перенесите")

        assert result.status == "rejected"
        assert result.rejection_reason == "Не та дата"
        assert result.rejection_comment == "Перенесите"

    @pytest.mark.asyncio
    async def test_cancel_success(self, service, mock_request_repo, mock_request):
        """Успешная отмена заявки"""
        mock_request.status = "pending"
        mock_request_repo.get.return_value = mock_request
        mock_request_repo.update.return_value = mock_request

        result = await service.cancel(str(mock_request.id))

        assert result.status == "closed"