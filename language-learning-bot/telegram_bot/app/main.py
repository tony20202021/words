import asyncio
import logging
import os

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand

from app.bls_client.client import get_bls_client
from app.bot.middleware import UserMiddleware
from app.bot.handlers import start, study, auth, help, stats, settings, admin as admin_handler, hints

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
logging.basicConfig(level=logging.INFO)


async def main() -> None:
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN env var is not set")

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    bls = get_bls_client()

    dp.update.middleware(UserMiddleware(bls))

    dp.include_router(auth.router)
    dp.include_router(hints.router)   # before study so hint: callbacks don't fall to study:
    dp.include_router(start.router)
    dp.include_router(study.router)
    dp.include_router(admin_handler.router)
    dp.include_router(help.router)
    dp.include_router(stats.router)
    dp.include_router(settings.router)

    await bot.delete_webhook(drop_pending_updates=True)
    await bot.set_my_commands([
        BotCommand(command="start",           description="Главное меню"),
        BotCommand(command="study",           description="Продолжить изучение"),
        BotCommand(command="restart",         description="Начать заново (сброс сессии)"),
        BotCommand(command="language",        description="Сменить язык"),
        BotCommand(command="stats",           description="Статистика"),
        BotCommand(command="web",             description="Открыть веб-версию"),
        BotCommand(command="android",         description="Скачать Android-приложение"),
        BotCommand(command="connect_android", description="Код для входа в Android-приложение"),
        BotCommand(command="help",            description="Помощь"),
    ])
    logging.info("Bot started")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
