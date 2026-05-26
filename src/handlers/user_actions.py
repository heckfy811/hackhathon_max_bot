from maxapi import Router, F
from maxapi.types import MessageCreated
from maxapi.types.callback import Callback
from maxapi.context import MemoryContext, State, StatesGroup

from ..keyboards import kb
from .common import (
    _get_request_service, _get_audit_service,
    _get_clarification_service, _format_request_short,
)

router = Router()


# ── FSM-состояния для ответа на уточнение ─────────────────────────────────────

class UserClarification(StatesGroup):
    answer = State()

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


# ── Действия пользователя ────────────────────────────────────────────────────

@router.message_callback(F.callback.payload.startswith("cancel:"))
async def user_cancel_request(callback: Callback):
    """Пользователь отменяет свою заявку."""
    user = callback.callback.user
    user_id = str(user.user_id)

    payload = callback.callback.payload.split(":", 1)
    action = payload[0]
    short_id = payload[1]

    service_r, session_r = _get_request_service()
    async with session_r:
        req = await service_r.get_by_short_id(short_id)
        if not req:
            await callback.message.answer("⚠️ Заявка не найдена.", attachments=[kb.user_menu_kb])
            return
        try:
            await service_r.cancel(str(req.id))
            service_a, session_a = _get_audit_service()
            async with session_a:
                await service_a.log(req.id, action, user_id)
            await callback.message.answer(
                f"🚫 Заявка {short_id} отменена.",
                attachments=[kb.user_menu_kb]
            )
        except ValueError as e:
            await callback.message.answer(
                f"⚠️ Не удалось отменить: {e}",
                attachments=[kb.user_menu_kb]
            )


# ── Сброс черновика заявки ─────────────────────────────────────────────────────

@router.message_callback(F.callback.payload.startswith("reset_draft:"))
async def user_reset_draft(callback: Callback):
    """Пользователь сбрасывает (удаляет) черновик заявки."""
    user = callback.callback.user
    user_id = str(user.user_id)

    payload = callback.callback.payload
    short_id = payload.split(":", 1)[1]

    service_r, session_r = _get_request_service()
    async with session_r:
        req = await service_r.get_by_short_id(short_id)
        if not req:
            await callback.message.answer("⚠️ Заявка не найдена.", attachments=[kb.user_menu_kb])
            return
        try:
            await service_r.delete_draft(str(req.id))
            await callback.message.answer(
                f"🗑 Черновик заявки {short_id} удалён.",
                attachments=[kb.user_menu_kb]
            )
        except ValueError as e:
            await callback.message.answer(
                f"⚠️ Не удалось сбросить заявку: {e}",
                attachments=[kb.user_menu_kb]
            )


# ── Ответ на уточняющий вопрос от админа ─────────────────────────────────────

@router.message_callback(F.callback.payload.startswith("answer_clarification:"))
async def user_answer_clarification_start(callback: Callback, context: MemoryContext):
    """Пользователь начинает отвечать на вопрос админа."""
    payload = callback.callback.payload
    short_id = payload.split(":", 1)[1]

    # Проверяем, что заявка в нужном статусе
    service_r, session_r = _get_request_service()
    async with session_r:
        req = await service_r.get_by_short_id(short_id)

    if not req:
        await callback.message.answer("⚠️ Заявка не найдена.", attachments=[kb.user_menu_kb])
        return

    if req.status != "need_clarification":
        await callback.message.answer(
            "⚠️ Эта заявка не требует уточнения.",
            attachments=[kb.user_menu_kb]
        )
        return

    # Получаем активный вопрос
    service_c, session_c = _get_clarification_service()
    async with session_c:
        active_clar = await service_c.get_active_by_request(str(req.id))

    if not active_clar:
        await callback.message.answer(
            "⚠️ Нет активного вопроса по этой заявке.",
            attachments=[kb.user_menu_kb]
        )
        return

    await context.update_data(
        clarification_id=str(active_clar.id),
        action_short_id=short_id,
    )
    await context.set_state(UserClarification.answer)
    await callback.message.answer(
        f"❓ Вопрос от администратора:\n{active_clar.question}\n\n"
        "✏️ Введите ваш ответ:",
        attachments=[kb.cancel_kb]
    )


@router.message_created(UserClarification.answer)
async def user_answer_clarification(event: MessageCreated, context: MemoryContext):
    """Обработка ответа пользователя на уточняющий вопрос."""
    answer_text = event.message.body.text.strip()
    if not answer_text:
        await event.message.answer("⚠️ Ответ не может быть пустым. Введите ответ:")
        return

    data = await context.get_data()
    clarification_id = data.get("clarification_id")
    short_id = data.get("action_short_id")
    user_id = str(event.message.sender.user_id)

    service_c, session_c = _get_clarification_service()
    async with session_c:
        try:
            await service_c.answer(clarification_id, answer_text)
        except ValueError as e:
            await event.message.answer(
                f"⚠️ Ошибка: {e}",
                attachments=[kb.user_menu_kb]
            )
            await context.clear()
            return

    # Запись в аудит-лог
    service_r, session_r = _get_request_service()
    async with session_r:
        req = await service_r.get_by_short_id(short_id)

    if req:
        service_a, session_a = _get_audit_service()
        async with session_a:
            await service_a.log(
                req.id, "answer_clarification", user_id, details=answer_text
            )

    await context.clear()
    await event.message.answer(
        f"✅ Ответ по заявке {short_id} отправлен.\n"
        "Заявка возвращена на рассмотрение администратору.",
        attachments=[kb.user_menu_kb]
    )