"""
Utility functions for working with API client in the bot.
"""

import logging
from typing import Optional, Any, Dict, Union

from aiogram import Bot, Dispatcher
from app.api.client import APIClient

# Set up logging
logger = logging.getLogger(__name__)

def store_api_client(bot: Bot, dispatcher: Dispatcher, api_client: APIClient) -> bool:
    """
    Store API client in both dispatcher and bot if possible.
    
    Args:
        bot: Bot instance
        dispatcher: Dispatcher instance
        api_client: API client instance to store
    
    Returns:
        bool: True if API client was stored successfully in both places,
              False if it was stored only in dispatcher
    """
    # Always store in dispatcher
    dispatcher["api_client"] = api_client
    logger.info("API client stored in dispatcher")
    
    # Try to store in bot as attribute
    try:
        # В aiogram 3.x бот не поддерживает словарный доступ, используем setattr
        setattr(bot, "api_client", api_client)
        logger.info("API client stored in bot as attribute")
        return True
    except (TypeError, AttributeError) as e:
        logger.warning(f"Could not store API client in bot object: {e}")
        logger.info("API client will be accessible only through dispatcher")
        return False


def get_api_client_from_bot(bot: Bot) -> Optional[APIClient]:
    """
    Try to get API client from bot or its dispatcher.
    
    Args:
        bot: Bot instance
    
    Returns:
        Optional[APIClient]: API client instance or None if not found
    """
    api_client = None
    
    # Try getting from bot as attribute first
    if hasattr(bot, "api_client"):
        api_client = getattr(bot, "api_client")
        if api_client:
            logger.debug("API client retrieved from bot attribute")
            return api_client
    
    # Try getting from bot dictionary access (for backward compatibility)
    try:
        api_client = bot.get("api_client")
        if api_client:
            logger.debug("API client retrieved from bot object")
            return api_client
    except (TypeError, AttributeError):
        pass
    
    # Try getting from dispatcher if available
    if hasattr(bot, "dispatcher"):
        try:
            api_client = bot.dispatcher.get("api_client")
            if api_client:
                logger.debug("API client retrieved from dispatcher")
                return api_client
        except (TypeError, AttributeError):
            pass
    
    # If not found anywhere
    if not api_client:
        logger.warning("API client not found in bot or dispatcher")
    
    return api_client


def get_api_client_from_dispatcher(dispatcher: Dispatcher) -> Optional[APIClient]:
    """
    Get API client from dispatcher.
    
    Args:
        dispatcher: Dispatcher instance
    
    Returns:
        Optional[APIClient]: API client instance or None if not found
    """
    api_client = dispatcher.get("api_client")
    if not api_client:
        logger.warning("API client not found in dispatcher")
    
    return api_client