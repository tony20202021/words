"""
Handlers for language management in administrative mode.
"""

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from app.utils.api_utils import get_api_client_from_bot
from app.utils.logger import setup_logger
from app.bot.states.centralized_states import AdminStates
from app.bot.keyboards.admin_keyboards import (
    get_admin_keyboard, 
    get_languages_keyboard,
    get_edit_language_keyboard,
    get_back_to_languages_keyboard,
    get_word_actions_keyboard
)
from app.utils.formatting_utils import format_date_standard
from app.utils.callback_constants import CallbackData

# Создаем роутер для обработчиков администрирования языками
language_router = Router()

logger = setup_logger(__name__)

@language_router.message(Command("managelang"))
async def cmd_manage_languages(message: Message, state: FSMContext):
    """
    Handle the /managelang command which shows language management options.
    
    Args:
        message: The message object from Telegram
        state: The FSM state context
    """
    user_id = message.from_user.id
    username = message.from_user.username
    full_name = message.from_user.full_name

    logger.info(f"'/managelang' command from {full_name} ({username})")
    
    # Вызываем общую функцию для обработки
    await handle_language_management(message, state, is_callback=False)

@language_router.callback_query(F.data == CallbackData.CREATE_LANGUAGE)
async def process_create_language(callback: CallbackQuery, state: FSMContext):
    """
    Start creating a new language.
    
    Args:
        callback: The callback query from Telegram
        state: The FSM state context
    """
    user_id = callback.from_user.id
    username = callback.from_user.username
    full_name = callback.from_user.full_name

    logger.info(f"'create_language' callback from {full_name} ({username})")
    
    # Получаем клиент API с помощью утилиты
    api_client = get_api_client_from_bot(callback.bot)
    
    # Проверяем права администратора
    user_response = await api_client.get_user_by_telegram_id(user_id)
    
    if not user_response["success"]:
        error_msg = user_response.get("error", "Неизвестная ошибка")
        await callback.message.answer(f"Ошибка при получении данных пользователя: {error_msg}")
        await callback.answer()
        logger.error(f"Failed to get user data during create_language. Error: {error_msg}")
        return
    
    # Получаем пользователя из ответа
    users = user_response["result"]
    user = users[0] if users and isinstance(users, list) and len(users) > 0 else None
    
    if not user or not user.get("is_admin", False):
        await callback.message.answer("У вас нет прав администратора.")
        await callback.answer()
        return
    
    await callback.message.answer(
        "🆕 Создание нового языка\n\n"
        "Введите название языка на русском языке:"
    )
    
    # Переходим в состояние создания языка
    await state.set_state(AdminStates.creating_language_name)
    
    await callback.answer()

@language_router.message(AdminStates.creating_language_name)
async def process_language_name(message: Message, state: FSMContext):
    """
    Process language name input from admin.
    
    Args:
        message: The message object from Telegram
        state: The FSM state context
    """
    # Сохраняем название языка в состоянии
    await state.update_data(language_name_ru=message.text)
    
    await message.answer(
        f"✅ Название на русском: {message.text}\n\n"
        "Теперь введите название языка на языке оригинала:"
    )
    
    # Переходим к вводу оригинального названия
    await state.set_state(AdminStates.creating_language_native_name)

@language_router.message(AdminStates.creating_language_native_name)
async def process_language_native_name(message: Message, state: FSMContext):
    """
    Process language native name input from admin.
    
    Args:
        message: The message object from Telegram
        state: The FSM state context
    """
    # Получаем данные состояния
    user_data = await state.get_data()
    name_ru = user_data.get('language_name_ru')
    name_foreign = message.text
    
    # Получаем клиент API с помощью утилиты
    api_client = get_api_client_from_bot(message.bot)
    
    # Создаем новый язык через API
    try:
        language_data = {
            "name_ru": name_ru,
            "name_foreign": name_foreign
        }
        
        create_response = await api_client.create_language(language_data)
        
        if not create_response["success"]:
            error_msg = create_response.get("error", "Неизвестная ошибка")
            await message.answer(f"Ошибка при создании языка: {error_msg}")
            logger.error(f"Failed to create language. Error: {error_msg}")
            await state.clear()
            return
        
        result = create_response["result"]
        
        await message.answer(
            f"✅ Язык успешно создан!\n\n"
            f"ID: {result.get('id')}\n"
            f"Название на русском: {result.get('name_ru')}\n"
            f"Название на языке оригинала: {result.get('name_foreign')}"
        )
        
    except Exception as e:
        logger.error(f"Error creating language: {e}")
        await message.answer(
            f"❌ Ошибка при создании языка: {str(e)}"
        )
    
    # Очищаем состояние
    await state.clear()

