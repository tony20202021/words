"""
Utilities for handling API errors and other common error cases.
"""

import logging
from typing import Dict, Any, Union, Tuple, Optional, List
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

logger = logging.getLogger(__name__)

async def handle_api_error(
    response: Dict[str, Any], 
    message_obj: Union[Message, CallbackQuery], 
    log_prefix: str = "API Error",
    user_prefix: str = "Ошибка"
) -> bool:
    """
    Handle API error response and send user-friendly message.
    
    Args:
        response: API response dictionary with 'success' and 'error' keys
        message_obj: Message or CallbackQuery object to respond to
        log_prefix: Prefix for log message
        user_prefix: Prefix for user message
        
    Returns:
        bool: True if error was handled, False if no error
    """
    if not response["success"]:
        status = response.get("status", "unknown")
        error_msg = response.get("error", "Неизвестная ошибка")
        
        # Log the error with full details
        logger.error(f"{log_prefix}: status={status}, error={error_msg}")
        
        # Send user-friendly message
        user_message = f"❌ {user_prefix}: {error_msg}"
        
        # Handle different message object types
        if isinstance(message_obj, CallbackQuery):
            await message_obj.answer("Произошла ошибка", show_alert=True)
            await message_obj.message.answer(user_message)
        else:
            await message_obj.answer(user_message)
            
        return True
    return False

async def validate_state_data(
    state: FSMContext,
    required_keys: List[str],
    message_obj: Union[Message, CallbackQuery],
    error_message: str = "Ошибка: недостаточно данных"
) -> Tuple[bool, Dict[str, Any]]:
    """
    Validate that all required keys are present in the state data.
    
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
        
        # Customize the error message with details about missing data
        detailed_message = f"{error_message} ({', '.join(missing_keys)})"
        
        # Handle different message object types
        if isinstance(message_obj, CallbackQuery):
            await message_obj.answer("Данные сессии неполные", show_alert=True)
            await message_obj.message.answer(detailed_message)
        else:
            await message_obj.answer(detailed_message)
            
        return False, state_data
    
    return True, state_data

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

"""
Утилита для проверки команд. Добавьте эту функцию в файл utils/error_utils.py
"""

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
