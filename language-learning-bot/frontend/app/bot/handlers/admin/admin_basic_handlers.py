"""
Basic admin handlers for common commands like /admin and /stats.
"""

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from app.utils.api_utils import get_api_client_from_bot
from app.utils.logger import setup_logger
from app.bot.keyboards.admin_keyboards import get_admin_keyboard
from app.bot.handlers.admin.admin_language_handlers import cmd_manage_languages
from app.bot.handlers.admin.admin_language_handlers import handle_language_management

# Создаем роутер для базовых обработчиков администратора
admin_router = Router()

logger = setup_logger(__name__)

async def handle_admin_mode(message_or_callback, state: FSMContext, is_callback=False):
    """
    Common handler logic for admin mode activation.
    
    Args:
        message_or_callback: The message or callback object from Telegram
        state: The FSM state context
        is_callback: Whether this is called from a callback handler
    """
    if is_callback:
        user_id = message_or_callback.from_user.id
        username = message_or_callback.from_user.username
        full_name = message_or_callback.from_user.full_name
        # Для callback используем message из callback
        message = message_or_callback.message
    else:
        user_id = message_or_callback.from_user.id
        username = message_or_callback.from_user.username
        full_name = message_or_callback.from_user.first_name
        # Для обычного message используем сам message
        message = message_or_callback
    
    logger.info(f"Admin mode activation for {full_name} ({username})")
    
    # Сначала очищаем состояние для предотвращения конфликтов
    # Но в данном случае мы хотим сохранить данные пользователя
    current_data = await state.get_data()
    await state.set_state(None)
    await state.update_data(**current_data)
    
    # Получаем клиент API с помощью утилиты
    api_client = get_api_client_from_bot(message.bot)
    
    # Получение данных состояния
    user_data = await state.get_data()
    logger.debug("User data: %s", user_data)
    
    # Получаем информацию о пользователе из API
    user_response = await api_client.get_user_by_telegram_id(user_id)
    
    # Проверяем успешность запроса
    if not user_response["success"]:
        error_msg = user_response.get("error", "Неизвестная ошибка")
        await message.answer(f"Ошибка при получении данных пользователя: {error_msg}")
        logger.error(f"Failed to get user data during admin mode activation. Error: {error_msg}")
        return False
    
    # Получаем пользователя из ответа
    users = user_response["result"]
    user = users[0] if users and isinstance(users, list) and len(users) > 0 else None
    
    # Проверяем, существует ли пользователь и является ли он администратором
    if not user:
        # Пользователь не найден, создаем нового
        user_data = {
            "telegram_id": user_id,
            "username": username,
            "first_name": full_name,
            "last_name": message_or_callback.from_user.last_name if not is_callback else None,
            "is_admin": False  # По умолчанию не администратор
        }
        create_response = await api_client.create_user(user_data)
        
        if not create_response["success"]:
            error_msg = create_response.get("error", "Неизвестная ошибка")
            await message.answer(f"Ошибка при создании пользователя: {error_msg}")
            logger.error(f"Failed to create user during admin mode activation. Error: {error_msg}")
            return False
            
        await message.answer("У вас нет прав администратора.")
        return False
    
    # Проверяем, является ли пользователь администратором
    if not user.get("is_admin", False):
        await message.answer("У вас нет прав администратора.")
        return False
    
    # Используем готовую клавиатуру из admin_keyboards.py
    keyboard = get_admin_keyboard()
    
    await message.answer(
        "✅ Режим администратора активирован!\n\n"
        "Доступные команды:\n"
        "/upload - Загрузить файл со словами\n"
        "/managelang - Управление языками\n"
        "/bot_stats - Статистика использования бота",
        reply_markup=keyboard
    )
    
    return True

