"""
Cancel handlers for user states.
Handles /cancel command in various user states.
"""

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from app.utils.logger import setup_logger
from app.utils.settings_utils import display_language_settings
from app.bot.states.centralized_states import UserStates, SettingsStates, StudyStates, HintStates, AdminStates, CommonStates

# Создаем роутер для обработчиков отмены
cancel_router = Router()

# Set up logging
logger = setup_logger(__name__)

# ОБНОВЛЕНО: Добавлены новые состояния для обработки команды /cancel
@cancel_router.message(Command("cancel"), UserStates.viewing_help, flags={"priority": 100})
@cancel_router.message(Command("cancel"), UserStates.viewing_hint_info, flags={"priority": 100})
@cancel_router.message(Command("cancel"), UserStates.viewing_stats, flags={"priority": 100})
@cancel_router.message(Command("cancel"), UserStates.selecting_language, flags={"priority": 100})
@cancel_router.message(Command("cancel"), SettingsStates.viewing_settings, flags={"priority": 100})
@cancel_router.message(Command("cancel"), SettingsStates.confirming_changes, flags={"priority": 100})
@cancel_router.message(Command("cancel"), StudyStates.confirming_word_knowledge, flags={"priority": 100})
@cancel_router.message(Command("cancel"), StudyStates.viewing_word_details, flags={"priority": 100})
@cancel_router.message(Command("cancel"), StudyStates.study_completed, flags={"priority": 100})
@cancel_router.message(Command("cancel"), HintStates.viewing, flags={"priority": 100})
@cancel_router.message(Command("cancel"), HintStates.confirming_deletion, flags={"priority": 100})
async def cmd_cancel_user_states(message: Message, state: FSMContext):
    """
    Handle the /cancel command in user states.
    
    Args:
        message: The message object from Telegram
        state: The FSM state context
    """
    # Get current state name
    current_state = await state.get_state()
    logger.info(f"Cancel command received in user state: {current_state}")
    
    # Handle settings states specially
    if current_state == "SettingsStates:confirming_changes":
        # Очищаем данные о предстоящем изменении
        await state.update_data(
            pending_setting_key=None,
            pending_setting_value=None,
            pending_setting_name=None
        )
        
        # Возвращаемся к настройкам
        await state.set_state(SettingsStates.viewing_settings)
        
        await display_language_settings(
            message, 
            state, 
            prefix="⚙️ Подтверждение изменения настройки отменено.\n\n"
        )
        return
    
    # Handle study states specially
    if current_state in ["StudyStates:confirming_word_knowledge", "StudyStates:viewing_word_details"]:
        # Возвращаемся к основному процессу изучения
        await state.set_state(StudyStates.studying)
        await message.answer(
            "✅ Отменено. Возвращаемся к изучению слов.\n\n"
            "Используйте /study для продолжения изучения или другие команды:\n"
            "/language - Выбор языка\n"
            "/settings - Настройки\n"
            "/stats - Статистика\n"
            "/start - Главное меню"
        )
        return
    
    if current_state == "StudyStates:study_completed":
        # Завершение изучения - возвращаемся в обычный режим
        await state.set_state(None)
        await message.answer(
            "✅ Выход из экрана завершения изучения.\n\n"
            "Доступные команды:\n"
            "/study - Начать изучение заново\n"
            "/language - Выбор другого языка\n"
            "/settings - Настройки\n"
            "/stats - Статистика\n"
            "/start - Главное меню"
        )
        return
    
    # Handle hint states specially
    if current_state == "HintStates:viewing":
        # Возвращаемся к основному процессу изучения
        await state.set_state(StudyStates.studying)
        await message.answer(
            "✅ Выход из просмотра подсказки. Возвращаемся к изучению слов.\n\n"
            "Используйте /study для продолжения изучения."
        )
        return
    
    if current_state == "HintStates:confirming_deletion":
        # Отменяем удаление подсказки, возвращаемся к просмотру
        await state.set_state(HintStates.viewing)
        await message.answer(
            "✅ Удаление подсказки отменено.\n\n"
            "Используйте /cancel еще раз для возврата к изучению слов."
        )
        return
    
    # Clear state and return to main menu for other states
    await state.set_state(None)
    
    # Provide contextual message based on previous state
    state_messages = {
        "UserStates:viewing_help": "Выход из справки.",
        "UserStates:viewing_hint_info": "Выход из информации о подсказках.",
        "UserStates:viewing_stats": "Выход из статистики.",
        "UserStates:selecting_language": "Отмена выбора языка.",
        "SettingsStates:viewing_settings": "Выход из настроек."
    }
    
    cancel_message = state_messages.get(
        current_state, 
        "Отменено."
    )
    
    await message.answer(
        f"✅ {cancel_message}\n\n"
        f"Используйте /start для возврата в главное меню или другие команды:\n"
        f"/language - Выбор языка\n"
        f"/study - Изучение слов\n"
        f"/settings - Настройки\n"
        f"/stats - Статистика\n"
        f"/help - Справка"
    )

