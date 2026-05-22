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
