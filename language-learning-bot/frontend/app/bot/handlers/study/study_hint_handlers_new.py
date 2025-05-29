"""
Study hint handlers for Language Learning Bot.
Handles hint-related callbacks during word study process.
UPDATED: Support for individual hint settings validation.
"""

from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext

from app.utils.logger import setup_logger
from app.utils.callback_constants import CallbackParser
from app.utils.state_models import UserWordState
from app.utils.settings_utils import get_hint_settings, is_hint_type_enabled  # ОБНОВЛЕНО
from app.utils.hint_constants import get_hint_name, is_hint_enabled  # НОВОЕ

# Import hint handlers
from app.bot.handlers.study.hint.create_handlers import handle_hint_create
from app.bot.handlers.study.hint.edit_handlers import handle_hint_edit
from app.bot.handlers.study.hint.view_handlers import handle_hint_view
from app.bot.handlers.study.hint.toggle_handlers import handle_hint_toggle
from app.bot.handlers.study.hint.common import handle_cancel_hint_action, handle_back_to_word

# Создаем роутер для обработчиков подсказок
hint_router = Router()

logger = setup_logger(__name__)

@hint_router.callback_query(F.data.regexp(r"hint_(create|edit|toggle|view)_\w+_.+"))
async def process_hint_action(callback: CallbackQuery, state: FSMContext):
    """
    Process hint action callbacks with individual settings validation.
    UPDATED: Validates hint type against user settings before processing.
    
    Args:
        callback: The callback query
        state: FSM context
    """
    # Parse callback data
    parsed = CallbackParser.parse_hint_action(callback.data)
    if not parsed:
        await callback.answer("❌ Неверный формат команды подсказки")
        logger.error(f"Failed to parse hint callback: {callback.data}")
        return
    
    action, hint_type, word_id = parsed
    
    user_id = callback.from_user.id
    username = callback.from_user.username or "Unknown"
    full_name = callback.from_user.full_name or "Unknown User"
    
    logger.info(f"Hint {action} action for {hint_type} from {full_name} ({username})")
    
    # НОВОЕ: Validate hint type against user settings
    if not await _validate_hint_type_enabled(callback, state, hint_type):
        hint_name = get_hint_name(hint_type) or hint_type
        await callback.answer(f"❌ Подсказки типа '{hint_name}' отключены в настройках")
        return
    
    # Get current word state
    user_word_state = await UserWordState.from_state(state)
    
    # Validate word state
    if not user_word_state.is_valid():
        await callback.answer("❌ Ошибка состояния слова")
        logger.error("Invalid word state for hint action")
        return
    
    # Validate word ID matches current word
    if user_word_state.word_id != word_id:
        await callback.answer("❌ Действие устарело, слово изменилось")
        logger.warning(f"Word ID mismatch: current={user_word_state.word_id}, callback={word_id}")
        return
    
    try:
        # Route to appropriate handler
        if action == "create":
            await handle_hint_create(callback, state, hint_type, word_id, user_word_state)
        elif action == "edit":
            await handle_hint_edit(callback, state, hint_type, word_id, user_word_state)
        elif action == "view":
            await handle_hint_view(callback, state, hint_type, word_id, user_word_state)
        elif action == "toggle":
            await handle_hint_toggle(callback, state, hint_type, word_id, user_word_state)
        else:
            await callback.answer(f"❌ Неизвестное действие: {action}")
            logger.error(f"Unknown hint action: {action}")
    
    except Exception as e:
        logger.error(f"Error processing hint {action} for {hint_type}: {e}", exc_info=True)
        await callback.answer("❌ Ошибка обработки подсказки")

@hint_router.callback_query(F.data == "cancel_action")
async def process_cancel_hint_action(callback: CallbackQuery, state: FSMContext):
    """
    Process hint action cancellation.
    
    Args:
        callback: The callback query
        state: FSM context
    """
    logger.info(f"Cancel hint action from {callback.from_user.full_name}")
    await handle_cancel_hint_action(callback, state)

@hint_router.callback_query(F.data == "back_to_word")
async def process_back_to_word(callback: CallbackQuery, state: FSMContext):
    """
    Process back to word action.
    
    Args:
        callback: The callback query
        state: FSM context
    """
    logger.info(f"Back to word from {callback.from_user.full_name}")
    await handle_back_to_word(callback, state)

# НОВОЕ: Обработчик для информационных callback'ов подсказок
@hint_router.callback_query(F.data == "no_action")
async def process_no_action(callback: CallbackQuery, state: FSMContext):
    """
    Process no-action callbacks (informational buttons).
    
    Args:
        callback: The callback query
        state: FSM context
    """
    await callback.answer("ℹ️ Это информационная кнопка")

# НОВОЕ: Обработчик для отключенных подсказок
@hint_router.callback_query(F.data.regexp(r"hint_disabled_\w+"))
async def process_disabled_hint(callback: CallbackQuery, state: FSMContext):
    """
    Process callbacks for disabled hint types.
    
    Args:
        callback: The callback query
        state: FSM context
    """
    # Extract hint type from callback
    hint_type = callback.data.split("_")[-1]
    hint_name = get_hint_name(hint_type) or hint_type
    
    await callback.answer(
        f"💡 {hint_name} отключены в настройках.\n"
        f"Включите их в /settings для использования.",
        show_alert=True
    )

# НОВОЕ: Вспомогательные функции
async def _validate_hint_type_enabled(
    callback: CallbackQuery, 
    state: FSMContext, 
    hint_type: str
) -> bool:
    """
    Validate that hint type is enabled in user settings.
    
    Args:
        callback: The callback query
        state: FSM context
        hint_type: Hint type to validate
        
    Returns:
        bool: True if hint type is enabled
    """
    try:
        # Check if hint type is enabled in user settings
        is_enabled = await is_hint_type_enabled(hint_type, callback, state)
        
        if not is_enabled:
            logger.info(f"Hint type {hint_type} is disabled for user {callback.from_user.id}")
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"Error validating hint type {hint_type}: {e}")
        # Default to allowing the action if validation fails
        return True

