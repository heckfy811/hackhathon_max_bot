# src/middleware/auth.py

import logging
from typing import Callable, Awaitable, Any
from src.services.user_service import UserService
from src.repositories.user_repo import UserRepository

logger = logging.getLogger(__name__)


class AuthMiddleware:
    def __init__(self, session_factory):
        self.session_factory = session_factory

    async def __call__(
            self,
            update: Any,
            handler: Callable[[Any], Awaitable[None]]
    ) -> None:
        user_id = self._get_user_id(update)

        # Если нет user_id, пропускаем (например, это не от пользователя)
        if not user_id:
            return await handler(update)

        async with self.session_factory() as session:
            user_repo = UserRepository(session)
            user_service = UserService(user_repo)
            user = await user_service.get(user_id)
            is_admin = user.role == "admin" if user else False

            if not hasattr(update, "ctx"):
                update.ctx = {}
            update.ctx["user"] = user
            update.ctx["is_admin"] = is_admin
            update.ctx["user_id"] = user_id

            # Проверяем доступ
            if not self._has_access(update, is_admin, user):
                await self._deny_access(update)
                return  # Не вызываем handler

            # Доступ разрешён
            return await handler(update)

    def _get_user_id(self, update: Any) -> str | None:
        if hasattr(update, "message") and update.message and hasattr(update.message, "from_user"):
            if hasattr(update.message.from_user, "id"):
                return str(update.message.from_user.id)
        if hasattr(update, "callback_query") and update.callback_query and hasattr(update.callback_query, "from_user"):
            if hasattr(update.callback_query.from_user, "id"):
                return str(update.callback_query.from_user.id)
        return None

    def _has_access(self, update: Any, is_admin: bool, user) -> bool:
        if not user:
            if hasattr(update, "message") and update.message and hasattr(update.message, "text"):
                cmd = update.message.text.split()[0] if update.message.text else ""
                return cmd == "/start"
            return False

        if hasattr(update, "message") and update.message and hasattr(update.message, "text"):
            cmd = update.message.text.split()[0] if update.message.text else ""
            admin_commands = ["/admin", "/queue", "/stats"]
            if cmd in admin_commands:
                return is_admin
            return True

        if hasattr(update, "callback_query") and update.callback_query and hasattr(update.callback_query, "data"):
            data = update.callback_query.data
            admin_prefixes = ["approve:", "reject:", "clarify:", "admin_", "queue:", "stats:", "admin_requests"]
            for prefix in admin_prefixes:
                if data.startswith(prefix):
                    return is_admin
            return True

        return True

    async def _deny_access(self, update: Any) -> None:
        user_id = self._get_user_id(update)
        logger.warning(f"Access denied for user {user_id}")

        if hasattr(update, "callback_query") and update.callback_query:
            await update.callback_query.answer(
                "⛔ У вас нет прав для этого действия",
                show_alert=True
            )
        elif hasattr(update, "message") and update.message:
            await update.message.answer(
                "⛔ У вас нет прав для этой команды.\n"
                "Используйте /start для регистрации."
            )