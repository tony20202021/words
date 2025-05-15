"""
Handlers for file upload in administrative mode.
"""

from aiogram import Router
from app.utils.logger import setup_logger

# Импортируем все роутеры из подмодуля file_upload
from app.bot.handlers.admin.file_upload import (
    language_router,
    file_router,
    column_router,
    column_type_router,
    settings_router,
    template_router
)

# Создаем основной роутер для обработчиков загрузки файлов
upload_router = Router()

logger = setup_logger(__name__)

# Включаем все подроутеры в основной роутер
upload_router.include_router(file_router)       # Содержит команду /upload и обработку файла
upload_router.include_router(language_router)   # Выбор языка для загрузки
upload_router.include_router(column_router)     # Конфигурация колонок и загрузка
upload_router.include_router(column_type_router)  # Выбор типа колонки и ввод номера
upload_router.include_router(settings_router)   # Управление настройками загрузки
upload_router.include_router(template_router)   # Шаблоны колонок и возврат в админку