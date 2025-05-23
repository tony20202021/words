#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Основной модуль для генерации кратких переводов китайских слов
с использованием языковых моделей из Hugging Face.
"""

import torch
import logging
import time

from .model_config import get_available_models, get_model_type, is_openai_model, AVAILABLE_MODELS
from .model_loader import ModelLoader
from .prompt_generator import PromptGenerator, process_response
from .seq2seq_handler import Seq2SeqHandler
from .openai_handler import OpenAIHandler

# Получаем logger, но не настраиваем базовую конфигурацию
logger = logging.getLogger(__name__)

class LLMTranslator:
    """
    Класс для создания кратких переводов китайских слов
    с использованием языковых моделей.
    """
    
    def __init__(self, model_name="qwen2-7b", use_cuda=True, max_length=256, temperature=0.3):
        """
        Инициализация переводчика.
        
        Args:
            model_name (str): Название модели из списка AVAILABLE_MODELS
            use_cuda (bool): Использовать ли CUDA для ускорения
            max_length (int): Максимальная длина генерируемого текста
            temperature (float): Температура генерации (выше - более креативно)
        """
        self.model_name = model_name
        self.hf_model_name = AVAILABLE_MODELS.get(model_name, model_name)
        self.model_type = get_model_type(model_name)
        self.use_cuda = use_cuda and torch.cuda.is_available()
        self.max_length = max_length
        self.temperature = temperature
        self.device = "cuda" if self.use_cuda else "cpu"
        
        logger.info(f"Инициализация переводчика:")
        logger.info(f"  Модель: {self.model_name}")
        logger.info(f"  HF имя: {self.hf_model_name}")
        logger.info(f"  Тип: {self.model_type}")
        logger.info(f"  Устройство: {self.device}")
        logger.info(f"  Температура: {self.temperature}")
        
        # Проверяем тип модели и инициализируем соответствующий обработчик
        if is_openai_model(model_name):
            # Для OpenAI API моделей
            try:
                self.openai_handler = OpenAIHandler(self.hf_model_name, temperature=self.temperature)
                logger.info("Инициализирован обработчик OpenAI API")
                # Для API моделей не нужны локальные model и tokenizer
                self.model = None
                self.tokenizer = None  
                self.prompt_generator = None
                self.seq2seq_handler = None
            except Exception as e:
                logger.error(f"Ошибка при инициализации OpenAI обработчика: {e}")
                raise
        else:
            # Загружаем локальную модель и токенизатор
            self._load_model_and_tokenizer()
            
            # Инициализируем генератор промптов
            self.prompt_generator = PromptGenerator(self.model_name, self.model_type)
            
            # Инициализируем обработчик seq2seq моделей, если необходимо
            if self.model_type == "seq2seq":
                self.seq2seq_handler = Seq2SeqHandler(
                    self.model_name, self.model, self.tokenizer, self.use_cuda
                )
                logger.info("Инициализирован обработчик seq2seq моделей")
            else:
                self.seq2seq_handler = None
            
            # Для локальных моделей OpenAI обработчик не нужен
            self.openai_handler = None
        
        # Кэш для уже переведенных слов
        self.translation_cache = {}
        
        logger.info("Переводчик успешно инициализирован")
        logger.info(f"  Тип: {self.model_type}")
        logger.info(f"  Устройство: {self.device}")
        logger.info(f"  Температура: {self.temperature}")
        
        # Загружаем модель и токенизатор
        self._load_model_and_tokenizer()
        
        # Инициализируем генератор промптов
        self.prompt_generator = PromptGenerator(self.model_name, self.model_type)
        
        # Инициализируем обработчик seq2seq моделей, если необходимо
        if self.model_type == "seq2seq":
            self.seq2seq_handler = Seq2SeqHandler(
                self.model_name, self.model, self.tokenizer, self.use_cuda
            )
            logger.info("Инициализирован обработчик seq2seq моделей")
        
        # Кэш для уже переведенных слов
        self.translation_cache = {}
        
        logger.info("Переводчик успешно инициализирован")
        
    def _load_model_and_tokenizer(self):
        """Загружает модель и токенизатор (только для локальных моделей)."""
        if is_openai_model(self.model_name):
            # Для OpenAI моделей не нужно загружать локальные модели
            return
            
        logger.info("Загрузка модели и токенизатора...")
        loader = ModelLoader(
            self.model_name, 
            self.hf_model_name, 
            self.model_type, 
            self.use_cuda
        )
        self.model, self.tokenizer = loader.load_model_and_tokenizer()
        logger.info("Модель и токенизатор успешно загружены")
    
    def translate(self, character, descriptions, use_description=True):
        """
        Создает краткий перевод для китайского слова.
        
        Args:
            character (str): Китайский иероглиф или слово
            descriptions (list): Список строк с описаниями
            use_description (bool): Использовать ли описание в промпте
            
        Returns:
            str: Краткий перевод
        """
        # Проверяем кэш
        cache_key = f"{character}_{hash(tuple(descriptions))}_{use_description}"
        if cache_key in self.translation_cache:
            logger.debug(f"Используем кэшированный перевод для {character}")
            return self.translation_cache[cache_key]
        
        try:
            logger.debug(f"Начало перевода: {character}")
            start_time = time.time()
            
            if is_openai_model(self.model_name) and hasattr(self, 'openai_handler') and self.openai_handler:
                translation = self._translate_openai(character, descriptions, use_description)
            elif self.model_type == "seq2seq" and hasattr(self, 'seq2seq_handler') and self.seq2seq_handler:
                translation = self._translate_seq2seq(character)
            else:
                translation = self._translate_causal(character, descriptions, use_description)
            
            # Ограничиваем длину до 5 слов для всех типов моделей
            words = translation.split()
            if len(words) > 5:
                translation = " ".join(words[:5])
                logger.debug(f"Обрезан перевод до 5 слов: {translation}")
            
            # Сохраняем в кэш
            self.translation_cache[cache_key] = translation
            
            elapsed_time = time.time() - start_time
            logger.debug(f"Перевод завершен за {elapsed_time:.2f}с: {character} -> {translation}")
            
            return translation
                
        except Exception as e:
            logger.error(f"Ошибка при переводе {character}: {e}")
            return f"Ошибка перевода: {str(e)[:50]}..."
    
    def _translate_openai(self, character, descriptions, use_description):
        """Переводит с помощью OpenAI API."""
        logger.debug(f"Использование OpenAI API для перевода: {character}")
        if hasattr(self, 'openai_handler') and self.openai_handler:
            return self.openai_handler.translate(character, descriptions, use_description)
        else:
            raise RuntimeError("OpenAI обработчик не инициализирован")
    
    def _translate_seq2seq(self, character):
        """Переводит с помощью seq2seq модели."""
        logger.debug(f"Использование seq2seq модели для перевода: {character}")
        if hasattr(self, 'seq2seq_handler') and self.seq2seq_handler:
            return self.seq2seq_handler.translate(character, self.temperature)
        else:
            raise RuntimeError("Seq2seq обработчик не инициализирован")
    
    def _translate_causal(self, character, descriptions, use_description):
        """Переводит с помощью каузальной языковой модели."""
        logger.debug(f"Использование каузальной модели для перевода: {character}")
        
        if not hasattr(self, 'model') or not self.model:
            raise RuntimeError("Локальная модель не загружена")
        if not hasattr(self, 'tokenizer') or not self.tokenizer:
            raise RuntimeError("Токенизатор не загружен")
        if not hasattr(self, 'prompt_generator') or not self.prompt_generator:
            raise RuntimeError("Генератор промптов не инициализирован")
        
        # Создаем промпт
        prompt = self.prompt_generator.create_prompt(character, descriptions, use_description)
        logger.debug(f"Создан промпт длиной {len(prompt)} символов")
        
        # Токенизация с проверкой длины
        inputs = self._prepare_inputs(prompt)
        
        # Генерация
        outputs = self.model.generate(
            **inputs,
            max_length=len(inputs["input_ids"][0]) + self.max_length,
            temperature=self.temperature if self.temperature > 0 else None,
            do_sample=self.temperature > 0,
            pad_token_id=self.tokenizer.eos_token_id
        )
        
        # Декодирование
        response = self.tokenizer.decode(outputs[0], skip_special_tokens=False)
        
        # Убираем промпт из ответа
        response = response[len(prompt):]
        
        # Обработка ответа
        processed_response = process_response(response, self.model_name)
        logger.debug(f"Обработанный ответ: {processed_response}")
        
        return processed_response
    
    def _prepare_inputs(self, prompt):
        """Подготавливает входные данные с проверкой длины."""
        inputs = self.tokenizer(prompt, return_tensors="pt")
        
        # Проверяем длину последовательности и обрезаем, если превышает максимум
        max_model_length = getattr(self.model.config, "max_position_embeddings", 2048)
        
        # Для моделей с известными ограничениями
        if "wenzhong" in self.model_name.lower() or "baichuan" in self.model_name.lower():
            max_model_length = min(max_model_length, 1024)
        elif "gpt2" in self.model_name.lower() or "gpt2" in self.hf_model_name.lower():
            max_model_length = min(max_model_length, 1024)
        
        if inputs["input_ids"].shape[1] > max_model_length:
            logger.warning(f"Длина входной последовательности ({inputs['input_ids'].shape[1]}) "
                          f"превышает максимальную длину модели ({max_model_length}). Обрезаем последовательность.")
            
            # Сохраняем начало и конец последовательности
            prefix_length = min(100, max_model_length // 4)
            suffix_length = min(max_model_length // 2, 512)
            
            # Объединяем начало и конец
            inputs["input_ids"] = torch.cat([
                inputs["input_ids"][:, :prefix_length],
                inputs["input_ids"][:, -(suffix_length):]
            ], dim=1)
            
            if "attention_mask" in inputs:
                inputs["attention_mask"] = torch.cat([
                    inputs["attention_mask"][:, :prefix_length],
                    inputs["attention_mask"][:, -(suffix_length):]
                ], dim=1)
        
        if self.use_cuda:
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
        
        return inputs
    
    def batch_translate(self, items, batch_size=10, use_description=True):
        """
        Пакетная обработка слов для перевода.
        
        Args:
            items (list): Список кортежей (character, descriptions)
            batch_size (int): Размер пакета для обработки
            use_description (bool): Использовать ли описание в промпте
            
        Returns:
            list: Список переводов
        """
        results = []
        total = len(items)
        
        logger.info(f"Начинаем пакетную обработку {total} элементов с размером пакета {batch_size}")
        
        # Для OpenAI API используем специализированный метод
        if is_openai_model(self.model_name) and hasattr(self, 'openai_handler') and self.openai_handler:
            return self.openai_handler.batch_translate(items, batch_size, use_description)
        
        # Для локальных моделей используем обычную обработку
        for i in range(0, total, batch_size):
            batch = items[i:i+batch_size]
            batch_num = i//batch_size + 1
            total_batches = (total+batch_size-1)//batch_size
            
            logger.info(f"Обработка пакета {batch_num}/{total_batches} ({len(batch)} элементов)")
            
            batch_results = []
            for j, (character, descriptions) in enumerate(batch):
                logger.debug(f"Обработка элемента {i+j+1}/{total}: {character}")
                translation = self.translate(character, descriptions, use_description)
                batch_results.append(translation)
                # Небольшая пауза чтобы не перегружать GPU
                time.sleep(0.2)
            
            results.extend(batch_results)
            logger.info(f"Пакет {batch_num}/{total_batches} завершен")
            
        logger.info(f"Пакетная обработка завершена. Обработано {len(results)} элементов")
        return results
    
    def get_statistics(self):
        """
        Возвращает статистику работы переводчика.
        
        Returns:
            dict: Статистика работы
        """
        base_stats = {
            "model_name": self.model_name,
            "model_type": self.model_type,
            "cached_translations": len(self.translation_cache)
        }
        
        # Добавляем статистику OpenAI API, если используется
        if is_openai_model(self.model_name) and hasattr(self, 'openai_handler') and self.openai_handler:
            base_stats.update(self.openai_handler.get_statistics())
        
        return base_stats
    
    def print_statistics(self):
        """Выводит статистику работы переводчика."""
        if is_openai_model(self.model_name) and hasattr(self, 'openai_handler') and self.openai_handler:
            self.openai_handler.print_statistics()
        else:
            stats = self.get_statistics()
            logger.info("Статистика переводчика:")
            logger.info(f"  Модель: {stats['model_name']}")
            logger.info(f"  Тип: {stats['model_type']}")
            logger.info(f"  Кэшированных переводов: {stats['cached_translations']}")

# Экспортируем функцию для обратной совместимости
def get_available_models():
    """
    Возвращает список доступных моделей.
    
    Returns:
        dict: Словарь доступных моделей
    """
    return AVAILABLE_MODELS
