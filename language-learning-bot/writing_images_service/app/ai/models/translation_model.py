"""
Translation Model for converting Russian meanings to English prompts.
Модель перевода для конвертации русских значений в английские промпты.

Supports multiple model types: Qwen, NLLB, mT5, OPUS
ИСПРАВЛЕНО: Проблема с несоответствием устройств GPU
"""

import time
import torch
import asyncio
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from pathlib import Path
import traceback

from transformers import (
    AutoTokenizer, AutoModelForSeq2SeqLM, AutoModelForCausalLM,
)

from app.utils.logger import get_module_logger

logger = get_module_logger(__name__)


@dataclass
class TranslationResult:
    """Результат перевода"""
    success: bool
    translated_text: str = ""
    original_text: str = ""
    character: str = ""
    translation_time_ms: int = 0
    model_used: str = ""
    cache_hit: bool = False
    confidence_score: float = 0.0
    error_message: Optional[str] = None


@dataclass
class ModelInfo:
    """Информация о модели перевода"""
    model_id: str
    model_type: str  # qwen, nllb, mt5, opus
    size_gb: float
    languages: List[str]
    strengths: List[str]
    loaded: bool = False
    load_time_seconds: float = 0.0
    memory_usage_mb: float = 0.0


class TranslationModel:
    """
    Базовый класс для всех моделей перевода.
    Поддерживает Qwen, NLLB, mT5, OPUS модели.
    ИСПРАВЛЕНО: Проблема с несоответствием устройств GPU
    """
    
    def __init__(self, model_config: Dict[str, Any]):
        """
        Инициализация модели перевода.
        
        Args:
            model_config: Конфигурация модели из YAML
        """
        self.model_config = model_config
        self.model_id = model_config.get("model_id", "")
        self.model_type = self._detect_model_type(self.model_id)
        
        # Модель и токенизер
        self.model = None
        self.tokenizer = None
        self.pipeline = None
        
        # Статус загрузки
        self._is_loaded = False
        self._loading_lock = asyncio.Lock()
        
        # ИСПРАВЛЕНО: Явно определяем основное устройство
        self.device = self._determine_primary_device()
        self.torch_dtype = torch.float16 if torch.cuda.is_available() else torch.float32
        
        # Статистика
        self.translation_count = 0
        self.total_translation_time = 0
        self.start_time = time.time()
        
        logger.info(f"TranslationModel initialized: {self.model_id} ({self.model_type}) on device: {self.device}")
    
    def _determine_primary_device(self) -> str:
        """
        Определяет основное устройство для модели.
        ИСПРАВЛЕНО: Использует первое доступное GPU устройство вместо автоматического распределения
        """
        if not torch.cuda.is_available():
            return "cpu"
        
        # Используем первое GPU устройство для избежания конфликтов
        primary_device = "cuda:0"
        
        # Логируем информацию о доступных устройствах
        if torch.cuda.device_count() > 1:
            logger.info(f"Multiple GPUs detected ({torch.cuda.device_count()}), using {primary_device} for translation model")
        
        return primary_device
    
    def _detect_model_type(self, model_id: str) -> str:
        """Определяет тип модели по ID."""
        model_id_lower = model_id.lower()
        
        if "qwen" in model_id_lower:
            return "qwen"
        elif "nllb" in model_id_lower:
            return "nllb"
        elif "mt5" in model_id_lower:
            return "mt5"
        elif "opus" in model_id_lower:
            return "opus"
        elif "m2m100" in model_id_lower:
            return "m2m100"
        else:
            # Fallback: пытаемся определить по архитектуре
            return "unknown"
    
    async def load_model(self) -> bool:
        """
        Загружает модель и токенизер.
        
        Returns:
            bool: True если загрузка успешна
        """
        async with self._loading_lock:
            if self._is_loaded:
                return True
            
            start_time = time.time()
            memory_before = self._get_memory_usage()
            
            try:
                logger.info(f"Loading translation model: {self.model_id} on device: {self.device}")
                
                # Загружаем в зависимости от типа модели
                if self.model_type == "qwen":
                    await self._load_qwen_model()
                elif self.model_type == "nllb":
                    await self._load_nllb_model()
                elif self.model_type == "mt5":
                    await self._load_mt5_model()
                elif self.model_type == "opus":
                    await self._load_opus_model()
                else:
                    # Универсальная загрузка
                    await self._load_generic_model()
                
                # ИСПРАВЛЕНО: Явно перемещаем модель на нужное устройство
                if self.device != "cpu" and self.model:
                    logger.info(f"Moving model to device: {self.device}")
                    self.model = self.model.to(self.device)
                    
                    # Проверяем что модель действительно на правильном устройстве
                    if hasattr(self.model, 'device'):
                        actual_device = next(self.model.parameters()).device
                        logger.info(f"Model device after move: {actual_device}")
                
                load_time = time.time() - start_time
                memory_after = self._get_memory_usage()
                memory_used = memory_after - memory_before
                
                self._is_loaded = True
                
                logger.info(f"✓ Translation model loaded successfully in {load_time:.1f}s "
                           f"(Memory used: {memory_used:.1f}MB, Device: {self.device})")
                
                return True
                
            except Exception as e:
                logger.error(f"Failed to load translation model {self.model_id}: {e}")
                logger.error(traceback.format_exc())
                self._is_loaded = False
                return False
    
    async def _load_qwen_model(self):
        """Загружает Qwen модель (инструкционная)."""
        try:
            from transformers import AutoTokenizer, AutoModelForCausalLM
            
            # Qwen модели - это causal LM с instruction following
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.model_id,
                trust_remote_code=True
            )
            
            # ИСПРАВЛЕНО: Используем явное указание устройства вместо device_map="auto"
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_id,
                torch_dtype=self.torch_dtype,
                trust_remote_code=True,
                device_map={"": self.device} if torch.cuda.is_available() else None
            )
            
            logger.debug(f"✓ Loaded Qwen model: {self.model_id} on device: {self.device}")
            
        except Exception as e:
            logger.error(f"Error loading Qwen model: {e}")
            raise
    
    async def _load_nllb_model(self):
        """Загружает NLLB модель (многоязычный перевод)."""
        try:
            # NLLB модели используют специальную архитектуру
            if "nllb-200" in self.model_id:
                from transformers import NllbTokenizer
                self.tokenizer = NllbTokenizer.from_pretrained(self.model_id)
            else:
                self.tokenizer = AutoTokenizer.from_pretrained(self.model_id)
            
            self.model = AutoModelForSeq2SeqLM.from_pretrained(
                self.model_id,
                torch_dtype=self.torch_dtype
            )
            
            logger.debug(f"✓ Loaded NLLB model: {self.model_id}")
            
        except Exception as e:
            logger.error(f"Error loading NLLB model: {e}")
            raise
    
    async def _load_mt5_model(self):
        """Загружает mT5 модель (многоязычный T5)."""
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_id)
            self.model = AutoModelForSeq2SeqLM.from_pretrained(
                self.model_id,
                torch_dtype=self.torch_dtype
            )
            
            logger.debug(f"✓ Loaded mT5 model: {self.model_id}")
            
        except Exception as e:
            logger.error(f"Error loading mT5 model: {e}")
            raise
    
    async def _load_opus_model(self):
        """Загружает OPUS модель (специализированный перевод)."""
        try:
            # OPUS модели обычно легкие и специализированные
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_id)
            self.model = AutoModelForSeq2SeqLM.from_pretrained(
                self.model_id,
                torch_dtype=self.torch_dtype
            )
            
            logger.debug(f"✓ Loaded OPUS model: {self.model_id}")
            
        except Exception as e:
            logger.error(f"Error loading OPUS model: {e}")
            raise
    
    async def _load_generic_model(self):
        """Универсальная загрузка модели."""
        try:
            # Пытаемся загрузить как seq2seq модель
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_id)
            
            try:
                self.model = AutoModelForSeq2SeqLM.from_pretrained(
                    self.model_id,
                    torch_dtype=self.torch_dtype
                )
                logger.debug(f"✓ Loaded as Seq2Seq model: {self.model_id}")
            except:
                # Если не получилось, пробуем как causal LM
                self.model = AutoModelForCausalLM.from_pretrained(
                    self.model_id,
                    torch_dtype=self.torch_dtype
                )
                logger.debug(f"✓ Loaded as Causal LM model: {self.model_id}")
                
        except Exception as e:
            logger.error(f"Error loading generic model: {e}")
            raise
    
    def _ensure_tensor_device(self, tensor_dict: Dict[str, torch.Tensor]) -> Dict[str, torch.Tensor]:
        """
        ИСПРАВЛЕНО: Обеспечивает что все тензоры находятся на правильном устройстве
        
        Args:
            tensor_dict: Словарь тензоров
            
        Returns:
            Dict[str, torch.Tensor]: Тензоры на правильном устройстве
        """
        result = {}
        for key, tensor in tensor_dict.items():
            if isinstance(tensor, torch.Tensor):
                result[key] = tensor.to(self.device)
            else:
                result[key] = tensor
        return result
    
    async def translate(
        self,
        character: str,
        russian_text: str,
        **generation_kwargs
    ) -> TranslationResult:
        """
        Переводит русский текст в английский для AI промптов.
        
        Args:
            character: Китайский иероглиф
            russian_text: Русское значение
            **generation_kwargs: Дополнительные параметры генерации
            
        Returns:
            TranslationResult: Результат перевода
        """
        if not self._is_loaded:
            await self.load_model()
            
        start_time = time.time()
        
        try:
            logger.debug(f"Translating: '{russian_text}' for character '{character}' on device: {self.device}")
            
            # Генерируем перевод в зависимости от типа модели
            if self.model_type == "qwen":
                translated_text = await self._translate_with_qwen(character, russian_text, **generation_kwargs)
            elif self.model_type == "nllb":
                translated_text = await self._translate_with_nllb(russian_text, **generation_kwargs)
            elif self.model_type == "mt5":
                translated_text = await self._translate_with_mt5(character, russian_text, **generation_kwargs)
            elif self.model_type == "opus":
                translated_text = await self._translate_with_opus(russian_text, **generation_kwargs)
            else:
                # Универсальный подход
                translated_text = await self._translate_generic(character, russian_text, **generation_kwargs)
            
            translation_time_ms = int((time.time() - start_time) * 1000)
            
            # Обновляем статистику
            self.translation_count += 1
            self.total_translation_time += translation_time_ms
            
            logger.debug(f"✓ Translation completed: '{translated_text}' ({translation_time_ms}ms)")
            
            return TranslationResult(
                success=True,
                translated_text=translated_text,
                original_text=russian_text,
                character=character,
                translation_time_ms=translation_time_ms,
                model_used=self.model_id,
                cache_hit=False,
                confidence_score=0.9  # TODO: вычислять реальную уверенность
            )
            
        except Exception as e:
            translation_time_ms = int((time.time() - start_time) * 1000)
            logger.error(traceback.format_exc())
            logger.error(f"Translation failed: {e}")
            
            return TranslationResult(
                success=False,
                original_text=russian_text,
                character=character,
                translation_time_ms=translation_time_ms,
                model_used=self.model_id,
                error_message=str(e)
            )
    
    async def _translate_with_qwen(self, character: str, russian_text: str, **kwargs) -> str:
        """
        Перевод с помощью Qwen модели (инструкционной).
        ИСПРАВЛЕНО: Обеспечение совместимости устройств
        """
        # Prompt для Qwen
        system_prompt = "You are a professional translator. Translate the given text to English concisely and accurately for AI image generation prompts."
        user_prompt = f"Chinese character: {character}\nRussian meaning: {russian_text}\nTranslate to English (short phrase for image prompt):"
        
        # Форматируем для Qwen
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        # Применяем chat template
        text = self.tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True
        )
        
        # ИСПРАВЛЕНО: Токенизируем и обеспечиваем правильное устройство
        model_inputs = self.tokenizer([text], return_tensors="pt")
        model_inputs = self._ensure_tensor_device(model_inputs)
        
        # Проверяем устройства перед генерацией
        input_device = model_inputs['input_ids'].device
        model_device = next(self.model.parameters()).device
        
        logger.debug(f"Input device: {input_device}, Model device: {model_device}")
        
        if input_device != model_device:
            logger.warning(f"Device mismatch detected! Moving inputs from {input_device} to {model_device}")
            model_inputs = {k: v.to(model_device) for k, v in model_inputs.items() if isinstance(v, torch.Tensor)}
        
        # Генерируем
        with torch.no_grad():  # Экономим память
            generated_ids = self.model.generate(
                model_inputs['input_ids'],
                max_new_tokens=50,
                temperature=kwargs.get('temperature', 0.3),
                do_sample=True,
                top_p=kwargs.get('top_p', 0.9),
                pad_token_id=self.tokenizer.eos_token_id,
                attention_mask=model_inputs.get('attention_mask')
            )
        
        # Декодируем только новые токены
        input_length = model_inputs['input_ids'].shape[1]
        new_tokens = generated_ids[:, input_length:]
        
        response = self.tokenizer.batch_decode(new_tokens, skip_special_tokens=True)[0]
        
        # Очищаем ответ
        response = response.strip()
        
        return response
    
    async def _translate_with_nllb(self, russian_text: str, **kwargs) -> str:
        """
        Перевод с помощью NLLB модели.
        ИСПРАВЛЕНО: Обеспечение совместимости устройств
        """
        # NLLB использует специальные коды языков
        self.tokenizer.src_lang = "rus_Cyrl"  # Русский
        
        # ИСПРАВЛЕНО: Токенизируем и обеспечиваем правильное устройство
        encoded = self.tokenizer(russian_text, return_tensors="pt")
        encoded = self._ensure_tensor_device(encoded)
        
        # Генерируем перевод
        with torch.no_grad():
            generated_tokens = self.model.generate(
                **encoded,
                forced_bos_token_id=self.tokenizer.lang_code_to_id["eng_Latn"],  # Английский
                max_length=kwargs.get('max_length', 50),
                num_beams=kwargs.get('num_beams', 5),
                length_penalty=kwargs.get('length_penalty', 1.0)
            )
        
        # Декодируем
        translated_text = self.tokenizer.batch_decode(generated_tokens, skip_special_tokens=True)[0]
        
        return translated_text.strip()
    
    async def _translate_with_mt5(self, character: str, russian_text: str, **kwargs) -> str:
        """
        Перевод с помощью mT5 модели.
        ИСПРАВЛЕНО: Обеспечение совместимости устройств
        """
        # mT5 использует prefix для указания задачи
        input_text = f"translate Russian to English: Character {character} means: {russian_text}"
        
        # ИСПРАВЛЕНО: Токенизируем и обеспечиваем правильное устройство
        model_inputs = self.tokenizer(input_text, return_tensors="pt")
        model_inputs = self._ensure_tensor_device(model_inputs)
        
        # Генерируем
        with torch.no_grad():
            outputs = self.model.generate(
                model_inputs['input_ids'],
                max_length=kwargs.get('max_length', 50),
                num_beams=kwargs.get('num_beams', 4),
                length_penalty=kwargs.get('length_penalty', 0.6),
                early_stopping=True
            )
        
        # Декодируем
        translated_text = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        
        return translated_text.strip()
    
    async def _translate_with_opus(self, russian_text: str, **kwargs) -> str:
        """
        Перевод с помощью OPUS модели.
        ИСПРАВЛЕНО: Обеспечение совместимости устройств
        """
        # ИСПРАВЛЕНО: Токенизируем и обеспечиваем правильное устройство
        model_inputs = self.tokenizer(russian_text, return_tensors="pt")
        model_inputs = self._ensure_tensor_device(model_inputs)
        
        with torch.no_grad():
            outputs = self.model.generate(
                model_inputs['input_ids'],
                max_length=kwargs.get('max_length', 50),
                num_beams=kwargs.get('num_beams', 4),
                early_stopping=True
            )
        
        translated_text = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        
        return translated_text.strip()
    
    async def _translate_generic(self, character: str, russian_text: str, **kwargs) -> str:
        """
        Универсальный перевод для неизвестных моделей.
        ИСПРАВЛЕНО: Обеспечение совместимости устройств
        """
        # Пробуем как seq2seq модель
        try:
            input_text = f"translate: {russian_text}"
            model_inputs = self.tokenizer(input_text, return_tensors="pt")
            model_inputs = self._ensure_tensor_device(model_inputs)
            
            with torch.no_grad():
                outputs = self.model.generate(
                    model_inputs['input_ids'],
                    max_length=kwargs.get('max_length', 50),
                    num_beams=kwargs.get('num_beams', 4)
                )
            
            translated_text = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            return translated_text.strip()
            
        except Exception as e:
            # Если не получилось, возвращаем оригинальный текст
            logger.warning(f"Generic translation failed: {e}, returning original text")
            return russian_text
    
    def _get_memory_usage(self) -> float:
        """Возвращает использование GPU памяти в MB."""
        if torch.cuda.is_available():
            # ИСПРАВЛЕНО: Используем правильное устройство для проверки памяти
            device_idx = int(self.device.split(':')[1]) if ':' in self.device else 0
            return torch.cuda.memory_allocated(device_idx) / 1024**2
        return 0.0
    
    def get_model_info(self) -> ModelInfo:
        """Возвращает информацию о модели."""
        memory_usage = self._get_memory_usage()
        
        return ModelInfo(
            model_id=self.model_id,
            model_type=self.model_type,
            size_gb=self.model_config.get("size_gb", 0.0),
            languages=self.model_config.get("languages", []),
            strengths=self.model_config.get("strengths", []),
            loaded=self._is_loaded,
            memory_usage_mb=memory_usage
        )
    
    def get_translation_stats(self) -> Dict[str, Any]:
        """Возвращает статистику переводов."""
        uptime_seconds = int(time.time() - self.start_time)
        avg_time = (
            self.total_translation_time / self.translation_count 
            if self.translation_count > 0 else 0
        )
        
        return {
            "model_id": self.model_id,
            "model_type": self.model_type,
            "is_loaded": self._is_loaded,
            "device": self.device,
            "translation_count": self.translation_count,
            "total_translation_time_ms": self.total_translation_time,
            "average_translation_time_ms": avg_time,
            "uptime_seconds": uptime_seconds,
            "memory_usage_mb": self._get_memory_usage()
        }
    
    async def unload_model(self):
        """Выгружает модель для освобождения памяти."""
        try:
            logger.info(f"Unloading translation model: {self.model_id}")
            
            if self.model is not None:
                del self.model
                self.model = None
            
            if self.tokenizer is not None:
                del self.tokenizer
                self.tokenizer = None
                
            if self.pipeline is not None:
                del self.pipeline
                self.pipeline = None
            
            # ИСПРАВЛЕНО: Очищаем память на правильном устройстве
            if torch.cuda.is_available():
                if ':' in self.device:
                    device_idx = int(self.device.split(':')[1])
                    torch.cuda.empty_cache()
                    torch.cuda.synchronize(device_idx)
                else:
                    torch.cuda.empty_cache()
            
            self._is_loaded = False
            
            logger.info(f"✓ Translation model unloaded: {self.model_id}")
            
        except Exception as e:
            logger.error(f"Error unloading translation model: {e}")
    
    def is_loaded(self) -> bool:
        """Проверяет загружена ли модель."""
        return self._is_loaded
    
    def __del__(self):
        """Деструктор для очистки ресурсов."""
        if hasattr(self, '_is_loaded') and self._is_loaded:
            logger.warning(f"Translation model {self.model_id} deleted without explicit cleanup")
            