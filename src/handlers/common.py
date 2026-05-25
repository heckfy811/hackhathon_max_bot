"""
Общие утилиты для хендлеров: хелперы, форматирование, константы.
"""

from ..database.db import AsyncSessionFactory
from ..repositories.audit_repo import AuditRepository
from ..repositories.clarification_repo import ClarificationRepository
from ..repositories.request_repo import RequestRepository
from ..repositories.user_repo import UserRepository
from ..services.audit_service import AuditService
from ..services.clarification_service import ClarificationService
from ..services.request_service import RequestService
from ..services.user_service import UserService


# Версия согласия — обновлять при изменении текста/файла согласия
CONSENT_VERSION = "1.0"

# TODO: при необходимости подгрузить файл с текстом согласия
CONSENT_TEXT = (
    "📋 Для оформления гостевого пропуска необходимо ваше согласие "
    "на обработку персональных данных.\n\n"
    "Нажимая кнопку «Даю согласие», вы подтверждаете, что ознакомлены "
    "с условиями обработки персональных данных и даёте своё согласие."
)

STATUS_LABELS = {
    "draft": "📝 Черновик",
    "pending": "⏳ На рассмотрении",
    "approved": "✅ Одобрена",
    "rejected": "❌ Отклонена",
    "closed": "🚫 Отменена",
    "need_clarification": "❓ Требует уточнения",
}


def _get_request_service() -> tuple[RequestService, object]:
    """Хелпер для создания RequestService с новой сессией."""
    session = AsyncSessionFactory()
    repo = RequestRepository(session)
    return RequestService(repo), session


def _get_user_service() -> tuple[UserService, object]:
    """Хелпер для создания UserService с новой сессией."""
    session = AsyncSessionFactory()
    repo = UserRepository(session)
    return UserService(repo), session


def _get_audit_service() -> tuple[AuditService, object]:
    """Хелпер для создания AuditService с новой сессией."""
    session = AsyncSessionFactory()
    repo = AuditRepository(session)
    return AuditService(repo), session


def _get_clarification_service() -> tuple[ClarificationService, object]:
    """Хелпер для создания ClarificationService с новой сессией."""
    session = AsyncSessionFactory()
    clar_repo = ClarificationRepository(session)
    request_repo = RequestRepository(session)
    return ClarificationService(clar_repo, request_repo), session


def _format_request_short(req) -> str:
    """Краткая информация о заявке для списка."""
    status = STATUS_LABELS.get(req.status, req.status)
    return (
        f"📄 {req.short_id} | {status}\n"
        f"   👤 {req.guest_name or '—'} | 📅 {req.visit_date or '—'}"
    )


async def _format_request_full(req) -> str:
    """Полная информация о заявке, включая историю уточнений."""
    status = STATUS_LABELS.get(req.status, req.status)
    text = (
        f"📄 Заявка {req.short_id}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📊 Статус: {status}\n"
        f"👤 ФИО гостя: {req.guest_name or '—'}\n"
        f"📅 Дата: {req.visit_date or '—'}\n"
        f"🕐 Время: {req.visit_time or '—'}\n"
        f"🏢 Место: {req.location or '—'}\n"
        f"📝 Цель: {req.purpose or '—'}\n"
    )
    if req.admin_comment:
        text += f"\n💬 Комментарий админа: {req.admin_comment}\n"
    if req.rejection_reason:
        text += f"\n❌ Причина отказа: {req.rejection_reason}\n"

    # История уточнений
    service_c, session_c = _get_clarification_service()
    async with session_c:
        history = await service_c.get_history(str(req.id))

    if history:
        text += "\n💬 История уточнений:\n"
        text += "───────────────────\n"
        for i, clar in enumerate(history, 1):
            text += f"  {i}. ❓ Вопрос: {clar.question}\n"
            if clar.answer:
                text += f"     ✏️ Ответ: {clar.answer}\n"
            else:
                text += "     ⏳ Ожидает ответа\n"

    return text


def _format_summary(draft) -> str:
    """Форматирует сводку заявки для подтверждения."""
    return (
        "📋 Проверьте данные заявки:\n\n"
        f"👤 ФИО гостя: {draft.guest_name or '—'}\n"
        f"📅 Дата: {draft.visit_date or '—'}\n"
        f"🕐 Время: {draft.visit_time or '—'}\n"
        f"🏢 Место: {draft.location or '—'}\n"
        f"📝 Цель: {draft.purpose or '—'}\n"
    )
