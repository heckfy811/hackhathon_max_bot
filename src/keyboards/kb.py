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