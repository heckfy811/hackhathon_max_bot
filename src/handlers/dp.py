from maxapi import Dispatcher

from . import admin_actions, consent, request_form, start, user_actions
from ..database.db import AsyncSessionFactory
from ..middleware.audit import AuditMiddleware

dp = Dispatcher()

# Регистрация middleware для записи событий в аудит-лог
dp.register_outer_middleware(AuditMiddleware(AsyncSessionFactory))

dp.include_routers(
    admin_actions.router,
    consent.router,
    request_form.router,
    start.router,
    user_actions.router,
)
