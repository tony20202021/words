#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Модуль для обработки seq2seq моделей (NLLB, MBart, OpusMT и др.).
"""

import logging

logger = logging.getLogger(__name__)

class Seq2SeqHandler:
    """Класс для обработки seq2seq моделей перевода."""
    
    def __init__(self, model_name, model, tokenizer, use_cuda=True):
        self.model_name = model_name
        self.model = model
        self.tokenizer = tokenizer
        self.use_cuda = use_cuda
        self.device = "cuda" if use_cuda else "cpu"
        
        # Настраиваем языковые коды
        self.src_lang, self.tgt_lang = self._setup_language_codes()
    
    def _setup_language_codes(self):
        """Настраивает языковые коды для модели."""
        if "nllb" in self.model_name.lower():
            return self._setup_nllb_languages()
        elif "mbart" in self.model_name.lower():
            return self._setup_mbart_languages()
        elif "opus-mt" in self.model_name.lower():
            return None, None  # OpusMT не требует явного указания языков
        else:
            return None, None
    
    def _setup_nllb_languages(self):
        """Настраивает языки для NLLB."""
        logger.info(f"Тип токенизатора NLLB: {type(self.tokenizer)}")
        if hasattr(self.tokenizer, 'vocab_size'):
            logger.info(f"Размер словаря NLLB: {self.tokenizer.vocab_size}")
        
        # Для NLLB используем упрощенный подход - перевод без явного указания языка
        logger.info("Для NLLB используется режим без явного указания языков")
        return None, None
    
    def _setup_mbart_languages(self):
        """Настраивает языки для MBart."""
        src_lang = "zh_CN"  # Китайский упрощенный
        tgt_lang = "ru_RU"  # Русский (полный код)
        
        if hasattr(self.tokenizer, 'lang_code_to_id'):
            available_langs = list(self.tokenizer.lang_code_to_id.keys())
            logger.info(f"Доступные языки для MBart: {available_langs}")
            
            # Проверяем и корректируем целевой язык
            tgt_lang = self._find_best_language_code(tgt_lang, ['ru_RU', 'ru_XX', 'ru'], available_langs, "русского")
            
            # Проверяем и корректируем исходный язык
            src_lang = self._find_best_language_code(src_lang, ['zh_CN', 'zh_XX', 'zh'], available_langs, "китайского")
        else:
            logger.warning("Токенизатор MBart не имеет атрибута lang_code_to_id")
            return None, None
        
        return src_lang, tgt_lang
    
    def _find_best_language_code(self, preferred_lang, variants, available_langs, lang_name):
        """Находит лучший доступный языковой код."""
        if preferred_lang in available_langs:
            logger.info(f"Используем код {lang_name} языка: {preferred_lang}")
            return preferred_lang
        
        # Ищем альтернативы
        for variant in variants:
            if variant in available_langs:
                logger.info(f"Используем альтернативный код {lang_name} языка: {variant}")
                return variant
        
        # Если язык не найден, для целевого языка пытаемся использовать английский
        if lang_name == "русского":
            english_variants = ['en_XX', 'en_US', 'en']
            for variant in english_variants:
                if variant in available_langs:
                    logger.info(f"Русский язык недоступен, используем английский: {variant}")
                    return variant
            
            # В крайнем случае используем первый доступный язык
            if available_langs:
                logger.info(f"Используем первый доступный язык: {available_langs[0]}")
                return available_langs[0]
        
        logger.warning(f"{lang_name.capitalize()} язык не найден в доступных языках: {available_langs}")
        return None
    
    def translate(self, character, temperature=0.3):
        """
        Выполняет перевод с помощью seq2seq модели.
        
        Args:
            character (str): Китайский иероглиф для перевода
            temperature (float): Температура генерации
            
        Returns:
            str: Переведенный текст
        """
        try:
            # Подготавливаем входные данные
            inputs, forced_bos_token_id = self._prepare_inputs(character)
            
            # Генерируем перевод
            translation = self._generate_translation(inputs, forced_bos_token_id, temperature)
            
            return translation
            
        except Exception as e:
            logger.error(f"Ошибка при переводе {character}: {e}")
            return f"Ошибка перевода: {str(e)[:50]}..."
    
    def _prepare_inputs(self, character):
        """Подготавливает входные данные для модели."""
        forced_bos_token_id = None
        
        if "nllb" in self.model_name.lower():
            inputs, forced_bos_token_id = self._prepare_nllb_inputs(character)
        elif "mbart" in self.model_name.lower():
            inputs, forced_bos_token_id = self._prepare_mbart_inputs(character)
        else:
            # Для других моделей (OpusMT и др.)
            inputs = self.tokenizer(character, return_tensors="pt")
            if self.use_cuda:
                inputs = {k: v.to(self.device) for k, v in inputs.items()}
        
        return inputs, forced_bos_token_id
    
    def _prepare_nllb_inputs(self, character):
        """Подготавливает входные данные для NLLB."""
        inputs = self.tokenizer(character, return_tensors="pt")
        if self.use_cuda:
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
        
        forced_bos_token_id = None
        
        # Пытаемся найти токен для русского языка
        if hasattr(self.tokenizer, 'convert_tokens_to_ids'):
            rus_token = self.tokenizer.convert_tokens_to_ids("rus_Cyrl")
            if rus_token is not None and rus_token != self.tokenizer.unk_token_id:
                forced_bos_token_id = rus_token
            else:
                # Пробуем альтернативные варианты
                alt_tokens = ["<rus_Cyrl>", "__rus_Cyrl__", "rus"]
                for token in alt_tokens:
                    try:
                        token_id = self.tokenizer.convert_tokens_to_ids(token)
                        if token_id != self.tokenizer.unk_token_id:
                            forced_bos_token_id = token_id
                            break
                    except:
                        continue
                
                if forced_bos_token_id is None:
                    logger.warning("Не удалось найти токен для русского языка в NLLB")
        else:
            logger.warning("Токенизатор NLLB не поддерживает convert_tokens_to_ids")
        
        return inputs, forced_bos_token_id
    
    def _prepare_mbart_inputs(self, character):
        """Подготавливает входные данные для MBart."""
        forced_bos_token_id = None
        
        if self.tgt_lang and hasattr(self.tokenizer, 'lang_code_to_id'):
            if self.tgt_lang in self.tokenizer.lang_code_to_id:
                # Для MBart устанавливаем исходный язык через атрибут токенизатора
                if hasattr(self.tokenizer, 'src_lang'):
                    self.tokenizer.src_lang = self.src_lang
                
                # Подготавливаем входные данные без параметра src_lang
                inputs = self.tokenizer(character, return_tensors="pt")
                if self.use_cuda:
                    inputs = {k: v.to(self.device) for k, v in inputs.items()}
                
                # Генерация с принудительным BOS-токеном целевого языка
                forced_bos_token_id = self.tokenizer.lang_code_to_id[self.tgt_lang]
            else:
                logger.error(f"Язык {self.tgt_lang} не поддерживается MBart")
                # Используем модель без указания языка
                inputs = self.tokenizer(character, return_tensors="pt")
                if self.use_cuda:
                    inputs = {k: v.to(self.device) for k, v in inputs.items()}
        else:
            logger.warning("Целевой язык для MBart не определен")
            inputs = self.tokenizer(character, return_tensors="pt")
            if self.use_cuda:
                inputs = {k: v.to(self.device) for k, v in inputs.items()}
        
        return inputs, forced_bos_token_id
    
    def _generate_translation(self, inputs, forced_bos_token_id, temperature):
        """Генерирует перевод."""
        generation_kwargs = {
            "max_length": 50,
            "num_beams": 4
        }
        
        # Добавляем температуру, если она задана
        if temperature > 0:
            generation_kwargs["temperature"] = temperature
            generation_kwargs["do_sample"] = True
        
        # Добавляем forced_bos_token_id, если он определен
        if forced_bos_token_id is not None:
            generation_kwargs["forced_bos_token_id"] = forced_bos_token_id
        
        outputs = self.model.generate(**inputs, **generation_kwargs)
        
        # Декодирование
        translation = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        
        return translation
    