@language_router.message(AdminStates.editing_language_name)
async def process_edit_language_name(message: Message, state: FSMContext):
    """
    Process edited language name from admin.
    
    Args:
        message: The message object from Telegram
        state: The FSM state context
    """
    # Получаем данные состояния
    user_data = await state.get_data()
    language_id = user_data.get('editing_language_id')
    
    if not language_id:
        await message.answer("❌ Ошибка: ID языка не найден. Начните редактирование заново.")
        await state.clear()
        return
    
    # Получаем клиент API с помощью утилиты
    api_client = get_api_client_from_bot(message.bot)
    
    # Обновляем язык через API
    try:
        update_data = {
            "name_ru": message.text
        }
        
        update_response = await api_client.update_language(language_id, update_data)
        
        if not update_response["success"]:
            error_msg = update_response.get("error", "Неизвестная ошибка")
            await message.answer(f"Ошибка при обновлении языка: {error_msg}")
            logger.error(f"Failed to update language {language_id}. Error: {error_msg}")
            await state.clear()
            return
        
        # Очищаем состояние
        await state.clear()
        
        # Сразу переходим к экрану редактирования языка
        await process_edit_language_after_update(message, language_id)
        
    except Exception as e:
        logger.error(f"Error updating language: {e}")
        await message.answer(
            f"❌ Ошибка при обновлении языка: {str(e)}"
        )
        # Очищаем состояние
        await state.clear()

@language_router.message(AdminStates.editing_language_native_name)
async def process_edit_language_native_name(message: Message, state: FSMContext):
    """
    Process edited language native name from admin.
    
    Args:
        message: The message object from Telegram
        state: The FSM state context
    """
    # Получаем данные состояния
    user_data = await state.get_data()
    language_id = user_data.get('editing_language_id')
    
    if not language_id:
        await message.answer("❌ Ошибка: ID языка не найден. Начните редактирование заново.")
        await state.clear()
        return
    
    # Получаем клиент API с помощью утилиты
    api_client = get_api_client_from_bot(message.bot)
    
    # Обновляем язык через API
    try:
        update_data = {
            "name_foreign": message.text
        }
        
        update_response = await api_client.update_language(language_id, update_data)
        
        if not update_response["success"]:
            error_msg = update_response.get("error", "Неизвестная ошибка")
            await message.answer(f"Ошибка при обновлении языка: {error_msg}")
            logger.error(f"Failed to update language {language_id}. Error: {error_msg}")
            await state.clear()
            return
        
        # Очищаем состояние
        await state.clear()
        
        # Сразу переходим к экрану редактирования языка
        await process_edit_language_after_update(message, language_id)
        
    except Exception as e:
        logger.error(f"Error updating language: {e}")
        await message.answer(
            f"❌ Ошибка при обновлении языка: {str(e)}"
        )
        # Очищаем состояние
        await state.clear()

@language_router.callback_query(F.data.startswith("edit_name_ru_"))
async def process_edit_name_ru(callback: CallbackQuery, state: FSMContext):
    """
    Start editing language Russian name.
    
    Args:
        callback: The callback query from Telegram
        state: The FSM state context
    """
    # Извлекаем ID языка из callback_data
    language_id = callback.data.split("_")[-1]
    
    # Сохраняем данные в состоянии
    await state.update_data(editing_language_id=language_id)
    
    await callback.message.answer(
        "✏️ Введите новое название языка на русском:"
    )
    
    # Переходим в состояние редактирования названия
    await state.set_state(AdminStates.editing_language_name)
    
    await callback.answer()

