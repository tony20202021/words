"""
Handlers for language management in administrative mode.
Updated with FSM states for better navigation control.
"""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from app.utils.api_utils import get_api_client_from_bot
from app.utils.logger import setup_logger
from app.bot.states.centralized_states import AdminStates, StudyStates
from app.bot.keyboards.admin_keyboards import (
    get_word_actions_keyboard
)
from app.utils.callback_constants import CallbackData
from app.bot.keyboards.admin_keyboards import get_word_actions_keyboard_from_study
from app.bot.keyboards.admin_keyboards import (
    get_word_actions_keyboard,
    get_word_actions_keyboard_from_study, 
)
from app.bot.handlers.admin.admin_language_handlers import show_language_edit_screen
from app.utils.message_utils import get_user_info
from app.utils.formatting_utils import MAX_MESSAGE_LENGTH

# Создаем роутер для обработчиков администрирования
word_router = Router()

logger = setup_logger(__name__)


@word_router.callback_query(AdminStates.viewing_language_details, F.data.startswith("search_word_by_number_"))
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

@word_router.message(AdminStates.input_word_number)
async def input_search_word_by_number(message: Message, state: FSMContext):
    """
    Обработчик для поиска слова по введенному номеру.
    
    Args:
        message: Объект сообщения от Telegram
        state: Контекст состояния FSM
    """
    user_id, username, full_name = get_user_info(message)

    logger.info(f"'process_word_number_input' message from: {username}")

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
        await state.set_state(AdminStates.viewing_language_details)
        await show_language_edit_screen(message, language_id, is_callback=False)
        return
    
    # Устанавливаем состояние просмотра результатов поиска слова
    await state.set_state(AdminStates.viewing_word_search_results)
    
    # Получаем слово (первый элемент в списке)
    words = result
    word = words[0] if isinstance(words, list) else words
    
    # Получаем ID слова, проверяя разные возможные ключи
    word_id = word.get('id') or word.get('_id') or word.get('word_id') or 'N/A'

    await show_word_details_screen(message, word_id, state)

        
@word_router.callback_query(AdminStates.viewing_word_search_results, F.data.startswith("edit_word_"))
@word_router.callback_query(AdminStates.viewing_word_details, F.data.startswith("edit_word_"))
@word_router.callback_query(StudyStates.viewing_word_details, F.data.startswith("edit_word_"))
@word_router.callback_query(StudyStates.studying, F.data.startswith("edit_word_"))
async def process_edit_word(callback: CallbackQuery, state: FSMContext):
    """
    Show word editing menu.
    
    Args:
        callback: The callback query from Telegram
        state: The FSM state context
    """
    from app.utils.callback_constants import CallbackParser
    
    # Парсим callback для получения word_id
    word_id = CallbackParser.parse_edit_word(callback.data)
    
    if not word_id:
        await callback.message.answer("❌ Ошибка: ID слова не найден")
        await callback.answer()
        return
    
    current_state = await state.get_state()

    logger.info(f"'edit_word' callback for word ID: {word_id}, current_state={current_state}")
    
    # Устанавливаем состояние просмотра деталей слова
    await state.set_state(AdminStates.viewing_word_details)
    await state.update_data(editing_word_id=word_id)
    
    # Получаем клиент API
    api_client = get_api_client_from_bot(callback.bot)
    
    # Получаем информацию о слове
    word_response = await api_client.get_word(word_id)
    
    if not word_response["success"] or not word_response["result"]:
        error_msg = word_response.get("error", "Слово не найдено")
        await callback.message.answer(f"Ошибка: {error_msg}")
        await callback.answer()
        logger.error(f"Failed to get word by ID {word_id}. Error: {error_msg}")
        return
    
    word = word_response["result"]
    
    # Получаем информацию о языке
    language_response = await api_client.get_language(word['language_id'])
    language_name = "Неизвестный язык"
    
    if language_response["success"] and language_response["result"]:
        language = language_response["result"]
        language_name = f"{language['name_ru']} ({language['name_foreign']})"
    
    # Формируем сообщение с информацией о слове
    word_info = (
        f"✏️ <b>Редактирование слова</b>\n\n"
        f"Язык: <b>{language_name}</b>\n"
        f"Номер: <b>{word.get('word_number', 'N/A')}</b>\n"
        f"Слово: <code>{word.get('word_foreign', 'N/A')}</code>\n"
        f"Транскрипция: <code>{word.get('transcription', 'N/A')}</code>\n"
        f"Перевод: <code>{word.get('translation', 'N/A')}</code>\n"
        f"Радикалы: <code>{word.get('radicals', 'N/A')}</code>\n"
        f"Ссылки: <code>{word.get('references', 'N/A')}</code>\n"
        f"Тоны: <code>{word.get('tones', 'N/A')}</code>\n\n"
        f"Выберите поле для редактирования:"
    )
    
    # Создаем клавиатуру для редактирования
    from app.bot.keyboards.admin_keyboards import get_word_filed_edit_keyboard
    keyboard = get_word_filed_edit_keyboard(word_id, word['language_id'])
    
    await callback.message.edit_text(
        word_info,
        parse_mode="HTML",
        reply_markup=keyboard
    )
    
    await callback.answer()


