"""
Утилиты для работы с ежедневной статистикой обучения.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple

from app.utils.api_utils import get_api_client_from_bot
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

# Константы для хранения данных активности в состоянии бота
ACTIVITY_KEY = "daily_activity"
SESSION_START_KEY = "session_start_time"

async def initialize_daily_activity(state):
    """
    Инициализирует данные активности в состоянии бота.
    
    Args:
        state: Состояние FSM
    """
    current_data = await state.get_data()
    
    # Если уже есть данные о сегодняшней активности, используем их
    if ACTIVITY_KEY in current_data:
        return
    
    # Иначе инициализируем новую активность и время начала сессии
    activity_data = {
        "words_studied": 0,
        "words_correct": 0,
        "words_incorrect": 0,
        "minutes_spent": 0,
        "last_update": datetime.now().isoformat()
    }
    
    await state.update_data({
        ACTIVITY_KEY: activity_data,
        SESSION_START_KEY: datetime.now().isoformat()
    })
    
    logger.info("Initialized daily activity data in state")

async def update_activity_stats(state, word_correct=False, word_incorrect=False, word_studied=False):
    """
    Обновляет статистику активности в состоянии.
    
    Args:
        state: Состояние FSM
        word_correct: Увеличить счетчик правильных ответов
        word_incorrect: Увеличить счетчик неправильных ответов
        word_studied: Увеличить счетчик изученных слов
    """
    current_data = await state.get_data()
    
    # Если нет данных активности, инициализируем их
    if ACTIVITY_KEY not in current_data:
        await initialize_daily_activity(state)
        current_data = await state.get_data()
    
    activity_data = current_data.get(ACTIVITY_KEY, {})
    
    # Обновляем счетчики
    if word_correct:
        activity_data["words_correct"] = activity_data.get("words_correct", 0) + 1
    if word_incorrect:
        activity_data["words_incorrect"] = activity