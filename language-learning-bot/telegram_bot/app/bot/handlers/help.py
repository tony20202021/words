from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

router = Router()

HELP_TEXT = (
    "📚 <b>Справка по боту</b>\n\n"
    "<b>Основные команды:</b>\n"
    "/start — главное меню, выбор языка\n"
    "/language — выбрать язык для изучения\n"
    "/study — начать изучение слов\n"
    "/settings — настройки процесса обучения\n"
    "/stats — статистика по текущему языку\n"
    "/web — открыть веб-версию\n"
    "/help — эта справка\n\n"
    "<b>Процесс изучения:</b>\n"
    "1. Выберите язык командой /language\n"
    "2. Начните изучение командой /study\n"
    "3. Для каждого слова:\n"
    "   • <b>Знаю</b> — слово запомнено, интервал повторения увеличивается вдвое\n"
    "   • <b>Не знаю</b> — интервал сбрасывается до 1 дня\n"
    "   • <b>Пропустить</b> — пометить слово для пропуска\n\n"
    "<b>Интервальное повторение:</b>\n"
    "Интервалы: 1 → 2 → 4 → 8 → 16 → 32 дня\n\n"
    "<b>Веб-версия:</b> /web"
)


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(HELP_TEXT, parse_mode="HTML")