@word_router.callback_query(AdminStates.viewing_word_details, F.data.startswith("edit_wordfield_foreign_"))
async def process_edit_wordfield_foreign(callback: CallbackQuery, state: FSMContext):
    """
    Start editing word foreign text.
    
    Args:
        callback: The callback query from Telegram
        state: The FSM state context
    """
    from app.utils.callback_constants import CallbackParser
    
    # Парсим callback для получения word_id
    field, word_id = CallbackParser.parse_edit_wordfield(callback.data)
    
    if not word_id:
        await callback.message.answer("❌ Ошибка: ID слова не найден")
        await callback.answer()
        return
    
    # Сохраняем данные в состоянии
    await state.update_data(editing_word_id=word_id, editing_field="word_foreign")
    
    await callback.message.answer(
        "✏️ <b>Редактирование иностранного слова</b>\n\n"
        "Введите новое слово на иностранном языке:",
        parse_mode="HTML"
    )
    
    # Переходим в состояние редактирования иностранного слова
    await state.set_state(AdminStates.editing_word_foreign)
    
    await callback.answer()


@word_router.callback_query(AdminStates.viewing_word_details, F.data.startswith("edit_wordfield_translation_"))
async def process_edit_wordfield_translation(callback: CallbackQuery, state: FSMContext):
    """
    Start editing word translation.
    
    Args:
        callback: The callback query from Telegram
        state: The FSM state context
    """
    from app.utils.callback_constants import CallbackParser
    
    # Парсим callback для получения word_id
    field, word_id = CallbackParser.parse_edit_wordfield(callback.data)
    
    if not word_id:
        await callback.message.answer("❌ Ошибка: ID слова не найден")
        await callback.answer()
        return
    
    # Сохраняем данные в состоянии
    await state.update_data(editing_word_id=word_id, editing_field="translation")
    
    await callback.message.answer(
        "✏️ <b>Редактирование перевода</b>\n\n"
        "Введите новый перевод на русский язык:",
        parse_mode="HTML"
    )
    
    # Переходим в состояние редактирования перевода
    await state.set_state(AdminStates.editing_word_translation)
    
    await callback.answer()


@word_router.callback_query(AdminStates.viewing_word_details, F.data.startswith("edit_wordfield_transcription_"))
async def process_edit_wordfield_transcription(callback: CallbackQuery, state: FSMContext):
    """
    Start editing word transcription.   
    
    Args:
        callback: The callback query from Telegram
        state: The FSM state context
    """
    from app.utils.callback_constants import CallbackParser
    
    # Парсим callback для получения word_id
    field, word_id = CallbackParser.parse_edit_wordfield(callback.data)
    
    if not word_id:
        await callback.message.answer("❌ Ошибка: ID слова не найден")
        await callback.answer()
        return
    
    # Сохраняем данные в состоянии
    await state.update_data(editing_word_id=word_id, editing_field="transcription")
    
    await callback.message.answer(
        "✏️ <b>Редактирование транскрипции</b>\n\n"
        "Введите новую транскрипцию слова:",
        parse_mode="HTML"
    )
    
    # Переходим в состояние редактирования транскрипции
    await state.set_state(AdminStates.editing_word_transcription)
    
    await callback.answer()


