"""
Utility functions for voice recognition using Whisper.
"""
import os
import whisper
import logging
import asyncio
import time
from typing import Optional

# Импортируем модуль для работы с аудиофайлами
from app.utils.audio_utils import convert_audio_format, get_audio_info

# Настройка логирования
logger = logging.getLogger(__name__)

# Глобальная переменная для хранения загруженной модели
_whisper_model = None

def get_whisper_model(model_size="small"):
    """
    Загружает модель Whisper указанного размера.
    Поддерживает кэширование модели для более быстрого повторного использования.
    
    Args:
        model_size (str): Размер модели ("tiny", "base", "small", "medium", "large")
        
    Returns:
        whisper.Whisper: Загруженная модель Whisper
    """
    global _whisper_model
    if _whisper_model is None:
        logger.info(f"Loading Whisper model of size '{model_size}'")
        start_time = time.time()
        _whisper_model = whisper.load_model(model_size)
        logger.info(f"Whisper model loaded successfully in {time.time() - start_time:.2f} seconds")
    return _whisper_model

async def recognize_speech_async(file_path: str, model_size: str = "small", language: str = "ru") -> Optional[str]:
    """
    Асинхронно распознает речь из аудиофайла, используя Whisper.
    
    Args:
        file_path (str): Путь к аудиофайлу
        model_size (str): Размер модели Whisper ("tiny", "base", "small", "medium", "large")
        language (str): Язык аудио (например, "ru" для русского)
        
    Returns:
        Optional[str]: Распознанный текст или None в случае ошибки
    """
    logger.info(f"Starting async speech recognition for file: {file_path}")
    start_time = time.time()
    
    try:
        # Подготовка аудиофайла для Whisper (конвертация в WAV если необходимо)
        audio_path = file_path
        is_temp_file = False
        
        # Если файл не в формате WAV или с неоптимальными параметрами, конвертируем
        audio_info = get_audio_info(file_path)
        optimal_format = (audio_info and 
                         audio_info.get("codec") == "pcm_s16le" and 
                         audio_info.get("sample_rate") == "16000" and 
                         audio_info.get("channels") == 1)
        
        if not optimal_format:
            logger.info(f"Converting audio to optimal format for Whisper")
            temp_path = await convert_audio_format(file_path)
            if temp_path:
                audio_path = temp_path
                is_temp_file = True
            else:
                logger.warning(f"Failed to convert audio, trying original file")
        
        # Функция для запуска в отдельном потоке
        def _recognize():
            model = get_whisper_model(model_size)
            result = model.transcribe(audio_path, language=language)
            return result["text"].strip()
        
        # Запуск распознавания в отдельном потоке
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, _recognize)
        
        # Удаление временного файла
        if is_temp_file and os.path.exists(audio_path):
            try:
                os.remove(audio_path)
                logger.info(f"Removed temporary file: {audio_path}")
            except Exception as e:
                logger.warning(f"Failed to remove temporary file: {e}")
        
        logger.info(f"Speech recognition completed in {time.time() - start_time:.2f} seconds")
        return result
    except Exception as e:
        logger.error(f"Error in speech recognition: {e}", exc_info=True)
        return None

async def process_telegram_voice(bot, voice_message, temp_dir: str = "temp") -> Optional[str]:
    """
    Обрабатывает голосовое сообщение из Telegram и распознает его в текст.
    
    Args:
        bot: Экземпляр бота Telegram
        voice_message: Объект голосового сообщения
        temp_dir (str): Директория для временных файлов
        
    Returns:
        Optional[str]: Распознанный текст или None в случае ошибки
    """
    try:
        # Создание временной директории, если она не существует
        if not os.path.exists(temp_dir):
            os.makedirs(temp_dir)
        
        # Формирование имени файла с использованием ID голосового сообщения
        file_id = voice_message.file_id
        file_unique_id = voice_message.file_unique_id
        file_path = os.path.join(temp_dir, f"{file_unique_id}.ogg")
        
        # Скачиваем файл
        logger.info(f"Downloading voice message: {file_id}")
        file_info = await bot.get_file(file_id)
        await bot.download_file(file_info.file_path, file_path)
        logger.info(f"Voice message downloaded to: {file_path}")
        
        # Проверка, что файл скачан успешно
        if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
            logger.error(f"Failed to download voice message or file is empty: {file_path}")
            return None
        
        # Распознаем речь
        logger.info(f"Starting speech recognition for: {file_path}")
        recognized_text = await recognize_speech_async(file_path, language="ru")
        
        # Удаляем временный файл
        try:
            os.remove(file_path)
            logger.info(f"Removed temporary file: {file_path}")
        except Exception as e:
            logger.warning(f"Failed to remove temporary file: {e}")
        
        return recognized_text
    except Exception as e:
        logger.error(f"Error processing Telegram voice message: {e}", exc_info=True)
        return None
    