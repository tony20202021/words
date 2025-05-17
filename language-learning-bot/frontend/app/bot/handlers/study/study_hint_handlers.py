"""
Handlers for hint functions in the study process.
Utilizes nested routers pattern for better modularity.
"""

from aiogram import Router

# Создаем основной роутер для подсказок
hint_router = Router()

# Импортируем и включаем вложенные роутеры
from app.bot.handlers.study.hint.create_handlers import create_router
from app.bot.handlers.study.hint.edit_handlers import edit_router
from app.bot.handlers.study.hint.toggle_handlers import toggle_router
from app.bot.handlers.study.hint.common import cancel_router

# Включаем вложенные роутеры в основной роутер
hint_router.include_router(cancel_router)
hint_router.include_router(create_router)
hint_router.include_router(edit_router)
hint_router.include_router(toggle_router)