@language_router.callback_query(F.data.startswith("edit_name_foreign_"))
async def process_edit_name_foreign(callback: CallbackQuery, state: FSMContext):
    """
    Start editing language native name.
    
    Args:
        callback: The callback query from Telegram
        state: The FSM state context
    """
    # Извлекаем ID языка из callback_data
    language_id = callback.data.split("_")[-1]
    
    # Сохраняем данные в состоянии
    await state.update_data(editing_language_id=language_id)
    
    await callback.message.answer(
        "✏️ Введите новое название языка на языке оригинала:"
    )
    
    # Переходим в состояние редактирования оригинального названия
    await state.set_state(AdminStates.editing_language_native_name)
    
    await callback.answer()

@language_router.callback_query(F.data.startswith("delete_language_"))
async def process_delete_language(callback: CallbackQuery, state: FSMContext):
    """
    Delete a language after confirmation.
    
    Args:
        callback: The callback query from Telegram
        state: The FSM state context
    """
    # Извлекаем ID языка из callback_data
    language_id = callback.data.split("_")[-1]
    
    # Получаем клиент API с помощью утилиты
    api_client = get_api_client_from_bot(callback.bot)
    
    # Получаем информацию о языке из API
    language_response = await api_client.get_language(language_id)
    
    if not language_response["success"] or not language_response["result"]:
        error_msg = language_response.get("error", "Язык не найден")
        await callback.message.answer(f"Ошибка: {error_msg}")
        await callback.answer()
        logger.error(f"Failed to get language by ID {language_id}. Error: {error_msg}")
        return
    
    language = language_response["result"]
    
    # Создаем билдер для клавиатуры
    builder = InlineKeyboardBuilder()
    
    builder.add(InlineKeyboardButton(
        text="✅ Да, удалить",
        callback_data=f"confirm_delete_{language_id}"
    ))
    
    builder.add(InlineKeyboardButton(
        text="❌ Отмена",
        callback_data=f"cancel_delete_{language_id}"
    ))
    
    # Настраиваем ширину строки клавиатуры
    builder.adjust(2)
    
    await callback.message.answer(
        f"🗑️ Вы действительно хотите удалить язык?\n\n"
        f"Название: {language.get('name_ru')} ({language.get('name_foreign')})\n\n"
        f"⚠️ Внимание! Это действие также удалит все слова, "
        f"связанные с этим языком, и не может быть отменено!",
        reply_markup=builder.as_markup()
    )
    
    await callback.answer()

@language_router.callback_query(F.data.startswith("confirm_delete_"))
async def process_confirm_delete_language(callback: CallbackQuery, state: FSMContext):
    """
    Confirm language deletion.
    
    Args:
        callback: The callback query from Telegram
        state: The FSM state context
    """
    # Извлекаем ID языка из callback_data
    language_id = callback.data.split("_")[-1]
    
    # Получаем клиент API с помощью утилиты
    api_client = get_api_client_from_bot(callback.bot)
    
    # Удаляем язык через API
    try:
        delete_response = await api_client.delete_language(language_id)
        
        if not delete_response["success"]:
            error_msg = delete_response.get("error", "Неизвестная ошибка")
            await callback.message.answer(f"Ошибка при удалении языка: {error_msg}")
            logger.error(f"Failed to delete language {language_id}. Error: {error_msg}")
            await callback.answer()
            return
        
        result = delete_response["result"]
        
        await callback.message.answer(
            f"✅ Язык успешно удален!\n\n"
            f"Сообщение: {result.get('message', 'Язык удален')}"
        )
        
    except Exception as e:
        logger.error(f"Error deleting language: {e}")
        await callback.message.answer(
            f"❌ Ошибка при удалении языка: {str(e)}"
        )
    
    await callback.answer()

@language_router.callback_query(F.data.startswith("cancel_delete_"))
async def process_cancel_delete_language(callback: CallbackQuery, state: FSMContext):
    """
    Cancel language deletion.
    
    Args:
        callback: The callback query from Telegram
        state: The FSM state context
    """
    await callback.message.answer("🚫 Удаление языка отменено")
    await callback.answer()

