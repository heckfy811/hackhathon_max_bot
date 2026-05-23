from maxapi import Router, F
from maxapi.types import MessageCreated
from maxapi.types.callback import Callback
from maxapi.context import MemoryContext, State, StatesGroup


from ..keyboards import kb
from .common import _get_user_service, _get_request_service, _format_request_short, _format_request_full

router = Router()
# ── Заявки пользователей (админ) ─────────────────────────────────────────────

@router.message_callback(F.callback.payload == "admin_requests")
async def admin_requests(callback: Callback):
    """Список заявок в статусе pending для администратора."""
    service, session = _get_request_service()
    async with session:
        requests = await service.get_pending_queue()

    if not requests:
        await callback.message.answer(
            "� Нет заявок на рассмотрении.",
            attachments=[kb.admin_menu_kb]
        )
        return

    lines = ["📂 Заявки на рассмотрении:\n"]
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



# ── FSM-состояния для действий админа ─────────────────────────────────────────
class AdminAction(StatesGroup):
    reject_reason = State()
    ask_question = State()

@router.message_callback(F.callback.payload.startswith("admin_approve:"))
async def admin_approve_request(callback: Callback):
    """Админ одобряет заявку."""
    payload = callback.callback.payload
    short_id = payload.split(":", 1)[1]

    service, session = _get_request_service()
    async with session:
        req = await service.get_by_short_id(short_id)
        if not req:
            await callback.message.answer("⚠️ Заявка не найдена.", attachments=[kb.admin_menu_kb])
            return
        try:
            await service.approve(str(req.id))
            await callback.message.answer(
                f"✅ Заявка {short_id} одобрена.",
                attachments=[kb.admin_menu_kb]
            )
        except ValueError as e:
            await callback.message.answer(
                f"⚠️ Ошибка: {e}",
                attachments=[kb.admin_menu_kb]
            )


@router.message_callback(F.callback.payload.startswith("admin_reject:"))
async def admin_reject_start(callback: Callback, context: MemoryContext):
    """Админ начинает отклонение — запрашиваем причину."""
    payload = callback.callback.payload
    short_id = payload.split(":", 1)[1]

    await context.update_data(action_short_id=short_id)
    await context.set_state(AdminAction.reject_reason)
    await callback.message.answer(
        f"❌ Отклонение заявки {short_id}.\n"
        "Введите причину отклонения:",
        attachments=[kb.cancel_kb]
    )


@router.message_created(AdminAction.reject_reason)
async def admin_reject_reason(event: MessageCreated, context: MemoryContext):
    """Обработка ввода причины отклонения."""
    reason = event.message.body.text.strip()
    if not reason:
        await event.message.answer("⚠️ Причина не может быть пустой. Введите причину:")
        return

    data = await context.get_data()
    short_id = data.get("action_short_id")

    service, session = _get_request_service()
    async with session:
        req = await service.get_by_short_id(short_id)
        if not req:
            await event.message.answer("⚠️ Заявка не найдена.", attachments=[kb.admin_menu_kb])
            await context.clear()
            return
        try:
            await service.reject(str(req.id), reason=reason)
            await event.message.answer(
                f"❌ Заявка {short_id} отклонена.\nПричина: {reason}",
                attachments=[kb.admin_menu_kb]
            )
        except ValueError as e:
            await event.message.answer(f"⚠️ Ошибка: {e}", attachments=[kb.admin_menu_kb])

    await context.clear()


@router.message_callback(F.callback.payload.startswith("admin_ask:"))
async def admin_ask_start(callback: Callback, context: MemoryContext):
    """Админ задаёт вопрос по заявке — запрашиваем текст вопроса."""
    payload = callback.callback.payload
    short_id = payload.split(":", 1)[1]

    await context.update_data(action_short_id=short_id)
    await context.set_state(AdminAction.ask_question)
    await callback.message.answer(
        f"❓ Уточнение по заявке {short_id}.\n"
        "Введите вопрос для инициатора:",
        attachments=[kb.cancel_kb]
    )


@router.message_created(AdminAction.ask_question)
async def admin_ask_question(event: MessageCreated, context: MemoryContext):
    """Обработка ввода вопроса от админа (заглушка — сохраняет в admin_comment)."""
    question = event.message.body.text.strip()
    if not question:
        await event.message.answer("⚠️ Вопрос не может быть пустым. Введите вопрос:")
        return

    data = await context.get_data()
    short_id = data.get("action_short_id")

    service, session = _get_request_service()
    async with session:
        req = await service.get_by_short_id(short_id)
        if not req:
            await event.message.answer("⚠️ Заявка не найдена.", attachments=[kb.admin_menu_kb])
            await context.clear()
            return

        # Сохраняем вопрос в admin_comment и меняем статус
        req.admin_comment = question
        req.status = "need_clarification"
        await session.commit()

        await event.message.answer(
            f"❓ Вопрос по заявке {short_id} отправлен инициатору.\n"
            f"Вопрос: {question}",
            attachments=[kb.admin_menu_kb]
        )

    await context.clear()