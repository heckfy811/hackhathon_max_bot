"""
Хендлеры FSM-заполнения заявки на гостевой пропуск.
"""

from maxapi import Router, F
from maxapi.types import MessageCreated
from maxapi.types.callback import Callback
from maxapi.context import MemoryContext, State, StatesGroup

from ..keyboards import kb
from .common import _get_request_service, _format_summary, _get_audit_service

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

    from datetime import datetime
    try:
        parsed_date = datetime.strptime(text, "%d.%m.%Y").date()
    except ValueError:
        await event.message.answer("⚠️ Неверный формат даты. Используйте ДД.ММ.ГГГГ (например, 15.06.2026):")
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

    data = await context.get_data()
    request_id = data.get("request_id")

    service, session = _get_request_service()
    async with session:
        await service.update_draft(request_id, visit_time=text)

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
