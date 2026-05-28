import pytest
from unittest.mock import AsyncMock, MagicMock
from src.services.clarification_service import ClarificationService
from src.models.clarification import Clarification
import uuid


class TestClarificationService:
    @pytest.fixture
    def mock_clar_repo(self):
        repo = MagicMock()
        repo.get = AsyncMock()
        repo.create = AsyncMock()
        repo.update = AsyncMock()
        repo.get_active_by_request = AsyncMock()
        repo.get_all_by_request = AsyncMock()
        repo.mark_answered = AsyncMock()
        return repo

    @pytest.fixture
    def mock_request_repo(self):
        repo = MagicMock()
        repo.get = AsyncMock()
        repo.update = AsyncMock()
        repo.update_status = AsyncMock()
        return repo

    @pytest.fixture
    def service(self, mock_clar_repo, mock_request_repo):
        return ClarificationService(mock_clar_repo, mock_request_repo)

    @pytest.fixture
    def mock_request(self):
        req = MagicMock()
        req.id = uuid.uuid4()
        req.status = "pending"
        return req

    @pytest.fixture
    def mock_clarification(self):
        return Clarification(
            id=uuid.uuid4(),
            request_id=uuid.uuid4(),
            question="Test question?",
            asked_by="admin_123",
            is_active=True
        )

    @pytest.mark.asyncio
    async def test_ask_success(self, service, mock_clar_repo, mock_request_repo, mock_request, mock_clarification):
        """Успешное создание уточнения"""
        mock_request_repo.get.return_value = mock_request
        mock_clar_repo.get_active_by_request.return_value = None
        mock_clar_repo.create.return_value = mock_clarification

        result = await service.ask(str(mock_request.id), "admin_123", "Test question?")

        assert result == mock_clarification
        assert mock_request.status == "need_clarification"
        mock_request_repo.update.assert_called_once()

    @pytest.mark.asyncio
    async def test_ask_not_pending(self, service, mock_request_repo, mock_request):
        """Попытка уточнить не-pending заявку — ошибка"""
        mock_request.status = "approved"
        mock_request_repo.get.return_value = mock_request

        with pytest.raises(ValueError, match="Only pending request can be clarified"):
            await service.ask(str(mock_request.id), "admin_123", "Question?")

    @pytest.mark.asyncio
    async def test_answer_success(self, service, mock_clar_repo, mock_request_repo, mock_clarification):
        """Успешный ответ на уточнение"""
        mock_clarification.is_active = True
        mock_clar_repo.get.return_value = mock_clarification

        await service.answer(str(mock_clarification.id), "Test answer")

        assert mock_clarification.answer == "Test answer"
        assert mock_clarification.is_active is False
        mock_clar_repo.update.assert_called_once()
        mock_request_repo.update_status.assert_called_once()

    @pytest.mark.asyncio
    async def test_answer_not_active(self, service, mock_clar_repo, mock_clarification):
        """Попытка ответить на неактивное уточнение — ошибка"""
        mock_clarification.is_active = False
        mock_clar_repo.get.return_value = mock_clarification

        with pytest.raises(ValueError, match="This clarification is not active"):
            await service.answer(str(mock_clarification.id), "Test answer")