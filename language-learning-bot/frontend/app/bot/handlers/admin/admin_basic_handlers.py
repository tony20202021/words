"""
Basic admin handlers for common commands like /admin and /stats.
Updated with FSM states for better navigation control.
"""

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from app.utils.api_utils import get_api_client_from_bot
from app.utils.logger import setup_logger
from app.bot.keyboards.admin_keyboards import get_admin_keyboard
from app.bot.handlers.admin.admin_language_handlers import cmd_manage_languages
from app.bot.handlers.admin.admin_language_handlers import handle_language_management
from app.utils.callback_constants import CallbackData
from app.bot.states.centralized_states import AdminStates

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
    await state.set_state(AdminStates.main_menu)  # ✅ НОВОЕ: Устанавливаем состояние главного меню
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
        "Доступные функции:\n"
        "👨‍💼 Управление языками - создание, редактирование, загрузка слов\n"
        "👥 Управление пользователями - просмотр, права администратора\n"
        "📊 Статистика - общая статистика системы\n"
        "⬅️ Выход - возврат в обычный режим",
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

@admin_router.callback_query(AdminStates.main_menu, F.data == CallbackData.BACK_TO_ADMIN)
@admin_router.callback_query(F.data == CallbackData.BACK_TO_ADMIN)
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

@admin_router.callback_query(AdminStates.main_menu, F.data == CallbackData.BACK_TO_START)
@admin_router.callback_query(F.data == CallbackData.BACK_TO_START)
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

@admin_router.callback_query(AdminStates.main_menu, F.data == CallbackData.ADMIN_LANGUAGES)
@admin_router.callback_query(F.data == CallbackData.ADMIN_LANGUAGES)
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
    
    # ✅ НОВОЕ: Устанавливаем состояние просмотра статистики
    await state.set_state(AdminStates.viewing_admin_stats)
    
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

@admin_router.callback_query(AdminStates.main_menu, F.data == CallbackData.ADMIN_STATS_CALLBACK)
@admin_router.callback_query(AdminStates.viewing_admin_stats, F.data == CallbackData.ADMIN_STATS_CALLBACK)
@admin_router.callback_query(F.data == CallbackData.ADMIN_STATS_CALLBACK)
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

@admin_router.callback_query(AdminStates.main_menu, F.data == CallbackData.ADMIN_USERS)
@admin_router.callback_query(AdminStates.viewing_users_list, F.data == CallbackData.ADMIN_USERS)
@admin_router.callback_query(F.data == CallbackData.ADMIN_USERS)
async def process_admin_users(callback: CallbackQuery, state: FSMContext):
    """
    Handle the 'admin_users' callback which shows user management.
    
    Args:
        callback: The callback query from Telegram
        state: The FSM state context
    """
    user_id = callback.from_user.id
    username = callback.from_user.username
    full_name = callback.from_user.full_name

    logger.info(f"'admin_users' callback from {full_name} ({username})")
    
    # Вызываем общую функцию для обработки
    success = await handle_user_management(callback, state, is_callback=True)
    
    # Отвечаем на callback
    await callback.answer()


@admin_router.callback_query(AdminStates.viewing_users_list, F.data.startswith("users_page_"))
@admin_router.callback_query(F.data.startswith("users_page_"))
async def process_users_page(callback: CallbackQuery, state: FSMContext):
    """
    Handle pagination for users list.
    
    Args:
        callback: The callback query from Telegram
        state: The FSM state context
    """
    # Извлекаем номер страницы
    page = int(callback.data.split("_")[-1])
    
    logger.info(f"Users page {page} requested")
    
    # Вызываем функцию управления пользователями с указанной страницей
    await handle_user_management(callback, state, is_callback=True, page=page)
    
    await callback.answer()


@admin_router.callback_query(AdminStates.viewing_users_list, F.data.startswith("view_user_"))
@admin_router.callback_query(AdminStates.viewing_user_details, F.data.startswith("view_user_"))
@admin_router.callback_query(F.data.startswith("view_user_"))
async def process_view_user(callback: CallbackQuery, state: FSMContext):
    """
    Handle viewing detailed user information.
    
    Args:
        callback: The callback query from Telegram
        state: The FSM state context
    """
    # Извлекаем ID пользователя
    user_id = callback.data.split("_")[-1]
    
    logger.info(f"View user {user_id} requested")
    
    # Вызываем функцию для отображения детальной информации о пользователе
    await show_user_details(callback, state, user_id)
    
    await callback.answer()


