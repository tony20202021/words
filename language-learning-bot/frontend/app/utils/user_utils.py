from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from app.utils.logger import setup_logger

logger = setup_logger(__name__)


async def get_or_create_user(user_info, api_client) -> tuple[str, dict]:
    """
    Get or create user in database.
    
    Args:
        user_info: User information from Telegram
        api_client: API client
        
    Returns:
        str: Database user ID or None if failed
    """
    user_id = user_info.id
    username = user_info.username
    
    # Check if user exists
    user_response = await api_client.get_user_by_telegram_id(user_id)
    
    if not user_response["success"]:
        logger.error(f"Failed to get user with Telegram ID {user_id}: {user_response['error']}")
        return None, None
        
    users = user_response["result"]
    user_data = users[0] if users and isinstance(users, list) and len(users) > 0 else None
    
    if user_data:
        db_user_id = user_data.get("id")
    else:
        # Create new user
        new_user_data = {
            "telegram_id": user_id,
            "username": username,
            "first_name": user_info.first_name,
            "last_name": user_info.last_name
        }
        
        create_response = await api_client.create_user(new_user_data)
        if not create_response["success"]:
            logger.error(f"Failed to create user with Telegram ID {user_id}: {user_response['error']}")
            return None, None
            
        user_data = create_response["result"]
        if user_data:
            db_user_id = user_data.get("id")
        else:
            db_user_id = None
    
    return db_user_id, user_data



async def validate_language_selected(state: FSMContext, message_or_callback) -> dict:
    """
    Validate that user has selected a language.
    
    Args:
        state: FSM context
        message_or_callback: Message or CallbackQuery object
        
    Returns:
        language
    """
    state_data = await state.get_data()
    current_language = state_data.get("current_language", None)
    
    if not current_language or not current_language.get("id"):
        error_message = (
            "⚠️ Сначала выберите язык для изучения с помощью команды /language"
        )
        
        if isinstance(message_or_callback, CallbackQuery):
            await message_or_callback.answer("Язык не выбран", show_alert=True)
            await message_or_callback.message.answer(error_message)
        else:
            await message_or_callback.answer(error_message)
        
        return None
    
    return current_language
