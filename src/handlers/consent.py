"""
Хендлеры согласия на обработку персональных данных.
"""

import logging

from maxapi import Router, F
from maxapi.types.callback import Callback

from ..keyboards import kb
from .common import CONSENT_TEXT, CONSENT_VERSION, _get_user_service

router = Router()


@router.message_callback(F.callback.payload == "start")
async def personal_data(callback: Callback):
    user = callback.callback.user
    user_id = str(user.user_id)
    display_name = f"{user.first_name} {user.last_name or ''}".strip()

    service, session = _get_user_service()
    async with session:
        db_user = await service.get_or_create(user_id, display_name)

    if not db_user.consent_given:
        await callback.message.answer(
            text=CONSENT_TEXT,
            attachments=[kb.consent_kb]
        )
    elif db_user.role == "admin":
        await callback.message.answer(
            text="👔 Панель администратора:",
            attachments=[kb.admin_menu_kb]
        )
    else:
        await callback.message.answer(
            text="📌 Главное меню:",
            attachments=[kb.user_menu_kb]
        )


@router.message_callback(F.callback.payload == "consent_agree")
async def consent_agree(callback: Callback):
    user = callback.callback.user
    user_id = str(user.user_id)
    display_name = f"{user.first_name} {user.last_name or ''}".strip()

    service, session = _get_user_service()
    async with session:
        try:
            # Убеждаемся, что пользователь существует
            await service.get_or_create(user_id, display_name)
            # Фиксируем согласие
            await service.give_consent(user_id, CONSENT_VERSION)

            await callback.message.answer(
                "✅ Спасибо! Ваше согласие зафиксировано.\n"
                "Теперь вы можете оформить заявку на пропуск."
            )
            await callback.message.answer(
                text="📌 Главное меню:", attachments=[kb.user_menu_kb]
            )
        except Exception as e:
            logging.error(f"Ошибка записи согласия пользователя {user_id}: {e}")
            await callback.message.answer(
                "⚠️ Произошла ошибка при сохранении согласия. Попробуйте позже.",
                attachments=[kb.start_kb]
            )


@router.message_callback(F.callback.payload == "consent_decline")
async def consent_decline(callback: Callback):
    await callback.message.answer(
        "❌ Вы отказались от обработки персональных данных.\n"
        "Без согласия оформление пропуска невозможно.\n\n"
        "Если передумаете — нажмите «Начать».",
        attachments=[kb.start_kb]
    )
