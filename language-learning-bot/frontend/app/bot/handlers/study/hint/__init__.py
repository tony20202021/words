"""
Hint handlers package for study process.
Contains handlers for hint creation, viewing, editing and toggling.
"""

from app.bot.handlers.study.hint.create_handlers import create_router
from app.bot.handlers.study.hint.edit_handlers import edit_router
from app.bot.handlers.study.hint.toggle_handlers import toggle_router


__all__ = [
    'create_router',
    'edit_router',
    'toggle_router',
]