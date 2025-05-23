#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Модуль для обработки OpenAI API моделей (GPT-4, GPT-3.5-turbo и др.).
"""

import logging
import os
import time
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

# Проверяем наличие библиотеки OpenAI
try:
    import openai
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logger.warning("Библиотека openai не установлена. Установите командой: pip install openai")

class OpenAIHandler:
    """Класс для обработки OpenAI API моделей."""
    
    def __init__(self, model_name: str, api_key: Optional[str] = None, temperature: float = 0.3):
        """
        Инициализирует обработчик OpenAI API.
        
        Args:
            model_name (str): Название модели OpenAI
            api_key (str, optional): API ключ OpenAI
            temperature (float): Температура генерации
        """
        if not OPENAI_AVAILABLE:
            raise ImportError("Библиотека openai не установлена. Установите командой: pip install openai")
        
        self.model_name = model_name
        self.temperature = temperature
        
        # Настраиваем API ключ
        api_key = api_key or os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError(
                "OpenAI API ключ не найден. Установите переменную окружения OPENAI_API_KEY "
                "или передайте api_key при инициализации"
            )
        
        # Инициализируем клиент OpenAI
        try:
            self.client = OpenAI(api_key=api_key)
            logger.info(f"Инициализирован обработчик OpenAI для модели {model_name}")
        except Exception as e:
            logger.error(f"Ошибка при инициализации OpenAI клиента: {e}")
            raise
        
        # Счетчики для статистики
        self.total_calls = 0
        self.total_input_tokens = 0
        self.total_output_tokens = 0
    
    def translate(self, character: str, descriptions: List[str] = None, use_description: bool = True) -> str:
        """
        Выполняет перевод с помощью OpenAI API.
        
        Args:
            character (str): Китайский иероглиф для перевода
            descriptions (List[str]): Список описаний на русском языке
            use_description (bool): Использовать ли описания
            
        Returns:
            str: Переведенный текст
        """
        try:
            # Создаем промпт
            messages = self._create_messages(character, descriptions, use_description)
            
            # Выполняем запрос к API
            start_time = time.time()
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=self.temperature,
                max_tokens=50,  # Ограничиваем длину ответа
                timeout=30  # Таймаут 30 секунд
            )
            elapsed_time = time.time() - start_time
            
            # Обновляем статистику
            self.total_calls += 1
            if hasattr(response, 'usage') and response.usage:
                self.total_input_tokens += response.usage.prompt_tokens
                self.total_output_tokens += response.usage.completion_tokens
                
                logger.debug(f"API вызов #{self.total_calls}: {response.usage.prompt_tokens} input, "
                           f"{response.usage.completion_tokens} output токенов за {elapsed_time:.2f}с")
            
            # Извлекаем ответ
            translation = response.choices[0].message.content.strip()
            
            # Постобработка ответа
            translation = self._postprocess_response(translation)
            
            logger.debug(f"Перевод {character} -> {translation}")
            return translation
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Ошибка при переводе {character} через OpenAI API: {error_msg}")
            
            # Проверяем специфические ошибки
            if "unsupported_country_region_territory" in error_msg:
                return f"Недоступно в регионе"
            elif "insufficient_quota" in error_msg:
                return f"Превышен лимит API"
            elif "rate_limit_exceeded" in error_msg:
                return f"Превышен лимит запросов"
            elif "invalid_api_key" in error_msg:
                return f"Неверный API ключ"
            else:
                return f"Ошибка API: {str(e)[:50]}..."
    
    def _create_messages(self, character: str, descriptions: List[str], use_description: bool) -> List[Dict[str, str]]:
        """
        Создает сообщения для OpenAI API.
        
        Args:
            character (str): Китайский иероглиф
            descriptions (List[str]): Описания
            use_description (bool): Использовать ли описания
            
        Returns:
            List[Dict[str, str]]: Список сообщений для API
        """
        # Системное сообщение
        system_content = (
            "Ты - профессиональный переводчик и синолог. "
            "Твоя задача - создать краткий и точный перевод китайского иероглифа или слова на русский язык. "
            "Перевод должен быть максимум 5 слов и отражать основное значение."
        )
        
        # Пользовательское сообщение
        if use_description and descriptions:
            # Подготавливаем описания
            desc_text = "\n".join([f"- {desc}" for desc in descriptions[:5]])  # Берем максимум 5 описаний
            
            user_content = f"""Переведи китайский иероглиф/слово: {character}

Контекст (описание на русском языке):
{desc_text}

