import logging

from maxapi import Dispatcher, F
from maxapi.types import BotStarted, Command, MessageCreated
from maxapi.types.callback import Callback
from maxapi.context import MemoryContext, State, StatesGroup

from ..keyboards import kb
from ..database.db import upsert_user_consent, get_user, AsyncSessionFactory
from ..repositories.request_repo import RequestRepository
from ..services.request_service import RequestService

dp = Dispatcher()

# TODO: при необходимости подгрузить файл с текстом согласия
CONSENT_TEXT = (
    "📋 Для оформления гостевого пропуска необходимо ваше согласие "
    "на обработку персональных данных.\n\n"
    "Нажимая кнопку «Даю согласие», вы подтверждаете, что ознакомлены "
    "с условиями обработки персональных данных и даёте своё согласие."
)


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


def _get_request_service() -> RequestService:
    """Хелпер для создания сервиса с новой сессией."""
    # Сессия будет закрыта после выхода из async with в вызывающем коде
    session = AsyncSessionFactory()
    repo = RequestRepository(session)
    return RequestService(repo), session


def _find_next_step(draft) -> int | None:
    """Находит индекс первого незаполненного поля в черновике."""
    for i, (field, _, _) in enumerate(STEPS):
        value = getattr(draft, field, None)
        if not value:
            return i
    return None  # Все поля заполнены


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


# ── Основные хендлеры ─────────────────────────────────────────────────────────

@dp.bot_started()
async def bot_init(event: BotStarted):
    await event.bot.send_message(
        chat_id=event.chat_id,
        text="👋 Привет! Добро пожаловать в сервис оформления гостевых пропусков!"
             "\nНажми кнопку 'Начать', чтобы создать заявку"
             "\n\nДИСКЛЕЙМЕР: Сервис разработан командой хакатона университета "
             "и не является официальной функцией платформы"
    )
    await event.bot.send_message(
        chat_id=event.chat_id,
        text="Выберите действие:",
        attachments=[kb.start_kb]
    )


@dp.message_created(Command('start'))
async def start(event: MessageCreated):
    await event.message.answer(text="Выберите действие:", attachments=[kb.start_kb])


@dp.message_callback(F.callback.payload == "start")
async def personal_data(callback: Callback):
    user = callback.callback.user
    user_id = str(user.user_id)

    db_user = await get_user(user_id)

    if db_user is None or not db_user["consent_given"]:
        await callback.message.answer(
            text=CONSENT_TEXT,
            attachments=[kb.consent_kb]
        )
    elif db_user["role"] == "admin":
        await callback.message.answer(
            text="👔 Панель администратора:",
            attachments=[kb.admin_menu_kb]
        )
    else:
        await callback.message.answer(
            text="📌 Главное меню:",
            attachments=[kb.user_menu_kb]
        )


@dp.message_callback(F.callback.payload == "consent_agree")
async def consent_agree(callback: Callback):
    user = callback.callback.user
    user_id = str(user.user_id)
    display_name = f"{user.first_name} {user.last_name or ''}".strip()

    try:
        await upsert_user_consent(max_user_id=user_id, display_name=display_name)
        await callback.message.answer(
            "✅ Спасибо! Ваше согласие зафиксировано.\n"
            "Теперь вы можете оформить заявку на пропуск."
        )
        await callback.message.answer(text="📌 Главное меню:", attachments=[kb.user_menu_kb])
    except Exception as e:
        logging.error(f"Ошибка записи согласия пользователя {user_id}: {e}")
        await callback.message.answer(
            "⚠️ Произошла ошибка при сохранении согласия. Попробуйте позже.",
            attachments=[kb.start_kb]
        )


@dp.message_callback(F.callback.payload == "consent_decline")
async def consent_decline(callback: Callback):
    await callback.message.answer(
        "❌ Вы отказались от обработки персональных данных.\n"
        "Без согласия оформление пропуска невозможно.\n\n"
        "Если передумаете — нажмите «Начать».",
        attachments=[kb.start_kb]
    )


# ── Заполнение заявки (FSM) ──────────────────────────────────────────────────