async def _log_hint_action_attempt(
    callback: CallbackQuery,
    action: str,
    hint_type: str,
    word_id: str,
    allowed: bool
):
    """
    Log hint action attempt for analytics.
    
    Args:
        callback: The callback query
        action: Hint action
        hint_type: Hint type
        word_id: Word ID
        allowed: Whether action was allowed
    """
    user_info = f"{callback.from_user.full_name} ({callback.from_user.id})"
    status = "ALLOWED" if allowed else "BLOCKED"
    
    logger.info(
        f"HINT_ACTION: {status} - User: {user_info}, "
        f"Action: {action}, Type: {hint_type}, Word: {word_id}"
    )

# НОВОЕ: Функция для получения статистики использования подсказок
async def get_user_hint_statistics(
    callback: CallbackQuery,
    state: FSMContext
) -> dict:
    """
    Get user's hint usage statistics.
    
    Args:
        callback: The callback query
        state: FSM context
        
    Returns:
        dict: Hint usage statistics
    """
    try:
        # Get user settings
        hint_settings = await get_hint_settings(callback, state)
        user_word_state = await UserWordState.from_state(state)
        
        # Get enabled and used hints
        enabled_hints = [
            hint_type for hint_type, enabled in hint_settings.items() 
            if enabled
        ]
        used_hints = user_word_state.get_used_hints()
        
        # Calculate statistics
        stats = {
            "total_enabled": len(enabled_hints),
            "total_used": len(used_hints),
            "enabled_types": enabled_hints,
            "used_types": used_hints,
            "usage_rate": len(used_hints) / max(1, len(enabled_hints)),
            "current_word_id": user_word_state.word_id
        }
        
        return stats
        
    except Exception as e:
        logger.error(f"Error getting hint statistics: {e}")
        return {}

# НОВОЕ: Функция для валидации доступности действия с подсказкой
async def validate_hint_action_availability(
    callback: CallbackQuery,
    state: FSMContext,
    hint_type: str,
    action: str
) -> tuple[bool, str]:
    """
    Validate if hint action is available for user.
    
    Args:
        callback: The callback query
        state: FSM context
        hint_type: Hint type
        action: Requested action
        
    Returns:
        tuple: (is_available, reason_if_not)
    """
    try:
        # Check if hint type is enabled
        if not await is_hint_type_enabled(hint_type, callback, state):
            hint_name = get_hint_name(hint_type) or hint_type
            return False, f"Подсказки '{hint_name}' отключены в настройках"
        
        # Check word state
        user_word_state = await UserWordState.from_state(state)
        if not user_word_state.is_valid():
            return False, "Неверное состояние слова"
        
        # Check if we have current word
        current_word = user_word_state.get_current_word()
        if not current_word:
            return False, "Нет текущего слова для изучения"
        
        # Additional validation based on action type
        if action == "edit" or action == "view":
            # Check if hint exists
            from app.utils.hint_constants import has_hint
            if not has_hint(current_word, hint_type):
                hint_name = get_hint_name(hint_type) or hint_type
                return False, f"Подсказка '{hint_name}' не существует"
        
        return True, ""
        
    except Exception as e:
        logger.error(f"Error validating hint action availability: {e}")
        return False, "Ошибка валидации действия"

# НОВОЕ: Middleware для проверки настроек подсказок
class HintSettingsMiddleware:
    """
    Middleware to check hint settings before processing hint actions.
    """
    
    async def __call__(self, handler, event, data):
        """
        Middleware handler.
        
        Args:
            handler: Next handler
            event: Event object
            data: Event data
        """
        # Only apply to hint callbacks
        if hasattr(event, 'data') and 'hint_' in event.data:
            callback = event
            state = data.get('state')
            
            if callback and state:
                # Parse hint callback
                parsed = CallbackParser.parse_hint_action(callback.data)
                if parsed:
                    action, hint_type, word_id = parsed
                    
                    # Validate availability
                    is_available, reason = await validate_hint_action_availability(
                        callback, state, hint_type, action
                    )
                    
                    if not is_available:
                        await callback.answer(f"❌ {reason}", show_alert=True)
                        return
                    
                    # Log attempt
                    await _log_hint_action_attempt(
                        callback, action, hint_type, word_id, True
                    )
        
        # Continue to next handler
        return await handler(event, data)

# НОВОЕ: Функция для создания адаптивной клавиатуры подсказок
async def create_adaptive_hint_keyboard(
    callback: CallbackQuery,
    state: FSMContext,
    word: dict,
    used_hints: list = None
):
    """
    Create adaptive hint keyboard based on user settings.
    
    Args:
        callback: The callback query
        state: FSM context
        word: Word data
        used_hints: List of used hints
        
    Returns:
        InlineKeyboardMarkup: Adaptive keyboard
    """
    from app.bot.keyboards.study_keyboards import create_word_keyboard
    
    # Get user settings
    hint_settings = await get_hint_settings(callback, state)
    
    # Create keyboard with individual settings
    keyboard = create_word_keyboard(
        word=word,
        word_shown=False,
        hint_settings=hint_settings,
        used_hints=used_hints or [],
        current_state=await state.get_state()
    )
    
    return keyboard

# Экспортируем роутер и вспомогательные функции
__all__ = [
    'hint_router',
    'get_user_hint_statistics',
    'validate_hint_action_availability',
    'create_adaptive_hint_keyboard',
    'HintSettingsMiddleware'
]