@admin_router.message(Command("admin"))
async def cmd_admin(message: Message, state: FSMContext):
    """
    Handle the /admin command which activates admin mode.
    
    Args:
        message: The message object from Telegram
        state: The FSM state context
    """
    user_id = message.from_user.id
    username = message.from_user.username
    full_name = message.from_user.first_name

    logger.info(f"'/admin' command from {full_name} ({username})")
    
    await handle_admin_mode(message, state)

@admin_router.callback_query(F.data == "back_to_admin")
async def process_back_to_admin(callback: CallbackQuery, state: FSMContext):
    """
    Handle the 'back_to_admin' callback which returns to admin mode.
    
    Args:
        callback: The callback query from Telegram
        state: The FSM state context
    """
    user_id = callback.from_user.id
    username = callback.from_user.username
    full_name = callback.from_user.full_name

    logger.info(f"'back_to_admin' callback from {full_name} ({username})")
    
    # Вызываем общую функцию для обработки
    success = await handle_admin_mode(callback, state, is_callback=True)
    
    # Отвечаем на callback
    await callback.answer()

@admin_router.callback_query(F.data == "back_to_start")
async def process_back_to_main(callback: CallbackQuery, state: FSMContext):
    """
    Handle the 'back_to_start' callback which exits admin mode and returns to the main screen.
    
    Args:
        callback: The callback query from Telegram
        state: The FSM state context
    """
    user_id = callback.from_user.id
    username = callback.from_user.username
    full_name = callback.from_user.full_name

    logger.info(f"'back_to_start' callback from {full_name} ({username})")
    
    # Очищаем состояние или сохраняем важные данные
    current_data = await state.get_data()
    important_data = {
        key: current_data[key] 
        for key in ["db_user_id", "current_language"] 
        if key in current_data
    }
    await state.clear()
    await state.update_data(**important_data)
    
    # Сообщение о выходе из режима администратора
    await callback.message.answer("✅ Вы вышли из режима администратора")
    
    # Импортируем функцию для обработки команды start
    from app.bot.handlers.user.basic_handlers import handle_start_command
    
    # Вызываем общую функцию, передавая данные из callback
    await handle_start_command(
        callback.message, 
        state, 
        user_id=user_id, 
        username=username, 
        full_name=full_name,
        is_callback=True
    )
    
    # Отвечаем на callback
    await callback.answer()

@admin_router.callback_query(F.data == "admin_languages")
async def process_admin_languages(callback: CallbackQuery, state: FSMContext):
    """
    Handle the 'admin_languages' callback which redirects to language management.
    
    Args:
        callback: The callback query from Telegram
        state: The FSM state context
    """
    user_id = callback.from_user.id
    username = callback.from_user.username
    full_name = callback.from_user.full_name

    logger.info(f"'admin_languages' callback from {full_name} ({username})")
    
    # Вызываем общую функцию для обработки
    success = await handle_language_management(callback, state, is_callback=True)
    
    # Отвечаем на callback
    await callback.answer()

