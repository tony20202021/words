"""
Help command handlers for Language Learning Bot.
"""

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from app.utils.api_utils import get_api_client_from_bot
from app.utils.logger import setup_logger

# Создаем роутер для справочных обработчиков
help_router = Router()

# Set up logging
logger = setup_logger(__name__)

@help_router.message(Command("help"))
async def cmd_help(message: Message, state: FSMContext):
    """
    Handle the /help command which shows bot instructions.
    
    Args:
        message: The message object from Telegram
        state: The FSM state context
    """
    # Сначала очищаем состояние для предотвращения конфликтов
    await state.clear()

    user_id = message.from_user.id
    username = message.from_user.username
    full_name = message.from_user.full_name

    logger.info(f"'/help' command from {full_name} ({username})")

    # Получаем клиент API с помощью утилиты
    api_client = get_api_client_from_bot(message.bot)
    
    # Получение данных состояния
    user_data = await state.get_data()
    logger.debug("User data: %s", user_data)

    # Проверяем, зарегистрирован ли пользователь
    user_response = await api_client.get_user_by_telegram_id(user_id)
    
    # Обрабатываем результат запроса
    if user_response["success"] and not user_response["result"]:
        # Пользователь не найден, создаем его
        new_user_data = {
            "telegram_id": user_id,
            "username": username,
            "first_name": message.from_user.first_name,
            "last_name": message.from_user.last_name
        }
        await api_client.create_user(new_user_data)

    help_text = (
        "📚 Справка по использованию бота\n\n"
        "Этот бот поможет вам эффективно изучать иностранные слова "
        "с использованием системы интервального повторения.\n\n"
        "🔹 Основные команды:\n"
        "/start - Начать работу с ботом\n"
        "/language - Выбрать язык для изучения\n"
        "/study - Начать изучение слов\n"
        "/settings - Настройки процесса обучения\n"
        "/stats - Показать статистику\n"
        "/hint - Информация о подсказках\n"
        "/cancel - Отмена текущего действия\n\n"  # Добавлена информация о команде /cancel
        "🔹 Процесс изучения:\n"
        "1. Выберите язык командой /language\n"
        "2. Настройте процесс обучения командой /settings\n"
        "3. Начните изучение командой /study\n"
        "4. Для каждого слова вы можете:\n"
        "   - Использовать подсказки\n"
        "   - Отметить слово как изученное\n"
        "   - Пропустить слово\n\n"
        "🔹 Система интервального повторения:\n"
        "- Если вы отметили слово как изученное, его интервал повторения "
        "увеличивается в 2 раза\n"
        "- Интервалы повторения: 1, 2, 4, 8, 16, 32 дня\n"
        "- Если вы не знаете слово, интервал сбрасывается до 1 дня\n\n"
        "Если у вас остались вопросы, обратитесь к администратору бота (@Anton_Mikhalev)."
    )
    
    await message.answer(help_text)