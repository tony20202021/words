"""
Settings command handlers for Language Learning Bot.
Handles all settings-related operations.
"""

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.dispatcher.router import Router
from aiogram.dispatcher.event.bases import SkipHandler
from aiogram.fsm.state import State, StatesGroup

from app.utils.api_utils import get_api_client_from_bot
from app.utils.logger import setup_logger
from app.utils.error_utils import handle_api_error
from app.utils.settings_utils import get_user_language_settings, save_user_language_settings, display_language_settings

# Создаем роутер для обработчиков настроек
settings_router = Router()

# Set up logging
logger = setup_logger(__name__)

# Определение состояний для FSM настроек
class SettingsStates(StatesGroup):
    waiting_start_word = State()  # Ожидание ввода начального слова

@settings_router.message(Command("settings"))
async def cmd_settings(message: Message, state: FSMContext):
    """
    Handle the /settings command which shows and allows changing learning settings.
    If language is not selected, redirects to language selection.
    
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

    logger.info(f"'/settings' command from {full_name} ({username})")

    # Получаем клиент API с помощью утилиты
    api_client = get_api_client_from_bot(message.bot)
    
    # Проверяем, зарегистрирован ли пользователь
    user_response = await api_client.get_user_by_telegram_id(user_id)
    
    db_user_id = None
    if not user_response["success"]:
        logger.error(f"Failed to get user with Telegram ID {user_id}: {user_response['error']}")
        await message.answer("Ошибка при получении данных пользователя. Попробуйте позже.")
        return
        
    users = user_response["result"]
    user = users[0] if users and len(users) > 0 else None
    
    if not user:
        # Пользователь не найден, создаем его
        new_user_data = {
            "telegram_id": user_id,
            "username": username,
            "first_name": message.from_user.first_name,
            "last_name": message.from_user.last_name
        }
        create_response = await api_client.create_user(new_user_data)
        if not create_response["success"]:
            logger.error(f"Failed to create user with Telegram ID {user_id}: {create_response['error']}")
            await message.answer("Ошибка при регистрации пользователя. Попробуйте позже.")
            return
        db_user_id = create_response["result"].get("id") if create_response["result"] else None
    else:
        db_user_id = user.get("id") if user else None
    
    # Сохраняем ID пользователя в базе данных в состоянии
    await state.update_data(db_user_id=db_user_id)
    
    # Проверяем, выбран ли язык
    current_language = current_data.get("current_language")
    
    if not current_language:
        # Если язык не выбран, предлагаем выбрать его сразу
        await message.answer(
            "⚠️ Вы еще не выбрали язык для изучения!\n"
            "Сейчас я помогу вам выбрать язык."
        )
        
        # Переиспользуем существующий обработчик для выбора языка
        from app.bot.handlers.language_handlers import cmd_language
        await cmd_language(message, state)
        return
    
    # Если язык выбран, используем функцию для отображения настроек
    await display_language_settings(message, state)

@settings_router.callback_query(F.data == "settings_toggle_skip_marked")
async def process_settings_toggle_skip_marked(callback: CallbackQuery, state: FSMContext):
    """
    Process callback to toggle skipping marked words.
    
    Args:
        callback: The callback query from Telegram
        state: The FSM state context
    """
    user_id = callback.from_user.id
    username = callback.from_user.username
    full_name = callback.from_user.full_name

    logger.info(f"'settings_toggle_skip_marked' callback from {full_name} ({username})")
    
    # Получаем настройки пользователя с помощью функции
    settings = await get_user_language_settings(callback, state)
    
    # Инвертируем настройку пропуска помеченных слов
    settings["skip_marked"] = not settings.get("skip_marked", False)
    
    # Сохраняем обновленные настройки
    success = await save_user_language_settings(callback, state, settings)
    
    if success:
        # Обновляем состояние FSM для совместимости со старым кодом
        await state.update_data(skip_marked=settings["skip_marked"])
        
        # Используем функцию для отображения настроек
        await display_language_settings(callback, state, 
                                       prefix="✅ Настройки успешно обновлены!\n\n", 
                                       is_callback=True)
    else:
        # В случае ошибки сообщаем пользователю
        await callback.message.answer("❌ Не удалось сохранить настройки. Попробуйте позже.")
    
    await callback.answer()


@settings_router.callback_query(F.data == "settings_toggle_check_date")
async def process_settings_toggle_check_date(callback: CallbackQuery, state: FSMContext):
    """
    Process callback to toggle using check date.
    
    Args:
        callback: The callback query from Telegram
        state: The FSM state context
    """
    user_id = callback.from_user.id
    username = callback.from_user.username
    full_name = callback.from_user.full_name

    logger.info(f"'settings_toggle_check_date' callback from {full_name} ({username})")
    
    # Получаем настройки пользователя с помощью функции
    settings = await get_user_language_settings(callback, state)
    
    # Инвертируем настройку использования даты проверки
    settings["use_check_date"] = not settings.get("use_check_date", True)
    
    # Сохраняем обновленные настройки
    success = await save_user_language_settings(callback, state, settings)
    
    if success:
        # Обновляем состояние FSM для совместимости со старым кодом
        await state.update_data(use_check_date=settings["use_check_date"])
        
        # Используем функцию для отображения настроек
        await display_language_settings(callback, state, 
                                       prefix="✅ Настройки успешно обновлены!\n\n", 
                                       is_callback=True)
    else:
        # В случае ошибки сообщаем пользователю
        await callback.message.answer("❌ Не удалось сохранить настройки. Попробуйте позже.")
    
    await callback.answer()


@settings_router.callback_query(F.data == "settings_start_word")
async def process_settings_start_word(callback: CallbackQuery, state: FSMContext):
    """
    Process callback to change the starting word number.
    
    Args:
        callback: The callback query from Telegram
        state: The FSM state context
    """
    user_id = callback.from_user.id
    username = callback.from_user.username
    full_name = callback.from_user.full_name

    logger.info(f"'settings_start_word' callback from {full_name} ({username})")
    
    # Получаем настройки пользователя с помощью функции
    settings = await get_user_language_settings(callback, state)
    
    # Получаем текущее начальное слово
    current_start_word = settings.get("start_word", 1)
    
    # Переходим в состояние ожидания ввода начального слова
    await state.set_state(SettingsStates.waiting_start_word)
    
    await callback.message.answer(
        f"🔢 Введите номер слова, с которого хотите начать изучение.\n"
        f"Текущее значение: {current_start_word}\n\n"
        f"Введите целое число (например, 1, 10, 100).\n\n"
        f"Для отмены и возврата к настройкам введите команду /cancel"
    )
    
    # Сохраняем сведения о callback чтобы потом проверить изменился ли callback
    await state.update_data(last_callback="settings_start_word")
    
    await callback.answer()


@settings_router.message(SettingsStates.waiting_start_word)
async def process_start_word_input(message: Message, state: FSMContext):
    """
    Process input for starting word number.
    
    Args:
        message: The message object from Telegram
        state: The FSM state context
    """
    user_id = message.from_user.id
    username = message.from_user.username
    full_name = message.from_user.full_name

    # Проверяем, является ли сообщение командой отмены
    if message.text and message.text.strip() == '/cancel':
        logger.info(f"'/cancel' command from {full_name} ({username}) while in start_word input")
        
        # Получаем текущие данные состояния
        current_data = await state.get_data()
        
        # Очищаем состояние, но сохраняем данные
        await state.set_state(None)
        await state.update_data(**current_data)
        
        # Отображаем экран настроек с помощью функции
        await display_language_settings(message, state, prefix="⚙️ Ввод отменен. Настройки процесса обучения\n\n")
        return

    # Добавляем логирование введенного пользователем значения
    logger.info(f"User {full_name} ({username}) entered start_word value: {message.text}")
    
    # Проверяем, что введено число
    try:
        start_word = int(message.text)
        
        if start_word < 1:
            await message.answer(
                "❌ Номер слова должен быть положительным числом.\n"
                "Введите целое число больше 0.\n\n"
                "Для отмены и возврата к настройкам введите команду /cancel"
            )
            return
        
        # Получаем API клиент
        api_client = get_api_client_from_bot(message.bot)
        
        # Получаем данные состояния
        state_data = await state.get_data()
        current_language = state_data.get("current_language")
        
        # Проверка на максимальный номер слова
        if current_language and "id" in current_language:
            language_id = current_language["id"]
            
            # Получаем количество слов в языке
            word_count_response = await api_client.get_word_count_by_language(language_id)
            
            if word_count_response["success"] and "count" in word_count_response["result"]:
                word_count = word_count_response["result"]["count"]
                
                if start_word > word_count:
                    await message.answer(
                        f"❌ Введенный номер слова ({start_word}) превышает количество слов в языке ({word_count}).\n"
                        f"Введите число от 1 до {word_count}.\n\n"
                        f"Для отмены и возврата к настройкам введите команду /cancel"
                    )
                    return
        
        # Получаем настройки пользователя
        settings = await get_user_language_settings(message, state)
        
        # Обновляем значение начального слова
        settings["start_word"] = start_word
        
        # Сохраняем обновленные настройки
        success = await save_user_language_settings(message, state, settings)
        
        if success:
            # Обновляем состояние FSM для совместимости со старым кодом
            await state.update_data(start_word=start_word)
            
            # Очищаем состояние FSM, но сохраняем данные
            current_data = await state.get_data()
            await state.set_state(None)
            await state.update_data(**current_data)
            
            # Отображаем экран настроек с обновленными данными
            await display_language_settings(message, state, prefix="✅ Настройки успешно обновлены!\n\n")
        else:
            # В случае ошибки сообщаем пользователю
            await message.answer(
                "❌ Не удалось сохранить настройки. Попробуйте позже.\n\n"
                "Нажмите /settings, чтобы вернуться к настройкам."
            )
            
    except ValueError:
        await message.answer(
            "❌ Некорректный ввод. Введите целое число (например, 1, 10, 100).\n\n"
            "Для отмены и возврата к настройкам введите команду /cancel"
        )


@settings_router.message(Command("cancel"), SettingsStates.waiting_start_word, flags={"command_priority": 10})
async def cancel_start_word_input(message: Message, state: FSMContext):
    """
    Обработчик команды /cancel для выхода из режима ввода начального слова.
    
    Args:
        message: Объект сообщения от Telegram
        state: Контекст состояния FSM
    """
    user_id = message.from_user.id
    username = message.from_user.username
    full_name = message.from_user.full_name
    
    logger.info(f"'/cancel' command from {full_name} ({username}) while in start_word input")
    
    # Получаем текущие данные состояния
    current_data = await state.get_data()
    
    # Очищаем состояние, но сохраняем данные
    await state.set_state(None)
    await state.update_data(**current_data)
    
    # Отображаем экран настроек
    await display_language_settings(message, state, prefix="⚙️ Ввод отменен. Настройки процесса обучения\n\n")
    
    # Важно: предотвращаем дальнейшую обработку этого сообщения другими обработчиками
    raise SkipHandler()

@settings_router.callback_query(F.data == "settings_toggle_show_hints")
async def process_settings_toggle_show_hints(callback: CallbackQuery, state: FSMContext):
    """
    Process callback to toggle showing hint buttons.
    
    Args:
        callback: The callback query from Telegram
        state: The FSM state context
    """
    user_id = callback.from_user.id
    username = callback.from_user.username
    full_name = callback.from_user.full_name

    logger.info(f"'settings_toggle_show_hints' callback from {full_name} ({username})")
    
    # Получаем настройки пользователя с помощью функции
    settings = await get_user_language_settings(callback, state)
    print(settings)
    
    # Инвертируем настройку отображения кнопок подсказок
    settings["show_hints"] = not settings.get("show_hints", True)
    
    # Сохраняем обновленные настройки
    success = await save_user_language_settings(callback, state, settings)
    
    if success:
        # Обновляем состояние FSM для совместимости со старым кодом
        await state.update_data(show_hints=settings["show_hints"])
        
        # Используем функцию для отображения настроек
        await display_language_settings(callback, state, 
                                       prefix="✅ Настройки успешно обновлены!\n\n", 
                                       is_callback=True)
    else:
        # В случае ошибки сообщаем пользователю
        await callback.message.answer("❌ Не удалось сохранить настройки. Попробуйте позже.")
    
    await callback.answer()