@word_router.callback_query(AdminStates.viewing_word_details, F.data.startswith("edit_wordfield_radicals_"))
async def process_edit_wordfield_radicals(callback: CallbackQuery, state: FSMContext):
    """
    Start editing word radicals.
    
    Args:
        callback: The callback query from Telegram
        state: The FSM state context
    """
    from app.utils.callback_constants import CallbackParser
    
    # Парсим callback для получения word_id
    field, word_id = CallbackParser.parse_edit_wordfield(callback.data)
    
    if not word_id:
        await callback.message.answer("❌ Ошибка: ID слова не найден")
        await callback.answer()
        return
    
    # Сохраняем данные в состоянии
    await state.update_data(editing_word_id=word_id, editing_field="transcription")
    
    await callback.message.answer(
        "✏️ <b>Редактирование радикалов</b>\n\n"
        "Введите новые радикалы слова:",
        parse_mode="HTML"
    )
    
    # Переходим в состояние редактирования радикалов
    await state.set_state(AdminStates.editing_word_radicals)
    
    await callback.answer()


@word_router.callback_query(AdminStates.viewing_word_details, F.data.startswith("edit_wordfield_references_"))
async def process_edit_wordfield_references(callback: CallbackQuery, state: FSMContext):
    """
    Start editing word references.
    
    Args:
        callback: The callback query from Telegram
        state: The FSM state context
    """
    from app.utils.callback_constants import CallbackParser
    
    # Парсим callback для получения word_id
    field, word_id = CallbackParser.parse_edit_wordfield(callback.data)
    
    if not word_id:
        await callback.message.answer("❌ Ошибка: ID слова не найден")
        await callback.answer()
        return
    
    # Сохраняем данные в состоянии
    await state.update_data(editing_word_id=word_id, editing_field="transcription")
    
    await callback.message.answer(
        "✏️ <b>Редактирование ссылок</b>\n\n"
        "Введите новые ссылки слова:",
        parse_mode="HTML"
    )
    
    # Переходим в состояние редактирования ссылок
    await state.set_state(AdminStates.editing_word_references)
    
    await callback.answer()


@word_router.callback_query(AdminStates.viewing_word_details, F.data.startswith("edit_wordfield_tones_"))
async def process_edit_wordfield_tones(callback: CallbackQuery, state: FSMContext):
    """
    Start editing word tones.
    
    Args:
        callback: The callback query from Telegram
        state: The FSM state context
    """
    from app.utils.callback_constants import CallbackParser
    
    # Парсим callback для получения word_id
    field, word_id = CallbackParser.parse_edit_wordfield(callback.data)
    
    if not word_id:
        await callback.message.answer("❌ Ошибка: ID слова не найден")
        await callback.answer()
        return
    
    # Сохраняем данные в состоянии
    await state.update_data(editing_word_id=word_id, editing_field="transcription")
    
    await callback.message.answer(
        "✏️ <b>Редактирование тонов</b>\n\n"
        "Введите новые тоны слова:",
        parse_mode="HTML"
    )
    
    # Переходим в состояние редактирования тонов
    await state.set_state(AdminStates.editing_word_tones)
    
    await callback.answer()


@word_router.callback_query(AdminStates.viewing_word_details, F.data.startswith("edit_wordfield_number_"))
async def process_edit_wordfield_number(callback: CallbackQuery, state: FSMContext):
    """
    Start editing word number.
    
    Args:
        callback: The callback query from Telegram
        state: The FSM state context
    """
    from app.utils.callback_constants import CallbackParser
    
    # Парсим callback для получения word_id
    field, word_id = CallbackParser.parse_edit_wordfield(callback.data)
    
    if not word_id:
        await callback.message.answer("❌ Ошибка: ID слова не найден")
        await callback.answer()
        return
    
    # Сохраняем данные в состоянии
    await state.update_data(editing_word_id=word_id, editing_field="word_number")
    
    await callback.message.answer(
        "✏️ <b>Редактирование номера слова</b>\n\n"
        "Введите новый номер слова в частотном списке:",
        parse_mode="HTML"
    )
    
    # Переходим в состояние редактирования номера слова
    await state.set_state(AdminStates.editing_word_number)
    
    await callback.answer()


@word_router.message(AdminStates.editing_word_foreign)
async def process_word_foreign_input(message: Message, state: FSMContext):
    """
    Process foreign word input from admin.
    
    Args:
        message: The message object from Telegram
        state: The FSM state context
    """
    await process_word_field_update(message, state, "word_foreign", "иностранного слова")


