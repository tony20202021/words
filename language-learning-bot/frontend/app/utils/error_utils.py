"""
Utilities for handling API errors and other common error cases.
Enhanced with meta-state transitions for system-wide error handling.
"""

import logging
from typing import Dict, Any, Union, Tuple, Optional, List
from datetime import datetime
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

# Импортируем централизованные состояния
from app.bot.states.centralized_states import StudyStates, HintStates, SettingsStates, AdminStates, CommonStates

logger = logging.getLogger(__name__)

async def handle_api_error(
    response: Dict[str, Any], 
    message_obj: Union[Message, CallbackQuery], 
    log_prefix: str = "API Error",
    user_prefix: str = "Ошибка",
    transition_to_error_state: bool = True
) -> bool:
    """
    Handle API error response and send user-friendly message.
    Enhanced with meta-state transition capability.
    
    Args:
        response: API response dictionary with 'success' and 'error' keys
        message_obj: Message or CallbackQuery object to respond to
        log_prefix: Prefix for log message
        user_prefix: Prefix for user message
        transition_to_error_state: Whether to transition to CommonStates.handling_api_error
        
    Returns:
        bool: True if error was handled, False if no error
    """
    if not response["success"]:
        status = response.get("status", "unknown")
        error_msg = response.get("error", "Неизвестная ошибка")
        
        # Log the error with full details
        logger.error(f"{log_prefix}: status={status}, error={error_msg}")
        
        # Determine error severity and user message
        if status == 0:
            # Connection error
            user_message = f"🔌 {user_prefix}: Нет соединения с сервером"
            if transition_to_error_state:
                await _transition_to_connection_lost(message_obj)
        elif status >= 500:
            # Server error
            user_message = f"🔥 {user_prefix}: Ошибка сервера ({status})"
            if transition_to_error_state:
                await _transition_to_api_error(message_obj, error_msg)
        elif status == 429:
            # Rate limit
            user_message = f"⏳ {user_prefix}: Слишком много запросов, попробуйте позже"
        else:
            # Other client errors
            user_message = f"❌ {user_prefix}: {error_msg}"
            if transition_to_error_state and status >= 400:
                await _transition_to_api_error(message_obj, error_msg)
        
        # Send user-friendly message
        if isinstance(message_obj, CallbackQuery):
            await message_obj.answer("Произошла ошибка", show_alert=True)
            await message_obj.message.answer(user_message)
        else:
            await message_obj.answer(user_message)
            
        return True
    return False

async def _transition_to_api_error(message_obj: Union[Message, CallbackQuery], error_details: str = ""):
    """
    Transition user to API error handling state.
    
    Args:
        message_obj: Message or CallbackQuery object
        error_details: Additional error details
    """
    try:
        # Get state from message context
        if hasattr(message_obj, 'state'):
            state = message_obj.state
        else:
            # Try to get state from bot data (this might not work in all cases)
            return
        
        await state.set_state(CommonStates.handling_api_error)
        await state.update_data(api_error_details=error_details, api_error_time=str(datetime.now()))
        
        logger.info(f"Transitioned user to API error state: {error_details}")
        
    except Exception as e:
        logger.error(f"Failed to transition to API error state: {e}")

async def _transition_to_connection_lost(message_obj: Union[Message, CallbackQuery]):
    """
    Transition user to connection lost state.
    
    Args:
        message_obj: Message or CallbackQuery object
    """
    try:
        # Get state from message context
        if hasattr(message_obj, 'state'):
            state = message_obj.state
        else:
            return
        
        await state.set_state(CommonStates.connection_lost)
        await state.update_data(connection_lost_time=str(datetime.now()))
        
        logger.info("Transitioned user to connection lost state")
        
    except Exception as e:
        logger.error(f"Failed to transition to connection lost state: {e}")

async def handle_unknown_command(
    message: Message,
    state: FSMContext,
    command_text: str = ""
) -> None:
    """
    Handle unknown command by transitioning to appropriate state.
    
    Args:
        message: Message object
        state: FSM state context
        command_text: The unknown command text
    """
    await state.set_state(CommonStates.unknown_command)
    await state.update_data(
        unknown_command=command_text,
        unknown_command_time=str(datetime.now())
    )
    
    logger.info(f"Transitioned user to unknown command state: {command_text}")
    
    # Send immediate feedback
    await message.answer(
        f"❓ Команда '{command_text}' не распознана.\n"
        "Подбираю подходящие варианты..."
    )

