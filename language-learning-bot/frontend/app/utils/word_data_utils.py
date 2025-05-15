"""
Utilities for working with word data and user word data.
"""

import logging
from typing import Dict, Any, Optional, Tuple, Union
from datetime import datetime, timedelta

from aiogram.types import Message, CallbackQuery
from app.utils.api_utils import get_api_client_from_bot
from app.utils.error_utils import handle_api_error
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

# Константа для максимального интервала повторения
MAX_INTERVAL_DAYS = 32

async def ensure_user_word_data(
    bot, 
    user_id: str, 
    word_id: str, 
    update_data: Dict[str, Any], 
    word: Optional[Dict[str, Any]] = None,
    message_obj = None
) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """
    Ensure that user word data exists and is updated properly.
    If data exists, update it; if not, create it.
    
    Args:
        bot: Bot instance to get API client
        user_id: User ID in database
        word_id: Word ID
        update_data: Data to update/create
        word: Optional word data for getting language_id
        message_obj: Optional message object for error handling
        
    Returns:
        Tuple[bool, Optional[Dict[str, Any]]]: (success, result_data) tuple
    """
    # Get API client
    api_client = get_api_client_from_bot(bot)
    
    # Try to get existing word data
    word_data_response = await api_client.get_user_word_data(user_id, word_id)
    # print(word_data_response)
    
    if word_data_response["success"] and word_data_response["result"]:
        # Update existing data
        logger.info(f"Updating existing word data for user={user_id}, word={word_id}")
        update_response = await api_client.update_user_word_data(user_id, word_id, update_data)
        logger.info(f"update_response={update_response}")
        # word_data_response = await api_client.get_user_word_data(user_id, word_id)
        # print(word_data_response)
        
        if message_obj and not update_response["success"]:
            await handle_api_error(update_response, message_obj, "Error updating word data")
            return False, None
            
        return update_response["success"], update_response.get("result")
    else:
        # Create new data - need language_id
        language_id = None
        
        # Try to get language_id from word data
        if word and "language_id" in word:
            language_id = word["language_id"]
        
        if not language_id:
            error_msg = "Cannot create user word data: missing language_id"
            logger.error(error_msg)
            
            if message_obj:
                if isinstance(message_obj, CallbackQuery):
                    await message_obj.message.answer(f"❌ Ошибка: {error_msg}")
                else:
                    await message_obj.answer(f"❌ Ошибка: {error_msg}")
            
            return False, None
        
        # Create new data
        logger.info(f"Creating new word data for user={user_id}, word={word_id}, language={language_id}")
        create_data = {
            "word_id": word_id,
            "language_id": language_id,
            **update_data
        }
        
        create_response = await api_client.create_user_word_data(user_id, create_data)
        logger.info(f"create_response={create_response}")
        
        if message_obj and not create_response["success"]:
            await handle_api_error(create_response, message_obj, "Error creating word data")
            return False, None
            
        return create_response["success"], create_response.get("result")