@language_router.callback_query(F.data.startswith("search_word_by_number_"))
async def process_search_word_by_number(callback_query: CallbackQuery, state: FSMContext):
    """
    Обработчик для инициализации поиска слова по номеру.
    
    Args:
        callback_query: Объект callback query от Telegram
        state: Контекст состояния FSM
    """
    # Изменяем извлечение ID языка
    language_id = callback_query.data.split("_")[-1]
    
    # Сохраняем ID языка в состоянии
    await state.update_data(language_id=language_id)
    
    # Отправляем запрос на ввод номера слова
    await callback_query.message.answer(
        "📝 <b>Введите номер слова для поиска:</b>\n\n"
        "Например: <code>1</code> - для поиска первого слова в списке",
        parse_mode="HTML"
    )
    
    # Устанавливаем состояние ввода номера слова
    await state.set_state(AdminStates.input_word_number)
    
    # Отвечаем на callback
    await callback_query.answer()

@language_router.message(AdminStates.input_word_number)
async def process_word_number_input(message: Message, state: FSMContext):
    """
    Обработчик для поиска слова по введенному номеру.
    
    Args:
        message: Объект сообщения от Telegram
        state: Контекст состояния FSM
    """
    user_id = message.from_user.id
    username = message.from_user.username
    full_name = message.from_user.first_name

    api_client = get_api_client_from_bot(message.bot)
    
    if not api_client:
        await message.reply("Ошибка: API клиент недоступен")
        return
    
    # Проверяем, что введено число
    if not message.text.isdigit():
        await message.reply(
            "❌ Пожалуйста, введите корректный номер слова (только цифры)."
        )
        return
    
    word_number = int(message.text)
    
    # Получаем ID языка из состояния
    data = await state.get_data()
    language_id = data.get('language_id')
    
    if not language_id:
        await message.reply(
            "❌ Ошибка: ID языка не найден. Пожалуйста, вернитесь в меню администратора и попробуйте снова."
        )
        return
    
    # Получаем слово по номеру
    word_response = await api_client.get_word_by_number(language_id, word_number)
    
    # Проверяем успешность запроса
    if not word_response["success"]:
        await message.reply(
            f"❌ Ошибка при поиске слова с номером {word_number}. "
            f"Возможно, слово с таким номером не существует."
        )
        return
    
    # Проверяем, есть ли результат
    result = word_response["result"]
    if not result or (isinstance(result, list) and len(result) == 0):
        await message.reply(
            f"⚠️ Слово с номером {word_number} не найдено в базе данных."
        )
        # Возвращаемся на экран редактирования языка
        await show_language_edit_screen(message, language_id, is_callback=False)
        return
    
    # Получаем слово (первый элемент в списке)
    words = result
    word = words[0] if isinstance(words, list) else words
    
    # Получаем информацию о языке
    language_response = await api_client.get_language(language_id)
    language_name = "Неизвестный язык"
    
    if language_response["success"] and language_response["result"]:
        language_name = language_response["result"]["name_ru"]
    
    # Получаем ID слова, проверяя разные возможные ключи
    word_id = word.get('id') or word.get('_id') or word.get('word_id') or 'N/A'
    
    # Получаем данные текущего пользователя
    user_info = ""
    
    # Получаем данные состояния - проверяем наличие db_user_id
    db_user_id = data.get('db_user_id')
    
    if db_user_id:
        # Получаем данные пользователя для этого слова
        user_word_response = await api_client.get_user_word_data(db_user_id, word_id)
        
        if user_word_response["success"] and user_word_response["result"]:
            user_word_data = user_word_response["result"]
            
            # Флаг пропуска слова
            is_skipped = user_word_data.get("is_skipped", False)
            
            # Период проверки
            check_interval = user_word_data.get("check_interval", 0)
            
            # Дата следующей проверки
            next_check_date = user_word_data.get("next_check_date")
            
            # Форматируем дату для отображения
            formatted_next_check_date = "Не установлена"
            if next_check_date:
                try:
                    # Импортируем функцию для форматирования даты
                    from app.utils.formatting_utils import format_date_standard
                    formatted_next_check_date = format_date_standard(next_check_date)
                except Exception as e:
                    logger.error(f"Error formatting date: {e}")
                    formatted_next_check_date = str(next_check_date).split('T')[0]
            
            # Добавляем информацию о пользовательских данных
            user_info = (
                f"\n<b>Данные для текущего пользователя ({username}):</b>\n"
                f"Флаг пропуска: <b>{'Да' if is_skipped else 'Нет'}</b>\n"
                f"Период проверки: <b>{check_interval} дней</b>\n"
                f"Дата следующей проверки: <b>{formatted_next_check_date}</b>\n"
            )
    
    # Формируем сообщение с информацией о слове
    word_info = (
        f"📖 <b>Информация о слове</b> 📖\n\n"
        f"Язык: <b>{language_name}</b>\n"
        f"Номер: <b>{word.get('word_number', 'N/A')}</b>\n"
        f"Слово: <b>{word.get('word_foreign', 'N/A')}</b>\n"
        f"Транскрипция: <b>{word.get('transcription', 'N/A')}</b>\n"
        f"Перевод: <b>{word.get('translation', 'N/A')}</b>\n"
        f"ID: <code>{word_id}</code>\n"
        f"{user_info}"
    )
    
    # Используем готовую клавиатуру
    keyboard = get_word_actions_keyboard(word_id, language_id)
    
    # Отправляем информацию о слове
    await message.reply(
        word_info,
        parse_mode="HTML",
        reply_markup=keyboard
    )

    # Очищаем состояние FSM
    await state.clear()