@word_router.message(AdminStates.editing_word_translation)
async def process_word_translation_input(message: Message, state: FSMContext):
    """
    Process translation input from admin.
    
    Args:
        message: The message object from Telegram
        state: The FSM state context
    """
    await process_word_field_update(message, state, "translation", "перевода")


@word_router.message(AdminStates.editing_word_transcription)
async def process_word_transcription_input(message: Message, state: FSMContext):
    """
    Process transcription input from admin.
    
    Args:
        message: The message object from Telegram
        state: The FSM state context
    """
    await process_word_field_update(message, state, "transcription", "транскрипции")


@word_router.message(AdminStates.editing_word_number)
async def process_word_number_input(message: Message, state: FSMContext):
    """
    Process word number input from admin.
    
    Args:
        message: The message object from Telegram
        state: The FSM state context
    """
    # Проверяем, что введено число
    if not message.text.isdigit():
        await message.reply(
            "❌ Пожалуйста, введите корректный номер слова (только цифры)."
        )
        return
    
    word_number = int(message.text)
    await process_word_field_update(message, state, "word_number", "номера слова", word_number)


async def process_word_field_update(message: Message, state: FSMContext, field_name: str, field_display_name: str, value=None):
    """
    Common function to update word field.
    
    Args:
        message: The message object from Telegram
        state: The FSM state context
        field_name: Name of the field to update
        field_display_name: Display name for user messages
        value: Value to update (if None, uses message.text)
    """
    # Получаем данные состояния
    user_data = await state.get_data()
    word_id = user_data.get('editing_word_id')
    
    if not word_id:
        await message.answer("❌ Ошибка: ID слова не найден. Начните редактирование заново.")
        await state.clear()
        return
    
    # Получаем клиент API
    api_client = get_api_client_from_bot(message.bot)
    
    # Подготавливаем данные для обновления
    update_value = value if value is not None else message.text
    update_data = {field_name: update_value}
    
    # Обновляем слово через API
    try:
        update_response = await api_client.update_word(word_id, update_data)
        
        if not update_response["success"]:
            error_msg = update_response.get("error", "Неизвестная ошибка")
            await message.answer(f"Ошибка при обновлении {field_display_name}: {error_msg}")
            logger.error(f"Failed to update word {word_id} field {field_name}. Error: {error_msg}")
            await state.clear()
            return
        
        await message.answer(
            f"✅ {field_display_name.capitalize()} успешно обновлено!"
        )
        
        # Возвращаемся к экрану редактирования слова
        await state.set_state(AdminStates.viewing_word_details)
        await show_word_fields_edit_screen(message, word_id)
        
    except Exception as e:
        logger.error(f"Error updating word field {field_name}: {e}")
        await message.answer(
            f"❌ Ошибка при обновлении {field_display_name}: {str(e)}"
        )
        await state.clear()


async def show_word_fields_edit_screen(message: Message, word_id: str):
    """
    Show word edit screen after successful update.
    
    Args:
        message: The message object from Telegram
        word_id: ID of the updated word
    """
    # Получаем клиент API
    api_client = get_api_client_from_bot(message.bot)
    
    # Получаем обновленную информацию о слове
    word_response = await api_client.get_word(word_id)
    
    if not word_response["success"] or not word_response["result"]:
        error_msg = word_response.get("error", "Слово не найдено")
        await message.answer(f"Ошибка при получении слова: {error_msg}")
        logger.error(f"Failed to get updated word by ID {word_id}. Error: {error_msg}")
        return
    
    word = word_response["result"]
    
    # Получаем информацию о языке
    language_response = await api_client.get_language(word['language_id'])
    language_name = "Неизвестный язык"
    
    if language_response["success"] and language_response["result"]:
        language = language_response["result"]
        language_name = f"{language['name_ru']} ({language['name_foreign']})"
    
    # Формируем сообщение с обновленной информацией о слове
    word_info = (
        f"✏️ <b>Редактирование слова</b>\n\n"
        f"Язык: <b>{language_name}</b>\n"
        f"Номер: <b>{word.get('word_number', 'N/A')}</b>\n"
        f"Слово: <b>{word.get('word_foreign', 'N/A')}</b>\n"
        f"Транскрипция: <b>{word.get('transcription', 'N/A')}</b>\n"
        f"Перевод: <b>{word.get('translation', 'N/A')}</b>\n"
        f"Радикалы: <b>{word.get('radicals', 'N/A')}</b>\n"
        f"Ссылки: <b>{word.get('references', 'N/A')}</b>\n"
        f"Тоны: <b>{word.get('tones', 'N/A')}</b>\n\n"
        f"Выберите поле для редактирования:"
    )
    
    # Создаем клавиатуру для редактирования
    from app.bot.keyboards.admin_keyboards import get_word_filed_edit_keyboard
    keyboard = get_word_filed_edit_keyboard(word_id, word['language_id'])
    
    await message.answer(
        word_info,
        parse_mode="HTML",
        reply_markup=keyboard
    )