async def safe_api_call(
    api_call_func,
    message_obj: Union[Message, CallbackQuery],
    error_context: str = "API вызов",
    handle_errors: bool = True
) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """
    Safely execute API call with automatic error handling and state transitions.
    
    Args:
        api_call_func: Async function that makes API call
        message_obj: Message or CallbackQuery object for error reporting
        error_context: Context description for logging
        handle_errors: Whether to handle errors automatically
        
    Returns:
        Tuple[bool, Optional[Dict]]: (success, result) tuple
    """
    try:
        response = await api_call_func()
        
        if handle_errors and not response.get("success", False):
            await handle_api_error(response, message_obj, f"Safe API call: {error_context}")
            return False, None
        
        return response.get("success", False), response.get("result")
        
    except Exception as e:
        logger.error(f"Exception in safe API call ({error_context}): {e}", exc_info=True)
        
        if handle_errors:
            error_message = f"❌ Ошибка при выполнении операции: {error_context}"
            
            if isinstance(message_obj, CallbackQuery):
                await message_obj.answer("Ошибка выполнения", show_alert=True)
                await message_obj.message.answer(error_message)
            else:
                await message_obj.answer(error_message)
        
        return False, None

async def validate_state_data(
    state: FSMContext,
    required_keys: List[str],
    message_obj: Union[Message, CallbackQuery],
    error_message: str = "Ошибка: недостаточно данных"
) -> Tuple[bool, Dict[str, Any]]:
    """
    Validate that all required keys are present in the state data.
    Enhanced with better error context and recovery suggestions.
    
    Args:
        state: FSM state context
        required_keys: List of required keys
        message_obj: Message or CallbackQuery object to respond to
        error_message: Error message to display
        
    Returns:
        Tuple[bool, Dict[str, Any]]: (is_valid, state_data) tuple
    """
    state_data = await state.get_data()
    
    # Check for missing keys
    missing_keys = [key for key in required_keys if key not in state_data or not state_data.get(key)]
    
    if missing_keys:
        # Log the error
        logger.error(f"Missing required state data: {', '.join(missing_keys)}")
        # logger.error(f"{state_data}")
        
        # Create contextual error message
        detailed_message = f"{error_message}\n\nОтсутствующие данные: {', '.join(missing_keys)}"
        
        # Add recovery suggestions based on missing keys
        recovery_suggestions = _get_recovery_suggestions(missing_keys)
        if recovery_suggestions:
            detailed_message += f"\n\nДля исправления:\n{recovery_suggestions}"
        
        # Handle different message object types
        if isinstance(message_obj, CallbackQuery):
            await message_obj.answer("Данные сессии неполные", show_alert=True)
            await message_obj.message.answer(detailed_message)
        else:
            await message_obj.answer(detailed_message)
            
        return False, state_data
    
    return True, state_data

def _get_recovery_suggestions(missing_keys: List[str]) -> str:
    """
    Get recovery suggestions based on missing state keys.
    
    Args:
        missing_keys: List of missing keys
        
    Returns:
        str: Recovery suggestions
    """
    suggestions = []
    
    if "db_user_id" in missing_keys:
        suggestions.append("• /start - перерегистрироваться")
    
    if "current_language" in missing_keys:
        suggestions.append("• /language - выбрать язык изучения")
    
    if "study_words" in missing_keys:
        suggestions.append("• /study - начать изучение заново")
    
    if any("hint" in key for key in missing_keys):
        suggestions.append("• Вернуться к изучению слов")
    
    if not suggestions:
        suggestions.append("• /start - перезапустить бота")
    
    return "\n".join(suggestions)

