"""
Hint handlers package for study process.
Contains handlers for hint creation, viewing, editing and toggling.
"""

# Экспорт роутеров для включения в основной роутер
from app.bot.handlers.study.hint.create_handlers import create_router
from app.bot.handlers.study.hint.edit_handlers import edit_router
from app.bot.handlers.study.hint.toggle_handlers import toggle_router
from app.bot.handlers.study.hint.common import common_router
from app.bot.handlers.study.hint.unknown import unknown_router

# Экспорт функций для обратной совместимости
from app.bot.handlers.study.hint.create_handlers import process_hint_create, process_hint_text
from app.bot.handlers.study.hint.edit_handlers import process_hint_edit, process_hint_edit_text
from app.bot.handlers.study.hint.toggle_handlers import process_hint_toggle
from app.bot.handlers.study.hint.common import cmd_cancel_hint

__all__ = [
    # Роутеры
    'create_router',
    'edit_router',
    'toggle_router',
    'cancel_router',
    
    # Функции (для обратной совместимости)
    'process_hint_create',
    'process_hint_text',
    'process_hint_edit',
    'process_hint_edit_text',
    'process_hint_toggle',
    'cmd_cancel_hint',
]