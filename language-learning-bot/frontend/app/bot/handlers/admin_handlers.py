"""
Main admin handlers module that imports and combines all admin routers.
"""

from aiogram import Dispatcher, Router

# Импортируем все роутеры из подмодулей
from app.bot.handlers.admin.admin_basic_handlers import admin_router as basic_router
from app.bot.handlers.admin.admin_language_handlers import language_router
from app.bot.handlers.admin.admin_word_handlers import word_router
from app.bot.handlers.admin.admin_upload_handlers import upload_router
from app.bot.handlers.admin.admin_export_handlers import export_router

# Создаем общий роутер для администраторов
admin_router = Router()

# Включаем все подроутеры в основной роутер администратора
admin_router.include_router(basic_router)
admin_router.include_router(language_router)
admin_router.include_router(word_router)
admin_router.include_router(upload_router)
admin_router.include_router(export_router)

def register_handlers(dp: Dispatcher):
    """
    Register all admin handlers.
    
    Args:
        dp: The dispatcher instance
    """
    # Для aiogram 3.x используем include_router
    dp.include_router(admin_router)