@word_router.callback_query(AdminStates.viewing_word_details, F.data == CallbackData.BACK_TO_WORD_DETAILS)
@word_router.callback_query(F.data == CallbackData.BACK_TO_WORD_DETAILS)
async def process_back_to_word_details(callback: CallbackQuery, state: FSMContext):
    """
    Handle going back to word details from edit menu.
    
    Args:
        callback: The callback query from Telegram
        state: The FSM state context
    """
    user_data = await state.get_data()
    word_id = user_data.get('editing_word_id')
    
    if not word_id:
        await callback.message.answer("❌ Ошибка: ID слова не найден")
        await callback.answer()
        return
    
    # Возвращаемся к экрану просмотра слова
    await show_word_details_screen(callback, word_id, state)
    
    await callback.answer()


async def show_word_details_screen(message_or_callback: CallbackQuery, word_id: str, state):
    """
    Show word details screen.
    
    Args:
        callback: The callback query from Telegram
        word_id: ID of the word
    """
    user_id = message_or_callback.from_user.id
    username = message_or_callback.from_user.username
    full_name = message_or_callback.from_user.full_name

    logger.info(f"'show_edit_word' from: {full_name}")

    if isinstance(message_or_callback, CallbackQuery):
        message = message_or_callback.message
    else:
        message = message_or_callback

    # Получаем клиент API
    api_client = get_api_client_from_bot(message_or_callback.bot)
    
    # Получаем информацию о слове
    word_response = await api_client.get_word(word_id)
    
    if not word_response["success"] or not word_response["result"]:
        error_msg = word_response.get("error", "Слово не найдено")
        await message.answer(f"Ошибка: {error_msg}")
        logger.error(f"Failed to get word by ID {word_id}. Error: {error_msg}")
        return
    
    word = word_response["result"]
    
    # Получаем информацию о языке
    language_id = word['language_id']
    language_response = await api_client.get_language(language_id)
    language_name = "Неизвестный язык"
    
    if language_response["success"] and language_response["result"]:
        language = language_response["result"]
        language_name = f"{language['name_ru']} ({language['name_foreign']})"
    
    # Получаем данные текущего пользователя
    user_info = ""
    
    # Получаем данные состояния 
    state_data = await state.get_data()

    # проверяем наличие db_user_id
    db_user_id = state_data.get('db_user_id')
    
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
        f"📖 <b>Информация о слове</b>\n\n"
        f"Язык: <b>{language_name}</b>\n"
        f"Номер: <b>{word.get('word_number', 'N/A')}</b>\n"
        f"Слово: <code>{word.get('word_foreign', 'N/A')}</code>\n"
        f"Транскрипция: <code>{word.get('transcription', 'N/A')}</code>\n"
        f"Перевод: <code>{word.get('translation', 'N/A')}</code>\n"
        f"Радикалы: <code>{word.get('radicals', 'N/A')}</code>\n"
        f"Ссылки: <code>{word.get('references', 'N/A')}</code>\n"
        f"Тоны: <code>{word.get('tones', 'N/A')[:MAX_MESSAGE_LENGTH]}</code>\n"
        f"ID: <code>{word_id}</code>"
        f"{user_info}"
    )
    
    from_study = state_data.get("return_to_study", False)

    # Выбираем клавиатуру в зависимости от контекста
    if from_study:
        keyboard = get_word_actions_keyboard_from_study(word_id, language_id)
    else:
        keyboard = get_word_actions_keyboard(word_id, language_id)

    await message.answer(
        word_info,
        parse_mode="HTML",
        reply_markup=keyboard
    )
    