# НОВОЕ: Добавлены обработчики для административных состояний
@cancel_router.message(Command("cancel"), AdminStates.main_menu, flags={"priority": 100})
@cancel_router.message(Command("cancel"), AdminStates.viewing_admin_stats, flags={"priority": 100})
@cancel_router.message(Command("cancel"), AdminStates.viewing_users_list, flags={"priority": 100})
@cancel_router.message(Command("cancel"), AdminStates.viewing_user_details, flags={"priority": 100})
@cancel_router.message(Command("cancel"), AdminStates.viewing_languages, flags={"priority": 100})
@cancel_router.message(Command("cancel"), AdminStates.viewing_language_details, flags={"priority": 100})
@cancel_router.message(Command("cancel"), AdminStates.viewing_word_search_results, flags={"priority": 100})
@cancel_router.message(Command("cancel"), AdminStates.confirming_language_deletion, flags={"priority": 100})
@cancel_router.message(Command("cancel"), AdminStates.confirming_admin_rights_change, flags={"priority": 100})
async def cmd_cancel_admin_states(message: Message, state: FSMContext):
    """
    Handle the /cancel command in admin states.
    
    Args:
        message: The message object from Telegram
        state: The FSM state context
    """
    # Get current state name
    current_state = await state.get_state()
    logger.info(f"Cancel command received in admin state: {current_state}")
    
    # Handle confirmation states specially
    if current_state in ["AdminStates:confirming_language_deletion", "AdminStates:confirming_admin_rights_change"]:
        # Возвращаемся к предыдущему состоянию
        if "language_deletion" in current_state:
            await state.set_state(AdminStates.viewing_language_details)
            await message.answer("✅ Удаление языка отменено.")
        else:
            await state.set_state(AdminStates.viewing_user_details)
            await message.answer("✅ Изменение прав администратора отменено.")
        return
    
    # For other admin states, return to admin main menu
    await state.set_state(AdminStates.main_menu)
    
    # Provide contextual message based on previous state
    admin_state_messages = {
        "AdminStates:viewing_admin_stats": "Выход из административной статистики.",
        "AdminStates:viewing_users_list": "Выход из списка пользователей.",
        "AdminStates:viewing_user_details": "Выход из деталей пользователя.",
        "AdminStates:viewing_languages": "Выход из списка языков.",
        "AdminStates:viewing_language_details": "Выход из деталей языка.",
        "AdminStates:viewing_word_search_results": "Выход из результатов поиска слова.",
    }
    
    cancel_message = admin_state_messages.get(
        current_state,
        "Возврат в главное меню администратора."
    )
    
    await message.answer(
        f"✅ {cancel_message}\n\n"
        f"Вы находитесь в режиме администратора.\n"
        f"Используйте /admin для отображения меню администратора или:\n"
        f"/start - Выйти из режима администратора"
    )

# НОВОЕ: Добавлены обработчики для meta-состояний
@cancel_router.message(Command("cancel"), CommonStates.handling_api_error, flags={"priority": 100})
@cancel_router.message(Command("cancel"), CommonStates.connection_lost, flags={"priority": 100})
@cancel_router.message(Command("cancel"), CommonStates.unknown_command, flags={"priority": 100})
async def cmd_cancel_common_states(message: Message, state: FSMContext):
    """
    Handle the /cancel command in common/meta states.
    
    Args:
        message: The message object from Telegram
        state: The FSM state context
    """
    # Get current state name
    current_state = await state.get_state()
    logger.info(f"Cancel command received in common state: {current_state}")
    
    # Clear state and return to main menu
    await state.set_state(None)
    
    # Provide contextual message based on previous state
    common_state_messages = {
        "CommonStates:handling_api_error": "Выход из обработки ошибки API.",
        "CommonStates:connection_lost": "Выход из ожидания восстановления соединения.",
        "CommonStates:unknown_command": "Выход из обработки неизвестной команды.",
    }
    
    cancel_message = common_state_messages.get(
        current_state,
        "Выход из системного состояния."
    )
    
    await message.answer(
        f"✅ {cancel_message}\n\n"
        f"Используйте /start для главного меню или другие доступные команды:\n"
        f"/language - Выбор языка\n"
        f"/study - Изучение слов\n"
        f"/settings - Настройки\n"
        f"/stats - Статистика\n"
        f"/help - Справка"
    )

