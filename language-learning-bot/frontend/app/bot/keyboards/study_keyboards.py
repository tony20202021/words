"""
Updated keyboards for word studying with individual hint settings support.
FIXED: Removed code duplication, improved architecture, proper imports.
UPDATED: Added word image display button.
UPDATED: Added admin edit button for admins during study.
UPDATED: Added writing image button - controlled by user settings only, no language restrictions.
"""

from typing import List, Dict, Optional

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.utils.callback_constants import CallbackData, format_hint_callback, format_admin_edit_from_study_callback
from app.utils.hint_constants import (
    format_hint_button,
    has_hint,
    get_enabled_hint_types,
    is_writing_images_enabled,
    format_writing_image_button,
)
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

def create_word_keyboard(
    word: dict, 
    word_shown: bool = False, 
    hint_settings: Optional[Dict[str, bool]] = None,
    used_hints: List[str] = None,
    is_admin: bool = False,
    show_writing_images: bool = False,
    current_language: Optional[dict] = None,
) -> InlineKeyboardMarkup:
    """
    Create inline keyboard for word interaction during study process.
    UPDATED: Added word image button when word is shown.
    UPDATED: Added admin edit button for administrators.
    UPDATED: Added writing image button - controlled by user settings only, no language restrictions.
    
    Args:
        word: The word data
        word_shown: Whether the word has been shown to the user
        hint_settings: Individual hint settings dictionary
        used_hints: List of hints already used by the user
        is_admin: Whether user is admin
        show_writing_images: Whether writing images are enabled in settings
        current_language: Current language information (not used for restrictions anymore)
        
    Returns:
        InlineKeyboardMarkup: The keyboard markup
    """
    builder = InlineKeyboardBuilder()
    
    if used_hints is None:
        used_hints = []
    
    # Main action buttons based on word state
    if word_shown or (len(used_hints) > 0):
        # Word has been shown or hints used - show next word button
        builder.add(InlineKeyboardButton(
            text="➡️ Следующее слово",
            callback_data=CallbackData.NEXT_WORD
        ))
        
        builder.add(InlineKeyboardButton(
            text="❓ Показать слово",
            callback_data=CallbackData.SHOW_WORD
        ))

        # Regular word image button
        if word_shown and word.get("word_foreign"):
            builder.add(InlineKeyboardButton(
                text="🔍 Показать крупное написание",
                callback_data=CallbackData.SHOW_WORD_IMAGE
            ))
        
        # Writing image button (controlled by user settings only)
        if word_shown and word.get("word_foreign") and show_writing_images:
            # Check if writing image exists (stub - always False for now)
            has_writing_image = False  # TODO: Replace with real check when backend is ready
            
            button_text = format_writing_image_button(
                has_image=has_writing_image,
                is_enabled=show_writing_images
            )
            
            builder.add(InlineKeyboardButton(
                text=button_text,
                callback_data=CallbackData.SHOW_WRITING_IMAGE
            ))
            
    else:
        # Word not shown yet - show evaluation buttons
        builder.add(InlineKeyboardButton(
            text="✅ Знаю, к следующему",
            callback_data=CallbackData.WORD_KNOW
        ))

        builder.add(InlineKeyboardButton(
            text="❓ Не знаю / не уверен, показать",
            callback_data=CallbackData.SHOW_WORD
        ))

    # Get word ID for hint callbacks
    word_id = _extract_word_id(word)
    
    # Add hint buttons based on individual settings
    if word_id:
        if hint_settings is not None:
            enabled_hint_types = get_enabled_hint_types(hint_settings)
            if enabled_hint_types:
                _add_hint_buttons(builder, word, word_id, used_hints, enabled_hint_types)
    
    # Добавляем кнопку редактирования для админов
    if is_admin and word_id:
        builder.add(InlineKeyboardButton(
            text="✏️ Редактировать слово",
            callback_data=format_admin_edit_from_study_callback(word_id)
        ))
    
    # Add word skip toggle button
    user_word_data = word.get("user_word_data", {})
    is_skipped = user_word_data.get("is_skipped", False)
    
    builder.add(InlineKeyboardButton(
        text=f"⏩ {'Не пропускать' if is_skipped else 'Пропускать'}",
        callback_data=CallbackData.TOGGLE_WORD_SKIP
    ))
    
    # Set layout: one button per row
    builder.adjust(1)

    return builder.as_markup()

def _extract_word_id(word: dict) -> Optional[str]:
    """
    Extract word ID from word data, handling different field names.
    
    Args:
        word: Word data dictionary
        
    Returns:
        str: Word ID or None if not found
    """
    for id_field in ["_id", "id", "word_id"]:
        if id_field in word and word[id_field]:
            word_id = str(word[id_field])
            logger.debug(f"Using word_id={word_id} for hint callbacks")
            return word_id
    
    logger.warning("No valid word_id found in word data")
    return None

