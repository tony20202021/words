"""
Study hint handlers router for Language Learning Bot.
This module only handles router organization - no handler implementations.
FIXED: Properly separated router imports from handler implementations.
"""

from aiogram import Router

from app.utils.logger import setup_logger

# Import all hint sub-routers (only routers, no implementations)
from app.bot.handlers.study.hint.create_handlers import create_router
from app.bot.handlers.study.hint.edit_handlers import edit_router
from app.bot.handlers.study.hint.toggle_handlers import toggle_router
from app.bot.handlers.study.hint.common import common_router
from app.bot.handlers.study.hint.unknown import unknown_router

# Create main hint router
hint_router = Router()

# Set up logging
logger = setup_logger(__name__)

hint_router.include_router(common_router)
hint_router.include_router(create_router)
hint_router.include_router(edit_router)
hint_router.include_router(toggle_router)
hint_router.include_router(unknown_router)

logger.info("Hint handlers router initialized with sub-routers")

def register_hint_handlers(dp):
    """
    Register hint handlers with dispatcher.
    
    Args:
        dp: Dispatcher instance
    """
    dp.include_router(hint_router)
    logger.info("Hint handlers registered with dispatcher")

# Export router for use in parent modules
__all__ = ['hint_router', 'register_hint_handlers']
