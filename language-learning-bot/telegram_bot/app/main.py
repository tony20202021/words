import asyncio
import logging
import os

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from app.bls_client.client import get_bls_client
from app.bot.middleware import UserMiddleware
from app.bot.handlers import start, study, auth, help, stats, settings, admin as admin_handler

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
    dp.include_router(start.router)
    dp.include_router(study.router)
    dp.include_router(admin_handler.router)
    dp.include_router(help.router)
    dp.include_router(stats.router)
    dp.include_router(settings.router)

    await bot.delete_webhook(drop_pending_updates=True)
    logging.info("Bot started")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