async def handle_language_management(message_or_callback, state: FSMContext, is_callback=False):
    """
    Common handler logic for language management.
    
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

    logger.info(f"Language management requested by {full_name} ({username})")
    
    # Получаем клиент API с помощью утилиты
    api_client = get_api_client_from_bot(message.bot)
    
    # Проверяем права администратора
    user_response = await api_client.get_user_by_telegram_id(user_id)
    
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
    
    # Получаем список языков из API
    languages_response = await api_client.get_languages()
    
    if not languages_response["success"]:
        error_msg = languages_response.get("error", "Неизвестная ошибка")
        await message.answer(f"Ошибка при получении списка языков: {error_msg}")
        logger.error(f"Failed to get languages. Error: {error_msg}")
        return
    
    languages = languages_response["result"] or []
    
    # Заголовок сообщения
    message_text = "🌍 Управление языками\n\n"
    
    # Если языки есть, добавляем их в сообщение
    if languages:
        message_text += "Список доступных языков:\n"
        for i, lang in enumerate(languages, 1):
            message_text += f"{i}. {lang['name_ru']} ({lang['name_foreign']})\n"
        
        message_text += "\nВыберите язык для редактирования или создайте новый:"
    else:
        message_text += "В системе пока нет языков. Создайте первый язык:"
    
    # Используем готовую функцию для создания клавиатуры
    keyboard = get_languages_keyboard(languages)
    
    await message.answer(message_text, reply_markup=keyboard)
    
    # Возвращаем True, чтобы показать, что обработка прошла успешно
    return True

@language_router.callback_query(F.data == CallbackData.BACK_TO_ADMIN)
async def process_back_to_admin_from_languages(callback: CallbackQuery, state: FSMContext):
    """
    Process callback to return to admin menu from language management.
    
    Args:
        callback: The callback query from Telegram
        state: The FSM state context
    """
    user_id = callback.from_user.id
    username = callback.from_user.username
    full_name = callback.from_user.full_name

    logger.info(f"'back_to_admin' callback from languages menu by {full_name} ({username})")
    
    # Импортируем функцию для обработки режима администратора
    from app.bot.handlers.admin.admin_basic_handlers import handle_admin_mode
    
    # Вызываем общую функцию, передавая данные из callback
    await handle_admin_mode(callback, state, is_callback=True)
    
    # Отвечаем на callback
    await callback.answer()

@language_router.callback_query(F.data == CallbackData.BACK_TO_LANGUAGES)
async def process_back_to_languages(callback: CallbackQuery, state: FSMContext):
    """
    Handle going back to languages list from language edit screen.
    
    Args:
        callback: The callback query from Telegram
        state: The FSM state context
    """
    user_id = callback.from_user.id
    username = callback.from_user.username
    full_name = callback.from_user.full_name

    logger.info(f"'back_to_languages' callback from language edit by {full_name} ({username})")
    
    # Вызываем общую функцию для обработки списка языков
    await handle_language_management(callback, state, is_callback=True)
    
    # Отвечаем на callback
    await callback.answer()
    
async def show_language_edit_screen(message_or_callback, language_id: str, is_callback=False):
    """
    Show language edit screen.
    
    Args:
        message_or_callback: The message or callback object from Telegram
        language_id: The ID of the language to edit
        is_callback: Whether this is called from a callback handler
    """
    if is_callback:
        message = message_or_callback.message
    else:
        message = message_or_callback
    
    # Получаем клиент API с помощью утилиты
    api_client = get_api_client_from_bot(message.bot)
    
    # Получаем информацию о языке из API
    language_response = await api_client.get_language(language_id)
    
    if not language_response["success"] or not language_response["result"]:
        error_msg = language_response.get("error", "Язык не найден")
        await message.answer(f"Ошибка: {error_msg}")
        logger.error(f"Failed to get language by ID {language_id}. Error: {error_msg}")
        return
    
    language = language_response["result"]
    
    # Получаем количество слов в языке
    word_count_response = await api_client.get_word_count_by_language(language_id)
    word_count = "N/A"  # значение по умолчанию

    if word_count_response["success"]:
        word_count = word_count_response["result"]["count"] if word_count_response["result"] else "0"
    else:
        logger.error(f"Failed to get word count for language {language_id}. Error: {word_count_response.get('error')}")    

    # Форматируем даты используя импортированную функцию
    created_at = format_date_standard(language.get('created_at', 'N/A'))
    updated_at = format_date_standard(language.get('updated_at', 'N/A'))
    
    # Используем готовую клавиатуру из admin_keyboards.py
    keyboard = get_edit_language_keyboard(language_id)
    
    await message.answer(
        f"🔹 <b>Редактирование языка</b> 🔹\n\n"
        f"ID: {language['id']}\n"
        f"Название (рус): <b>{language['name_ru']}</b>\n"
        f"Название (ориг.): <b>{language['name_foreign']}</b>\n"
        f"Количество слов: <b>{word_count}</b>\n"
        f"Дата создания: <b>{created_at}</b>\n"
        f"Дата обновления: <b>{updated_at}</b>",
        parse_mode="HTML",
        reply_markup=keyboard
    )
    
@language_router.callback_query(F.data.startswith("edit_language_"))
async def process_edit_language(callback: CallbackQuery, state: FSMContext):
    """
    Show language edit options.
    
    Args:
        callback: The callback query from Telegram
        state: The FSM state context
    """
    # Извлекаем ID языка из callback_data
    language_id = callback.data.split("_")[-1]
    
    # Логируем выбранный язык
    logger.info(f"'edit_language_' callback for language ID: {language_id}")
    
    # Получаем клиент API с помощью утилиты
    api_client = get_api_client_from_bot(callback.bot)
    
    # Проверяем права администратора
    user_response = await api_client.get_user_by_telegram_id(callback.from_user.id)
    
    if not user_response["success"]:
        error_msg = user_response.get("error", "Неизвестная ошибка")
        await callback.message.answer(f"Ошибка при получении данных пользователя: {error_msg}")
        await callback.answer()
        logger.error(f"Failed to get user data during edit_language. Error: {error_msg}")
        return
    
    # Получаем пользователя из ответа
    users = user_response["result"]
    user = users[0] if users and isinstance(users, list) and len(users) > 0 else None
    
    if not user or not user.get("is_admin", False):
        await callback.message.answer("У вас нет прав администратора.")
        await callback.answer()
        return
    
    # Сохраняем ID языка в состоянии для дальнейшего использования
    await state.update_data(editing_language_id=language_id)
    
    # Вызываем общую функцию для отображения экрана редактирования
    await show_language_edit_screen(callback, language_id, is_callback=True)
    
    await callback.answer()

async def process_edit_language_after_update(message: Message, language_id: str):
    """
    Show language edit screen after update.
    
    Args:
        message: The message object from Telegram
        language_id: The ID of the edited language
    """
    # Вызываем общую функцию для отображения экрана редактирования
    await show_language_edit_screen(message, language_id, is_callback=False)