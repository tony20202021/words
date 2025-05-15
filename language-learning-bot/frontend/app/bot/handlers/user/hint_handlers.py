"""
Hint information command handlers for Language Learning Bot.
"""

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from app.utils.api_utils import get_api_client_from_bot
from app.utils.logger import setup_logger

# Создаем роутер для обработчиков подсказок
hint_router = Router()

# Set up logging
logger = setup_logger(__name__)

@hint_router.message(Command("hint"))
async def cmd_hint(message: Message, state: FSMContext):
    """
    Handle the /hint command which provides information about hint functionality.
    
    Args:
        message: The message object from Telegram
        state: The FSM state context
    """
    # Сначала очищаем состояние для предотвращения конфликтов
    # Но в данном случае мы хотим сохранить данные пользователя
    current_data = await state.get_data()
    await state.set_state(None)
    await state.update_data(**current_data)
    
    user_id = message.from_user.id
    username = message.from_user.username
    full_name = message.from_user.full_name

    logger.info(f"'/hint' command from {full_name} ({username})")
    
    # Получаем клиент API с помощью утилиты
    api_client = get_api_client_from_bot(message.bot)
    
    # Получение данных состояния
    user_data = await state.get_data()
    logger.debug("User data: %s", user_data)
    
    # Получаем данные пользователя из API
    user_response = await api_client.get_user_by_telegram_id(user_id)
    
    # Если пользователь не найден, создаем его
    if not user_response["success"]:
        logger.error(f"Failed to get user with Telegram ID {user_id}: {user_response['error']}")
        await message.answer("Ошибка при получении данных пользователя. Попробуйте позже.")
        return
    
    users = user_response["result"]
    user = users[0] if users and len(users) > 0 else None
    
    if not user:
        user_data = {
            "telegram_id": user_id,
            "username": username,
            "first_name": message.from_user.first_name,
            "last_name": message.from_user.last_name
        }
        create_response = await api_client.create_user(user_data)
        if not create_response["success"]:
            logger.error(f"Failed to create user with Telegram ID {user_id}: {create_response['error']}")
            await message.answer("Ошибка при регистрации пользователя. Попробуйте позже.")
            return
    
    await message.answer(
        "🔍 Подсказки помогают вам запоминать слова!\n\n"
        "Вы можете создавать различные типы подсказок:\n"
        "- Фонетическое разложение на слоги (фонетика)\n"
        "- Ассоциации (ассоциация)\n"
        "- Значение слова на русском (значение)\n"
        "- Подсказка по написанию (написание)\n\n"
        "Во время изучения слов вы увидите кнопки для создания подсказок. "
        "После создания подсказки вы сможете использовать её при повторении слова.\n\n"
        "❗️ Помните: использование подсказки автоматически устанавливает оценку 0 "
        "для этого слова, и оно будет показано для повторения через 1 день."
    )