"""
File upload module initialization.
"""

# Экспортируем все роутеры для удобного импорта в основном модуле
from app.bot.handlers.admin.file_upload.language_selection import language_router
from app.bot.handlers.admin.file_upload.file_processing import file_router
from app.bot.handlers.admin.file_upload.column_configuration import column_router
from app.bot.handlers.admin.file_upload.column_type_processing import column_type_router
from app.bot.handlers.admin.file_upload.settings_management import settings_router
from app.bot.handlers.admin.file_upload.template_processing import template_router

__all__ = [
    'language_router',
    'file_router',
    'column_router',
    'column_type_router',
    'settings_router',
    'template_router'
]