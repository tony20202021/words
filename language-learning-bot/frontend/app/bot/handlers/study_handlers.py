"""
Main study handlers module that imports and combines all study routers.
"""

from aiogram import Dispatcher, Router

# Импортируем все роутеры из подмодулей
from app.bot.handlers.study.study_commands import study_router as commands_router
from app.bot.handlers.study.study_word_actions import word_router
from app.bot.handlers.study.study_hint_handlers import hint_router

# Создаем общий роутер для процесса изучения
study_router = Router()
# Включаем все подроутеры в основной роутер изучения
study_router.include_router(commands_router)
study_router.include_router(word_router)
study_router.include_router(hint_router)


def register_handlers(dp: Dispatcher):
    """
    Register all study handlers.
    
    Args:
        dp: The dispatcher instance
    """
    # Для aiogram 3.x используем include_router
    dp.include_router(study_router)
