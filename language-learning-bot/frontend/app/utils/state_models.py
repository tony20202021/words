"""
State models for working with FSM state.
"""

from typing import Dict, List, Any, Optional, Union
from aiogram.fsm.context import FSMContext
from app.utils.hint_constants import DB_FIELD_HINT_KEY_MAPPING
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
        
        # Инициализируем флаги для активных подсказок, если их нет
        if "active_hints" not in self.flags:
            self.flags["active_hints"] = []
        
        # Инициализируем флаги для просмотренных подсказок
        if "seen_hints" not in self.flags:
            self.flags["seen_hints"] = []
    
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
        self.flags["active_hints"] = []
        self.flags["seen_hints"] = []
        
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
    
    def get_active_hints(self):
        """
        Получить список активных подсказок.
        
        Returns:
            List[str]: Список типов активных подсказок
        """
        return self.get_flag("active_hints", [])
    
    def add_active_hint(self, hint_type):
        """
        Добавить подсказку в список активных.
        
        Args:
            hint_type: Тип подсказки
        """
        active_hints = self.get_active_hints()
        if hint_type not in active_hints:
            active_hints.append(hint_type)
            self.set_flag("active_hints", active_hints)
    
    def remove_active_hint(self, hint_type):
        """
        Удалить подсказку из списка активных.
        
        Args:
            hint_type: Тип подсказки
        """
        active_hints = self.get_active_hints()
        if hint_type in active_hints:
            active_hints.remove(hint_type)
            self.set_flag("active_hints", active_hints)
    
    def is_hint_active(self, hint_type):
        """
        Проверить, активна ли подсказка.
        
        Args:
            hint_type: Тип подсказки
            
        Returns:
            bool: True если подсказка активна, иначе False
        """
        return hint_type in self.get_active_hints()
    
    def get_seen_hints(self):
        """
        Получить список просмотренных подсказок.
        
        Returns:
            List[str]: Список типов просмотренных подсказок
        """
        return self.get_flag("seen_hints", [])
    
    def add_seen_hint(self, hint_type):
        """
        Добавить подсказку в список просмотренных.
        
        Args:
            hint_type: Тип подсказки
        """
        seen_hints = self.get_seen_hints()
        if hint_type not in seen_hints:
            seen_hints.append(hint_type)
            self.set_flag("seen_hints", seen_hints)
    
    def is_hint_seen(self, hint_type):
        """
        Проверить, была ли просмотрена подсказка.
        
        Args:
            hint_type: Тип подсказки
            
        Returns:
            bool: True если подсказка была просмотрена, иначе False
        """
        return hint_type in self.get_seen_hints()
    
    def remove_flag(self, flag_name):
        """
        Удалить флаг из состояния.
        
        Args:
            flag_name: Имя флага для удаления
        """
        if flag_name in self.flags:
            del self.flags[flag_name]


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