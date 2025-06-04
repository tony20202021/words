"""
Handlers for column type selection and processing.
Updated with FSM states for better navigation control.
"""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from app.utils.logger import setup_logger
from app.bot.states.centralized_states import AdminStates
from app.utils.callback_constants import CallbackData

logger = setup_logger(__name__)

# Создаем роутер для обработчиков выбора типа колонки
column_type_router = Router()

@column_type_router.callback_query(AdminStates.configuring_columns, F.data.startswith(CallbackData.SELECT_COLUMN_TYPE))
@column_type_router.callback_query(AdminStates.configuring_upload_settings, F.data.startswith(CallbackData.SELECT_COLUMN_TYPE))
async def process_select_column_type(callback: CallbackQuery, state: FSMContext):
    """
    Process column type selection.
    
    Args:
        callback: The callback query from Telegram
        state: The FSM state context
    """
    # Извлекаем ID языка из callback_data
    language_id = callback.data.split(":")[-1]
    logger.info(f"Column type selection for language ID: {language_id}")
    
    # ✅ НОВОЕ: Устанавливаем состояние конфигурации колонок
    await state.set_state(AdminStates.configuring_columns)
    
    # Получаем текущие данные состояния для отображения текущих номеров колонок
    user_data = await state.get_data()
    
    # Создаем билдер для клавиатуры
    builder = InlineKeyboardBuilder()
    
    # Кнопки для выбора типа колонки с текущими значениями
    column_types = [
        ("number", "Колонка номера", "select_number"),
        ("word", "Колонка слова", "select_word"),
        ("transcription", "Колонка транскрипции", "select_transcription"),
        ("translation", "Колонка перевода", "select_translation"),
    ]
    
    for col_type, display_name, callback_data in column_types:
        current_value = user_data.get(f"column_{col_type}")
        value_text = f" (сейчас: {current_value})" if current_value is not None else ""
        builder.add(InlineKeyboardButton(
            text=f"📊 {display_name}{value_text}",
            callback_data=callback_data
        ))
    
    # Кнопка подтверждения и возврата
    builder.add(InlineKeyboardButton(
        text="✅ Подтвердить и загрузить",
        callback_data=CallbackData.CONFIRM_UPLOAD
    ))
    builder.add(InlineKeyboardButton(
        text="⬅️ Назад к настройкам",
        callback_data=CallbackData.BACK_TO_SETTINGS
    ))
    
    # Настраиваем ширину строки клавиатуры (по 1 кнопке в ряд)
    builder.adjust(1)
    
    await callback.message.edit_text(
        "📋 Выберите тип колонки, который хотите настроить:\n\n"
        "После выбора типа колонки вам будет предложено ввести её номер\n"
        "(нумерация начинается с 0)",
        reply_markup=builder.as_markup()
    )
    
    await callback.answer()

@column_type_router.callback_query(AdminStates.configuring_columns, F.data.startswith("select_"))
async def process_column_type_selection(callback: CallbackQuery, state: FSMContext):
    """
    Process column type selection and prompt for column index.
    
    Args:
        callback: The callback query from Telegram
        state: The FSM state context
    """
    # Извлекаем тип колонки из callback_data
    column_type = callback.data.split("_")[-1]
    logger.info(f"Selected column type: {column_type}")
    
    # Получаем текущее значение колонки
    user_data = await state.get_data()
    current_value = user_data.get(f"column_{column_type}")
    current_info = f" (текущее значение: {current_value})" if current_value is not None else ""
    
    # Сохраняем выбранный тип колонки и сообщение в состоянии
    await state.update_data(
        selected_column_type=column_type,
        column_settings_message_id=callback.message.message_id,
        column_settings_chat_id=callback.message.chat.id
    )
    
    # ✅ НОВОЕ: Переходим в состояние ввода номера колонки
    await state.set_state(AdminStates.input_column_number)
    
    # Заменяем сообщение на запрос ввода номера колонки
    await callback.message.edit_text(
        f"Введите номер колонки для {column_type}{current_info} (начиная с 0):"
    )
    
    await callback.answer()

