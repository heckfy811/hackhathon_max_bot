"""
Модуль подключения к БД и SQL-запросы для работы с пользователями.
"""
import os
from datetime import datetime

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import text


DATABASE_URL: str = os.getenv("DATABASE_URL", "")

engine = create_async_engine(DATABASE_URL, echo=False, pool_pre_ping=True)

AsyncSessionFactory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# Версия согласия — обновлять при изменении текста/файла согласия
CONSENT_VERSION = "1.0"


async def upsert_user_consent(
    max_user_id: str,
    display_name: str,
) -> None:
    """
    Записывает пользователя в bot_schema.users с consent_given=true.
    Если пользователь уже существует — обновляет согласие.
    """
    query = text("""
        INSERT INTO bot_schema.users (max_user_id, display_name, consent_given, consent_version, consent_timestamp, role)
        VALUES (:max_user_id, :display_name, TRUE, :consent_version, :consent_timestamp, 'user')
        ON CONFLICT (max_user_id)
        DO UPDATE SET
            consent_given = TRUE,
            consent_version = :consent_version,
            consent_timestamp = :consent_timestamp
    """)

    async with AsyncSessionFactory() as session:
        await session.execute(query, {
            "max_user_id": max_user_id,
            "display_name": display_name,
            "consent_version": CONSENT_VERSION,
            "consent_timestamp": datetime.utcnow(),
        })
        await session.commit()


async def get_user(max_user_id: str) -> dict | None:
    """
    Получает пользователя по max_user_id. Возвращает dict или None.
    """
    query = text("""
        SELECT max_user_id, display_name, consent_given, role
        FROM bot_schema.users
        WHERE max_user_id = :max_user_id
    """)

    async with AsyncSessionFactory() as session:
        result = await session.execute(query, {"max_user_id": max_user_id})
        row = result.mappings().first()
        return dict(row) if row else None