@dp.message_callback(F.callback.payload == "create_request")
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
        # Ищем существующий черновик
        draft = await service.get_draft(user_id)

        if draft is None:
            # Создаём новый черновик
            draft = await service.create_draft(initiator_id=user_id)

        # Сохраняем ID черновика в контексте FSM
        await context.update_data(request_id=str(draft.id))

        # Определяем, с какого шага продолжить
        step_index = _find_next_step(draft)

        if step_index is None:
            # Все поля заполнены — показываем сводку
            await context.set_state(RequestForm.confirm)
            await callback.message.answer(
                _format_summary(draft),
                attachments=[kb.confirm_request_kb]
            )
        else:
            # Переходим к нужному шагу
            _, state, prompt = STEPS[step_index]
            await context.set_state(state)
            await callback.message.answer(prompt, attachments=[kb.cancel_kb])


@dp.message_callback(F.callback.payload == "cancel_request")
async def cancel_request(callback: Callback, context: MemoryContext):
    """Отмена заполнения — черновик остаётся в БД для продолжения позже."""
    await context.clear()
    await callback.message.answer(
        "↩️ Заполнение приостановлено. Черновик сохранён.\n"
        "Вы можете продолжить позже, нажав «Заполнение заявки».",
        attachments=[kb.user_menu_kb]
    )


@dp.message_created(RequestForm.guest_name)
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

    # Переход к следующему шагу
    await context.set_state(RequestForm.visit_date)
    await event.message.answer("📅 Введите дату визита (ДД.ММ.ГГГГ):", attachments=[kb.cancel_kb])


@dp.message_created(RequestForm.visit_date)
async def process_visit_date(event: MessageCreated, context: MemoryContext):
    """Обработка ввода даты визита."""
    text = event.message.body.text.strip()
    if not text:
        await event.message.answer("⚠️ Дата не может быть пустой. Попробуйте ещё раз:")
        return

    # Простая валидация формата даты
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


@dp.message_created(RequestForm.visit_time)
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


@dp.message_created(RequestForm.location)
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


@dp.message_created(RequestForm.purpose)
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


@dp.message_callback(F.callback.payload == "confirm_request", RequestForm.confirm)
async def confirm_request(callback: Callback, context: MemoryContext):
    """Подтверждение и отправка заявки — статус меняется на pending."""
    data = await context.get_data()
    request_id = data.get("request_id")

    service, session = _get_request_service()
    async with session:
        try:
            await service.submit(request_id)
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


# ── FSM-состояния для действий админа ─────────────────────────────────────────

class AdminAction(StatesGroup):
    reject_reason = State()
    ask_question = State()


# ── Мои заявки (пользователь) ─────────────────────────────────────────────────

STATUS_LABELS = {
    "draft": "📝 Черновик",
    "pending": "⏳ На рассмотрении",
    "approved": "✅ Одобрена",
    "rejected": "❌ Отклонена",
    "closed": "🚫 Отменена",
    "need_clarification": "❓ Требует уточнения",
}


def _format_request_short(req) -> str:
    """Краткая информация о заявке для списка."""
    status = STATUS_LABELS.get(req.status, req.status)
    return (
        f"📄 {req.short_id} | {status}\n"
        f"   👤 {req.guest_name or '—'} | 📅 {req.visit_date or '—'}"
    )


def _format_request_full(req) -> str:
    """Полная информация о заявке."""
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
    return text


@dp.message_callback(F.callback.payload == "my_requests")
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


# ── Заявки пользователей (админ) ─────────────────────────────────────────────

@dp.message_callback(F.callback.payload == "admin_requests")
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

@dp.message_callback(F.callback.payload.startswith("view_request:"))
async def view_request(callback: Callback, context: MemoryContext):
    """Просмотр конкретной заявки. Показывает действия в зависимости от роли."""
    payload = callback.callback.payload
    short_id = payload.split(":", 1)[1]

    user = callback.callback.user
    user_id = str(user.user_id)

    service, session = _get_request_service()
    async with session:
        req = await service.get_by_short_id(short_id)

    if not req:
        await callback.message.answer("⚠️ Заявка не найдена.", attachments=[kb.user_menu_kb])
        return

    text = _format_request_full(req)

    # Определяем роль пользователя
    db_user = await get_user(user_id)
    role = db_user["role"] if db_user else "user"

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

@dp.message_callback(F.callback.payload.startswith("user_cancel:"))
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


# ── Действия администратора ───────────────────────────────────────────────────

@dp.message_callback(F.callback.payload.startswith("admin_approve:"))
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


@dp.message_callback(F.callback.payload.startswith("admin_reject:"))
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


@dp.message_created(AdminAction.reject_reason)
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


@dp.message_callback(F.callback.payload.startswith("admin_ask:"))
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


@dp.message_created(AdminAction.ask_question)
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
