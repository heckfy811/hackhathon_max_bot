import asyncio
import os
import logging

from maxapi import Bot, Router
from dotenv import load_dotenv
from sqlalchemy import text as sa_text

from src.handlers.dp import dp
from src.database.db import engine
from src.middleware import AuthMiddleware
from src.database.db import AsyncSessionFactory

load_dotenv()

logging.basicConfig(level=logging.DEBUG)

router = Router()


async def main():
    # Проверка подключения к БД при старте
    async with engine.connect() as conn:
        await conn.execute(sa_text("SELECT 1"))
    logging.info("Подключение к базе данных установлено")

    dp.update.middleware(AuthMiddleware(AsyncSessionFactory))
    logging.info("AuthMiddleware подключён")

    # Инициализация бота
    bot = Bot(token=os.getenv("BOT_TOKEN"))
    # Подключение роутеров
    dp.include_routers(router)

    try:
        await dp.start_polling(bot)
    finally:
        # Корректное закрытие пула соединений при остановке
        await engine.dispose()
        logging.info("Пул соединений с БД закрыт")


if __name__ == '__main__':
    asyncio.run(main())
