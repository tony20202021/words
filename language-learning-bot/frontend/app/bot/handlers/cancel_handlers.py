"""
Cancel handlers for user states.
Handles /cancel command in various user states.
FIXED: Removed code duplication, improved architecture, centralized state handling.
"""

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from typing import Dict, List, Optional, Tuple

from app.utils.logger import setup_logger
from app.utils.settings_utils import display_language_settings
from app.bot.states.centralized_states import (
    UserStates, SettingsStates, StudyStates, HintStates, 
    AdminStates, CommonStates
)

# Создаем роутер для обработчиков отмены
cancel_router = Router()

# Set up logging
logger = setup_logger(__name__)

# НОВОЕ: Централизованные данные для обработки состояний
class StateHandlerConfig:
    """Configuration for state-specific cancel handling."""
    
    # User states configuration
    USER_STATES = {
        UserStates.viewing_help.state: {
            "message": "Выход из справки.",
            "clear_state": True,
            "show_main_menu": True
        },
        UserStates.viewing_hint_info.state: {
            "message": "Выход из информации о подсказках.",
            "clear_state": True,
            "show_main_menu": True
        },
        UserStates.viewing_stats.state: {
            "message": "Выход из статистики.",
            "clear_state": True,
            "show_main_menu": True
        },
        UserStates.selecting_language.state: {
            "message": "Отмена выбора языка.",
            "clear_state": True,
            "show_main_menu": True
        }
    }
    
    # Settings states configuration
    SETTINGS_STATES = {
        SettingsStates.viewing_settings.state: {
            "message": "Выход из настроек.",
            "clear_state": True,
            "show_main_menu": True
        },
        SettingsStates.confirming_changes.state: {
            "message": "Подтверждение изменения настройки отменено.",
            "clear_state": False,
            "new_state": SettingsStates.viewing_settings,
            "special_handler": "_handle_settings_confirmation_cancel"
        }
    }
    
    # Study states configuration
    STUDY_STATES = {
        StudyStates.confirming_word_knowledge.state: {
            "message": "Отменено. Возвращаемся к изучению слов.",
            "clear_state": False,
            "new_state": StudyStates.studying,
            "show_study_menu": True
        },
        StudyStates.viewing_word_details.state: {
            "message": "Отменено. Возвращаемся к изучению слов.",
            "clear_state": False,
            "new_state": StudyStates.studying,
            "show_study_menu": True
        },
        StudyStates.study_completed.state: {
            "message": "Выход из экрана завершения изучения.",
            "clear_state": True,
            "show_study_completion_menu": True
        }
    }
    
    # Hint states configuration
    HINT_STATES = {
        HintStates.creating.state: {
            "message": "Выход из создания подсказки. Возвращаемся к изучению слов.",
            "clear_state": False,
            "new_state": StudyStates.studying,
            "show_study_menu": False
        },
        HintStates.editing.state: {
            "message": "Выход из просмотра подсказки. Возвращаемся к изучению слов.",
            "clear_state": False,
            "new_state": StudyStates.studying,
            "show_study_menu": False
        },
    }
    
    # Admin states configuration
    ADMIN_STATES = {
        AdminStates.main_menu.state: {
            "message": "Возврат в главное меню администратора.",
            "clear_state": False,
            "new_state": AdminStates.main_menu,
            "show_admin_menu": True
        },
        AdminStates.viewing_admin_stats.state: {
            "message": "Выход из административной статистики.",
            "clear_state": False,
            "new_state": AdminStates.main_menu,
            "show_admin_menu": True
        },
        AdminStates.viewing_users_list.state: {
            "message": "Выход из списка пользователей.",
            "clear_state": False,
            "new_state": AdminStates.main_menu,
            "show_admin_menu": True
        },
        AdminStates.viewing_user_details.state: {
            "message": "Выход из деталей пользователя.",
            "clear_state": False,
            "new_state": AdminStates.main_menu,
            "show_admin_menu": True
        },
        AdminStates.viewing_languages.state: {
            "message": "Выход из списка языков.",
            "clear_state": False,
            "new_state": AdminStates.main_menu,
            "show_admin_menu": True
        },
        AdminStates.viewing_language_details.state: {
            "message": "Выход из деталей языка.",
            "clear_state": False,
            "new_state": AdminStates.main_menu,
            "show_admin_menu": True
        },
        AdminStates.viewing_word_search_results.state: {
            "message": "Выход из результатов поиска слова.",
            "clear_state": False,
            "new_state": AdminStates.main_menu,
            "show_admin_menu": True
        },
        AdminStates.confirming_language_deletion.state: {
            "message": "Удаление языка отменено.",
            "clear_state": False,
            "new_state": AdminStates.viewing_language_details
        },
        AdminStates.confirming_admin_rights_change.state: {
            "message": "Изменение прав администратора отменено.",
            "clear_state": False,
            "new_state": AdminStates.viewing_user_details
        }
    }
    
    # Common/Meta states configuration
    COMMON_STATES = {
        CommonStates.handling_api_error.state: {
            "message": "Выход из обработки ошибки API.",
            "clear_state": True,
            "show_main_menu": True
        },
        CommonStates.connection_lost.state: {
            "message": "Выход из ожидания восстановления соединения.",
            "clear_state": True,
            "show_main_menu": True
        },
        CommonStates.unknown_command.state: {
            "message": "Выход из обработки неизвестной команды.",
            "clear_state": True,
            "show_main_menu": True
        }
    }

