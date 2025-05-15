"""
Utility functions for audio processing using imageio-ffmpeg.
"""
import os
import logging
import subprocess
from pathlib import Path
from typing import Optional, Tuple, Dict

# Настройка логирования
logger = logging.getLogger(__name__)

def get_ffmpeg_path() -> str:
    """
    Получение пути к FFmpeg из пакета imageio-ffmpeg.
    
    Returns:
        str: Путь к исполняемому файлу FFmpeg
    """
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()

def get_audio_info(file_path: str) -> Optional[Dict[str, any]]:
    """
    Получение информации об аудиофайле.
    
    Args:
        file_path: Путь к аудиофайлу
        
    Returns:
        Optional[Dict]: Информация об аудиофайле или None в случае ошибки
    """
    try:
        ffmpeg_path = get_ffmpeg_path()
        cmd = [ffmpeg_path, "-i", file_path, "-hide_banner"]
        
        # FFmpeg выводит информацию о файле в stderr
        process = subprocess.Popen(
            cmd, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE
        )
        stdout, stderr = process.communicate()
        
        stderr_text = stderr.decode("utf-8", errors="replace")
        
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

async def convert_audio_format(input_file: str, output_file: Optional[str] = None, 
                        format: str = "wav", sample_rate: int = 16000) -> Optional[str]:
    """
    Конвертирует аудиофайл в другой формат, оптимизированный для распознавания речи.
    
    Args:
        input_file: Путь к входному аудиофайлу
        output_file: Путь к выходному файлу (если None, генерируется автоматически)
        format: Формат выходного файла
        sample_rate: Частота дискретизации выходного файла
        
    Returns:
        Optional[str]: Путь к конвертированному файлу или None в случае ошибки
    """
    try:
        if output_file is None:
            output_file = f"{os.path.splitext(input_file)[0]}.{format}"
        
        ffmpeg_path = get_ffmpeg_path()
        cmd = [
            ffmpeg_path,
            "-y",                # Перезаписывать существующие файлы
            "-i", input_file,    # Входной файл
            "-ar", str(sample_rate),  # Частота дискретизации
            "-ac", "1",          # Моно аудио
            "-c:a", "pcm_s16le", # 16-bit PCM кодирование
            output_file          # Выходной файл
        ]
        
        logger.info(f"Converting {input_file} to {output_file}")
        logger.debug(f"Command: {' '.join(cmd)}")
        
        process = subprocess.Popen(
            cmd, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE
        )
        stdout, stderr = process.communicate()
        
        if process.returncode != 0:
            logger.error(f"FFmpeg error: {stderr.decode('utf-8', errors='replace')}")
            return None
        
        if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
            logger.info(f"Successfully converted to {output_file}")
            return output_file
        else:
            logger.error(f"Output file missing or empty: {output_file}")
            return None
            
    except Exception as e:
        logger.error(f"Error converting audio: {e}")
        return None