def _add_hint_buttons(
    builder: InlineKeyboardBuilder, 
    word: dict, 
    word_id: str, 
    used_hints: List[str],
    enabled_hint_types: List[str]
) -> int:
    """
    Add hint buttons for enabled hint types.
    
    Args:
        builder: Keyboard builder to add buttons to
        word: Word data
        word_id: Word ID for callbacks
        used_hints: List of already used hints
        enabled_hint_types: List of enabled hint types from settings
        
    Returns:
        int: Number of hint buttons added
    """
    buttons_added = 0
    
    for hint_type in enabled_hint_types:
        # Check if hint exists
        hint_exists = has_hint(word, hint_type)
        
        # Check if hint is currently active
        is_active = hint_type in used_hints
        
        # Format button text
        button_text = format_hint_button(hint_type, hint_exists, is_active, is_enabled=True)
        
        # Determine callback action based on hint state
        if hint_exists:
            if is_active:
                # Hint is shown - allow editing
                callback_data = format_hint_callback("edit", hint_type, word_id)
            else:
                # Hint exists but not shown - allow toggling
                callback_data = format_hint_callback("toggle", hint_type, word_id)
        else:
            # No hint exists - allow creation
            callback_data = format_hint_callback("create", hint_type, word_id)
        
        builder.add(InlineKeyboardButton(
            text=button_text,
            callback_data=callback_data
        ))
        buttons_added += 1
    
    logger.info(f"Added {buttons_added} hint buttons for enabled types: {enabled_hint_types}")
    return buttons_added

def create_adaptive_study_keyboard(
    word: dict,
    word_shown: bool = False,
    hint_settings: Optional[Dict[str, bool]] = None,
    used_hints: List[str] = None,
    current_state: str = None,
    is_admin: bool = False,
    show_writing_images: bool = False,
    current_language: Optional[dict] = None,
) -> InlineKeyboardMarkup:
    """
    Create adaptive keyboard that changes based on current FSM state and word status.
    UPDATED: Uses individual hint settings and includes word image button.
    UPDATED: Added admin edit button for administrators.
    UPDATED: Added writing image button - controlled by user settings only.
    
    Args:
        word: Word data
        word_shown: Whether word has been shown
        hint_settings: Individual hint settings
        used_hints: List of used hints
        current_state: Current FSM state
        is_admin: Whether user is admin
        show_writing_images: Whether writing images are enabled
        current_language: Current language information (not used for restrictions anymore)
        
    Returns:
        InlineKeyboardMarkup: Adaptive keyboard
    """
    # Import states here to avoid circular import
    from app.bot.states.centralized_states import StudyStates
    
    if used_hints is None:
        used_hints = []
    
    # Choose keyboard based on state
    if current_state == StudyStates.study_completed.state:
        return create_study_completed_keyboard()
    elif current_state == StudyStates.viewing_word_details.state:
        return create_word_details_keyboard(
            word, hint_settings, used_hints, is_admin, 
            show_writing_images, current_language
        )
    elif current_state == StudyStates.confirming_word_knowledge.state:
        return create_word_confirmation_keyboard()
    elif current_state == StudyStates.viewing_word_image.state:
        return create_word_image_keyboard()
    elif current_state == StudyStates.viewing_writing_image.state:
        return create_writing_image_keyboard()
    else:
        # Default to standard word keyboard
        return create_word_keyboard(
            word, word_shown, hint_settings, used_hints, is_admin,
            show_writing_images, current_language
        )

