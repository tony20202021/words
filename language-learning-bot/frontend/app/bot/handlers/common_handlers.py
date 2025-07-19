"""
Common handlers for meta-states and system-wide error handling.
These handlers manage system states like API errors, connection issues, and unknown commands.
"""

from aiogram import Router
from aiogram.filters import Command, StateFilter
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram import F

# Import centralized states
from app.bot.states.centralized_states import CommonStates
from app.utils.api_utils import get_api_client_from_bot
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

# Create router for common handlers
common_router = Router()


@common_router.message(StateFilter(CommonStates.handling_api_error))
async def handle_api_error_state(message: Message, state: FSMContext):
    """
    Handle messages when user is in API error state.
    Provides options to retry or get help.
    """
    await state.clear()
    await message.answer(
        "ℹ️ Произошла ошибка API.\n\n"
        "Начните сначала по команде /start\n"
    )


@common_router.message(StateFilter(CommonStates.connection_lost))
async def handle_connection_lost_state(message: Message, state: FSMContext):
    """
    Handle messages when connection to backend is lost.
    Attempts to restore connection and provides user feedback.
    """
    # Try to test connection
    api_client = get_api_client_from_bot(message.bot)
    
    if api_client:
        # Test with a simple API call
        health_response = await api_client._make_request("GET", "/health")
        
        if health_response.get("success"):
            # Connection restored
            await state.clear()
            await message.answer(
                "✅ Соединение восстановлено!\n"
                "Можете продолжать работу с ботом."
            )
            logger.info("Connection restored for user")
        else:
            # Still no connection
            await message.answer(
                "❌ Соединение с сервером все еще недоступно.\n\n"
                "Попробуйте позже или обратитесь к администратору.\n\n"
                "Доступные команды:\n"
                "/start - попробовать подключиться\n"
                "/help - получить помощь"
            )
    else:
        # No API client available
        await message.answer(
            "❌ Сервис временно недоступен.\n"
            "Попробуйте позже."
        )


@common_router.message(StateFilter(CommonStates.unknown_command))
async def handle_unknown_command_state(message: Message, state: FSMContext):
    """
    Handle messages when user sent an unknown command.
    Provides command suggestions and clears the state.
    """
    await state.clear()
    
    user_input = message.text if message.text else "неизвестная команда"
    
    # Try to suggest similar commands
    available_commands = [
        "/start", "/help", "/language", "/study", 
        "/settings", "/stats", "/hint", "/admin"
    ]
    
    suggestions = []
    user_input_lower = user_input.lower()
    
    # Simple similarity check
    for cmd in available_commands:
        if any(part in cmd for part in user_input_lower.split()) or \
           any(part in user_input_lower for part in cmd.split('/')):
            suggestions.append(cmd)
    
    response = f"❓ Команда '{user_input}' не распознана.\n\n"
    
    if suggestions:
        response += "Возможно, вы имели в виду:\n"
        for suggestion in suggestions[:3]:  # Show max 3 suggestions
            response += f"• {suggestion}\n"
        response += "\n"
    
    response += (
        "Доступные команды:\n"
        "/start - Главное меню\n"
        "/help - Помощь\n"
        "/language - Выбрать язык\n"
        "/study - Изучение слов\n"
        "/settings - Настройки\n"
        "/stats - Статистика"
    )
    
    await message.answer(response)


@common_router.callback_query(StateFilter(CommonStates.handling_api_error))
async def handle_api_error_callback(callback: CallbackQuery, state: FSMContext):
    """
    Handle callback queries in API error state.
    """
    await callback.answer("❌ Действие недоступно из-за ошибки API")
    
    await callback.message.answer(
        "⚠️ Произошла ошибка API.\n\n"
        "Используйте команды:\n"
        "/start - главное меню\n"
        "/help - помощь"
    )


@common_router.callback_query(StateFilter(CommonStates.connection_lost))
async def handle_connection_lost_callback(callback: CallbackQuery, state: FSMContext):
    """
    Handle callback queries when connection is lost.
    """
    await callback.answer("❌ Нет соединения с сервером", show_alert=True)
    
    # Try to restore connection
    api_client = get_api_client_from_bot(callback.bot)
    
    if api_client:
        health_response = await api_client._make_request("GET", "/health")
        
        if health_response.get("success"):
            await state.clear()
            await callback.message.answer("✅ Соединение восстановлено!")
        else:
            await callback.message.answer(
                "❌ Сервер недоступен. Попробуйте позже."
            )


@common_router.callback_query(StateFilter(CommonStates.unknown_command))
async def handle_unknown_command_callback(callback: CallbackQuery, state: FSMContext):
    """
    Handle callback queries in unknown command state.
    """
    await state.clear()
    await callback.answer("Команда обработана")
    
    await callback.message.answer(
        "ℹ️ Вы можете продолжить работу с ботом.\n"
        "Используйте /help для получения списка команд."
    )


# Global error handlers that can transition to meta-states

@common_router.message(Command("retry"))
async def cmd_retry(message: Message, state: FSMContext):
    """
    Handle retry command - clear any error states and provide fresh start.
    """
    current_state = await state.get_state()
    
    if current_state in [
        CommonStates.handling_api_error.state,
        CommonStates.connection_lost.state,
        CommonStates.unknown_command.state
    ]:
        await state.clear()
        await message.answer(
            "🔄 Состояние сброшено. Попробуйте выполнить нужное действие заново.\n\n"
            "Доступные команды:\n"
            "/start - Главное меню\n"
            "/study - Начать изучение\n"
            "/language - Выбрать язык"
        )
    else:
        await message.answer(
            "ℹ️ Нет активных ошибок для повтора.\n"
            "Используйте /help для просмотра доступных команд."
        )


@common_router.message(Command("status"))
async def cmd_status(message: Message, state: FSMContext):
    """
    Show current system status and user state.
    """
    current_state = await state.get_state()
    state_data = await state.get_data()
    db_user_id = state_data.get('db_user_id', None)
    
    # Test API connection
    api_client = get_api_client_from_bot(message.bot)
    api_status = "❌ Недоступен"
    
    if api_client:
        health_response = await api_client._make_request("GET", "/health")
        if health_response.get("success"):
            api_status = "✅ Работает"
    
    status_text = (
        f"📊 **Статус системы:**\n\n"
        f"🔗 API соединение: {api_status}\n"
        f"🎯 Текущее состояние: {current_state or 'None'}\n"
        f"👤 Пользователь в БД: {db_user_id if db_user_id else '❌'}\n"
        f"🌐 Выбранный язык: {state_data.get('current_language', {}).get('name_ru', 'Не выбран')}\n\n"
        f"Используйте /help для получения списка команд."
    )
    
    await message.answer(status_text, parse_mode="Markdown")


def register_common_handlers(dp):
    """
    Register all common handlers with the dispatcher.
    
    Args:
        dp: Dispatcher instance
    """
    dp.include_router(common_router)
    logger.info("Common handlers registered successfully")
    