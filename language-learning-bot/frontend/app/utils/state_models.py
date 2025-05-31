"""
Enhanced state models with batch loading support.
ОБНОВЛЕНО: Добавлена поддержка автоматической загрузки партий слов.
"""

from typing import Dict, List, Any, Optional
from aiogram.fsm.context import FSMContext

# Импортируем централизованные состояния
from app.bot.states.centralized_states import StudyStates, HintStates

from app.utils.hint_constants import DB_FIELD_HINT_KEY_MAPPING
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class UserWordState:
    """
    Enhanced UserWordState class with batch loading support.
    Tracks current word, study progress, and automatic batch loading.
    """
    
    def __init__(
        self, 
        word_id=None, 
        word_data=None, 
        user_id=None, 
        language_id=None,
        current_index_in_batch=0,
        study_words=None,
        study_settings=None,
        flags=None,
        # НОВОЕ: Поля для работы с партиями
        batch_info={},
        session_info={},
    ):
        """
        Инициализация состояния слова пользователя.
        
        Args:
            word_id: ID текущего слова
            word_data: Данные текущего слова
            user_id: ID пользователя в БД
            language_id: ID изучаемого языка
            current_index_in_batch: Индекс текущего слова в списке изучения
            study_words: Список слов для изучения
            study_settings: Настройки процесса изучения
            flags: Флаги состояния (например, было ли показано слово)
            total_words_processed: Количество обработанных слов в сессии
            current_batch_index: Номер текущей партии
            words_loaded_in_session: Всего слов загружено в сессии
        """
        self.word_id = word_id
        self.word_data = word_data or {}
        self.user_id = user_id
        self.language_id = language_id
        self.current_index_in_batch = current_index_in_batch
        self.study_words = study_words or []
        self.study_settings = study_settings or {}
        self.flags = flags or {}

        # НОВОЕ: Счетчики для партий
        self.batch_info = batch_info
        self.session_info = session_info
        
        # Инициализируем флаги для просмотренных подсказок
        if "used_hints" not in self.flags:
            self.flags["used_hints"] = []

    @classmethod
    async def from_state(cls, state: FSMContext) -> 'UserWordState':
        """Create UserWordState from FSM context data."""
        data = await state.get_data()
        
        # Создаем экземпляр с данными из состояния
        instance = cls(
            word_id=data.get("word_id") or data.get("current_word_id"),
            word_data=data.get("word_data") or data.get("current_word", {}),
            user_id=data.get("user_id") or data.get("db_user_id"),
            language_id=data.get("language_id") or data.get("current_language", {}).get("id"),
            current_index_in_batch=data.get("current_index_in_batch", 0),
            study_words=data.get("study_words", []),
            study_settings=data.get("study_settings", {}),
            flags=data.get("flags") or data.get("user_word_flags", {}),
            batch_info=data.get("batch_info", {}),
            session_info=data.get("session_info", {}),
        )
        
        logger.debug(f"UserWordState loaded from FSM: batch #{instance.batch_info.get('current_batch_index', '?')}, "
                    f"processed: {instance.session_info.get('total_words_processed', '?')}")
        
        return instance

    async def save_to_state(self, state: FSMContext):
        """Save the current state to FSM context."""
        state_data = {
            "word_id": self.word_id,
            "word_data": self.word_data,
            "user_id": self.user_id,
            "language_id": self.language_id,
            "current_index_in_batch": self.current_index_in_batch,
            "study_words": self.study_words,
            "study_settings": self.study_settings,
            "flags": self.flags,
            # данные о партиях
            "batch_info": self.batch_info,
            "session_info": self.session_info,
        }
        
        await state.update_data(**state_data)
        logger.debug(f"UserWordState saved to FSM: batch #{self.batch_info['current_batch_index']}, "
                    f"processed: {self.session_info['total_words_processed']}")

    def is_valid(self) -> bool:
        """
        Проверить, что состояние содержит необходимые данные.
        
        Returns:
            bool: True если состояние валидно, иначе False
        """
        return (
            self.user_id is not None and 
            self.language_id is not None and
            isinstance(self.study_words, list) and
            len(self.study_words) > 0
        )

    def has_more_words(self) -> bool:
        """
        Проверить, есть ли еще слова для изучения в текущей партии.
        
        Returns:
            bool: True если есть слова для изучения, иначе False
        """
        return (
            isinstance(self.study_words, list) and
            len(self.study_words) > 0 and
            0 <= self.current_index_in_batch < len(self.study_words)
        )

    def get_current_word(self) -> Optional[Dict]:
        """
        Получить данные текущего слова.
        
        Returns:
            dict: Данные текущего слова или None если нет слов или индекс за пределами
        """
        if not self.has_more_words():
            return None
            
        return self.study_words[self.current_index_in_batch]

    def set_current_word(self, new_word) -> None:
        """
            new_word: Данные слова
        """
        self.study_words[self.current_index_in_batch] = new_word

    def advance_to_next_word(self) -> bool:
        """
        Перейти к следующему слову в текущей партии.
        ОБНОВЛЕНО: Не увеличивает общий счетчик обработанных слов - это делается отдельно.
        
        Returns:
            bool: True если успешно перешли к следующему слову, иначе False
        """
        if not self.has_more_words():
            return False
            
        self.current_index_in_batch += 1
        
        # Сбрасываем флаги активных подсказок при переходе к новому слову
        self.flags["used_hints"] = []
        
        # Сбрасываем флаг показа слова
        self.flags["word_shown"] = False
        
        # Clear word-specific flags
        self.remove_flag('word_shown')
        self.remove_flag('used_hints')
        self.remove_flag('active_hints')
        self.remove_flag('pending_word_know')
        self.remove_flag('pending_next_word')
        self.remove_flag('word_processed')
        
        if self.has_more_words():
            # Обновляем данные текущего слова
            current_word = self.get_current_word()
            
            # Ищем ID в различных полях
            for id_field in ["_id", "id", "word_id"]:
                if id_field in current_word and current_word[id_field]:
                    self.word_id = current_word[id_field]
                    break
                    
            self.word_data = current_word
            return True
            
        return False

    def get_session_info(self) -> int:
        return self.session_info

    def set_session_info(self, session_info) -> None:
        self.session_info = session_info

    def get_batch_info(self) -> int:
        return self.batch_info

    def set_batch_info(self, batch_info) -> None:
        self.batch_info = batch_info

    def get_next_batch_skip(self) -> int:
        """
        Рассчитать skip для следующей партии.
        
        Returns:
            int: Количество слов для пропуска при запросе следующей партии
        """
        return self.batch_info["batch_start_number"] + self.batch_info["batch_requested_count"]

    def mark_word_as_processed(self):
        """
        Отметить текущее слово как обработанное.
        Увеличивает счетчик обработанных слов в сессии.
        """
        if not self.get_flag('word_processed', False):
            self.session_info['total_words_processed'] += 1
            self.set_flag('word_processed', True)
            logger.info(f"Word marked as processed. Total processed: {self.session_info['total_words_processed']}")

    def reset_session_counters(self):
        """
        Сбросить счетчики сессии (при перезапуске /study).
        """
        self.session_info['total_words_processed'] = 0
        self.batch_info["current_batch_index"] = 0
        self.session_info['words_loaded_in_session'] = 0
        logger.info("Session counters reset")

    def load_new_batch(self, new_words: List[Dict]) -> bool:
        """
        Загрузить новую партию слов.
        
        Args:
            new_words: Список новых слов для изучения
            
        Returns:
            bool: True если партия загружена успешно, False иначе
        """
        if not new_words:
            logger.warning("Attempted to load empty batch")
            return False
            
        self.study_words = new_words
        self.current_index_in_batch = 0
        self.session_info['words_loaded_in_session'] += len(new_words)
        
        # Устанавливаем текущее слово из новой партии
        if self.has_more_words():
            current_word = self.get_current_word()
            
            # Находим ID слова
            for id_field in ["_id", "id", "word_id"]:
                if id_field in current_word and current_word[id_field]:
                    self.word_id = current_word[id_field]
                    break
                    
            self.word_data = current_word
        
        # Clear word-specific flags for new batch
        self.remove_flag('word_shown')
        self.remove_flag('used_hints')
        self.remove_flag('active_hints')
        self.remove_flag('pending_word_know')
        self.remove_flag('pending_next_word')
        self.remove_flag('word_processed')
        
        logger.info(f"Loaded batch #{self.batch_info['current_batch_index']}: {len(new_words)} words, "
                   f"total in session: {self.session_info['words_loaded_in_session']}")
        return True

    def get_session_statistics(self) -> Dict[str, Any]:
        """
        Get comprehensive session statistics.
        НОВОЕ: Статистика сессии для отображения в завершении изучения.
        
        Returns:
            Dict with session statistics
        """
        batch_info = self.get_batch_info()
        
        return {
            **batch_info,
            "batches_loaded": self.batch_info["current_batch_index"],
            "average_words_per_batch": (
                self.session_info['total_words_processed'] / max(1, self.batch_info["current_batch_index"])
            ),
            "current_session_progress": (
                f"{batch_info['current_index_in_batch'] + 1}/{batch_info['words_in_current_batch']}"
                if batch_info['words_in_current_batch'] > 0 else "0/0"
            )
        }

    # Методы для работы с флагами
    def set_flag(self, flag_name: str, flag_value):
        """
        Установить флаг состояния.
        
        Args:
            flag_name: Имя флага
            flag_value: Значение флага
        """
        self.flags[flag_name] = flag_value

    def get_flag(self, flag_name: str, default=None):
        """
        Получить значение флага.
        
        Args:
            flag_name: Имя флага
            default: Значение по умолчанию, если флаг не найден
            
        Returns:
            any: Значение флага или default если флаг не найден
        """
        return self.flags.get(flag_name, default)

    def remove_flag(self, flag_name: str):
        """
        Удалить флаг из состояния.
        
        Args:
            flag_name: Имя флага для удаления
        """
        if flag_name in self.flags:
            del self.flags[flag_name]

    def clear_word_flags(self):
        """Clear all word-specific flags."""
        word_flags = [
            'word_shown', 'used_hints', 'active_hints', 
            'pending_word_know', 'pending_next_word', 'word_processed'
        ]
        for flag in word_flags:
            self.remove_flag(flag)

    def get_used_hints(self) -> List[str]:
        """
        Получить список просмотренных подсказок.
        
        Returns:
            List[str]: Список типов просмотренных подсказок
        """
        return self.get_flag("used_hints", [])

    def add_used_hint(self, hint_type: str):
        """
        Добавить подсказку в список просмотренных.
        
        Args:
            hint_type: Тип подсказки
        """
        used_hints = self.get_used_hints()
        if hint_type not in used_hints:
            used_hints.append(hint_type)
            self.set_flag("used_hints", used_hints)

    def is_hint_used(self, hint_type: str) -> bool:
        """
        Проверить, была ли просмотрена подсказка.
        
        Args:
            hint_type: Тип подсказки
            
        Returns:
            bool: True если подсказка была просмотрена, иначе False
        """
        return hint_type in self.get_used_hints()

    # НОВОЕ: Методы для работы с FSM состояниями
    async def get_appropriate_study_state(self, state: FSMContext):
        """
        Определить подходящее состояние изучения на основе текущих флагов.
        
        Args:
            state: Объект состояния FSM
            
        Returns:
            State: Подходящее состояние для установки
        """
        word_shown = self.get_flag("word_shown", False)
        pending_next_word = self.get_flag("pending_next_word", False)
        pending_word_know = self.get_flag("pending_word_know", False)
        
        if pending_word_know and pending_next_word:
            return StudyStates.confirming_word_knowledge
        elif word_shown:
            return StudyStates.viewing_word_details
        elif not self.has_more_words():
            return StudyStates.study_completed
        else:
            return StudyStates.studying

    async def transition_to_appropriate_state(self, state: FSMContext):
        """
        Перейти в подходящее состояние изучения.
        
        Args:
            state: Объект состояния FSM
        """
        appropriate_state = await self.get_appropriate_study_state(state)
        await state.set_state(appropriate_state)
        logger.info(f"Transitioned to state: {appropriate_state.state}")

    def is_in_completion_state(self) -> bool:
        """
        Проверить, должно ли состояние быть study_completed.
        
        Returns:
            bool: True если нет больше слов для изучения
        """
        return not self.has_more_words()


