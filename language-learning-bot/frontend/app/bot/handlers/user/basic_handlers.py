"""
Basic user command handlers for Language Learning Bot.
Handles start, help, and other basic commands.
"""

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from app.utils.api_utils import get_api_client_from_bot
from app.utils.logger import setup_logger
from app.utils.error_utils import handle_api_error

# Создаем роутер для базовых обработчиков
basic_router = Router()

# Set up logging
logger = setup_logger(__name__)

async def handle_start_command(message, state: FSMContext, user_id=None, username=None, full_name=None, is_callback=False):
    """
    Common handler logic for start command.
    
    Args:
        message: The message object from Telegram (или callback.message при is_callback=True)
        state: The FSM state context
        user_id: User ID (опционально, если вызов из callback)
        username: Username (опционально, если вызов из callback)
        full_name: Full name (опционально, если вызов из callback)
        is_callback: Whether this is called from a callback handler
    """
    # Сначала очищаем состояние для предотвращения конфликтов
    await state.clear()

    # Используем либо переданные данные пользователя, либо берем из message
    if not user_id:
        user_id = message.from_user.id
    if not username:
        username = message.from_user.username
    if not full_name:
        full_name = message.from_user.first_name
    
    logger.info(f"Start command handler for {full_name} ({username})")

    # Получаем клиент API с помощью утилиты
    api_client = get_api_client_from_bot(message.bot)
    
    # Проверяем доступность API клиента
    if api_client is None:
        await message.answer(
            "⚠️ Не удалось установить соединение с сервером. "
            "Бот может работать некорректно. Пожалуйста, попробуйте позже или "
            "обратитесь к администратору."
        )
        logger.error(f"API client not available during start command from {full_name} ({username})")
        return
    
    # Получение данных состояния
    user_data = await state.get_data()
    logger.debug("User data: %s", user_data)

    # Формируем базовое приветственное сообщение, которое отправим в любом случае
    welcome_message = (
        f"👋 Здравствуйте, {full_name}!\n\n"
        f"Добро пожаловать в бот для изучения иностранных слов!\n\n"
    )

    # Получаем информацию о пользователе
    user_response = await api_client.get_user_by_telegram_id(user_id)
    
    # Проверяем успешность запроса
    if not user_response["success"]:
        error_msg = user_response.get("error", "Неизвестная ошибка")
        welcome_message += (
            f"⚠️ Не удалось получить данные с сервера.\n"
            f"Причина: {error_msg}\n\n"
            f"Функциональность бота ограничена. Попробуйте позже или обратитесь к администратору.\n"
            f"Вы можете воспользоваться справкой: /help"
        )
        await message.answer(welcome_message)
        logger.error(f"Failed to get user data during start command. Error: {error_msg}")
        return

    # Получаем пользователя из ответа
    users = user_response["result"]
    user = users[0] if users and isinstance(users, list) and len(users) > 0 else None

    # Создаем пользователя, если он не найден
    db_user_id = None
    if not user:
        # Создаем нового пользователя
        new_user_data = {
            "telegram_id": user_id,
            "username": username,
            "first_name": message.from_user.first_name if not is_callback else full_name,
            "last_name": message.from_user.last_name if not is_callback else None
        }
        
        create_response = await api_client.create_user(new_user_data)
        
        if not create_response["success"]:
            error_msg = create_response.get("error", "Неизвестная ошибка")
            welcome_message += (
                f"⚠️ Не удалось создать пользователя.\n"
                f"Причина: {error_msg}\n\n"
                f"Пожалуйста, попробуйте позже или обратитесь к администратору."
            )
            await message.answer(welcome_message)
            logger.error(f"Failed to create user during start command. Error: {error_msg}")
            return
            
        created_user = create_response["result"]
        db_user_id = created_user.get("id") if created_user else None
    else:
        # Пользователь найден
        db_user_id = user.get("id")
    
    # Получаем список языков из API
    languages_response = await api_client.get_languages()
    
    if not languages_response["success"]:
        error_msg = languages_response.get("error", "Неизвестная ошибка")
        welcome_message += (
            f"⚠️ Не удалось получить список языков.\n"
            f"Причина: {error_msg}\n\n"
            f"Пожалуйста, попробуйте позже."
        )
        await message.answer(welcome_message)
        logger.error(f"Failed to get languages during start command. Error: {error_msg}")
        return
    
    languages = languages_response["result"] or []
    
    # Дополняем приветственное сообщение информацией о языках
    if languages:
        welcome_message += f"🌍 В системе доступно {len(languages)} языков для изучения.\n\n"
    else:
        welcome_message += "🌍 В системе пока нет доступных языков. Обратитесь к администратору.\n\n"
    
    # Если у пользователя уже есть ID в базе данных, получаем его статистику
    if db_user_id:
        # Сохраняем ID пользователя в состоянии
        await state.update_data(db_user_id=db_user_id)
        
        # Собираем статистику по всем языкам
        user_progress_by_language = []
        
        for language in languages:
            # Получаем прогресс пользователя для конкретного языка
            try:
                progress_response = await api_client.get_user_progress(db_user_id, language.get("id"))
                
                if progress_response["success"] and progress_response["result"]:
                    user_progress_by_language.append(progress_response["result"])
            except Exception as e:
                logger.error(f"Error getting progress for language {language.get('id')}: {e}")
        
        if user_progress_by_language:
            welcome_message += "📊 Ваш прогресс по языкам:\n"
            for progress in user_progress_by_language:
                lang_name = progress.get("language_name_ru")
                progress_percentage = progress.get("progress_percentage", 0)
                welcome_message += f"- {lang_name}: {progress_percentage:.1f}%\n"
        else:
            welcome_message += (
                "У вас пока нет прогресса по изучению языков.\n"
                "Начните с выбора языка с помощью команды /language\n"
            )
    else:
        welcome_message += (
            "У вас пока нет прогресса по изучению языков.\n"
            "Начните с выбора языка с помощью команды /language\n"
        )
    
    welcome_message += (
        "\nОсновные команды:\n"
        "/language - Выбрать язык для изучения\n"
        "/study - Начать изучение слов\n"
        "/settings - Настройки процесса обучения\n"
        "/stats - Показать статистику\n"
        "/help - Показать справку"
    )
    
    await message.answer(welcome_message)
    
    return True

@basic_router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    """
    Handle the /start command for new users.
    
    Args:
        message: The message object from Telegram
        state: The FSM state context
    """
    await handle_start_command(message, state)

@basic_router.callback_query(F.data == "back_to_start")
async def process_back_to_main(callback: CallbackQuery, state: FSMContext):
    """
    Process callback to return to the main menu.
    
    Args:
        callback: The callback query from Telegram
        state: The FSM state context
    """
    user_id = callback.from_user.id
    username = callback.from_user.username
    full_name = callback.from_user.full_name

    logger.info(f"'back_to_start' callback from {full_name} ({username})")
    
    # Вызываем общую функцию обработки команды /start
    await handle_start_command(
        callback.message, 
        state, 
        user_id=callback.from_user.id,
        username=callback.from_user.username,
        full_name=callback.from_user.full_name,
        is_callback=True
    )
    
    await callback.answer()