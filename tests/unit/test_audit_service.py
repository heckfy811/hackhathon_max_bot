import pytest
from unittest.mock import AsyncMock, MagicMock
from src.services.audit_service import AuditService
from src.models.audit_log import AuditLog
import uuid


class TestAuditService:
    @pytest.fixture
    def mock_audit_repo(self):
        repo = MagicMock()
        repo.create = AsyncMock()
        repo.get_by_request = AsyncMock()
        repo.get_by_actor = AsyncMock()
        return repo

    @pytest.fixture
    def service(self, mock_audit_repo):
        return AuditService(mock_audit_repo)

    @pytest.mark.asyncio
    async def test_log_creates_audit(self, service, mock_audit_repo):
        """Создание записи аудита"""
        request_id = uuid.uuid4()
        mock_audit_repo.create.return_value = AuditLog(
            request_id=request_id,
            action="approved",
            actor_id="admin_123"
        )

        result = await service.log(request_id, "approved", "admin_123", "Комментарий")

        assert result.action == "approved"
        assert result.actor_id == "admin_123"
        mock_audit_repo.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_request(self, service, mock_audit_repo):
        """Получение аудита по заявке"""
        mock_audit_repo.get_by_request.return_value = [AuditLog(), AuditLog()]

        result = await service.get_by_request("req_123")

        assert len(result) == 2
        mock_audit_repo.get_by_request.assert_called_once_with("req_123")