from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from app.bls_client.client import get_bls_client

router = Router()

_BOT_COMMANDS = (
    "\n\n<b>Команды бота:</b>\n"
    "/study — начать изучение\n"
    "/language — сменить язык\n"
    "/settings — настройки\n"
    "/stats — статистика\n"
    "/web — веб-версия\n"
    "/android — Android-приложение\n"
    "/help — эта справка"
)


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    bls = get_bls_client()
    data = await bls.get_help()
    text = data.get("text", "Справка недоступна.") + _BOT_COMMANDS
    await message.answer(text, parse_mode="HTML")