@admin_router.callback_query(AdminStates.viewing_user_details, F.data.startswith("user_stats_"))
@admin_router.callback_query(F.data.startswith("user_stats_"))
async def process_user_stats(callback: CallbackQuery, state: FSMContext):
    """
    Handle viewing detailed user statistics.
    
    Args:
        callback: The callback query from Telegram
        state: The FSM state context
    """
    # Извлекаем ID пользователя
    user_id = callback.data.split("_")[-1]
    
    logger.info(f"User stats for {user_id} requested")
    
    # Вызываем функцию для отображения подробной статистики пользователя
    await show_user_statistics(callback, state, user_id)
    
    await callback.answer()


@admin_router.callback_query(AdminStates.viewing_user_details, F.data.startswith("toggle_admin_"))
@admin_router.callback_query(F.data.startswith("toggle_admin_"))
async def process_toggle_admin(callback: CallbackQuery, state: FSMContext):
    """
    Handle toggling admin rights for a user.
    
    Args:
        callback: The callback query from Telegram
        state: The FSM state context
    """
    # Извлекаем ID пользователя
    user_id = callback.data.split("_")[-1]
    
    logger.info(f"Toggle admin rights for {user_id} requested")
    
    # ✅ НОВОЕ: Устанавливаем состояние подтверждения изменения прав
    await state.set_state(AdminStates.confirming_admin_rights_change)
    
    # Вызываем функцию для изменения прав администратора
    await toggle_user_admin_rights(callback, state, user_id)
    
    await callback.answer()


@admin_router.callback_query(F.data == CallbackData.PAGE_INFO)
async def process_page_info(callback: CallbackQuery, state: FSMContext):
    """
    Handle page info button (does nothing, just answers callback).
    
    Args:
        callback: The callback query from Telegram
        state: The FSM state context
    """
    await callback.answer("Информация о текущей странице")


async def handle_user_management(message_or_callback, state: FSMContext, is_callback=False, page=0):
    """
    Common handler logic for user management.
    
    Args:
        message_or_callback: The message or callback object from Telegram
        state: The FSM state context
        is_callback: Whether this is called from a callback handler
        page: Page number for pagination (default: 0)
    """
    if is_callback:
        user_id = message_or_callback.from_user.id
        username = message_or_callback.from_user.username
        full_name = message_or_callback.from_user.full_name
        message = message_or_callback.message
    else:
        user_id = message_or_callback.from_user.id
        username = message_or_callback.from_user.username
        full_name = message_or_callback.from_user.full_name
        message = message_or_callback

    logger.info(f"User management requested by {full_name} ({username})")
    
    # ✅ НОВОЕ: Устанавливаем состояние просмотра списка пользователей
    await state.set_state(AdminStates.viewing_users_list)
    
    # Получаем клиент API
    api_client = get_api_client_from_bot(message.bot)
    
    # Проверяем права администратора
    user_response = await api_client.get_user_by_telegram_id(user_id)
    
    if not user_response["success"]:
        error_msg = user_response.get("error", "Неизвестная ошибка")
        await message.answer(f"Ошибка при получении данных пользователя: {error_msg}")
        logger.error(f"Failed to get user data. Error: {error_msg}")
        return
    
    users = user_response["result"]
    user = users[0] if users and isinstance(users, list) and len(users) > 0 else None
    
    if not user or not user.get("is_admin", False):
        await message.answer("У вас нет прав администратора.")
        return
    
    # Получаем список всех пользователей
    all_users_response = await api_client.get_users(skip=0, limit=1000)  # Получаем много пользователей
    
    if not all_users_response["success"]:
        error_msg = all_users_response.get("error", "Неизвестная ошибка")
        await message.answer(f"Ошибка при получении списка пользователей: {error_msg}")
        logger.error(f"Failed to get users list. Error: {error_msg}")
        return
    
    all_users = all_users_response["result"] or []
    
    # Заголовок сообщения
    message_text = "👥 Управление пользователями\n\n"
    
    if all_users:
        total_users = len(all_users)
        admins_count = sum(1 for u in all_users if u.get("is_admin", False))
        
        message_text += f"📈 Всего пользователей: {total_users}\n"
        message_text += f"👑 Администраторов: {admins_count}\n"
        message_text += f"👤 Обычных пользователей: {total_users - admins_count}\n\n"
        message_text += "Выберите пользователя для просмотра:"
        
        # Используем функцию для создания клавиатуры с пагинацией
        from app.bot.keyboards.admin_keyboards import get_users_keyboard
        keyboard = get_users_keyboard(all_users, page=page)
        
        # Редактируем сообщение, если это callback
        if is_callback:
            try:
                await message.edit_text(message_text, reply_markup=keyboard)
            except Exception as e:
                logger.error(f"Error editing message: {e}")
                # Если не удалось отредактировать, отправляем новое
                await message.answer(message_text, reply_markup=keyboard)
        else:
            await message.answer(message_text, reply_markup=keyboard)
    else:
        message_text += "В системе пока нет зарегистрированных пользователей."
        await message.answer(message_text)
    
    return True

