"""
Main user handlers module that imports and combines all user routers.
"""

from aiogram import Dispatcher, Router

# Импортируем все роутеры из подмодулей
from app.bot.handlers.user.basic_handlers import basic_router
from app.bot.handlers.user.settings_handlers import settings_router
from app.bot.handlers.user.help_handlers import help_router
from app.bot.handlers.user.stats_handlers import stats_router
from app.bot.handlers.user.hint_handlers import hint_router

# Создаем общий роутер для пользователя
user_router = Router()

# Включаем все подроутеры в основной роутер пользователя
user_router.include_router(basic_router)
user_router.include_router(settings_router)
user_router.include_router(help_router)
user_router.include_router(stats_router)
user_router.include_router(hint_router)

def register_handlers(dp: Dispatcher):
    """
    Register all user handlers.
    
    Args:
        dp: The dispatcher instance
    """
    # Для aiogram 3.x используем include_router
    dp.include_router(user_router)