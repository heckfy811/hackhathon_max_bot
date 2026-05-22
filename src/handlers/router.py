import logging

from maxapi import Dispatcher, F
from maxapi.types import BotStarted, Command, MessageCreated
from maxapi.types.callback import Callback

from ..keyboards import kb
from ..database.db import upsert_user_consent, get_user

dp = Dispatcher()

# TODO: при необходимости подгрузить файл с текстом согласия
# CONSENT_FILE_PATH = "path/to/consent.pdf"  # или .txt / .docx
# Пока текст согласия захардкожен ниже:
CONSENT_TEXT = (
    "📋 Для оформления гостевого пропуска необходимо ваше согласие "
    "на обработку персональных данных.\n\n"
    "Нажимая кнопку «Даю согласие», вы подтверждаете, что ознакомлены "
    "с условиями обработки персональных данных и даёте своё согласие."
)


#TODO: раскидать методы по роутерам вместо диспатчера
#Метод, вызывающийся при запуске бота
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


#Метод, вызывающийся при ручной команде /start
@dp.message_created(Command('start'))
async def start(event: MessageCreated):
    await event.message.answer(text="Выберите действие:", attachments=[kb.start_kb])


#Метод, вызывающийся при нажатии на кнопку "Начать"
#Проверяет наличие пользователя в БД и его согласие, показывает соответствующее меню
@dp.message_callback(F.callback.payload == "start")
async def personal_data(callback: Callback):
    user = callback.callback.user
    user_id = str(user.user_id)

    # Проверяем, есть ли пользователь в БД и подписано ли согласие
    db_user = await get_user(user_id)

    if db_user is None or not db_user["consent_given"]:
        # Пользователя нет или согласие не подписано — показываем согласие
        # TODO: здесь можно подгрузить файл с согласием и отправить его вложением
        # from maxapi.types.attachments import FileAttachment
        # consent_attachment = FileAttachment(url=CONSENT_FILE_PATH)
        # await callback.message.answer("...", attachments=[consent_attachment, kb.consent_kb])
        await callback.message.answer(
            text=CONSENT_TEXT,
            attachments=[kb.consent_kb]
        )
    elif db_user["role"] == "admin":
        # Администратор — показываем админ-меню
        await callback.message.answer(
            text="👔 Панель администратора:",
            attachments=[kb.admin_menu_kb]
        )
    else:
        # Обычный пользователь — показываем пользовательское меню
        await callback.message.answer(
            text="📌 Главное меню:",
            attachments=[kb.user_menu_kb]
        )


#Метод, вызывающийся при нажатии на кнопку "Даю согласие"
@dp.message_callback(F.callback.payload == "consent_agree")
async def consent_agree(callback: Callback):
    user = callback.callback.user
    user_id = str(user.user_id)
    display_name = f"{user.first_name} {user.last_name or ''}".strip()

    try:
        await upsert_user_consent(
            max_user_id=user_id,
            display_name=display_name,
        )
        # После согласия показываем пользовательское меню
        await callback.message.answer(
            "✅ Спасибо! Ваше согласие зафиксировано.\n"
            "Теперь вы можете оформить заявку на пропуск."
        )
        await callback.message.answer(
            text="📌 Главное меню:",
            attachments=[kb.user_menu_kb]
        )
    except Exception as e:
        logging.error(f"Ошибка записи согласия пользователя {user_id}: {e}")
        await callback.message.answer(
            "⚠️ Произошла ошибка при сохранении согласия. Попробуйте позже.",
            attachments=[kb.start_kb]
        )


#Метод, вызывающийся при нажатии на кнопку "Отказываюсь"
@dp.message_callback(F.callback.payload == "consent_decline")
async def consent_decline(callback: Callback):
    await callback.message.answer(
        "❌ Вы отказались от обработки персональных данных.\n"
        "Без согласия оформление пропуска невозможно.\n\n"
        "Если передумаете — нажмите «Начать».",
        attachments=[kb.start_kb]
    )


# ── Заглушки для кнопок меню ──────────────────────────────────────────────────

#Заглушка: Заполнение заявки
@dp.message_callback(F.callback.payload == "create_request")
async def create_request_stub(callback: Callback):
    await callback.message.answer(
        "🚧 Функция «Заполнение заявки» в разработке 🚧",
        attachments=[kb.user_menu_kb]
    )


#Заглушка: Мои заявки
@dp.message_callback(F.callback.payload == "my_requests")
async def my_requests_stub(callback: Callback):
    await callback.message.answer(
        "🚧 Функция «Мои заявки» в разработке 🚧",
        attachments=[kb.user_menu_kb]
    )


#Заглушка: Заявки пользователей (админ)
@dp.message_callback(F.callback.payload == "admin_requests")
async def admin_requests_stub(callback: Callback):
    await callback.message.answer(
        "🚧 Функция «Заявки пользователей» в разработке 🚧",
        attachments=[kb.admin_menu_kb]
    )
