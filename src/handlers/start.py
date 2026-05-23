"""
Хендлеры начального взаимодействия: приветствие и команда /start.
"""

from maxapi import Router
from maxapi.types import BotStarted

from ..keyboards import kb

router = Router()


@router.bot_started()
async def bot_init(event: BotStarted):
    await event.bot.send_message(
        chat_id=event.chat_id,
        text="👋 Привет! Добро пожаловать в сервис оформления гостевых пропусков!"
             "\nНажми кнопку 'Начать', чтобы начать работу"
             "\n\nДИСКЛЕЙМЕР: Сервис разработан командой хакатона университета "
             "и не является официальной функцией платформы"
    )
    await event.bot.send_message(
        chat_id=event.chat_id,
        text="Выберите действие:",
        attachments=[kb.start_kb]
    )