async def show_user_details(callback: CallbackQuery, state: FSMContext, user_id: str):
    """
    Show detailed information about a specific user.
    
    Args:
        callback: The callback query from Telegram
        state: The FSM state context
        user_id: ID of the user to show details for
    """
    # ✅ НОВОЕ: Устанавливаем состояние просмотра деталей пользователя
    await state.set_state(AdminStates.viewing_user_details)
    
    api_client = get_api_client_from_bot(callback.bot)
    
    # Получаем информацию о пользователе
    user_response = await api_client.get_users(skip=0, limit=1000)
    
    if not user_response["success"]:
        await callback.message.answer("Ошибка при получении данных пользователя")
        return
    
    all_users = user_response["result"] or []
    user = None
    
    # Находим нужного пользователя
    for u in all_users:
        if u.get('_id') == user_id or u.get('id') == user_id:
            user = u
            break
    
    if not user:
        await callback.message.answer("Пользователь не найден")
        return
    
    # Получаем список языков для проверки статистики
    languages_response = await api_client.get_languages()
    languages = languages_response["result"] if languages_response["success"] else []
    
    # Собираем информацию о статистике пользователя по языкам
    language_stats = []
    
    for language in languages:
        lang_id = language.get('_id', language.get('id'))
        progress_response = await api_client.get_user_progress(user_id, lang_id)
        
        if progress_response["success"] and progress_response["result"]:
            progress = progress_response["result"]
            words_studied = progress.get('words_studied', 0)
            
            # ИСПРАВЛЕНО: Показываем только языки, где есть статистика (изучено > 0 слов)
            if words_studied > 0:
                language_stats.append({
                    'name': f"{language['name_ru']} ({language['name_foreign']})",
                    'words_studied': words_studied,
                    'words_known': progress.get('words_known', 0),
                    'total_words': progress.get('total_words', 0),
                    'progress_percentage': progress.get('progress_percentage', 0)
                })
    
    # Формируем сообщение с информацией о пользователе
    user_info = f"👤 <b>Информация о пользователе</b>\n\n"
    user_info += f"ID: <code>{user_id}</code>\n"
    user_info += f"Telegram ID: <code>{user.get('telegram_id', 'N/A')}</code>\n"
    user_info += f"Имя: <b>{user.get('first_name', 'Не указано')}</b>\n"
    
    if user.get('last_name'):
        user_info += f"Фамилия: <b>{user.get('last_name')}</b>\n"
    
    if user.get('username'):
        user_info += f"Username: <b>@{user.get('username')}</b>\n"
    
    user_info += f"Администратор: <b>{'Да' if user.get('is_admin', False) else 'Нет'}</b>\n"
    
    # Даты регистрации и обновления
    if user.get('created_at'):
        from app.utils.formatting_utils import format_date_standard
        created_date = format_date_standard(user.get('created_at'))
        user_info += f"Дата регистрации: <b>{created_date}</b>\n"
    
    # Статистика по языкам - ИСПРАВЛЕНО: показываем только если есть изученные языки
    if language_stats:
        user_info += f"\n📊 <b>Статистика изучения:</b>\n"
        for stat in language_stats:
            user_info += f"\n• {stat['name']}:\n"
            user_info += f"  Изучено слов: {stat['words_studied']}\n"  
            user_info += f"  Известно слов: {stat['words_known']}\n"
            user_info += f"  Всего слов: {stat['total_words']}\n"
            user_info += f"  Прогресс: {stat['progress_percentage']:.1f}%\n"
    else:
        user_info += f"\n📊 Пользователь еще не начинал изучение языков"
    
    # Создаем клавиатуру
    from app.bot.keyboards.admin_keyboards import get_user_detail_keyboard
    keyboard = get_user_detail_keyboard(user_id)
    
    await callback.message.edit_text(
        user_info,
        parse_mode="HTML",
        reply_markup=keyboard
    )