@word_router.callback_query(AdminStates.viewing_word_search_results, F.data.startswith("delete_word_"))
@word_router.callback_query(AdminStates.viewing_word_details, F.data.startswith("delete_word_"))
@word_router.callback_query(F.data.startswith("delete_word_"))
async def process_delete_word(callback: CallbackQuery, state: FSMContext):
    """
    Start word deletion process with confirmation.
    
    Args:
        callback: The callback query from Telegram
        state: The FSM state context
    """
    from app.utils.callback_constants import CallbackParser
    
    # Парсим callback для получения word_id
    word_id = CallbackParser.parse_delete_word(callback.data)
    
    if not word_id:
        await callback.message.answer("❌ Ошибка: ID слова не найден")
        await callback.answer()
        return
    
    logger.info(f"'delete_word' callback for word ID: {word_id}")
    
    # Получаем клиент API
    api_client = get_api_client_from_bot(callback.bot)
    
    # Получаем информацию о слове для отображения в подтверждении
    word_response = await api_client.get_word(word_id)
    
    if not word_response["success"] or not word_response["result"]:
        error_msg = word_response.get("error", "Слово не найдено")
        await callback.message.answer(f"Ошибка: {error_msg}")
        await callback.answer()
        logger.error(f"Failed to get word by ID {word_id}. Error: {error_msg}")
        return
    
    word = word_response["result"]
    
    # Получаем информацию о языке
    language_response = await api_client.get_language(word['language_id'])
    language_name = "Неизвестный язык"
    
    if language_response["success"] and language_response["result"]:
        language = language_response["result"]
        language_name = f"{language['name_ru']} ({language['name_foreign']})"
    
    # Устанавливаем состояние подтверждения удаления слова
    await state.set_state(AdminStates.confirming_word_deletion)
    await state.update_data(deleting_word_id=word_id, word_language_id=word['language_id'])
    
    # Формируем сообщение с подтверждением
    confirmation_message = (
        f"🗑️ <b>Подтверждение удаления слова</b>\n\n"
        f"Вы действительно хотите удалить это слово?\n\n"
        f"Язык: <b>{language_name}</b>\n"
        f"Номер: <b>{word.get('word_number', 'N/A')}</b>\n"
        f"Слово: <b>{word.get('word_foreign', 'N/A')}</b>\n"
        f"Транскрипция: <b>{word.get('transcription', 'N/A')}</b>\n"
        f"Перевод: <b>{word.get('translation', 'N/A')}</b>\n"
        f"Радикалы: <b>{word.get('radicals', 'N/A')}</b>\n"
        f"Ссылки: <b>{word.get('references', 'N/A')}</b>\n"
        f"Тоны: <b>{word.get('tones', 'N/A')}</b>\n\n"
        f"⚠️ <b>Внимание!</b> Это действие также удалит:\n"
        f"• Все пользовательские данные для этого слова\n"
        f"• Все созданные подсказки для этого слова\n"
        f"• Статистику изучения этого слова\n\n"
        f"Это действие не может быть отменено!"
    )
    
    # Создаем клавиатуру подтверждения
    from app.bot.keyboards.admin_keyboards import get_word_delete_confirmation_keyboard
    keyboard = get_word_delete_confirmation_keyboard(word_id)
    
    await callback.message.edit_text(
        confirmation_message,
        parse_mode="HTML",
        reply_markup=keyboard
    )
    
    await callback.answer()