@cancel_router.message(UserStates.viewing_help)
@cancel_router.message(UserStates.viewing_hint_info)
@cancel_router.message(UserStates.viewing_stats)
@cancel_router.message(UserStates.selecting_language)
@cancel_router.message(SettingsStates.viewing_settings)
@cancel_router.message(SettingsStates.confirming_changes)
@cancel_router.message(StudyStates.confirming_word_knowledge)
@cancel_router.message(StudyStates.viewing_word_details)
@cancel_router.message(StudyStates.study_completed)
@cancel_router.message(HintStates.viewing)
@cancel_router.message(HintStates.confirming_deletion)
async def handle_unexpected_message_in_user_states(message: Message, state: FSMContext):
    """
    Handle unexpected messages in user states.
    
    Args:
        message: The message object from Telegram
        state: The FSM state context
    """
    current_state = await state.get_state()
    logger.info(f"Unexpected message in user state: {current_state}, message: {message.text}")
    
    # Handle settings states specially
    if current_state == "SettingsStates:confirming_changes":
        await message.answer(
            "⚠️ Вы находитесь в процессе подтверждения изменения настройки.\n\n"
            "Используйте кнопки выше для подтверждения или отмены, либо:\n"
            "/cancel - Отменить изменение и вернуться к настройкам\n"
            "/start - Главное меню"
        )
        return
    
    # Handle study states specially
    if current_state in ["StudyStates:confirming_word_knowledge", "StudyStates:viewing_word_details"]:
        await message.answer(
            "⚠️ Вы находитесь в процессе изучения слов.\n\n"
            "Используйте кнопки выше для действий со словом или:\n"
            "/cancel - Вернуться к изучению\n"
            "/start - Главное меню"
        )
        return
    
    if current_state == "StudyStates:study_completed":
        await message.answer(
            "🎉 Вы завершили изучение всех доступных слов!\n\n"
            "Доступные действия:\n"
            "/study - Начать изучение заново\n"
            "/language - Выбрать другой язык\n"
            "/settings - Изменить настройки\n"
            "/cancel - Выйти из этого экрана\n"
            "/start - Главное меню"
        )
        return
    
    # Handle hint states specially
    if current_state == "HintStates:viewing":
        await message.answer(
            "⚠️ Вы просматриваете подсказку.\n\n"
            "Используйте кнопки выше для действий с подсказкой или:\n"
            "/cancel - Вернуться к изучению слов\n"
            "/start - Главное меню"
        )
        return
    
    if current_state == "HintStates:confirming_deletion":
        await message.answer(
            "⚠️ Вы подтверждаете удаление подсказки.\n\n"
            "Используйте кнопки выше для подтверждения или:\n"
            "/cancel - Отменить удаление\n"
            "/start - Главное меню"
        )
        return
    
    # Provide helpful message based on current state
    state_help_messages = {
        "UserStates:viewing_help": (
            "Вы находитесь в разделе справки.\n"
            "Используйте /cancel для выхода или выберите команду:\n"
            "/start - Главное меню\n"
            "/study - Изучение слов"
        ),
        "UserStates:viewing_hint_info": (
            "Вы находитесь в разделе информации о подсказках.\n"
            "Используйте /cancel для выхода или выберите команду:\n"
            "/start - Главное меню\n"
            "/study - Изучение слов"
        ),
        "UserStates:viewing_stats": (
            "Вы находитесь в разделе статистики.\n"
            "Используйте /cancel для выхода или выберите команду:\n"
            "/start - Главное меню\n"
            "/study - Изучение слов"
        ),
        "UserStates:selecting_language": (
            "Вы находитесь в процессе выбора языка.\n"
            "Используйте кнопки выше для выбора языка или:\n"
            "/cancel - Отменить выбор\n"
            "/start - Главное меню"
        ),
        "SettingsStates:viewing_settings": (
            "Вы находитесь в настройках.\n"
            "Используйте кнопки выше для изменения настроек или:\n"
            "/cancel - Выйти из настроек\n"
            "/start - Главное меню"
        )
    }
    
    help_message = state_help_messages.get(
        current_state,
        "Используйте /cancel для выхода или /start для главного меню."
    )
    
    await message.answer(f"ℹ️ {help_message}")

# НОВОЕ: Обработчики неожиданных сообщений в административных состояниях
@cancel_router.message(AdminStates.main_menu)
@cancel_router.message(AdminStates.viewing_admin_stats)
@cancel_router.message(AdminStates.viewing_users_list)
@cancel_router.message(AdminStates.viewing_user_details)
@cancel_router.message(AdminStates.viewing_languages)
@cancel_router.message(AdminStates.viewing_language_details)
@cancel_router.message(AdminStates.viewing_word_search_results)
@cancel_router.message(AdminStates.confirming_language_deletion)
@cancel_router.message(AdminStates.confirming_admin_rights_change)
async def handle_unexpected_message_in_admin_states(message: Message, state: FSMContext):
    """
    Handle unexpected messages in admin states.
    
    Args:
        message: The message object from Telegram
        state: The FSM state context
    """
    current_state = await state.get_state()
    logger.info(f"Unexpected message in admin state: {current_state}, message: {message.text}")
    
    # Handle confirmation states specially
    if current_state in ["AdminStates:confirming_language_deletion", "AdminStates:confirming_admin_rights_change"]:
        await message.answer(
            "⚠️ Вы находитесь в процессе подтверждения административного действия.\n\n"
            "Используйте кнопки выше для подтверждения или отмены, либо:\n"
            "/cancel - Отменить действие\n"
            "/admin - Меню администратора\n"
            "/start - Выйти из режима администратора"
        )
        return
    
    # Generic message for admin states
    await message.answer(
        "ℹ️ Вы находитесь в режиме администратора.\n\n"
        "Используйте кнопки выше для навигации или команды:\n"
        "/cancel - Вернуться к главному меню администратора\n"
        "/admin - Показать меню администратора\n"
        "/start - Выйти из режима администратора"
    )
    