async def show_user_statistics(callback: CallbackQuery, state: FSMContext, user_id: str):
    """
    Show detailed statistics for a specific user.
    
    Args:
        callback: The callback query from Telegram
        state: The FSM state context
        user_id: ID of the user to show statistics for
    """
    api_client = get_api_client_from_bot(callback.bot)
    
    # Получаем информацию о пользователе для отображения имени
    user_response = await api_client.get_users(skip=0, limit=1000)
    user = None
    
    if user_response["success"]:
        all_users = user_response["result"] or []
        for u in all_users:
            if u.get('_id') == user_id or u.get('id') == user_id:
                user = u
                break
    
    user_name = "Неизвестный пользователь"
    if user:
        user_name = user.get('first_name', 'Без имени')
        if user.get('username'):
            user_name += f" (@{user.get('username')})"
    
    # Получаем подробную статистику
    languages_response = await api_client.get_languages()
    languages = languages_response["result"] if languages_response["success"] else []
    
    stats_text = f"📈 <b>Подробная статистика</b>\n"
    stats_text += f"Пользователь: <b>{user_name}</b>\n\n"
    
    total_studied = 0
    total_known = 0
    total_available = 0
    
    for language in languages:
        lang_id = language.get('_id', language.get('id'))
        progress_response = await api_client.get_user_progress(user_id, lang_id)
        
        if progress_response["success"] and progress_response["result"]:
            progress = progress_response["result"]
            
            words_studied = progress.get('words_studied', 0)
            words_known = progress.get('words_known', 0)
            total_words = progress.get('total_words', 0)
            progress_percentage = progress.get('progress_percentage', 0)
            
            if words_studied > 0:  # Показываем только языки, которые изучались
                stats_text += f"🌍 <b>{language['name_ru']} ({language['name_foreign']})</b>\n"
                stats_text += f"  📚 Изучено слов: {words_studied}\n"
                stats_text += f"  ✅ Известно слов: {words_known}\n"
                stats_text += f"  📖 Всего доступно: {total_words}\n"
                stats_text += f"  📊 Прогресс: {progress_percentage:.1f}%\n\n"
                
                total_studied += words_studied
                total_known += words_known
                total_available += total_words
    
    if total_studied > 0:
        overall_progress = (total_studied / total_available * 100) if total_available > 0 else 0
        stats_text += f"🎯 <b>Общая статистика:</b>\n"
        stats_text += f"  📚 Всего изучено: {total_studied}\n"
        stats_text += f"  ✅ Всего известно: {total_known}\n"
        stats_text += f"  📖 Всего доступно: {total_available}\n"
        stats_text += f"  📊 Общий прогресс: {overall_progress:.1f}%\n"
    else:
        stats_text += "Пользователь еще не начинал изучение языков."
    
    # Создаем клавиатуру для возврата
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад к пользователю", callback_data=f"view_user_{user_id}")]
    ])
    
    await callback.message.edit_text(
        stats_text,
        parse_mode="HTML",
        reply_markup=keyboard
    )


async def toggle_user_admin_rights(callback: CallbackQuery, state: FSMContext, user_id: str):
    """
    Toggle admin rights for a specific user.
    
    Args:
        callback: The callback query from Telegram
        state: The FSM state context
        user_id: ID of the user to toggle admin rights for
    """
    api_client = get_api_client_from_bot(callback.bot)
    
    # Получаем текущую информацию о пользователе
    user_response = await api_client.get_users(skip=0, limit=1000)
    user = None
    
    if user_response["success"]:
        all_users = user_response["result"] or []
        for u in all_users:
            if u.get('_id') == user_id or u.get('id') == user_id:
                user = u
                break
    
    if not user:
        await callback.message.answer("Пользователь не найден")
        return
    
    # Получаем текущий статус администратора
    current_admin_status = user.get('is_admin', False)
    new_admin_status = not current_admin_status
    
    # Обновляем статус пользователя
    update_data = {"is_admin": new_admin_status}
    update_response = await api_client.update_user(user_id, update_data)
    
    if not update_response["success"]:
        error_msg = update_response.get("error", "Неизвестная ошибка")
        await callback.message.answer(f"Ошибка при обновлении прав: {error_msg}")
        return
    
    # Формируем сообщение об успешном изменении
    user_name = user.get('first_name', 'Пользователь')
    if user.get('username'):
        user_name += f" (@{user.get('username')})"
    
    action = "получил права" if new_admin_status else "лишен прав"
    status_text = "администратором" if new_admin_status else "обычным пользователем"
    
    success_message = f"✅ {user_name} {action} администратора и теперь является {status_text}."
    
    await callback.message.answer(success_message)
    
    # Возвращаемся к детальному просмотру пользователя
    await show_user_details(callback, state, user_id)

@admin_router.message(Command("users"))
async def cmd_manage_users(message: Message, state: FSMContext):
    """
    Handle the /users command which shows user management.
    
    Args:
        message: The message object from Telegram
        state: The FSM state context
    """
    user_id = message.from_user.id
    username = message.from_user.username
    full_name = message.from_user.first_name

    logger.info(f"'/users' command from {full_name} ({username})")
    
    # Вызываем общую функцию для обработки
    await handle_user_management(message, state)
    