# НОВОЕ: Централизованные функции для обработки cancel
async def _handle_settings_confirmation_cancel(message: Message, state: FSMContext) -> None:
    """
    Special handler for settings confirmation cancel.
    НОВОЕ: Специальный обработчик для отмены подтверждения настроек.
    """
    # Clear pending changes data
    await state.update_data(
        pending_setting_key=None,
        pending_setting_value=None,
        pending_setting_name=None
    )
    
    # Return to settings display
    await display_language_settings(
        message, 
        state, 
        prefix="⚙️ Подтверждение изменения настройки отменено.\n\n"
    )

def _get_main_menu_commands() -> str:
    """
    Get main menu commands text.
    НОВОЕ: Централизованный текст команд главного меню.
    """
    return (
        "Используйте /start для возврата в главное меню или другие команды:\n"
        "/language - Выбор языка\n"
        "/study - Изучение слов\n"
        "/settings - Настройки\n"
        "/stats - Статистика\n"
        "/help - Справка"
    )

def _get_study_menu_commands() -> str:
    """
    Get study menu commands text.
    НОВОЕ: Централизованный текст команд изучения.
    """
    return (
        "Используйте /study для продолжения изучения или другие команды:\n"
        "/language - Выбор языка\n"
        "/settings - Настройки\n"
        "/stats - Статистика\n"
        "/start - Главное меню"
    )

def _get_study_completion_commands() -> str:
    """
    Get study completion commands text.
    НОВОЕ: Централизованный текст команд завершения изучения.
    """
    return (
        "Доступные команды:\n"
        "/study - Начать изучение заново\n"
        "/language - Выбрать другой язык\n"
        "/settings - Изменить настройки\n"
        "/stats - Статистика\n"
        "/start - Главное меню"
    )

def _get_admin_menu_commands() -> str:
    """
    Get admin menu commands text.
    НОВОЕ: Централизованный текст команд администратора.
    """
    return (
        "Вы находитесь в режиме администратора.\n"
        "Используйте /admin для отображения меню администратора или:\n"
        "/start - Выйти из режима администратора"
    )

async def _process_state_cancel(
    message: Message, 
    state: FSMContext, 
    current_state: str,
    config: Dict
) -> None:
    """
    Process cancel for a specific state using its configuration.
    НОВОЕ: Универсальная функция обработки отмены для любого состояния.
    
    Args:
        message: Message object
        state: FSM context
        current_state: Current state string
        config: State configuration
    """
    # Handle special handlers first
    if config.get("special_handler"):
        handler_name = config["special_handler"]
        if handler_name == "_handle_settings_confirmation_cancel":
            await _handle_settings_confirmation_cancel(message, state)
            return
    
    # Set new state or clear
    if config.get("clear_state", False):
        await state.set_state(None)
    elif config.get("new_state"):
        await state.set_state(config["new_state"])
    
    # Build response message
    response_message = f"✅ {config['message']}\n\n"
    
    # Add additional message if specified
    if config.get("additional_message"):
        response_message += f"{config['additional_message']}\n\n"
    
    # Add appropriate command menu
    if config.get("show_main_menu"):
        response_message += _get_main_menu_commands()
    elif config.get("show_study_menu"):
        response_message += _get_study_menu_commands()
    elif config.get("show_study_completion_menu"):
        response_message += _get_study_completion_commands()
    elif config.get("show_admin_menu"):
        response_message += _get_admin_menu_commands()
    
    await message.answer(response_message)