def validate_word_data(word: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Validate that word data contains all required fields.
    
    Args:
        word: Word data dictionary
        
    Returns:
        Tuple[bool, List[str]]: (is_valid, missing_fields) tuple
    """
    required_fields = ["_id", "word_foreign", "translation", "language_id"]
    missing = [field for field in required_fields if field not in word or not word.get(field)]
    
    if missing:
        logger.warning(f"Word data missing required fields: {', '.join(missing)}")
        return False, missing
    
    return True, []

def get_word_id(word: Dict[str, Any]) -> Optional[str]:
    """
    Get word ID from word data, handling different field names.
    
    Args:
        word: Word data dictionary
        
    Returns:
        Optional[str]: Word ID or None if not found
    """
    # Check different possible field names for ID
    for id_field in ["_id", "id", "word_id"]:
        if id_field in word and word[id_field]:
            return word[id_field]
    return None

def is_command(text: str) -> bool:
    """
    Проверяет, является ли текст командой Telegram.
    
    Args:
        text: Текст для проверки
        
    Returns:
        bool: True, если текст является командой, иначе False
    """
    if not text:
        return False
    
    # Команды начинаются с символа / и состоят из букв, цифр и подчеркиваний
    # Также могут содержать @ и название бота
    text = text.strip()
    if text.startswith('/'):
        # Проверяем, что после / идет хотя бы один символ
        command_part = text[1:].split('@')[0]  # Отсекаем @bot_name если есть
        return len(command_part) > 0
        
    return False

# ENHANCED: Валидация состояний FSM с meta-state поддержкой

async def validate_study_state(
    state: FSMContext,
    message_obj: Union[Message, CallbackQuery],
    expected_states: Optional[List] = None
) -> bool:
    """
    Проверяет, что пользователь находится в правильном состоянии изучения.
    Enhanced with automatic recovery via meta-states.
    
    Args:
        state: FSM state context
        message_obj: Message or CallbackQuery object to respond to
        expected_states: Список ожидаемых состояний (опционально)
        
    Returns:
        bool: True если состояние корректно
    """
    current_state = await state.get_state()
    
    # Если не указаны ожидаемые состояния, проверяем любое из состояний изучения
    if expected_states is None:
        expected_states = [
            StudyStates.studying.state,
            StudyStates.viewing_word_details.state,
            StudyStates.confirming_word_knowledge.state,
            StudyStates.study_completed.state
        ]
    else:
        # Преобразуем State объекты в строки
        expected_states = [
            state.state if hasattr(state, 'state') else str(state) 
            for state in expected_states
        ]
    
    if current_state not in expected_states:
        logger.warning(f"Invalid study state: current={current_state}, expected={expected_states}")
        
        error_message = (
            "⚠️ Действие недоступно в текущем состоянии.\n"
            "Используйте команду /study для начала изучения."
        )
        
        if isinstance(message_obj, CallbackQuery):
            await message_obj.answer("Неверное состояние", show_alert=True)
            await message_obj.message.answer(error_message)
        else:
            await message_obj.answer(error_message)
        
        return False
    
    return True

async def validate_hint_state(
    state: FSMContext,
    message_obj: Union[Message, CallbackQuery],
    expected_states: Optional[List] = None
) -> bool:
    """
    Проверяет, что пользователь находится в правильном состоянии работы с подсказками.
    
    Args:
        state: FSM state context
        message_obj: Message or CallbackQuery object to respond to
        expected_states: Список ожидаемых состояний (опционально)
        
    Returns:
        bool: True если состояние корректно
    """
    current_state = await state.get_state()
    
    # Если не указаны ожидаемые состояния, проверяем любое из состояний подсказок
    if expected_states is None:
        expected_states = [
            HintStates.creating.state,
            HintStates.editing.state,
            HintStates.viewing.state,
            HintStates.confirming_deletion.state
        ]
    else:
        # Преобразуем State объекты в строки
        expected_states = [
            state.state if hasattr(state, 'state') else str(state) 
            for state in expected_states
        ]
    
    if current_state not in expected_states:
        logger.warning(f"Invalid hint state: current={current_state}, expected={expected_states}")
        
        error_message = "⚠️ Действие с подсказкой недоступно в текущем состоянии.\nВозможно, истекла сессия работы с подсказками."
        
        if isinstance(message_obj, CallbackQuery):
            await message_obj.answer("Неверное состояние подсказки", show_alert=True)
            await message_obj.message.answer(error_message)
        else:
            await message_obj.answer(error_message)
        
        return False
    
    return True

async def handle_state_error(
    state: FSMContext,
    message_obj: Union[Message, CallbackQuery],
    error_context: str = "неизвестная операция"
) -> None:
    """
    Обработка ошибки состояния с автоматическим сбросом в безопасное состояние.
    Enhanced with better recovery options.
    
    Args:
        state: FSM state context
        message_obj: Message or CallbackQuery object to respond to
        error_context: Контекст ошибки для логирования
    """
    current_state = await state.get_state()
    logger.error(f"State error in {error_context}: current_state={current_state}")
    
    # Сохраняем важные данные перед сбросом
    state_data = await state.get_data()
    important_data = {
        "db_user_id": state_data.get("db_user_id"),
        "current_language": state_data.get("current_language"),
        "is_admin": state_data.get("is_admin", False)
    }
    
    # Сбрасываем состояние, но сохраняем важные данные
    await state.clear()
    await state.update_data(**{k: v for k, v in important_data.items() if v is not None})
    
    error_message = (
        f"❌ Произошла ошибка при выполнении операции.\n\n"
        f"**Контекст:** {error_context}\n\n"
        "Состояние сессии сброшено, но основные данные сохранены.\n\n"
        "Для продолжения используйте:\n"
        "/study - начать изучение слов\n"
        "/language - выбрать язык\n"
        "/settings - настройки\n"
        "/help - получить справку"
    )
    
    if isinstance(message_obj, CallbackQuery):
        await message_obj.answer("Ошибка состояния", show_alert=True)
        await message_obj.message.answer(error_message, parse_mode="Markdown")
    else:
        await message_obj.answer(error_message, parse_mode="Markdown")

# ENHANCED: Утилиты для работы с контекстными сообщениями об ошибках

def get_contextual_error_message(current_state: str) -> str:
    """
    Получить контекстное сообщение об ошибке в зависимости от текущего состояния.
    Enhanced with meta-states support.
    
    Args:
        current_state: Текущее состояние FSM
        
    Returns:
        str: Контекстное сообщение об ошибке
    """
    state_messages = {
        # Состояния изучения
        StudyStates.studying.state: (
            "Вы изучаете слова. Используйте кнопки под сообщениями для взаимодействия.\n"
            "Доступные команды: /cancel, /stats, /settings, /help"
        ),
        StudyStates.viewing_word_details.state: (
            "Вы просматриваете детали слова. Используйте кнопки для перехода к следующему слову.\n"
            "Доступные команды: /cancel, /help"
        ),
        StudyStates.confirming_word_knowledge.state: (
            "Подтвердите знание слова или измените решение, используя кнопки.\n"
            "Доступные команды: /cancel, /help"
        ),
        StudyStates.study_completed.state: (
            "Изучение завершено! Доступные команды:\n"
            "/study - начать заново, /stats - статистика, /settings - настройки"
        ),
        
        # Состояния подсказок
        HintStates.creating.state: (
            "Вы создаете подсказку. Отправьте текст или голосовое сообщение.\n"
            "Доступные команды: /cancel, /help"
        ),
        HintStates.editing.state: (
            "Вы редактируете подсказку. Отправьте новый текст или голосовое сообщение.\n"
            "Доступные команды: /cancel, /help"
        ),
        HintStates.viewing.state: (
            "Вы просматриваете подсказку. Используйте кнопки для навигации.\n"
            "Доступные команды: /cancel, /help"
        ),
        HintStates.confirming_deletion.state: (
            "Подтвердите удаление подсказки, используя кнопки.\n"
            "Доступные команды: /cancel, /help"
        ),
        
        # Состояния настроек
        SettingsStates.viewing_settings.state: (
            "Вы в настройках. Используйте кнопки для изменения параметров."
        ),
        SettingsStates.waiting_start_word.state: (
            "Введите номер слова для начала изучения."
        ),
        
        # Meta-состояния
        CommonStates.handling_api_error.state: (
            "Обрабатывается ошибка API. Используйте:\n"
            "/retry - повторить операцию\n"
            "/start - главное меню\n"
            "/status - проверить состояние системы"
        ),
        CommonStates.connection_lost.state: (
            "Потеряно соединение с сервером. Пожалуйста, подождите...\n"
            "Используйте /status для проверки соединения"
        ),
        CommonStates.unknown_command.state: (
            "Обрабатывается неизвестная команда. Будут предложены альтернативы."
        )
    }
    
    return state_messages.get(
        current_state, 
        "Используйте /help для получения информации о доступных командах."
    )

async def send_contextual_help(
    state: FSMContext,
    message_obj: Union[Message, CallbackQuery],
    additional_context: str = ""
) -> None:
    """
    Отправить контекстную справку в зависимости от текущего состояния.
    
    Args:
        state: FSM state context
        message_obj: Message or CallbackQuery object to respond to
        additional_context: Дополнительный контекст для сообщения
    """
    current_state = await state.get_state()
    contextual_message = get_contextual_error_message(current_state or "")
    
    help_message = "ℹ️ <b>Текущее состояние:</b>\n\n" + contextual_message
    
    if additional_context:
        help_message += f"\n\n<b>Дополнительная информация:</b>\n{additional_context}"
    
    if isinstance(message_obj, CallbackQuery):
        await message_obj.message.answer(help_message, parse_mode="HTML")
    else:
        await message_obj.answer(help_message, parse_mode="HTML")

# ENHANCED: Утилиты для валидации данных пользователя

async def validate_user_session(
    state: FSMContext,
    message_obj: Union[Message, CallbackQuery],
    require_language: bool = True,
    require_user_id: bool = True
) -> Tuple[bool, Dict[str, Any]]:
    """
    Проверить корректность сессии пользователя.
    Enhanced with automatic recovery suggestions.
    
    Args:
        state: FSM state context
        message_obj: Message or CallbackQuery object to respond to
        require_language: Требовать наличие выбранного языка
        require_user_id: Требовать наличие ID пользователя в БД
        
    Returns:
        Tuple[bool, Dict[str, Any]]: (is_valid, state_data) tuple
    """
    state_data = await state.get_data()
    issues = []
    
    if require_user_id and not state_data.get("db_user_id"):
        issues.append("не найден ID пользователя")
    
    if require_language and not state_data.get("current_language"):
        issues.append("не выбран язык для изучения")
    
    if issues:
        logger.warning(f"Invalid user session: {', '.join(issues)}")
        
        error_message = "⚠️ Проблема с сессией пользователя:\n" + "\n".join(f"• {issue}" for issue in issues)
        error_message += "\n\n**Для исправления используйте:**\n"
        
        if "не выбран язык" in str(issues):
            error_message += "/language - выбрать язык\n"
        
        if "не найден ID пользователя" in str(issues):
            error_message += "/start - перерегистрироваться\n"
        
        error_message += "/status - проверить состояние системы"
        
        if isinstance(message_obj, CallbackQuery):
            await message_obj.answer("Проблема с сессией", show_alert=True)
            await message_obj.message.answer(error_message, parse_mode="Markdown")
        else:
            await message_obj.answer(error_message, parse_mode="Markdown")
        
        return False, state_data
    
    return True, state_data

async def safe_state_operation(
    operation_func,
    state: FSMContext,
    message_obj: Union[Message, CallbackQuery],
    operation_name: str = "операция",
    fallback_state = None
):
    """
    Безопасное выполнение операции с автоматической обработкой ошибок состояния.
    Enhanced with meta-state transitions.
    
    Args:
        operation_func: Функция операции для выполнения
        state: FSM state context
        message_obj: Message or CallbackQuery object to respond to
        operation_name: Название операции для логирования
        fallback_state: Состояние для fallback при ошибке
    """
    try:
        await operation_func()
    except Exception as e:
        logger.error(f"Error during {operation_name}: {e}", exc_info=True)
        
        if fallback_state:
            await state.set_state(fallback_state)
            logger.info(f"Set fallback state: {fallback_state}")
        else:
            # Transition to API error state if no specific fallback
            await state.set_state(CommonStates.handling_api_error)
            await state.update_data(
                api_error_details=f"Error in {operation_name}: {str(e)}",
                api_error_time=str(datetime.now())
            )
        
        await handle_state_error(state, message_obj, operation_name)

# НОВОЕ: Утилиты для работы с meta-состояниями

async def check_system_health(bot) -> Dict[str, bool]:
    """
    Check overall system health including API connectivity.
    
    Args:
        bot: Bot instance
        
    Returns:
        Dict with health status of different components
    """
    from app.utils.api_utils import get_api_client_from_bot
    
    health_status = {
        "api_connection": False,
        "database_accessible": False,
        "bot_responsive": True  # If we're running this, bot is responsive
    }
    
    try:
        api_client = get_api_client_from_bot(bot)
        if api_client:
            # Test API connection
            response = await api_client._make_request("GET", "/health")
            health_status["api_connection"] = response.get("success", False)
            
            # Test database via API
            if health_status["api_connection"]:
                # Try a simple database operation
                lang_response = await api_client.get_languages()
                health_status["database_accessible"] = lang_response.get("success", False)
    
    except Exception as e:
        logger.error(f"Health check failed: {e}")
    
    return health_status

async def auto_recover_from_error_state(
    state: FSMContext,
    message_obj: Union[Message, CallbackQuery]
) -> bool:
    """
    Attempt automatic recovery from error states.
    
    Args:
        state: FSM state context
        message_obj: Message or CallbackQuery object
        
    Returns:
        bool: True if recovery was successful
    """
    current_state = await state.get_state()
    
    if current_state == CommonStates.connection_lost.state:
        # Try to restore connection
        health = await check_system_health(message_obj.bot)
        
        if health["api_connection"]:
            await state.clear()
            # Restore important session data
            state_data = await state.get_data()
            important_data = {
                "db_user_id": state_data.get("db_user_id"),
                "current_language": state_data.get("current_language"),
                "is_admin": state_data.get("is_admin", False)
            }
            await state.update_data(**{k: v for k, v in important_data.items() if v is not None})
            
            await message_obj.answer("✅ Соединение восстановлено!")
            return True
    
    elif current_state == CommonStates.handling_api_error.state:
        # Check if API is working now
        health = await check_system_health(message_obj.bot)
        
        if health["api_connection"] and health["database_accessible"]:
            await state.clear()
            await message_obj.answer("✅ Система работает нормально. Можете продолжить.")
            return True
    
    return False
