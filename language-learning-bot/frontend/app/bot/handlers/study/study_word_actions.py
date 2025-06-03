"""
Study word actions handlers for Language Learning Bot.
"""

from aiogram import Router

from app.utils.logger import setup_logger
from app.bot.handlers.study.word_actions.word_display_actions import display_router
from app.bot.handlers.study.word_actions.word_evaluation_actions import evaluation_router
from app.bot.handlers.study.word_actions.word_navigation_actions import navigation_router
from app.bot.handlers.study.word_actions.word_utility_actions import utility_router

# Создаем роутер для действий со словами
word_actions_router = Router()

logger = setup_logger(__name__)

word_actions_router.include_router(display_router)
word_actions_router.include_router(evaluation_router)
word_actions_router.include_router(navigation_router)
word_actions_router.include_router(utility_router)

def register_study_handlers(dp):
    """
    Register study handlers with dispatcher.
    
    Args:
        dp: Dispatcher instance
    """
    dp.include_router(word_actions_router)
    logger.info("word_actions handlers registered with dispatcher")
