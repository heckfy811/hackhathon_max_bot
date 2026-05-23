from maxapi import Router, F
from maxapi.types.callback import Callback
from maxapi.context import MemoryContext

from ..keyboards import kb
from .common import _get_user_service, _get_request_service, _format_request_short, _format_request_full

router = Router()

@router.message_callback(F.callback.payload == "my_requests")
async def my_requests(callback: Callback):
    """Список всех заявок пользователя."""
    user = callback.callback.user
    user_id = str(user.user_id)

    service, session = _get_request_service()
    async with session:
        requests = await service.get_by_user(user_id)

    if not requests:
        await callback.message.answer(
            "📋 У вас пока нет заявок.",
            attachments=[kb.user_menu_kb]
        )
        return

    # Формируем текст списка
    lines = ["📋 Ваши заявки:\n"]
    for req in requests:
        lines.append(_format_request_short(req))
    lines.append("\nНажмите на номер заявки для подробностей:")

    await callback.message.answer(
        "\n".join(lines),
        attachments=[kb.requests_list_kb(requests, back_payload="start")]
    )
# ── Просмотр конкретной заявки ────────────────────────────────────────────────

@router.message_callback(F.callback.payload.startswith("view_request:"))
async def view_request(callback: Callback, context: MemoryContext):
    """Просмотр конкретной заявки. Показывает действия в зависимости от роли."""
    payload = callback.callback.payload
    short_id = payload.split(":", 1)[1]

    user = callback.callback.user
    user_id = str(user.user_id)

    service_r, session_r = _get_request_service()
    async with session_r:
        req = await service_r.get_by_short_id(short_id)

    if not req:
        await callback.message.answer("⚠️ Заявка не найдена.", attachments=[kb.user_menu_kb])
        return

    text = _format_request_full(req)

    # Определяем роль пользователя
    service_u, session_u = _get_user_service()
    async with session_u:
        db_user = await service_u.get(user_id)
    role = db_user.role if db_user else "user"

    if role == "admin":
        # Админ видит действия только для pending-заявок
        if req.status == "pending":
            await callback.message.answer(
                text, attachments=[kb.admin_request_actions_kb(short_id)]
            )
        else:
            await callback.message.answer(
                text, attachments=[kb.admin_menu_kb]
            )
    else:
        # Пользователь может отменить только pending-заявку
        if req.status == "pending":
            await callback.message.answer(
                text, attachments=[kb.user_request_actions_kb(short_id)]
            )
        else:
            await callback.message.answer(
                text, attachments=[kb.user_menu_kb]
            )


# ── Действия пользователя ────────────────────────────────────────────────────

@router.message_callback(F.callback.payload.startswith("user_cancel:"))
async def user_cancel_request(callback: Callback):
    """Пользователь отменяет свою заявку."""
    payload = callback.callback.payload
    short_id = payload.split(":", 1)[1]

    service, session = _get_request_service()
    async with session:
        req = await service.get_by_short_id(short_id)
        if not req:
            await callback.message.answer("⚠️ Заявка не найдена.", attachments=[kb.user_menu_kb])
            return
        try:
            await service.cancel(str(req.id))
            await callback.message.answer(
                f"🚫 Заявка {short_id} отменена.",
                attachments=[kb.user_menu_kb]
            )
        except ValueError as e:
            await callback.message.answer(
                f"⚠️ Не удалось отменить: {e}",
                attachments=[kb.user_menu_kb]
            )