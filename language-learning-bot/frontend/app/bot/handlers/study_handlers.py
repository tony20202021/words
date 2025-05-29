"""
Main study handlers router for Language Learning Bot.
This module only handles router organization - no handler implementations.
FIXED: Properly separated router imports from handler implementations.
"""

from aiogram import Router

from app.utils.logger import setup_logger

# Import all study sub-routers (only routers, no implementations)
from app.bot.handlers.study.study_commands import study_router as commands_router
from app.bot.handlers.study.study_words import word_display_router
from app.bot.handlers.study.study_word_actions import word_actions_router
from app.bot.handlers.study.study_hint_handlers import hint_router

# Create main study router
study_router = Router()

# Set up logging
logger = setup_logger(__name__)

# Include sub-routers in correct priority order
# Commands have highest priority
study_router.include_router(commands_router)

# Word display and actions
study_router.include_router(word_display_router)
study_router.include_router(word_actions_router)

# Hint handlers have lower priority (more specific)
study_router.include_router(hint_router)

logger.info("Study handlers router initialized with sub-routers")

def register_study_handlers(dp):
    """
    Register study handlers with dispatcher.
    
    Args:
        dp: Dispatcher instance
    """
    dp.include_router(study_router)
    logger.info("Study handlers registered with dispatcher")

# Export router for use in parent modules
__all__ = ['study_router', 'register_study_handlers']
