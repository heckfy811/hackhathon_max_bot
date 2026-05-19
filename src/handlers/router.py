from maxapi import Dispatcher, F
from maxapi.types import BotStarted, Command, MessageCreated
from maxapi.types.callback import Callback

import kb

dp = Dispatcher()

#TODO: раскидать методы по роутерам вместо диспатчера
#Метод, вызывающийся при запуске бота
@dp.bot_started()
async def bot_init(event: BotStarted):
    await event.bot.send_message(chat_id=event.chat_id, text="👋 Привет! Добро пожаловать в сервис оформления гостевых пропусков!"
                               "\nНажми кнопку 'Начать', чтобы создать заявку"
                               "\n\nДИСКЛЕЙМЕР: Сервис разработан командой хакатона университета и не является официальной функцией платформы")
    await event.bot.send_message(chat_id=event.chat_id, text="Выберите действие:", attachments=[kb.start_kb])

#Метод, вызывающийся при ручной команде /start
@dp.message_created(Command('start'))
async def start(event: MessageCreated):
    await event.message.answer(text="Выберите действие:", attachments=[kb.start_kb])

#Метод, вызывающийся при нажатии на кнопку
@dp.message_callback(F.callback.payload == "start")
async def personal_data(callback: Callback):
    #TODO: Написать метод обработки персональных данных
    await callback.message.answer("🚧Функция в разработке🚧")
    await callback.message.answer("Выберите действие:", attachments=[kb.start_kb])