async def handle_stats(message_or_callback, state: FSMContext, is_callback=False):
    """
    Common handler logic for statistics.
    
    Args:
        message_or_callback: The message or callback object from Telegram
        state: The FSM state context
        is_callback: Whether this is called from a callback handler
    """
    if is_callback:
        user_id = message_or_callback.from_user.id
        username = message_or_callback.from_user.username
        full_name = message_or_callback.from_user.full_name
        # Для callback используем message из callback
        message = message_or_callback.message
    else:
        user_id = message_or_callback.from_user.id
        username = message_or_callback.from_user.username
        full_name = message_or_callback.from_user.full_name
        # Для обычного message используем сам message
        message = message_or_callback

    logger.info(f"Statistics requested by {full_name} ({username})")
    
    # Получаем клиент API с помощью утилиты
    api_client = get_api_client_from_bot(message.bot)
    
    # Проверяем права администратора
    user_response = await api_client.get_user_by_telegram_id(user_id)
    
    # Проверяем успешность запроса
    if not user_response["success"]:
        error_msg = user_response.get("error", "Неизвестная ошибка")
        await message.answer(f"Ошибка при получении данных пользователя: {error_msg}")
        logger.error(f"Failed to get user data. Error: {error_msg}")
        return
    
    # Получаем пользователя из ответа
    users = user_response["result"]
    user = users[0] if users and isinstance(users, list) and len(users) > 0 else None
    
    if not user or not user.get("is_admin", False):
        await message.answer("У вас нет прав администратора.")
        return
    
    # Получаем список языков
    languages_response = await api_client.get_languages()
    
    # Проверяем успешность запроса
    if not languages_response["success"]:
        error_msg = languages_response.get("error", "Неизвестная ошибка")
        await message.answer(f"Ошибка при получении списка языков: {error_msg}")
        logger.error(f"Failed to get languages. Error: {error_msg}")
        return
        
    languages = languages_response["result"] or []
    
    # Получаем всех пользователей для подсчета
    users_response = await api_client.get_users_count()
    print(users_response)
    
    if users_response["success"] and "count" in users_response.get("result", {}):
        total_users = users_response["result"]["count"]
    
    # Для каждого языка получаем статистику по словам
    languages_stats = []
    
    for language in languages:
        # Получаем количество слов для языка через API
        word_count_response = await api_client.get_word_count_by_language(language['id'])
        word_count = word_count_response.get("result", {}).get("count", 0) if word_count_response.get("success") else 0
        
        # Получаем количество активных пользователей для языка
        active_users_response = await api_client.get_language_active_users(language['id'])
        
        if active_users_response["success"] and "count" in active_users_response.get("result", {}):
            active_users = active_users_response["result"]["count"]
        
        languages_stats.append({
            'id': language['id'],
            'name': f"{language['name_ru']} ({language['name_foreign']})",
            'word_count': word_count,
            'active_users': active_users
        })
    
    # Формируем сообщение со статистикой
    stats_message = "📊 Статистика использования бота\n\n"
    stats_message += f"👥 Всего пользователей: {total_users}\n"
    stats_message += f"🔤 Всего языков: {len(languages)}\n\n"
    stats_message += f"🌍 Статистика по языкам:\n"
    
    for lang_stat in languages_stats:
        stats_message += f"- {lang_stat['name']}: {lang_stat['word_count']} слов"
        
        # Если данные о активных пользователях доступны, добавляем их
        if lang_stat['active_users'] != "Нет данных":
            stats_message += f", {lang_stat['active_users']} активных пользователей"
        
        stats_message += "\n"
    
    # Отправляем сообщение со статистикой без клавиатуры
    await message.answer(stats_message)
    
    # Вызываем функцию для отображения административного экрана
    await handle_admin_mode(message_or_callback, state, is_callback=is_callback)
    
    # Возвращаем True, чтобы показать, что обработка прошла успешно
    return True

@admin_router.message(Command("bot_stats"))
async def cmd_bot_stats(message: Message, state: FSMContext):
    """
    Handle the /bot_stats command which shows administrative statistics.
    
    Args:
        message: The message object from Telegram
        state: The FSM state context
    """
    user_id = message.from_user.id
    username = message.from_user.username
    full_name = message.from_user.first_name

    logger.info(f"'/bot_stats' command from {full_name} ({username})")
    
    # Вызываем общую функцию для обработки статистики
    await handle_stats(message, state, is_callback=False)

@admin_router.callback_query(F.data == "admin_stats_callback")
async def process_admin_stats(callback: CallbackQuery, state: FSMContext):
    """
    Handle the 'admin_stats' callback which shows usage statistics.
    
    Args:
        callback: The callback query from Telegram
        state: The FSM state context
    """
    user_id = callback.from_user.id
    username = callback.from_user.username
    full_name = callback.from_user.full_name

    logger.info(f"'admin_stats' callback from {full_name} ({username})")
    
    # Вызываем общую функцию для обработки
    success = await handle_stats(callback, state, is_callback=True)
    
    # Отвечаем на callback
    await callback.answer()