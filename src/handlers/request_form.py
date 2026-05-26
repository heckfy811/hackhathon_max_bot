"""
Хендлеры FSM-заполнения заявки на гостевой пропуск.
"""

from maxapi import Router, F
from maxapi.types import MessageCreated
from maxapi.types.callback import Callback
from maxapi.context import MemoryContext, State, StatesGroup

from ..keyboards import kb
from .common import _get_user_service, _get_request_service, _get_clarification_service, _get_audit_service, _format_summary, _format_request_full

router = Router()


# ── FSM-состояния для заполнения заявки ───────────────────────────────────────

class RequestForm(StatesGroup):
    guest_name = State()
    visit_date = State()
    visit_time = State()
    location = State()
    purpose = State()
    confirm = State()


# Порядок полей и подсказки
STEPS = [
    ("guest_name", RequestForm.guest_name, "👤 Введите ФИО гостя:"),
    ("visit_date", RequestForm.visit_date, "📅 Введите дату визита (ДД.ММ.ГГГГ):"),
    ("visit_time", RequestForm.visit_time, "🕐 Введите время визита (например, 10:00):"),
    ("location", RequestForm.location, "🏢 Введите место (корпус/аудитория):"),
    ("purpose", RequestForm.purpose, "📝 Введите цель визита:"),
]


def _find_next_step(draft) -> int | None:
    """Находит индекс первого незаполненного поля в черновике."""
    for i, (field, _, _) in enumerate(STEPS):
        value = getattr(draft, field, None)
        if not value:
            return i
    return None  # Все поля заполнены


# ── Начало заполнения / продолжение черновика ─────────────────────────────────

@router.message_callback(F.callback.payload == "create_request")
async def create_request_start(callback: Callback, context: MemoryContext):
    """
    Начало заполнения заявки.
    Ищет существующий черновик в БД — если есть, продолжает с незаполненного поля.
    Если нет — создаёт новый черновик.
    """
    user = callback.callback.user
    user_id = str(user.user_id)

    service, session = _get_request_service()
    async with session:
        draft = await service.get_draft(user_id)

        if draft is None:
            draft = await service.create_draft(initiator_id=user_id)

        await context.update_data(request_id=str(draft.id))

        step_index = _find_next_step(draft)

        if step_index is None:
            await context.set_state(RequestForm.confirm)
            await callback.message.answer(
                _format_summary(draft),
                attachments=[kb.confirm_request_kb]
            )
        else:
            _, state, prompt = STEPS[step_index]
            await context.set_state(state)
            await callback.message.answer(prompt, attachments=[kb.cancel_kb])


@router.message_callback(F.callback.payload == "cancel_request")
async def cancel_request(callback: Callback, context: MemoryContext):
    """Отмена заполнения — черновик остаётся в БД для продолжения позже."""
    await context.clear()
    await callback.message.answer(
        "↩️ Заполнение приостановлено. Черновик сохранён.\n"
        "Вы можете продолжить позже, нажав «Заполнение заявки».",
        attachments=[kb.user_menu_kb]
    )


# ── Обработка шагов FSM ──────────────────────────────────────────────────────

@router.message_created(RequestForm.guest_name)
async def process_guest_name(event: MessageCreated, context: MemoryContext):
    """Обработка ввода ФИО гостя."""
    text = event.message.body.text.strip()
    if not text:
        await event.message.answer("⚠️ ФИО не может быть пустым. Попробуйте ещё раз:")
        return

    data = await context.get_data()
    request_id = data.get("request_id")

    service, session = _get_request_service()
    async with session:
        await service.update_draft(request_id, guest_name=text)

    await context.set_state(RequestForm.visit_date)
    await event.message.answer("📅 Введите дату визита (ДД.ММ.ГГГГ):", attachments=[kb.cancel_kb])


@router.message_created(RequestForm.visit_date)
async def process_visit_date(event: MessageCreated, context: MemoryContext):
    """Обработка ввода даты визита."""
    text = event.message.body.text.strip()
    if not text:
        await event.message.answer("⚠️ Дата не может быть пустой. Попробуйте ещё раз:")
        return

    from datetime import datetime, timedelta, date

    try:
        parsed_date = datetime.strptime(text, "%d.%m.%Y").date()
    except ValueError:
        await event.message.answer("⚠️ Неверный формат даты. Используйте ДД.ММ.ГГГГ (например, 15.06.2026):")
        return

    today = date.today()
    min_date = today + timedelta(days=1)
    max_date = today + timedelta(days=60)

    if parsed_date < min_date:
        await event.message.answer(
            f"⚠️ Дата визита должна быть не раньше завтрашнего дня ({min_date.strftime('%d.%m.%Y')}). "
            "Попробуйте ещё раз:"
        )
        return

    if parsed_date > max_date:
        await event.message.answer(
            f"⚠️ Дата визита не может быть позже чем через 2 месяца ({max_date.strftime('%d.%m.%Y')}). "
            "Попробуйте ещё раз:"
        )
        return

    data = await context.get_data()
    request_id = data.get("request_id")

    service, session = _get_request_service()
    async with session:
        await service.update_draft(request_id, visit_date=parsed_date)

    await context.set_state(RequestForm.visit_time)
    await event.message.answer("🕐 Введите время визита (например, 10:00):", attachments=[kb.cancel_kb])


