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
