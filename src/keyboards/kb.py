from maxapi.utils.inline_keyboard import InlineKeyboardBuilder
from maxapi.types.attachments.buttons import CallbackButton

start_kb = (
    InlineKeyboardBuilder()
    .row(
        CallbackButton(
            text="Начать",
            payload="start"
        )
    )
    .as_markup()
)

# Клавиатура согласия на обработку персональных данных
consent_kb = (
    InlineKeyboardBuilder()
    .row(
        CallbackButton(
            text="✅ Даю согласие",
            payload="consent_agree"
        )
    )
    .row(
        CallbackButton(
            text="❌ Отказываюсь",
            payload="consent_decline"
        )
    )
    .as_markup()
)

# Меню пользователя (роль user)
user_menu_kb = (
    InlineKeyboardBuilder()
    .row(
        CallbackButton(
            text="📝 Заполнение заявки",
            payload="create_request"
        )
    )
    .row(
        CallbackButton(
            text="📋 Мои заявки",
            payload="my_requests"
        )
    )
    .as_markup()
)

# Меню администратора (роль admin)
admin_menu_kb = (
    InlineKeyboardBuilder()
    .row(
        CallbackButton(
            text="📂 Заявки пользователей",
            payload="admin_requests"
        )
    )
    .as_markup()
)

# Кнопка отмены заполнения заявки (возврат в меню)
cancel_kb = (
    InlineKeyboardBuilder()
    .row(
        CallbackButton(
            text="❌ Отмена (вернуться в меню)",
            payload="cancel_request"
        )
    )
    .as_markup()
)

# Кнопка подтверждения отправки заявки
confirm_request_kb = (
    InlineKeyboardBuilder()
    .row(
        CallbackButton(
            text="✅ Отправить заявку",
            payload="confirm_request"
        )
    )
    .row(
        CallbackButton(
            text="❌ Отмена",
            payload="cancel_request"
        )
    )
    .as_markup()
)


# ── Динамические клавиатуры ───────────────────────────────────────────────────

def requests_list_kb(requests, back_payload: str = "start"):
    """Клавиатура со списком заявок (по short_id). Каждая кнопка — переход к заявке."""
    builder = InlineKeyboardBuilder()
    for req in requests:
        builder.row(
            CallbackButton(
                text=f"📄 {req.short_id}",
                payload=f"view_request:{req.short_id}"
            )
        )
    builder.row(
        CallbackButton(text="↩️ Назад", payload=back_payload)
    )
    return builder.as_markup()


def user_request_actions_kb(short_id: str):
    """Действия пользователя над заявкой: только отмена."""
    return (
        InlineKeyboardBuilder()
        .row(
            CallbackButton(
                text="🚫 Отменить заявку",
                payload=f"user_cancel:{short_id}"
            )
        )
        .row(
            CallbackButton(text="↩️ К списку заявок", payload="my_requests")
        )
        .as_markup()
    )


def admin_request_actions_kb(short_id: str):
    """Действия администратора над заявкой: одобрить, отклонить, задать вопрос."""
    return (
        InlineKeyboardBuilder()
        .row(
            CallbackButton(
                text="✅ Одобрить",
                payload=f"admin_approve:{short_id}"
            )
        )
        .row(
            CallbackButton(
                text="❌ Отклонить",
                payload=f"admin_reject:{short_id}"
            )
        )
        .row(
            CallbackButton(
                text="❓ Задать вопрос",
                payload=f"admin_ask:{short_id}"
            )
        )
        .row(
            CallbackButton(text="↩️ К списку заявок", payload="admin_requests")
        )
        .as_markup()
    )