@router.message_created(RequestForm.visit_time)
async def process_visit_time(event: MessageCreated, context: MemoryContext):
    """Обработка ввода времени визита."""
    text = event.message.body.text.strip()
    if not text:
        await event.message.answer("⚠️ Время не может быть пустым. Попробуйте ещё раз:")
        return

    import re

    if not re.match(r"^\d{1,2}:\d{2}$", text):
        await event.message.answer(
            "⚠️ Неверный формат времени. Используйте формат ЧЧ:ММ (например, 10:00):"
        )
        return

    parts = text.split(":")
    hour = int(parts[0])
    minute = int(parts[1])

    if minute < 0 or minute > 59:
        await event.message.answer(
            "⚠️ Некорректные минуты. Допустимые значения: 00–59. Попробуйте ещё раз:"
        )
        return

    if hour < 8 or hour > 20:
        await event.message.answer(
            "⚠️ Время визита должно быть в рабочие часы (с 08:00 до 20:00). Попробуйте ещё раз:"
        )
        return

    if hour == 20 and minute > 0:
        await event.message.answer(
            "⚠️ Время визита должно быть не позднее 20:00. Попробуйте ещё раз:"
        )
        return

    # Нормализуем формат к HH:MM
    normalized_time = f"{hour:02d}:{minute:02d}"

    data = await context.get_data()
    request_id = data.get("request_id")

    service, session = _get_request_service()
    async with session:
        await service.update_draft(request_id, visit_time=normalized_time)

    await context.set_state(RequestForm.location)
    await event.message.answer("🏢 Введите место (корпус/аудитория):", attachments=[kb.cancel_kb])


@router.message_created(RequestForm.location)
async def process_location(event: MessageCreated, context: MemoryContext):
    """Обработка ввода места."""
    text = event.message.body.text.strip()
    if not text:
        await event.message.answer("⚠️ Место не может быть пустым. Попробуйте ещё раз:")
        return

    data = await context.get_data()
    request_id = data.get("request_id")

    service, session = _get_request_service()
    async with session:
        await service.update_draft(request_id, location=text)

    await context.set_state(RequestForm.purpose)
    await event.message.answer("📝 Введите цель визита:", attachments=[kb.cancel_kb])


@router.message_created(RequestForm.purpose)
async def process_purpose(event: MessageCreated, context: MemoryContext):
    """Обработка ввода цели визита — последний шаг, показываем сводку."""
    text = event.message.body.text.strip()
    if not text:
        await event.message.answer("⚠️ Цель визита не может быть пустой. Попробуйте ещё раз:")
        return

    data = await context.get_data()
    request_id = data.get("request_id")

    service, session = _get_request_service()
    async with session:
        await service.update_draft(request_id, purpose=text)
        draft = await service.get(request_id)

    await context.set_state(RequestForm.confirm)
    await event.message.answer(
        _format_summary(draft),
        attachments=[kb.confirm_request_kb]
    )


@router.message_callback(F.callback.payload == "submit", RequestForm.confirm)
async def confirm_request(callback: Callback, context: MemoryContext):
    """Подтверждение и отправка заявки — статус меняется на pending."""
    data = await context.get_data()
    request_id = data.get("request_id")

    user = callback.callback.user
    user_id = str(user.user_id)
    payload = callback.callback.payload

    service_r, session_r = _get_request_service()
    async with session_r:
        try:
            await service_r.submit(request_id)
            service_a, session_a = _get_audit_service()
            async with session_a:
                await service_a.log(request_id, payload, user_id)
        except ValueError as e:
            await callback.message.answer(
                f"⚠️ Не удалось отправить заявку: {e}",
                attachments=[kb.user_menu_kb]
            )
            await context.clear()
            return

    await context.clear()
    await callback.message.answer(
        "✅ Заявка успешно отправлена на рассмотрение!\n"
        "Вы получите уведомление о решении.",
        attachments=[kb.user_menu_kb]
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
        elif req.status == "need_clarification":
            # Показываем вопрос админа и кнопку ответа
            service_c, session_c = _get_clarification_service()
            async with session_c:
                active_clar = await service_c.get_active_by_request(str(req.id))
            if active_clar:
                text += f"\n❓ Вопрос от администратора:\n{active_clar.question}\n"
            await callback.message.answer(
                text, attachments=[kb.user_clarification_kb(short_id)]
            )
        else:
            await callback.message.answer(
                text, attachments=[kb.user_menu_kb]
            )