@word_router.callback_query(AdminStates.confirming_word_deletion, F.data.startswith("confirm_word_delete_"))
@word_router.callback_query(F.data.startswith("confirm_word_delete_"))
async def process_confirm_word_delete(callback: CallbackQuery, state: FSMContext):
    """
    Confirm and execute word deletion.
    
    Args:
        callback: The callback query from Telegram
        state: The FSM state context
    """
    from app.utils.callback_constants import CallbackParser
    
    # Парсим callback для получения word_id
    word_id = CallbackParser.parse_confirm_word_delete(callback.data)
    
    if not word_id:
        await callback.message.answer("❌ Ошибка: ID слова не найден")
        await callback.answer()
        return
    
    logger.info(f"'confirm_word_delete' callback for word ID: {word_id}")
    
    # Получаем данные из состояния
    user_data = await state.get_data()
    language_id = user_data.get('word_language_id')
    
    # Получаем клиент API
    api_client = get_api_client_from_bot(callback.bot)
    
    # Получаем информацию о слове перед удалением (для логирования)
    word_response = await api_client.get_word(word_id)
    word_info = "неизвестное слово"
    
    if word_response["success"] and word_response["result"]:
        word = word_response["result"]
        word_info = f"{word.get('word_foreign', 'N/A')} - {word.get('translation', 'N/A')}"
    
    # Удаляем слово через API
    try:
        delete_response = await api_client.delete_word(word_id)
        
        if not delete_response["success"]:
            error_msg = delete_response.get("error", "Неизвестная ошибка")
            await callback.message.answer(f"Ошибка при удалении слова: {error_msg}")
            logger.error(f"Failed to delete word {word_id}. Error: {error_msg}")
            await callback.answer()
            return
        
        # Успешное удаление
        result = delete_response["result"]
        success_message = f"✅ Слово успешно удалено!\n\n"
        
        if isinstance(result, dict) and result.get('message'):
            success_message += f"Сообщение: {result.get('message')}"
        else:
            success_message += f"Удалено слово: {word_info}"
        
        await callback.message.answer(success_message)
        
        # Логируем успешное удаление
        logger.info(f"Word {word_id} ({word_info}) successfully deleted by admin")
        
        # возвращаемся в админку
        await state.set_state(AdminStates.main_menu)
        from app.bot.handlers.admin.admin_basic_handlers import handle_admin_mode
        await handle_admin_mode(callback, state, is_callback=True)
        
    except Exception as e:
        logger.error(f"Error deleting word {word_id}: {e}")
        await callback.message.answer(
            f"❌ Критическая ошибка при удалении слова: {str(e)}"
        )
        # Очищаем состояние при критической ошибке
        await state.clear()
    
    await callback.answer()


@word_router.callback_query(AdminStates.confirming_word_deletion, F.data.startswith("cancel_word_delete_"))
@word_router.callback_query(F.data.startswith("cancel_word_delete_"))
async def process_cancel_word_delete(callback: CallbackQuery, state: FSMContext):
    """
    Cancel word deletion and return to word details.
    
    Args:
        callback: The callback query from Telegram
        state: The FSM state context
    """
    from app.utils.callback_constants import CallbackParser
    
    # Парсим callback для получения word_id
    word_id = CallbackParser.parse_cancel_word_delete(callback.data)
    
    if not word_id:
        await callback.message.answer("❌ Ошибка: ID слова не найден")
        await callback.answer()
        return
    
    logger.info(f"'cancel_word_delete' callback for word ID: {word_id}")
    
    # Получаем данные из состояния
    user_data = await state.get_data()
    language_id = user_data.get('word_language_id')
    
    await callback.message.answer("🚫 Удаление слова отменено")
    
    # Возвращаемся к деталям слова
    await state.set_state(AdminStates.viewing_word_details)
    await state.update_data(editing_word_id=word_id)
    
    # Показываем экран с деталями слова
    await show_word_details_screen(callback, word_id, state)
    
    await callback.answer()


@word_router.callback_query(F.data.startswith(CallbackData.ADMIN_EDIT_WORD_FROM_STUDY), StudyStates.studying)
@word_router.callback_query(F.data.startswith(CallbackData.ADMIN_EDIT_WORD_FROM_STUDY), StudyStates.viewing_word_details)
async def process_edit_word_from_study(callback: CallbackQuery, state: FSMContext):
    """
    Show word editing menu when coming from study mode.
    
    Args:
        callback: The callback query from Telegram
        state: The FSM state context
    """
    from app.utils.callback_constants import CallbackParser
    
    # Парсим callback для получения word_id
    word_id = CallbackParser.parse_admin_edit_from_study(callback.data)
    
    if not word_id:
        await callback.message.answer("❌ Ошибка: ID слова не найден")
        await callback.answer()
        return
    
    logger.info(f"'edit_word_from_study' callback for word ID: {word_id}")
    
    # Сохраняем контекст возврата к изучению
    await state.update_data(
        return_to_study=True,
    )

    # Получаем клиент API
    api_client = get_api_client_from_bot(callback.bot)
    
    # Получаем информацию о слове
    word_response = await api_client.get_word(word_id)
    
    if not word_response["success"] or not word_response["result"]:
        error_msg = word_response.get("error", "Слово не найдено")
        await callback.message.answer(f"Ошибка: {error_msg}")
        await callback.answer()
        logger.error(f"Failed to get word by ID {word_id}. Error: {error_msg}")
        return
    
    word = word_response["result"]
        
    await callback.answer()

    await show_word_details_screen(callback, word_id, state)