async def update_word_score(
    bot, 
    user_id: str, 
    word_id: str, 
    score: int, 
    word: Dict[str, Any],
    message_obj = None,
    is_skipped: bool = False
) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """
    Update word score and calculate next check date based on score.
    
    Args:
        bot: Bot instance to get API client
        user_id: User ID in database
        word_id: Word ID
        score: New score (0 or 1)
        word: Word data for getting language_id
        message_obj: Optional message object for error handling
        is_skipped: Whether the word is marked as skipped
        
    Returns:
        Tuple[bool, Optional[Dict[str, Any]]]: (success, result_data) tuple
    """
    logger.info(f"update_word_score for user: {user_id}, score: {score}, word: {word}")

    # Get API client
    api_client = get_api_client_from_bot(bot)
    
    # Get current word data
    word_data_response = await api_client.get_user_word_data(user_id, word_id)
    if (not word_data_response["success"]):
        logger.error(f"get_user_word_data: not success")
        logger.error(f"word_data_response: {word_data_response}")
        return False, None

    if (word_data_response["result"] is None):
        word_data = {}
    else:
        word_data = word_data_response["result"]
    
    # Prepare update data
    update_data = {
        "score": score,
        "is_skipped": is_skipped
    }
    
    # Calculate interval and next check date based on score
    if score == 1:
        current_score = word_data.get("score", 0)
        current_interval = word_data.get("check_interval", 0)
        current_check_date_str = word_data.get("next_check_date")
        
        # Initialize with default values for new records
        should_update_interval = True
        
        # Check if we need to update interval based on current date and check date
        if current_check_date_str and current_score == 1:
            try:
                # Parse the date string into a datetime object
                current_check_date = datetime.fromisoformat(current_check_date_str.replace('Z', '+00:00'))
                
                # Calculate days difference between now and check date
                delta_days = (datetime.now() - current_check_date).days
                
                # Only update interval if we're on or past the check date
                should_update_interval = delta_days >= 0
            except (ValueError, TypeError):
                # If there's any issue parsing the date, default to updating
                logger.warning(f"Error parsing check date: {current_check_date_str}")
                should_update_interval = True
        
        # Update interval if needed
        if should_update_interval or current_score == 0:
            # Calculate new interval (double previous, max 32 days)
            new_interval = 1  # Default start with 1 day
            if current_interval > 0:
                new_interval = min(current_interval * 2, MAX_INTERVAL_DAYS)
                
            # Calculate new check date
            new_check_date = (datetime.now() + timedelta(days=new_interval)).replace(
                hour=0, minute=0, second=0, microsecond=0
            ).isoformat()
            
            # Add to update data
            update_data["check_interval"] = new_interval
            update_data["next_check_date"] = new_check_date
        else:
            # Keep current interval and check date
            update_data["check_interval"] = current_interval
            update_data["next_check_date"] = current_check_date_str
    else:
        # For score 0, reset interval and set next check date to today
        update_data["check_interval"] = 0
        update_data["next_check_date"] = datetime.now().replace(
            hour=0, minute=0, second=0, microsecond=0
        ).isoformat()
    
    # Update or create word data
    return await ensure_user_word_data(bot, user_id, word_id, update_data, word, message_obj)

async def get_hint_text(
    bot, 
    user_id: str, 
    word_id: str, 
    hint_key: str, 
    word: Dict[str, Any]
) -> Optional[str]:
    """
    Get hint text from various sources (word data, user_word_data, or API).
    
    Args:
        bot: Bot instance to get API client
        user_id: User ID in database
        word_id: Word ID
        hint_key: Hint key (e.g., 'hint_syllables')
        word: Word data
        
    Returns:
        Optional[str]: Hint text or None if not found
    """
    # First check in word data
    hint_text = word.get(hint_key)
    
    # Then check in user_word_data if present
    if not hint_text:
        user_word_data = word.get("user_word_data", {})
        if user_word_data:
            hint_text = user_word_data.get(hint_key)
    
    # Finally try to get from API
    if not hint_text:
        api_client = get_api_client_from_bot(bot)
        word_data_response = await api_client.get_user_word_data(user_id, word_id)
        
        if word_data_response["success"] and word_data_response["result"]:
            hint_text = word_data_response["result"].get(hint_key)
    
    return hint_text

def calculate_new_interval(current_data: Optional[Dict[str, Any]], score: int) -> Dict[str, Any]:
    """
    Calculate new interval based on spaced repetition algorithm:
    - If score is 0, reset interval
    - If score is 1, increase interval by multiplying by 2 
      (or set to 1 if there was no interval or it was 0)
    
    Args:
        current_data: Current word data
        score: New score (0 or 1)
        
    Returns:
        Dict with updated fields
    """
    new_data = {"score": score}
    
    if score == 0:
        # Reset interval
        new_data["check_interval"] = 0
        new_data["next_check_date"] = None
    else:  # score == 1
        # Get current interval
        current_interval = 0
        if current_data and "check_interval" in current_data:
            current_interval = current_data.get("check_interval", 0)
            
        # Calculate new interval
        if current_interval == 0:
            new_interval = 1  # Start with 1 day
        else:
            new_interval = current_interval * 2  # Double the interval
            
        # Cap the interval at maximum
        if new_interval > MAX_INTERVAL_DAYS:
            new_interval = MAX_INTERVAL_DAYS
            
        # Calculate next check date
        next_check_date = datetime.now() + timedelta(days=new_interval)
        
        new_data["check_interval"] = new_interval
        new_data["next_check_date"] = next_check_date
    
    return new_data