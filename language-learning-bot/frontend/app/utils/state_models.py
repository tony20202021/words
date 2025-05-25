"""
State models for working with FSM state.
"""

from typing import Dict, List, Any, Optional, Union
from aiogram.fsm.context import FSMContext

# Импортируем централизованные состояния
from app.bot.states.centralized_states import StudyStates, HintStates

from app.utils.hint_constants import DB_FIELD_HINT_KEY_MAPPING
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

class UserWordState:
    """
    Класс для хранения и управления данными текущего слова и процесса изучения.
    """
    
    def __init__(
        self, 
        word_id=None, 
        word_data=None, 
        user_id=None, 
        language_id=None, 
        current_study_index=0, 
        study_words=None,
        study_settings=None,
        flags=None
    ):
        """
        Инициализация состояния слова пользователя.
        
        Args:
            word_id: ID текущего слова
            word_data: Данные текущего слова
            user_id: ID пользователя в БД
            language_id: ID изучаемого языка
            current_study_index: Индекс текущего слова в списке изучения
            study_words: Список слов для изучения
            study_settings: Настройки процесса изучения
            flags: Флаги состояния (например, было ли показано слово)
        """
        self.word_id = word_id
        self.word_data = word_data
        self.user_id = user_id
        self.language_id = language_id
        self.current_study_index = current_study_index
        self.study_words = study_words or []
        self.study_settings = study_settings or {}
        self.flags = flags or {}
        
        # Инициализируем флаги для просмотренных подсказок
        if "used_hints" not in self.flags:
            self.flags["used_hints"] = []
    
    @classmethod
    async def from_state(cls, state):
        """
        Создать экземпляр из состояния FSM.
        
        Args:
            state: Объект состояния FSM
            
        Returns:
            UserWordState: Новый экземпляр класса с данными из состояния
        """
        state_data = await state.get_data()
        
        return cls(
            word_id=state_data.get("current_word_id"),
            word_data=state_data.get("current_word"),
            user_id=state_data.get("db_user_id"),
            language_id=state_data.get("current_language", {}).get("id"),
            current_study_index=state_data.get("current_study_index", 0),
            study_words=state_data.get("study_words", []),
            study_settings={
                "start_word": state_data.get("start_word", 1),
                "skip_marked": state_data.get("skip_marked", False),
                "use_check_date": state_data.get("use_check_date", True),
                "show_hints": state_data.get("show_hints", True),
                "show_debug": state_data.get("show_debug", True),
            },
            flags=state_data.get("user_word_flags", {})
        )
    
    async def save_to_state(self, state):
        """
        Сохранить данные в состояние FSM.
        
        Args:
            state: Объект состояния FSM
        """
        await state.update_data(
            current_word_id=self.word_id,
            current_word=self.word_data,
            db_user_id=self.user_id,
            current_study_index=self.current_study_index,
            study_words=self.study_words,
            start_word=self.study_settings.get("start_word", 1),
            skip_marked=self.study_settings.get("skip_marked", False),
            use_check_date=self.study_settings.get("use_check_date", True),
            show_hints=self.study_settings.get("show_hints", True),
            show_debug=self.study_settings.get("show_debug", True),
            user_word_flags=self.flags
        )
    
    def is_valid(self):
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
    
    def has_more_words(self):
        """
        Проверить, есть ли еще слова для изучения.
        
        Returns:
            bool: True если есть слова для изучения, иначе False
        """
        return (
            isinstance(self.study_words, list) and
            len(self.study_words) > 0 and
            0 <= self.current_study_index < len(self.study_words)
        )
    
    def get_current_word(self):
        """
        Получить данные текущего слова.
        
        Returns:
            dict: Данные текущего слова или None если нет слов или индекс за пределами
        """
        if not self.has_more_words():
            return None
            
        return self.study_words[self.current_study_index]
    
    def advance_to_next_word(self):
        """
        Перейти к следующему слову.
        
        Returns:
            bool: True если успешно перешли к следующему слову, иначе False
        """
        if not self.has_more_words():
            return False
            
        self.current_study_index += 1
        
        # Сбрасываем флаги активных подсказок при переходе к новому слову
        self.flags["used_hints"] = []
        
        # Сбрасываем флаг показа слова
        self.flags["word_shown"] = False
        
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
    
    def set_flag(self, flag_name, flag_value):
        """
        Установить флаг состояния.
        
        Args:
            flag_name: Имя флага
            flag_value: Значение флага
        """
        self.flags[flag_name] = flag_value
    
    def get_flag(self, flag_name, default=None):
        """
        Получить значение флага.
        
        Args:
            flag_name: Имя флага
            default: Значение по умолчанию, если флаг не найден
            
        Returns:
            any: Значение флага или default если флаг не найден
        """
        return self.flags.get(flag_name, default)
        
    def get_used_hints(self):
        """
        Получить список просмотренных подсказок.
        
        Returns:
            List[str]: Список типов просмотренных подсказок
        """
        return self.get_flag("used_hints", [])
    
    def add_used_hint(self, hint_type):
        """
        Добавить подсказку в список просмотренных.
        
        Args:
            hint_type: Тип подсказки
        """
        used_hints = self.get_used_hints()
        if hint_type not in used_hints:
            used_hints.append(hint_type)
            self.set_flag("used_hints", used_hints)
    
    def is_hint_used(self, hint_type):
        """
        Проверить, была ли просмотрена подсказка.
        
        Args:
            hint_type: Тип подсказки
            
        Returns:
            bool: True если подсказка была просмотрена, иначе False
        """
        return hint_type in self.get_used_hints()
    
    def remove_flag(self, flag_name):
        """
        Удалить флаг из состояния.
        
        Args:
            flag_name: Имя флага для удаления
        """
        if flag_name in self.flags:
            del self.flags[flag_name]
            
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
    
    def is_in_completion_state(self):
        """
        Проверить, должно ли состояние быть study_completed.
        
        Returns:
            bool: True если нет больше слов для изучения
        """
        return not self.has_more_words()


class HintState:
    """
    Состояние подсказки для FSM.
    """
    def __init__(self, hint_key: str, hint_name: str, hint_word_id: str, current_hint_text: str = None):
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
    
    def get_hint_type(self) -> str:
        """
        Получить тип подсказки на основе ключа подсказки.
        
        Returns:
            str: Тип подсказки (например, "meaning" и т.д.)
            или None, если тип не определен
        """
        
        return DB_FIELD_HINT_KEY_MAPPING.get(self.hint_key)
    
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
        state_data = await state.get_data()
        user_word_state = await UserWordState.from_state(state)
        
        return {
            "current_fsm_state": current_state,
            "user_word_state_valid": user_word_state.is_valid(),
            "has_more_words": user_word_state.has_more_words(),
            "word_shown": user_word_state.get_flag("word_shown", False),
            "used_hints": user_word_state.get_used_hints(),
            "current_study_index": user_word_state.current_study_index,
            "total_study_words": len(user_word_state.study_words)
        }
    