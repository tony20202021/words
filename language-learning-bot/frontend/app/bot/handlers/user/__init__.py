"""
User handlers package module.
This package contains all user-related handlers.
"""

from app.bot.handlers.user.basic_handlers import basic_router
from app.bot.handlers.user.settings_handlers import settings_router
from app.bot.handlers.user.help_handlers import help_router
from app.bot.handlers.user.stats_handlers import stats_router
from app.bot.handlers.user.hint_handlers import hint_router

__all__ = [
    'basic_router',
    'settings_router',
    'help_router',
    'stats_router',
    'hint_router',
]