import asyncio
import os
import logging

from maxapi import Bot, Router
from dotenv import load_dotenv

from router import dp

load_dotenv()

logging.basicConfig(level=logging.DEBUG)

router = Router()

async def main():
    #Инициализация бота
    bot = Bot(token=os.getenv("TOKEN"))
    #Подключение роутеров
    dp.include_routers(router)

    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())