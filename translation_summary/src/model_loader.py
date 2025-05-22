#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Модуль для загрузки моделей и токенизаторов.
"""

import torch
from transformers import (
    AutoModelForCausalLM, 
    AutoModelForSeq2SeqLM,
    AutoTokenizer,
    AutoConfig,
    LlamaForCausalLM,
    BitsAndBytesConfig
)
import logging
import sys
import os

# Добавляем текущую директорию в путь Python
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from model_config import needs_trust_remote_code
except ImportError:
    # Альтернативный способ импорта
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
    from src.model_config import needs_trust_remote_code

logger = logging.getLogger(__name__)

# Кэш для уже загруженных моделей
_MODEL_CACHE = {}
_TOKENIZER_CACHE = {}

class ModelLoader:
    """Класс для загрузки и управления моделями."""
    
    def __init__(self, model_name, hf_model_name, model_type, use_cuda=True):
        self.model_name = model_name
        self.hf_model_name = hf_model_name
        self.model_type = model_type
        self.use_cuda = use_cuda and torch.cuda.is_available()
        self.device = "cuda" if self.use_cuda else "cpu"
        
    def load_model_and_tokenizer(self):
        """Загружает модель и токенизатор."""
        cache_key = f"{self.hf_model_name}_{self.device}_{self.model_type}"
        
        # Проверяем кэш
        if cache_key in _MODEL_CACHE and cache_key in _TOKENIZER_CACHE:
            logger.info(f"Используем кэшированную модель {self.hf_model_name}")
            return _MODEL_CACHE[cache_key], _TOKENIZER_CACHE[cache_key]
        
        logger.info(f"Загружаем модель {self.hf_model_name} (тип: {self.model_type}) на устройство {self.device}")
        
        # Загружаем токенизатор
        tokenizer = self._load_tokenizer()
        
        # Загружаем модель
        model, using_quantization = self._load_model()
        
        # Перенос модели на GPU, если не используется квантизация
        if self.use_cuda and not using_quantization:
            model = model.to(self.device)
        
        # Сохраняем в кэш
        _MODEL_CACHE[cache_key] = model
        _TOKENIZER_CACHE[cache_key] = tokenizer
        
        logger.info(f"Модель {self.hf_model_name} успешно загружена")
        return model, tokenizer
    
    def _load_tokenizer(self):
        """Загружает токенизатор."""
        tokenizer_options = {}
        
        if needs_trust_remote_code(self.model_name):
            tokenizer_options["trust_remote_code"] = True
            logger.info(f"Для токенизатора {self.hf_model_name} установлен параметр trust_remote_code=True")
        
        return AutoTokenizer.from_pretrained(self.hf_model_name, **tokenizer_options)
    
    def _load_model(self):
        """Загружает модель."""
        load_options = self._prepare_load_options()
        using_quantization = False
        
        # Обработка особых случаев
        if "saiga" in self.model_name.lower():
            return self._load_saiga_model(load_options)
        elif self.model_type == "seq2seq":
            return self._load_seq2seq_model(load_options), using_quantization
        else:
            return self._load_causal_model(load_options)
    
    def _prepare_load_options(self):
        """Подготавливает опции для загрузки модели."""
        load_options = {
            "torch_dtype": torch.float16 if self.use_cuda else torch.float32,
            "low_cpu_mem_usage": True,
        }
        
        if needs_trust_remote_code(self.model_name):
            load_options["trust_remote_code"] = True
            logger.info(f"Для модели {self.hf_model_name} установлен параметр trust_remote_code=True")
        
        return load_options
    
    def _load_causal_model(self, load_options):
        """Загружает каузальную языковую модель."""
        using_quantization = False
        
        # Для больших моделей используем квантизацию, но не для моделей с trust_remote_code
        should_quantize = (
            ("7b" in self.model_name.lower() or "7B" in self.hf_model_name) and
            not needs_trust_remote_code(self.model_name)
        )
        
        if should_quantize:
            quantization_config = BitsAndBytesConfig(
                load_in_8bit=True,
                llm_int8_threshold=6.0,
                llm_int8_has_fp16_weight=False
            )
            load_options["quantization_config"] = quantization_config
            using_quantization = True
            logger.info(f"Включена 8-битная квантизация для модели {self.hf_model_name}")
        else:
            if "7b" in self.model_name.lower() or "7B" in self.hf_model_name:
                logger.info(f"Квантизация отключена для модели {self.hf_model_name} (требует trust_remote_code)")
        
        model = AutoModelForCausalLM.from_pretrained(self.hf_model_name, **load_options)
        return model, using_quantization
    
    def _load_seq2seq_model(self, load_options):
        """Загружает seq2seq модель."""
        return AutoModelForSeq2SeqLM.from_pretrained(self.hf_model_name, **load_options)
    
    def _load_saiga_model(self, load_options):
        """Загружает модель Saiga с несколькими попытками."""
        logger.info(f"Определена модель Saiga, пытаемся различные подходы для загрузки")
        
        # Первый подход: AutoConfig с явным указанием типа
        try:
            config = AutoConfig.from_pretrained(self.hf_model_name)
            config.model_type = "llama"
            
            model = LlamaForCausalLM.from_pretrained(
                self.hf_model_name,
                config=config,
                **load_options
            )
            using_quantization = "quantization_config" in load_options
            return model, using_quantization
        except Exception as e1:
            logger.warning(f"Первый подход загрузки Saiga не удался: {e1}")
        
        # Второй подход: trust_remote_code
        try:
            load_options["trust_remote_code"] = True
            model = AutoModelForCausalLM.from_pretrained(self.hf_model_name, **load_options)
            logger.info("Saiga загружена с trust_remote_code=True")
            using_quantization = "quantization_config" in load_options
            return model, using_quantization
        except Exception as e2:
            logger.warning(f"Второй подход загрузки Saiga не удался: {e2}")
        
        # Третий подход: LlamaForCausalLM без квантизации
        try:
            load_options_simple = {
                "torch_dtype": torch.float16 if self.use_cuda else torch.float32,
                "low_cpu_mem_usage": True,
                "trust_remote_code": True
            }
            
            model = LlamaForCausalLM.from_pretrained(self.hf_model_name, **load_options_simple)
            logger.info("Saiga загружена напрямую через LlamaForCausalLM без квантизации")
            return model, False
        except Exception as e3:
            logger.error(f"Все подходы для загрузки Saiga не удались. Последняя ошибка: {e3}")
            raise Exception(f"Невозможно загрузить модель Saiga. Попробуйте исключить её из списка моделей.")

