#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Основной модуль для генерации кратких переводов китайских слов
с использованием языковых моделей из Hugging Face.
"""

import torch
import logging
import time

from .model_config import get_available_models, get_model_type, AVAILABLE_MODELS
from .model_loader import ModelLoader
from .prompt_generator import PromptGenerator, process_response
from .seq2seq_handler import Seq2SeqHandler

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
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
        
        # Загружаем модель и токенизатор
        self._load_model_and_tokenizer()
        
        # Инициализируем генератор промптов
        self.prompt_generator = PromptGenerator(self.model_name, self.model_type)
        
        # Инициализируем обработчик seq2seq моделей, если необходимо
        if self.model_type == "seq2seq":
            self.seq2seq_handler = Seq2SeqHandler(
                self.model_name, self.model, self.tokenizer, self.use_cuda
            )
        
        # Кэш для уже переведенных слов
        self.translation_cache = {}
        
    def _load_model_and_tokenizer(self):
        """Загружает модель и токенизатор."""
        loader = ModelLoader(
            self.model_name, 
            self.hf_model_name, 
            self.model_type, 
            self.use_cuda
        )
        self.model, self.tokenizer = loader.load_model_and_tokenizer()
    
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
            return self.translation_cache[cache_key]
        
        try:
            if self.model_type == "seq2seq":
                translation = self._translate_seq2seq(character)
            else:
                translation = self._translate_causal(character, descriptions, use_description)
            
            # Ограничиваем длину до 5 слов для всех типов моделей
            words = translation.split()
            if len(words) > 5:
                translation = " ".join(words[:5])
            
            # Сохраняем в кэш
            self.translation_cache[cache_key] = translation
            
            return translation
                
        except Exception as e:
            logger.error(f"Ошибка при переводе {character}: {e}")
            return f"Ошибка перевода: {str(e)[:50]}..."
    
    def _translate_seq2seq(self, character):
        """Переводит с помощью seq2seq модели."""
        return self.seq2seq_handler.translate(character, self.temperature)
    
    def _translate_causal(self, character, descriptions, use_description):
        """Переводит с помощью каузальной языковой модели."""
        # Создаем промпт
        prompt = self.prompt_generator.create_prompt(character, descriptions, use_description)
        
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
        return process_response(response, self.model_name)
    
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
        
        for i in range(0, total, batch_size):
            batch = items[i:i+batch_size]
            logger.info(f"Обработка пакета {i//batch_size + 1}/{(total+batch_size-1)//batch_size}")
            
            batch_results = []
            for character, descriptions in batch:
                translation = self.translate(character, descriptions, use_description)
                batch_results.append(translation)
                # Небольшая пауза чтобы не перегружать GPU
                time.sleep(0.2)
            
            results.extend(batch_results)
            
        return results

# Экспортируем функцию для обратной совместимости
def get_available_models():
    """
    Возвращает список доступных моделей.
    
    Returns:
        dict: Словарь доступных моделей
    """
    return AVAILABLE_MODELS
    