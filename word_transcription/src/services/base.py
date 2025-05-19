from abc import ABC, abstractmethod
from typing import Optional
import logging

# Настройка логирования
logger = logging.getLogger(__name__)

class TranscriptionService(ABC):
    """
    Абстрактный базовый класс для всех сервисов транскрипции.
    
    Этот класс определяет общий интерфейс для всех сервисов, 
    которые предоставляют транскрипции иностранных символов.
    """
    
    @abstractmethod
    def get_transcription(self, character: str, lang_code: str) -> Optional[str]:
        """
        Получает транскрипцию для иероглифа или символа.
        
        Args:
            character (str): Иероглиф или символ для транскрибирования
            lang_code (str): Код языка (например, 'zh' для китайского, 'ja' для японского)
            
        Returns:
            Optional[str]: Строка с транскрипцией или None в случае ошибки
        """
        pass
    
    def supports_language(self, lang_code: str) -> bool:
        """
        Проверяет, поддерживает ли сервис указанный язык.
        
        Args:
            lang_code (str): Код языка
            
        Returns:
            bool: True, если язык поддерживается, иначе False
        """
        # По умолчанию возвращаем True, подклассы могут переопределить этот метод
        return True
    
    def initialize(self) -> bool:
        """
        Инициализирует сервис, загружает необходимые данные.
        
        Returns:
            bool: True, если инициализация прошла успешно, иначе False
        """
        # По умолчанию считаем, что инициализация не нужна
        return True
    
    def close(self) -> None:
        """
        Освобождает ресурсы, используемые сервисом.
        """
        # По умолчанию ничего не делаем
        pass
    
    def get_name(self) -> str:
        """
        Возвращает имя сервиса.
        
        Returns:
            str: Имя сервиса
        """
        # По умолчанию используем имя класса
        return self.__class__.__name__
    
    def get_priority(self) -> int:
        """
        Возвращает приоритет сервиса. Сервисы с более высоким приоритетом используются в первую очередь.
        
        Returns:
            int: Приоритет сервиса (чем больше, тем выше приоритет)
        """
        # По умолчанию возвращаем 0, подклассы могут переопределить этот метод
        return 0
    
    def __str__(self) -> str:
        """
        Возвращает строковое представление сервиса.
        
        Returns:
            str: Строковое представление
        """
        return f"{self.get_name()} (priority: {self.get_priority()})"
        