# НОВОЕ: Универсальный обработчик cancel
@cancel_router.message(Command("cancel"))
async def cmd_cancel_universal(message: Message, state: FSMContext):
    """
    Universal cancel handler for all states.
    НОВОЕ: Универсальный обработчик отмены для всех состояний с централизованной логикой.
    
    Args:
        message: The message object from Telegram
        state: The FSM state context
    """
    current_state = await state.get_state()
    logger.info(f"Cancel command received in state: {current_state}")
    
    # Combine all state configurations
    all_configs = {
        **StateHandlerConfig.USER_STATES,
        **StateHandlerConfig.SETTINGS_STATES,
        **StateHandlerConfig.STUDY_STATES,
        **StateHandlerConfig.HINT_STATES,
        **StateHandlerConfig.ADMIN_STATES,
        **StateHandlerConfig.COMMON_STATES
    }
    
    # Find configuration for current state
    config = all_configs.get(current_state)
    
    if config:
        await _process_state_cancel(message, state, current_state, config)
    else:
        # Default handler for unknown states
        await _handle_unknown_state_cancel(message, state, current_state)

async def _handle_unknown_state_cancel(message: Message, state: FSMContext, current_state: str) -> None:
    """
    Handle cancel for unknown or unhandled states.
    НОВОЕ: Обработчик для неизвестных состояний.
    
    Args:
        message: Message object
        state: FSM context  
        current_state: Current state string
    """
    logger.warning(f"Cancel received for unknown state: {current_state}")
    
    # Clear state and return to main menu
    await state.set_state(None)
    
    # Preserve important data
    state_data = await state.get_data()
    important_data = {
        "db_user_id": state_data.get("db_user_id"),
        "current_language": state_data.get("current_language"),
        "is_admin": state_data.get("is_admin", False)
    }
    
    # Update state with preserved data
    await state.update_data(**{k: v for k, v in important_data.items() if v is not None})
    
    response_message = (
        f"✅ Операция отменена.\n\n"
        f"Состояние сброшено для безопасности.\n\n"
        f"{_get_main_menu_commands()}"
    )
    
    await message.answer(response_message)

# НОВОЕ: Обработчики неожиданных сообщений в различных состояниях
def _get_unexpected_message_configs() -> Dict[str, Dict]:
    """
    Get configurations for unexpected message handling.
    НОВОЕ: Конфигурации для обработки неожиданных сообщений.
    """
    return {
        # User states
        UserStates.viewing_help.state: {
            "message": "Вы находитесь в разделе справки.",
            "commands": ["/cancel для выхода", "/start - Главное меню", "/study - Изучение слов"]
        },
        UserStates.viewing_hint_info.state: {
            "message": "Вы находитесь в разделе информации о подсказках.",
            "commands": ["/cancel для выхода", "/start - Главное меню", "/study - Изучение слов"]
        },
        UserStates.viewing_stats.state: {
            "message": "Вы находитесь в разделе статистики.",
            "commands": ["/cancel для выхода", "/start - Главное меню", "/study - Изучение слов"]
        },
        UserStates.selecting_language.state: {
            "message": "Вы находитесь в процессе выбора языка.",
            "commands": ["кнопки выше для выбора языка", "/cancel - Отменить выбор", "/start - Главное меню"]
        },
        
        # Settings states
        SettingsStates.viewing_settings.state: {
            "message": "Вы находитесь в настройках.",
            "commands": ["кнопки выше для изменения настроек", "/cancel - Выйти из настроек", "/start - Главное меню"]
        },
        SettingsStates.confirming_changes.state: {
            "message": "Вы находитесь в процессе подтверждения изменения настройки.",
            "commands": ["кнопки выше для подтверждения или отмены", "/cancel - Отменить изменение", "/start - Главное меню"]
        },
        
        # Study states
        StudyStates.confirming_word_knowledge.state: {
            "message": "Вы находитесь в процессе изучения слов.",
            "commands": ["кнопки выше для действий со словом", "/cancel - Вернуться к изучению", "/start - Главное меню"]
        },
        StudyStates.viewing_word_details.state: {
            "message": "Вы просматриваете детали слова.",
            "commands": ["кнопки выше для перехода к следующему слову", "/cancel - Вернуться к изучению", "/start - Главное меню"]
        },
        StudyStates.study_completed.state: {
            "message": "Вы завершили изучение всех доступных слов!",
            "commands": ["/study - Начать заново", "/language - Выбрать другой язык", "/cancel - Выйти", "/start - Главное меню"]
        },
        
        # Hint states
        HintStates.viewing.state: {
            "message": "Вы просматриваете подсказку.",
            "commands": ["кнопки выше для действий с подсказкой", "/cancel - Вернуться к изучению", "/start - Главное меню"]
        },
        HintStates.confirming_deletion.state: {
            "message": "Вы подтверждаете удаление подсказки.",
            "commands": ["кнопки выше для подтверждения", "/cancel - Отменить удаление", "/start - Главное меню"]
        }
    }

