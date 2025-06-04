"""
Main user handlers router for Language Learning Bot.
This module only handles router organization - no handler implementations.
FIXED: Corrected import paths and router organization.
"""

from aiogram import Router

from app.utils.logger import setup_logger

# Import all user sub-routers
from app.bot.handlers.user.basic_handlers import basic_router
from app.bot.handlers.user.settings_handlers import settings_router
from app.bot.handlers.user.help_handlers import help_router
from app.bot.handlers.user.stats_handlers import stats_router
from app.bot.handlers.user.hint_handlers import hint_router

# Create main user router
user_router = Router()

# Set up logging
logger = setup_logger(__name__)

user_router.include_router(basic_router)
user_router.include_router(settings_router)
user_router.include_router(help_router)
user_router.include_router(stats_router)
user_router.include_router(hint_router)

def register_user_handlers(dp):
    """
    Register user handlers with dispatcher.
    
    Args:
        dp: Dispatcher instance
    """
    dp.include_router(user_router)
    logger.info("User handlers registered with dispatcher")

# Export router and utility functions for use in parent modules
__all__ = [
    'user_router', 
    'register_user_handlers',
]