Требования:
- Максимум 5 слов в переводе
- Выбери самое важное и частое значение
- Перевод должен быть понятным русскоговорящему
- Только сам перевод, никаких пояснений

Перевод:"""
        else:
            user_content = f"""Переведи китайский иероглиф/слово: {character}

Требования:
- Максимум 5 слов
- Самое основное значение
- Только перевод, без объяснений

Перевод:"""
        
        return [
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_content}
        ]
    
    def _postprocess_response(self, response: str) -> str:
        """
        Постобработка ответа от API.
        
        Args:
            response (str): Ответ от API
            
        Returns:
            str: Обработанный ответ
        """
        # Удаляем лишние символы
        response = response.strip()
        
        # Удаляем кавычки, если есть
        if response.startswith('"') and response.endswith('"'):
            response = response[1:-1]
        if response.startswith("'") and response.endswith("'"):
            response = response[1:-1]
        
        # Удаляем префиксы типа "Перевод:", если есть
        prefixes = ["Перевод:", "перевод:", "Ответ:", "ответ:", "Translation:", "Answer:"]
        for prefix in prefixes:
            if response.startswith(prefix):
                response = response[len(prefix):].strip()
                break
        
        # Ограничиваем длину до 5 слов
        words = response.split()
        if len(words) > 5:
            response = " ".join(words[:5])
        
        # Удаляем лишние знаки препинания
        response = response.strip(".,;:!?-")
        
        return response
    
    def batch_translate(self, items: List[tuple], batch_size: int = 10, use_description: bool = True) -> List[str]:
        """
        Пакетная обработка переводов.
        
        Args:
            items (List[tuple]): Список кортежей (character, descriptions)
            batch_size (int): Размер пакета (для API не критично)
            use_description (bool): Использовать ли описания
            
        Returns:
            List[str]: Список переводов
        """
        results = []
        total = len(items)
        
        logger.info(f"Начинаем пакетную обработку {total} элементов через OpenAI API")
        
        for i, (character, descriptions) in enumerate(items):
            logger.debug(f"Обрабатываем элемент {i+1}/{total}: {character}")
            
            translation = self.translate(character, descriptions, use_description)
            results.append(translation)
            
            # Небольшая пауза чтобы не превысить rate limits
            time.sleep(0.1)
            
            # Выводим прогресс каждые 10 элементов
            if (i + 1) % 10 == 0:
                logger.info(f"Обработано {i+1}/{total} элементов")
        
        logger.info(f"Пакетная обработка завершена. Обработано {len(results)} элементов")
        return results
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Возвращает статистику использования API.
        
        Returns:
            Dict[str, Any]: Статистика использования
        """
        try:
            from .model_config import get_api_cost
        except ImportError:
            # Fallback для случая прямого запуска
            try:
                from model_config import get_api_cost
            except ImportError:
                # Если не удается импортировать, используем базовые значения
                def get_api_cost(model_name):
                    cost_table = {
                        "gpt-4o": {"input": 0.005, "output": 0.015},
                        "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
                        "gpt-4-turbo": {"input": 0.01, "output": 0.03},
                        "gpt-3.5-turbo": {"input": 0.001, "output": 0.002},
                    }
                    return cost_table.get(model_name, {"input": 0, "output": 0})
        
        cost_info = get_api_cost(self.model_name)
        estimated_cost = (
            self.total_input_tokens * cost_info["input"] / 1000 +
            self.total_output_tokens * cost_info["output"] / 1000
        )
        
        return {
            "model": self.model_name,
            "total_calls": self.total_calls,
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "estimated_cost_usd": round(estimated_cost, 4),
            "avg_input_tokens": round(self.total_input_tokens / max(self.total_calls, 1), 1),
            "avg_output_tokens": round(self.total_output_tokens / max(self.total_calls, 1), 1)
        }
    
    def print_statistics(self):
        """Выводит статистику использования API."""
        stats = self.get_statistics()
        
        logger.info("=" * 50)
        logger.info("Статистика использования OpenAI API:")
        logger.info(f"Модель: {stats['model']}")
        logger.info(f"Всего вызовов: {stats['total_calls']}")
        logger.info(f"Входные токены: {stats['total_input_tokens']}")
        logger.info(f"Выходные токены: {stats['total_output_tokens']}")
        logger.info(f"Средний размер запроса: {stats['avg_input_tokens']} токенов")
        logger.info(f"Средний размер ответа: {stats['avg_output_tokens']} токенов")
        logger.info(f"Примерная стоимость: ${stats['estimated_cost_usd']}")
        logger.info("=" * 50)
        