"""
Utility functions for FFmpeg operations using imageio-ffmpeg.
"""
import os
import logging
import subprocess
from pathlib import Path
from typing import Optional, Union, Tuple

# Настройка логирования
logger = logging.getLogger(__name__)

def get_ffmpeg_path() -> Optional[str]:
    """
    Получает путь к FFmpeg из пакета imageio-ffmpeg.
    
    Returns:
        Optional[str]: Путь к FFmpeg или None в случае ошибки
    """
    try:
        import imageio_ffmpeg
        ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()
        logger.info(f"Found FFmpeg from imageio-ffmpeg: {ffmpeg_path}")
        
        # Проверка работоспособности
        try:
            result = subprocess.run(
                [ffmpeg_path, "-version"], 
                capture_output=True, 
                text=True
            )
            if result.returncode == 0:
                logger.info(f"FFmpeg version: {result.stdout.splitlines()[0]}")
                return ffmpeg_path
            else:
                logger.error(f"FFmpeg test failed: {result.stderr}")
        except Exception as e:
            logger.error(f"Error testing FFmpeg: {e}")
        
        return None
    except ImportError:
        logger.error("imageio-ffmpeg not found. Install with 'pip install imageio-ffmpeg'")
        return None
    except Exception as e:
        logger.error(f"Error getting FFmpeg path: {e}")
        return None

def check_opus_support(ffmpeg_path: str) -> bool:
    """
    Проверяет поддержку кодека Opus в FFmpeg.
    
    Args:
        ffmpeg_path: Путь к FFmpeg
        
    Returns:
        bool: True если кодек Opus поддерживается, иначе False
    """
    try:
        result = subprocess.run(
            [ffmpeg_path, "-codecs"], 
            capture_output=True, 
            text=True
        )
        return "opus" in result.stdout.lower()
    except Exception as e:
        logger.error(f"Error checking Opus support: {e}")
        return False

async def convert_audio(input_file: str, output_file: str = None, output_format: str = "wav") -> Optional[str]:
    """
    Конвертирует аудиофайл в указанный формат.
    
    Args:
        input_file: Путь к исходному аудиофайлу
        output_file: Путь для выходного файла (опционально)
        output_format: Формат выходного файла (по умолчанию "wav")
        
    Returns:
        Optional[str]: Путь к выходному файлу или None в случае ошибки
    """
    # Если выходной файл не указан, генерируем имя
    if output_file is None:
        output_file = os.path.splitext(input_file)[0] + f".{output_format}"
    
    ffmpeg_path = get_ffmpeg_path()
    if not ffmpeg_path:
        logger.error("FFmpeg not found, cannot convert audio")
        return None
    
    try:
        # Определяем оптимальные параметры для Whisper
        params = [
            ffmpeg_path,
            "-y",                # Перезаписывать существующие файлы
            "-i", input_file,    # Входной файл
            "-ar", "16000",      # Частота дискретизации 16kHz (оптимально для Whisper)
            "-ac", "1",          # Моно аудио
            "-c:a", "pcm_s16le", # 16-bit PCM кодирование
            output_file          # Выходной файл
        ]
        
        # Выполняем команду асинхронно
        process = subprocess.Popen(
            params, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE
        )
        stdout, stderr = process.communicate()
        
        if process.returncode != 0:
            error_msg = stderr.decode('utf-8', errors='replace')
            logger.error(f"FFmpeg conversion error: {error_msg}")
            
            # Проверка на ошибки, связанные с кодеком Opus
            if "opus" in error_msg.lower() and "unknown encoder" in error_msg.lower():
                logger.error("FFmpeg does not support Opus codec. Try installing a full version of FFmpeg.")
            
            return None
        
        # Проверка, что файл создан и имеет ненулевой размер
        if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
            logger.info(f"Successfully converted {input_file} to {output_file}")
            return output_file
        else:
            logger.error(f"Output file {output_file} is empty or does not exist")
            return None
    except Exception as e:
        logger.error(f"Error converting audio: {e}")
        return None

def get_audio_info(file_path: str) -> Optional[dict]:
    """
    Получает информацию об аудиофайле.
    
    Args:
        file_path: Путь к аудиофайлу
        
    Returns:
        Optional[dict]: Словарь с информацией о файле или None в случае ошибки
    """
    ffmpeg_path = get_ffmpeg_path()
    if not ffmpeg_path:
        return None
    
    try:
        cmd = [
            ffmpeg_path,
            "-i", file_path,
            "-hide_banner"
        ]
        
        # ffprobe возвращает информацию о файле в stderr
        process = subprocess.Popen(
            cmd, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE
        )
        stdout, stderr = process.communicate()
        
        stderr_text = stderr.decode('utf-8', errors='replace')
        
        # Базовый парсинг информации
        info = {
            "format": None,
            "codec": None,
            "duration": None,
            "channels": None,
            "sample_rate": None,
        }
        
        # Извлекаем информацию из вывода
        if "Audio:" in stderr_text:
            audio_line = [line for line in stderr_text.splitlines() if "Audio:" in line][0]
            info["codec"] = audio_line.split("Audio:")[1].strip().split(",")[0].strip()
            
            if "Hz" in audio_line:
                sample_rate_part = [part for part in audio_line.split(",") if "Hz" in part][0]
                info["sample_rate"] = sample_rate_part.strip().split(" ")[0]
            
            if "mono" in audio_line.lower():
                info["channels"] = 1
            elif "stereo" in audio_line.lower():
                info["channels"] = 2
        
        if "Duration:" in stderr_text:
            duration_line = [line for line in stderr_text.splitlines() if "Duration:" in line][0]
            duration_part = duration_line.split("Duration:")[1].split(",")[0].strip()
            info["duration"] = duration_part
        
        return info
    except Exception as e:
        logger.error(f"Error getting audio info: {e}")
        return None
    