@column_type_router.message(AdminStates.input_column_number)
async def process_column_number_input(message: Message, state: FSMContext):
    """
    Process column number input.
    
    Args:
        message: The message object from Telegram
        state: The FSM state context
    """
    # Получаем данные состояния
    user_data = await state.get_data()
    column_type = user_data.get('selected_column_type')
    message_id = user_data.get('column_settings_message_id')
    
    if not column_type:
        await message.answer("❌ Ошибка: тип колонки не найден. Начните процесс заново.")
        # ✅ НОВОЕ: Возвращаемся к настройкам загрузки при ошибке
        await state.set_state(AdminStates.configuring_upload_settings)
        return
    
    # Проверяем, что введен корректный номер колонки
    try:
        column_index = int(message.text)
        if column_index < 0:
            raise ValueError("Номер колонки должен быть не меньше 0")
    except ValueError:
        # Временное сообщение об ошибке, которое будет удалено
        error_message = await message.answer(
            "❌ Пожалуйста, введите корректный номер колонки (целое неотрицательное число)"
        )
        # Отложенное удаление сообщения через 5 секунд
        try:
            await error_message.delete_delayed(delay=5)
        except:
            # Если delete_delayed не поддерживается, просто продолжаем
            pass
        return
    
    # Сохраняем номер колонки в состоянии
    column_key = f"column_{column_type}"
    await state.update_data({column_key: column_index})
    
    # Получаем обновленные данные состояния
    user_data = await state.get_data()
    
    # ✅ НОВОЕ: Возвращаемся к состоянию настройки колонок
    await state.set_state(AdminStates.configuring_columns)
    
    # Создаем билдер для клавиатуры
    builder = InlineKeyboardBuilder()
    
    # Кнопки для выбора типа колонки с обновленными значениями
    column_types = [
        ("number", "Колонка номера", "select_number"),
        ("word", "Колонка слова", "select_word"),
        ("transcription", "Колонка транскрипции", "select_transcription"),
        ("translation", "Колонка перевода", "select_translation"),
    ]
    
    for col_type, display_name, callback_data in column_types:
        current_value = user_data.get(f"column_{col_type}")
        value_text = f" (сейчас: {current_value})" if current_value is not None else ""
        builder.add(InlineKeyboardButton(
            text=f"📊 {display_name}{value_text}",
            callback_data=callback_data
        ))
    
    # Кнопка подтверждения и возврата
    builder.add(InlineKeyboardButton(
        text="✅ Подтвердить и загрузить",
        callback_data=CallbackData.CONFIRM_UPLOAD
    ))
    builder.add(InlineKeyboardButton(
        text="⬅️ Назад к настройкам",
        callback_data=CallbackData.BACK_TO_SETTINGS
    ))
    
    # Настраиваем ширину строки клавиатуры (по 1 кнопке в ряд)
    builder.adjust(1)
    
    # Отображаем текущие настройки колонок
    current_settings = []
    for col_type, display_name, _ in column_types:
        col_key = f"column_{col_type}"
        col_value = user_data.get(col_key)
        if col_value is not None:
            current_settings.append(f"✅ {display_name}: {col_value}")
    
    settings_text = "\n".join(current_settings) if current_settings else "Колонки еще не настроены"
    
    # Обновляем оригинальное сообщение с настройками
    try:
        # Редактируем исходное сообщение
        await message.bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=message_id,
            text=f"📋 Выберите тип колонки, который хотите настроить:\n\n"
                f"✅ {column_key.replace('column_', 'Колонка ')} установлена на {column_index}\n\n"
                f"Текущие настройки колонок:\n{settings_text}\n\n"
                f"Выберите следующую колонку для настройки или подтвердите загрузку:",
            reply_markup=builder.as_markup()
        )
    except Exception as e:
        logger.error(f"Error updating message: {e}")
        # Если не удалось обновить, отправляем новое сообщение
        await message.answer(
            f"📋 Выберите тип колонки, который хотите настроить:\n\n"
            f"✅ {column_key.replace('column_', 'Колонка ')} установлена на {column_index}\n\n"
            f"Текущие настройки колонок:\n{settings_text}\n\n"
            f"Выберите следующую колонку для настройки или подтвердите загрузку:",
            reply_markup=builder.as_markup()
        )
    
    # Удаляем сообщение с введенным номером, чтобы не засорять чат
    try:
        await message.delete()
    except Exception as e:
        logger.error(f"Error deleting message: {e}")

@column_type_router.message(AdminStates.input_column_number, F.text == "/cancel")
async def process_cancel_column_input(message: Message, state: FSMContext):
    """
    Handle canceling column number input.
    
    Args:
        message: The message object from Telegram
        state: The FSM state context
    """
    logger.info("Cancel column number input")
    
    # ✅ НОВОЕ: Возвращаемся к состоянию конфигурации колонок
    await state.set_state(AdminStates.configuring_columns)
    
    await message.answer(
        "❌ Ввод номера колонки отменен.\n\n"
        "Вы можете выбрать другую колонку для настройки или подтвердить загрузку с текущими настройками."
    )

# ✅ НОВОЕ: Обработчик возврата в админку из ввода номера колонки
@column_type_router.callback_query(AdminStates.input_column_number, F.data == CallbackData.BACK_TO_ADMIN)
async def process_back_to_admin_from_column_input(callback: CallbackQuery, state: FSMContext):
    """
    Handle going back to admin menu from column number input.
    
    Args:
        callback: The callback query from Telegram
        state: The FSM state context
    """
    logger.info("Back to admin from column number input")
    
    # Очищаем состояние
    await state.clear()
    
    # Импортируем и вызываем функцию возврата в административное меню
    from app.bot.handlers.admin.admin_basic_handlers import handle_admin_mode
    await handle_admin_mode(callback, state, is_callback=True)
    
    await callback.answer()
    