class HintState:
    """State for hint operations."""
    
    def __init__(
        self, 
        hint_key: str = None, 
        hint_name: str = None, 
        hint_word_id: str = None,
        current_hint_text: str = None
    ):
        """
        Инициализация состояния подсказки.
        
        Args:
            hint_key: Ключ подсказки (поле в БД)
            hint_name: Название подсказки для отображения
            hint_word_id: ID слова
            current_hint_text: Текущий текст подсказки (для редактирования)
        """
        self.hint_key = hint_key
        self.hint_name = hint_name
        self.hint_word_id = hint_word_id
        self.current_hint_text = current_hint_text

    def is_valid(self) -> bool:
        """
        Проверка корректности состояния.
        
        Returns:
            bool: True если состояние корректно
        """
        return bool(self.hint_key) and bool(self.hint_name) and bool(self.hint_word_id)

    def get_hint_type(self) -> Optional[str]:
        """
        Получить тип подсказки на основе ключа подсказки.
        
        Returns:
            str: Тип подсказки (например, "meaning" и т.д.)
            или None, если тип не определен
        """
        return DB_FIELD_HINT_KEY_MAPPING.get(self.hint_key)

    async def save_to_state(self, state: FSMContext) -> None:
        """
        Сохранение состояния в FSM.
        
        Args:
            state: Контекст состояния FSM
        """
        hint_state_data = {
            "hint_key": self.hint_key,
            "hint_name": self.hint_name,
            "hint_word_id": self.hint_word_id,
            "current_hint_text": self.current_hint_text
        }
        await state.update_data(hint_state=hint_state_data)

    @classmethod
    async def from_state(cls, state: FSMContext) -> "HintState":
        """
        Получение состояния из FSM.
        
        Args:
            state: Контекст состояния FSM
            
        Returns:
            HintState: Новый объект состояния подсказки
        """
        state_data = await state.get_data()
        hint_state_data = state_data.get("hint_state", {})
        
        return cls(
            hint_key=hint_state_data.get("hint_key"),
            hint_name=hint_state_data.get("hint_name"),
            hint_word_id=hint_state_data.get("hint_word_id"),
            current_hint_text=hint_state_data.get("current_hint_text")
        )

    # НОВОЕ: Методы для работы с FSM состояниями подсказок
    async def get_appropriate_hint_state(self, action: str = "viewing"):
        """
        Определить подходящее состояние подсказки на основе действия.
        
        Args:
            action: Тип действия ("creating", "editing", "viewing", "deleting")
            
        Returns:
            State: Подходящее состояние для установки
        """
        if action == "creating":
            return HintStates.creating
        elif action == "editing":
            return HintStates.editing
        elif action == "viewing":
            return HintStates.viewing
        elif action == "deleting":
            return HintStates.confirming_deletion
        else:
            logger.warning(f"Unknown hint action: {action}, defaulting to viewing")
            return HintStates.viewing

    async def clear_from_state(self, state: FSMContext):
        """
        Очистить данные подсказки из состояния FSM.
        
        Args:
            state: Контекст состояния FSM
        """
        state_data = await state.get_data()
        if "hint_state" in state_data:
            state_data.pop("hint_state")
            await state.set_data(state_data)
            logger.info("Hint state cleared from FSM")


