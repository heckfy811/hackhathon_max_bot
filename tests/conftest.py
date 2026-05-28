import uuid

import pytest
from unittest.mock import AsyncMock, MagicMock
from src.models.user import User
from src.models.request import Request
from src.models.clarification import Clarification
from src.models.audit_log import AuditLog


@pytest.fixture
def mock_user():
    return User(
        max_user_id="12345",
        display_name="Test User",
        consent_given=True,
        role="user"
    )


@pytest.fixture
def mock_admin():
    return User(
        max_user_id="admin_123",
        display_name="Admin User",
        consent_given=True,
        role="admin"
    )


@pytest.fixture
def mock_request():
    return Request(
        id=uuid.UUID("550e8400-e29b-41d4-a716-446655440000"),
        short_id="REQ-TEST123456",
        guest_name="Test Guest",
        status="pending",
        initiator_id="12345"
    )


@pytest.fixture
def mock_repo():
    """Базовый мок для репозитория"""
    repo = MagicMock()
    repo.get = AsyncMock()
    repo.create = AsyncMock()
    repo.update = AsyncMock()
    repo.delete = AsyncMock()
    return repo