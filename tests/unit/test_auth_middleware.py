# tests/unit/test_auth_middleware.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.middleware.auth import AuthMiddleware
from src.models.user import User


class TestAuthMiddleware:
    @pytest.fixture
    def mock_session(self):
        session = AsyncMock()
        session.__aenter__ = AsyncMock(return_value=session)
        session.__aexit__ = AsyncMock()
        return session

    @pytest.fixture
    def mock_session_factory(self, mock_session):
        factory = MagicMock()
        factory.return_value = mock_session
        return factory

    @pytest.fixture
    def auth_middleware(self, mock_session_factory):
        return AuthMiddleware(mock_session_factory)

    @pytest.fixture
    def mock_user(self):
        return User(
            max_user_id="12345",
            display_name="Test User",
            consent_given=True,
            role="user"
        )

    @pytest.fixture
    def mock_admin(self):
        return User(
            max_user_id="admin_123",
            display_name="Admin User",
            consent_given=True,
            role="admin"
        )

    def _create_mock_user(self, user_id: int, first_name: str):
        """Создаёт простой мок пользователя без pydantic валидации"""
        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user.user_id = user_id
        mock_user.first_name = first_name
        mock_user.last_name = ""
        mock_user.is_bot = False
        return mock_user

    # ========== Сценарий 1: Новый пользователь ==========
    @pytest.mark.asyncio
    async def test_new_user_start_allowed(self, auth_middleware):
        """Новый пользователь пишет /start → пропускаем"""
        mock_message = MagicMock()
        mock_message.from_user = self._create_mock_user(999, "New")
        mock_message.text = "/start"

        update = MagicMock()
        update.message = mock_message
        update.callback_query = None
        update.ctx = {}

        handler = AsyncMock()

        with patch("src.services.user_service.UserService.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = None

            await auth_middleware(update, handler)

        handler.assert_awaited_once()
        assert update.ctx["user"] is None
        assert update.ctx["is_admin"] is False

    @pytest.mark.asyncio
    async def test_new_user_menu_denied(self, auth_middleware):
        """Новый пользователь пишет /menu → отказ"""
        mock_message = MagicMock()
        mock_message.from_user = self._create_mock_user(999, "New")
        mock_message.text = "/menu"

        update = MagicMock()
        update.message = mock_message
        update.callback_query = None
        update.ctx = {}

        handler = AsyncMock()

        with patch("src.services.user_service.UserService.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = None

            await auth_middleware(update, handler)

        handler.assert_not_awaited()
        assert update.message.answer.call_count == 1

    @pytest.mark.asyncio
    async def test_new_user_callback_denied(self, auth_middleware):
        """Новый пользователь нажимает кнопку → отказ"""
        mock_callback = MagicMock()
        mock_callback.from_user = self._create_mock_user(999, "New")
        mock_callback.data = "create_request"

        update = MagicMock()
        update.message = None
        update.callback_query = mock_callback
        update.ctx = {}

        handler = AsyncMock()

        with patch("src.services.user_service.UserService.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = None

            await auth_middleware(update, handler)

        handler.assert_not_awaited()
        assert update.callback_query.answer.call_count == 1

    # ========== Сценарий 2: Обычный пользователь ==========
    @pytest.mark.asyncio
    async def test_user_start_allowed(self, auth_middleware, mock_user):
        """Зарегистрированный пользователь пишет /start → пропускаем"""
        mock_message = MagicMock()
        mock_message.from_user = self._create_mock_user(12345, "Test")
        mock_message.text = "/start"

        update = MagicMock()
        update.message = mock_message
        update.callback_query = None
        update.ctx = {}

        handler = AsyncMock()

        with patch("src.services.user_service.UserService.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_user

            await auth_middleware(update, handler)

        handler.assert_awaited_once()
        assert update.ctx["user"] == mock_user
        assert update.ctx["is_admin"] is False
        assert update.ctx["user_id"] == "12345"

    @pytest.mark.asyncio
    async def test_user_admin_command_denied(self, auth_middleware, mock_user):
        """Обычный пользователь пишет /admin → отказ"""
        mock_message = MagicMock()
        mock_message.from_user = self._create_mock_user(12345, "Test")
        mock_message.text = "/admin"

        update = MagicMock()
        update.message = mock_message
        update.callback_query = None
        update.ctx = {}

        handler = AsyncMock()

        with patch("src.services.user_service.UserService.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_user

            await auth_middleware(update, handler)

        handler.assert_not_awaited()
        assert update.message.answer.call_count == 1

    @pytest.mark.asyncio
    async def test_user_admin_callback_denied(self, auth_middleware, mock_user):
        """Обычный пользователь нажимает approve: → отказ"""
        mock_callback = MagicMock()
        mock_callback.from_user = self._create_mock_user(12345, "Test")
        mock_callback.data = "approve:REQ-123"

        update = MagicMock()
        update.message = None
        update.callback_query = mock_callback
        update.ctx = {}

        handler = AsyncMock()

        with patch("src.services.user_service.UserService.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_user

            await auth_middleware(update, handler)

        handler.assert_not_awaited()
        assert update.callback_query.answer.call_count == 1

    @pytest.mark.asyncio
    async def test_user_user_callback_allowed(self, auth_middleware, mock_user):
        """Обычный пользователь нажимает create_request → пропускаем"""
        mock_callback = MagicMock()
        mock_callback.from_user = self._create_mock_user(12345, "Test")
        mock_callback.data = "create_request"

        update = MagicMock()
        update.message = None
        update.callback_query = mock_callback
        update.ctx = {}

        handler = AsyncMock()

        with patch("src.services.user_service.UserService.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_user

            await auth_middleware(update, handler)

        handler.assert_awaited_once()
        assert update.ctx["is_admin"] is False

    # ========== Сценарий 3: Администратор ==========
    @pytest.mark.asyncio
    async def test_admin_admin_command_allowed(self, auth_middleware, mock_admin):
        """Админ пишет /admin → пропускаем"""
        mock_message = MagicMock()
        mock_message.from_user = self._create_mock_user(12345, "Admin")
        mock_message.text = "/admin"

        update = MagicMock()
        update.message = mock_message
        update.callback_query = None
        update.ctx = {}

        handler = AsyncMock()

        with patch("src.services.user_service.UserService.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_admin

            await auth_middleware(update, handler)

        handler.assert_awaited_once()
        assert update.ctx["is_admin"] is True

    @pytest.mark.asyncio
    async def test_admin_admin_callback_allowed(self, auth_middleware, mock_admin):
        """Админ нажимает approve: → пропускаем"""
        mock_callback = MagicMock()
        mock_callback.from_user = self._create_mock_user(12345, "Admin")
        mock_callback.data = "approve:REQ-123"

        update = MagicMock()
        update.message = None
        update.callback_query = mock_callback
        update.ctx = {}

        handler = AsyncMock()

        with patch("src.services.user_service.UserService.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_admin

            await auth_middleware(update, handler)

        handler.assert_awaited_once()
        assert update.ctx["is_admin"] is True

    @pytest.mark.asyncio
    async def test_admin_user_callback_allowed(self, auth_middleware, mock_admin):
        """Админ нажимает create_request → пропускаем"""
        mock_callback = MagicMock()
        mock_callback.from_user = self._create_mock_user(12345, "Admin")
        mock_callback.data = "create_request"

        update = MagicMock()
        update.message = None
        update.callback_query = mock_callback
        update.ctx = {}

        handler = AsyncMock()

        with patch("src.services.user_service.UserService.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_admin

            await auth_middleware(update, handler)

        handler.assert_awaited_once()
        assert update.ctx["is_admin"] is True