# НОВОЕ: Класс для управления состояниями системы
class StateManager:
    """
    Менеджер для управления переходами между состояниями.
    """
    
    @staticmethod
    async def safe_transition_to_study(state: FSMContext, user_word_state: UserWordState = None):
        """
        Безопасный переход к состоянию изучения с автоматическим определением подходящего состояния.
        
        Args:
            state: Контекст состояния FSM
            user_word_state: Состояние слова пользователя (опционально)
        """
        if user_word_state is None:
            user_word_state = await UserWordState.from_state(state)
        
        if user_word_state.is_valid():
            await user_word_state.transition_to_appropriate_state(state)
        else:
            # Fallback к основному состоянию изучения
            await state.set_state(StudyStates.studying)
            logger.warning("Invalid user word state, fell back to StudyStates.studying")

    @staticmethod
    async def transition_from_hint_to_study(state: FSMContext, word_shown: bool = False):
        """
        Переход от состояний подсказки к соответствующему состоянию изучения.
        
        Args:
            state: Контекст состояния FSM
            word_shown: Было ли показано слово
        """
        if word_shown:
            await state.set_state(StudyStates.viewing_word_details)
        else:
            await state.set_state(StudyStates.studying)
        logger.info(f"Transitioned from hint to {'viewing_word_details' if word_shown else 'studying'}")

    @staticmethod
    async def handle_study_completion(state: FSMContext):
        """
        Обработка завершения изучения всех слов.
        
        Args:
            state: Контекст состояния FSM
        """
        await state.set_state(StudyStates.study_completed)
        logger.info("Transitioned to study completion state")

    @staticmethod
    async def get_current_state_info(state: FSMContext) -> Dict[str, Any]:
        """
        Получить информацию о текущем состоянии для отладки.
        
        Args:
            state: Контекст состояния FSM
            
        Returns:
            Dict: Информация о состоянии
        """
        current_state = await state.get_state()
        user_word_state = await UserWordState.from_state(state)
        
        return {
            "current_fsm_state": current_state,
            "user_word_state_valid": user_word_state.is_valid(),
            "has_more_words": user_word_state.has_more_words(),
            "word_shown": user_word_state.get_flag("word_shown", False),
            "used_hints": user_word_state.get_used_hints(),
            "current_index_in_batch": user_word_state.current_index_in_batch,
            "total_study_words": len(user_word_state.study_words),
            # НОВОЕ: Информация о партиях
            "batch_info": user_word_state.get_batch_info()
        }
    