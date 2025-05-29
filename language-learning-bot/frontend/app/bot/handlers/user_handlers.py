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
from app.bot.handlers.user.cancel_handlers import cancel_router  # FIXED: Corrected import

# Create main user router
user_router = Router()

# Set up logging
logger = setup_logger(__name__)

# Include sub-routers in correct priority order
# IMPORTANT: Order matters for handler processing!

# 1. Cancel handlers have highest priority (handle /cancel in any state)
user_router.include_router(cancel_router)

# 2. Basic handlers (start, main menu) - high priority for core commands
user_router.include_router(basic_router)

# 3. Settings handlers (with individual hint settings) - medium priority
user_router.include_router(settings_router)

# 4. Information handlers - lower priority as they're less frequently used
user_router.include_router(help_router)
user_router.include_router(stats_router)
user_router.include_router(hint_router)

logger.info("User handlers router initialized with sub-routers in priority order")
logger.info(f"Router hierarchy: cancel -> basic -> settings -> help -> stats -> hint")

def register_user_handlers(dp):
    """
    Register user handlers with dispatcher.
    
    Args:
        dp: Dispatcher instance
    """
    dp.include_router(user_router)
    logger.info("User handlers registered with dispatcher")

def get_router_info():
    """
    Get information about the user router structure for debugging.
    
    Returns:
        dict: Router structure information
    """
    return {
        "main_router": "user_router",
        "sub_routers": [
            "cancel_router (priority: highest)",
            "basic_router (priority: high)", 
            "settings_router (priority: medium)",
            "help_router (priority: low)",
            "stats_router (priority: low)",
            "hint_router (priority: low)"
        ],
        "total_routers": 6
    }

# Export router and utility functions for use in parent modules
__all__ = [
    'user_router', 
    'register_user_handlers',
    'get_router_info'
]