def create_word_details_keyboard(
    word: dict,
    hint_settings: Optional[Dict[str, bool]] = None,
    used_hints: List[str] = None,
    is_admin: bool = False,
    show_writing_images: bool = False,
    current_language: Optional[dict] = None,
) -> InlineKeyboardMarkup:
    """
    Create keyboard specifically for viewing word details state.
    UPDATED: Uses individual hint settings and includes word image button.
    UPDATED: Added admin edit button for administrators.
    UPDATED: Added writing image button - controlled by user settings only.
    
    Args:
        word: Word data
        hint_settings: Individual hint settings
        used_hints: List of used hints
        is_admin: Whether user is admin
        show_writing_images: Whether writing images are enabled
        current_language: Current language information (not used for restrictions anymore)
        
    Returns:
        InlineKeyboardMarkup: Word details keyboard
    """
    builder = InlineKeyboardBuilder()
    
    if used_hints is None:
        used_hints = []
    
    # Main navigation button
    builder.add(InlineKeyboardButton(
        text="➡️ К следующему слову",
        callback_data=CallbackData.NEXT_WORD
    ))
    
    # Get word ID for hint callbacks
    word_id = _extract_word_id(word)
    
    # Add hint management buttons based on individual settings
    if word_id and hint_settings is not None:
        enabled_hint_types = get_enabled_hint_types(hint_settings)
        if enabled_hint_types:
            _add_hint_buttons(builder, word, word_id, used_hints, enabled_hint_types)
    
    # Regular word image button
    if word.get("word_foreign"):
        builder.add(InlineKeyboardButton(
            text="🔍 Показать крупное написание",
            callback_data=CallbackData.SHOW_WORD_IMAGE
        ))
    
    # Writing image button (controlled by user settings only)
    if word.get("word_foreign") and show_writing_images:
        # Check if writing image exists (stub - always False for now)
        has_writing_image = False  # TODO: Replace with real check when backend is ready
        
        button_text = format_writing_image_button(
            has_image=has_writing_image,
            is_enabled=show_writing_images
        )
        
        builder.add(InlineKeyboardButton(
            text=button_text,
            callback_data=CallbackData.SHOW_WRITING_IMAGE
        ))
    
    # Добавляем кнопку редактирования для админов
    if is_admin and word_id:
        builder.add(InlineKeyboardButton(
            text="✏️ Редактировать слово",
            callback_data=format_admin_edit_from_study_callback(word_id)
        ))
    
    # Skip toggle button
    user_word_data = word.get("user_word_data", {})
    is_skipped = user_word_data.get("is_skipped", False)
    
    builder.add(InlineKeyboardButton(
        text=f"⏩ {'Не пропускать' if is_skipped else 'Пропускать'}",
        callback_data=CallbackData.TOGGLE_WORD_SKIP
    ))
    
    builder.adjust(1)
    return builder.as_markup()

def create_word_confirmation_keyboard() -> InlineKeyboardMarkup:
    """
    Create confirmation keyboard after word evaluation.
    
    Returns:
        InlineKeyboardMarkup: Confirmation keyboard
    """
    builder = InlineKeyboardBuilder()
    
    builder.add(InlineKeyboardButton(
        text="✅ К следующему слову",
        callback_data=CallbackData.CONFIRM_NEXT_WORD
    ))
    
    builder.add(InlineKeyboardButton(
        text="❌ Ой, все-таки не знаю",
        callback_data=CallbackData.SHOW_WORD
    ))
    
    builder.adjust(1)
    return builder.as_markup()

def create_word_image_keyboard() -> InlineKeyboardMarkup:
    """
    Create keyboard for word image viewing state.
    
    Returns:
        InlineKeyboardMarkup: Word image keyboard
    """
    builder = InlineKeyboardBuilder()
    
    builder.add(InlineKeyboardButton(
        text="⬅️ Вернуться к слову",
        callback_data=CallbackData.BACK_FROM_IMAGE
    ))
    
    builder.adjust(1)
    return builder.as_markup()

def create_writing_image_keyboard() -> InlineKeyboardMarkup:
    """
    Create keyboard for writing image viewing state.
    
    Returns:
        InlineKeyboardMarkup: Writing image keyboard
    """
    builder = InlineKeyboardBuilder()
    
    builder.add(InlineKeyboardButton(
        text="⬅️ Вернуться к слову",
        callback_data=CallbackData.BACK_FROM_WRITING_IMAGE
    ))
    
    builder.adjust(1)
    return builder.as_markup()

def create_study_completed_keyboard() -> InlineKeyboardMarkup:
    """
    Create keyboard for study completed state.
    
    Returns:
        InlineKeyboardMarkup: Study completed keyboard
    """
    builder = InlineKeyboardBuilder()
    
    builder.add(InlineKeyboardButton(
        text="🔄 Начать изучение заново",
        callback_data="restart_study"
    ))
    
    builder.add(InlineKeyboardButton(
        text="📊 Посмотреть статистику",
        callback_data="view_stats"
    ))
    
    builder.add(InlineKeyboardButton(
        text="🌐 Выбрать другой язык",
        callback_data="change_language"
    ))
    
    builder.adjust(2, 2)  # 2x2 layout
    return builder.as_markup()

# Export main functions
__all__ = [
    'create_word_keyboard',
    'create_adaptive_study_keyboard', 
    'create_word_details_keyboard',
    'create_word_confirmation_keyboard',
    'create_word_image_keyboard',
    'create_writing_image_keyboard',
    'create_study_completed_keyboard',
]