# # НОВОЕ: Универсальный обработчик неожиданных сообщений
# @cancel_router.message()
# async def handle_unexpected_message_universal(message: Message, state: FSMContext):
#     """
#     Universal handler for unexpected messages in various states.
#     НОВОЕ: Универсальный обработчик неожиданных сообщений с централизованной логикой.
    
#     Args:
#         message: The message object from Telegram
#         state: The FSM state context
#     """
#     current_state = await state.get_state()
    
#     # Skip if no state (let other handlers process)
#     if not current_state:
#         return
    
#     logger.info(f"Unexpected message in state: {current_state}, message: {message.text}")
    
#     # Get configuration for unexpected messages
#     configs = _get_unexpected_message_configs()
#     config = configs.get(current_state)
    
#     if config:
#         # Format response based on configuration
#         response_message = f"ℹ️ {config['message']}\n\n"
#         response_message += "Используйте:\n"
        
#         for command in config['commands']:
#             response_message += f"• {command}\n"
        
#         await message.answer(response_message)
#     else:
#         # Default response for unknown states
#         await message.answer(
#             f"ℹ️ Используйте /cancel для выхода или /start для главного меню.\n\n"
#             f"Если возникли проблемы, попробуйте /help для получения справки."
#         )

# НОВОЕ: Utility functions for state management
def get_state_category(state_string: str) -> str:
    """
    Get category of a state.
    НОВОЕ: Определение категории состояния.
    
    Args:
        state_string: State string
        
    Returns:
        str: State category
    """
    if not state_string:
        return "none"
    
    if state_string.startswith("UserStates:"):
        return "user"
    elif state_string.startswith("SettingsStates:"):
        return "settings"
    elif state_string.startswith("StudyStates:"):
        return "study"
    elif state_string.startswith("HintStates:"):
        return "hint"
    elif state_string.startswith("AdminStates:"):
        return "admin"
    elif state_string.startswith("CommonStates:"):
        return "common"
    else:
        return "unknown"

def is_cancellable_state(state_string: str) -> bool:
    """
    Check if a state can be cancelled.
    НОВОЕ: Проверка возможности отмены состояния.
    
    Args:
        state_string: State string
        
    Returns:
        bool: True if state can be cancelled
    """
    all_configs = {
        **StateHandlerConfig.USER_STATES,
        **StateHandlerConfig.SETTINGS_STATES,
        **StateHandlerConfig.STUDY_STATES,
        **StateHandlerConfig.HINT_STATES,
        **StateHandlerConfig.ADMIN_STATES,
        **StateHandlerConfig.COMMON_STATES
    }
    
    return state_string in all_configs

async def get_state_help_text(state_string: str) -> str:
    """
    Get help text for a specific state.
    НОВОЕ: Получение справочного текста для состояния.
    
    Args:
        state_string: State string
        
    Returns:
        str: Help text for the state
    """
    configs = _get_unexpected_message_configs()
    config = configs.get(state_string)
    
    if config:
        help_text = f"ℹ️ {config['message']}\n\nДоступные действия:\n"
        for command in config['commands']:
            help_text += f"• {command}\n"
        return help_text
    
    return "Используйте /cancel для выхода или /help для получения справки."


def register_cancel_handlers(dp):
    dp.include_router(cancel_router)
    logger.info("cancel handlers registered successfully")
