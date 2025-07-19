"""
handlers for unknown commands and callbacks
"""

from aiogram import Router
from aiogram.types import Message, CallbackQuery
from aiogram import F

from app.utils.logger import setup_logger

logger = setup_logger(__name__)

unknown_router = Router()


@unknown_router.message(F.text.startswith("/"))
async def cmd_unknown_command(message: Message):
    await message.answer("Произошла ошибка. Возможно, сервис был перезапущен. Попробуйте начать сессию заново по команде /start.")


@unknown_router.message()
async def fallback_message(message: Message):
    await message.answer("Произошла ошибка. Возможно, сервис был перезапущен. Попробуйте начать сессию заново по команде /start.")


@unknown_router.callback_query()
async def fallback_callback(callback: CallbackQuery):
    await callback.message.answer("Произошла ошибка. Возможно, сервис был перезапущен. Попробуйте начать сессию заново по команде /start.")


def register_unknown_handlers(dp):
    """
    Register all unknown handlers with the dispatcher.
    
    Args:
        dp: Dispatcher instance
    """
    dp.include_router(unknown_router)
    logger.info("Unknown handlers registered successfully")
    