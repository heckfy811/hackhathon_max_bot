import pytest
from unittest.mock import AsyncMock, MagicMock
from src.services.user_service import UserService
from src.models.user import User


class TestUserService:
    @pytest.fixture
    def mock_user_repo(self):
        repo = MagicMock()
        repo.get = AsyncMock()
        repo.create = AsyncMock()
        repo.update = AsyncMock()
        return repo

    @pytest.fixture
    def service(self, mock_user_repo):
        return UserService(mock_user_repo)

    @pytest.mark.asyncio
    async def test_get_or_create_existing_user(self, service, mock_user_repo, mock_user):
        """Существующий пользователь — возвращаем из БД"""
        mock_user_repo.get.return_value = mock_user

        result = await service.get_or_create("12345", "Test User")

        assert result == mock_user
        assert result.max_user_id == "12345"
        mock_user_repo.get.assert_called_once_with("12345")
        mock_user_repo.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_or_create_new_user(self, service, mock_user_repo):
        """Новый пользователь — создаём"""
        mock_user_repo.get.return_value = None
        mock_user_repo.create.return_value = User(
            max_user_id="new_123",
            display_name="New User",
            consent_given=False,
            role="user"
        )

        result = await service.get_or_create("new_123", "New User")

        assert result.max_user_id == "new_123"
        assert result.consent_given is False
        mock_user_repo.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_is_admin_true(self, service, mock_user_repo, mock_admin):
        """Админ — возвращаем True"""
        mock_user_repo.get.return_value = mock_admin

        result = await service.is_admin("admin_123")

        assert result is True

    @pytest.mark.asyncio
    async def test_is_admin_false(self, service, mock_user_repo, mock_user):
        """Обычный пользователь — возвращаем False"""
        mock_user_repo.get.return_value = mock_user

        result = await service.is_admin("12345")

        assert result is False

    @pytest.mark.asyncio
    async def test_is_admin_user_not_found(self, service, mock_user_repo):
        """Пользователь не найден — возвращаем False"""
        mock_user_repo.get.return_value = None

        result = await service.is_admin("unknown")

        assert result is False

    @pytest.mark.asyncio
    async def test_give_consent(self, service, mock_user_repo, mock_user):
        """Фиксация согласия"""
        mock_user_repo.get.return_value = mock_user
        mock_user_repo.update.return_value = mock_user

        result = await service.give_consent("12345", "1.0")

        assert result.consent_given is True
        assert result.consent_version == "1.0"
        mock_user_repo.update.assert_called_once()

    @pytest.mark.asyncio
    async def test_give_consent_user_not_found(self, service, mock_user_repo):
        """Пользователь не найден — ошибка"""
        mock_user_repo.get.return_value = None

        with pytest.raises(ValueError, match="User unknown not found"):
            await service.give_consent("unknown", "1.0")