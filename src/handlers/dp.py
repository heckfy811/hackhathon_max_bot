from maxapi import Dispatcher

from . import admin_actions, consent, request_form, start, user_actions

dp = Dispatcher()

dp.include_routers(
    admin_actions.router,
    consent.router,
    request_form.router,
    start.router,
    user_actions.router,
)
