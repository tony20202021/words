"""
Генератор изображений для слов с транскрипцией.
Создает красивые изображения с крупным текстом слова
"""

import io
import os
import tempfile
from typing import Optional
from pathlib import Path

import asyncio
from PIL import Image, ImageDraw, ImageFont

from app.utils import config_holder
from app.utils.logger import setup_logger
from common.utils.font_utils import get_font_manager

logger = setup_logger(__name__)


class BigWordGenerator:
    """Генератор изображений для слов с транскрипцией."""
    
    def __init__(self):
        """
        Инициализация генератора.
        """
        # Размеры изображения
        self.width = 800
        self.height = 400
        
        # Цвета
        self.bg_color = (255, 255, 255)  # Белый фон
        self.text_color = (50, 50, 50)   # Темно-серый текст
        self.border_color = (200, 200, 200)  # Светло-серая рамка
        self.transcription_color = (50, 50, 50)   # Темно-серый текст
        
        # Размеры шрифтов (по умолчанию)
        self.word_font_size = 80
        self.transcription_font_size = 20
        
        # Font manager для Unicode поддержки
        self.font_manager = get_font_manager()
        
        logger.info(f"WordImageGenerator.config: {config_holder.cfg.show_big}")
        # Применяем конфигурацию если есть
        if config_holder.cfg.show_big:
            self.width = config_holder.cfg.show_big.get('width', self.width)
            self.height = config_holder.cfg.show_big.get('height', self.height)
            
            # Цвета
            colors = config_holder.cfg.show_big.get('colors', {})
            self.bg_color = tuple(colors.get('background', self.bg_color))
            self.text_color = tuple(colors.get('text', self.text_color))
            self.border_color = tuple(colors.get('border', self.border_color))
            self.transcription_color = tuple(colors.get('transcription', self.transcription_color))
            
            # Размеры шрифтов
            fonts = config_holder.cfg.show_big.get('fonts', {})
            self.word_font_size = fonts.get('word_size', self.word_font_size)
            self.transcription_font_size = fonts.get('transcription_size', self.transcription_font_size)            
        
        logger.info(f"WordImageGenerator.word_font_size: {self.word_font_size}")

        # Настройка временной директории
        self.temp_dir = config_holder.cfg.show_big.temp_dir or tempfile.gettempdir()

    async def generate_big_word(
        self, 
        word: str, 
        transcription: Optional[str] = None,
        save_to_temp: bool = False
    ) -> io.BytesIO:
        """
        Генерирует изображение со словом и транскрипцией
        
        Args:
            word: Слово для отображения
            transcription: Транскрипция (опционально)
            save_to_temp: Сохранять ли во временный файл (для отладки)
            
        Returns:
            io.BytesIO: Изображение в памяти
        """
        try:
            logger.info(f"Generating image for word: '{word}', transcription: '{transcription}'")
            
            # Создаем изображение
            image = Image.new('RGB', (self.width, self.height), self.bg_color)
            draw = ImageDraw.Draw(image)
            
            # Доступная ширина (с отступами)
            margin = 20  # Отступы по бокам
            available_width = self.width - 2 * margin
            min_font_size = 12  # Минимальный размер шрифта
            
            # АВТОПОДБОР РАЗМЕРА ШРИФТА ДЛЯ СЛОВА с Unicode поддержкой
            word_font, actual_word_font_size, word_width, word_height, word_begin_y = await self.font_manager.auto_fit_font_size(
                word,
                available_width,
                self.height // 2,  # Половина высоты для слова
                self.word_font_size,
                min_font_size
            )
            
            logger.info(f"Auto-fitted word font size: {actual_word_font_size}")
            logger.info(f"Word dimensions: {word_width}x{word_height}px (available: {available_width}px)")
            
            # АВТОПОДБОР РАЗМЕРА ШРИФТА ДЛЯ ТРАНСКРИПЦИИ
            trans_font = None
            actual_transcription_font_size = self.transcription_font_size
            trans_width = 0
            trans_height = 0
            transcription_text = ""
            
            if transcription:
                transcription_text = f"[{transcription}]"
                
                trans_font, actual_transcription_font_size, trans_width, trans_height, trans_begin_y = await self.font_manager.auto_fit_font_size(
                    transcription_text,
                    available_width,
                    self.height // 4,  # Четверть высоты для транскрипции
                    self.transcription_font_size,
                    min_font_size
                )
                
                logger.info(f"Auto-fitted transcription font size: {actual_transcription_font_size}")
                logger.info(f"Transcription dimensions: {trans_width}x{trans_height}px")
            
            free_space_all = (self.height - word_height - trans_height)
            free_space_top = free_space_all * 0.4            
            free_space_middle = free_space_all * 0.4

            # Позиция слова: горизонтально
            word_x = (self.width - word_width) // 2
            word_y = free_space_top - word_begin_y
            
            logger.info(f"Final font sizes: word={actual_word_font_size}, transcription={actual_transcription_font_size}")
            logger.info(f"Content heights: word={word_height} (word_begin_y={word_begin_y}), transcription={trans_height} (trans_begin_y={trans_begin_y})")
            logger.info(f"free_space_all: {free_space_all}, free_space_top: {free_space_top}, free_space_middle: {free_space_middle}")
            logger.info(f"Final word position: x={word_x}, y={word_y}")
            
            # Рисуем слово
            draw.text((word_x, word_y), word, font=word_font, fill=self.text_color)

            # Рисуем транскрипцию если есть
            if transcription and trans_font:
                # Позиция транскрипции: под словом с динамическим отступом
                trans_x = (self.width - trans_width) // 2
                trans_y = free_space_top + word_height + free_space_middle - trans_begin_y
                
                logger.info(f"Final transcription position: x={trans_x}, y={trans_y}")
                
                draw.text(
                    (trans_x, trans_y), 
                    transcription_text, 
                    font=trans_font, 
                    fill=self.transcription_color
                )

            # Сохраняем в BytesIO
            image_buffer = io.BytesIO()
            image.save(image_buffer, format='PNG', quality=95, optimize=True)
            image_buffer.seek(0)
            
            # Опционально сохраняем во временный файл для отладки
            if save_to_temp:
                await self._save_temp_file(image, word)
            
            logger.info(f"Generated image for word: {word} (size: {len(image_buffer.getvalue())} bytes)")
            return image_buffer
            
        except Exception as e:
            logger.error(f"Error generating word image: {e}", exc_info=True)
            raise
    
    async def _save_temp_file(self, image: Image.Image, word: str):
        """
        Сохраняет изображение во временный файл для отладки.
        
        Args:
            image: Изображение для сохранения
            word: Слово (для имени файла)
        """
        try:
            # Создаем безопасное имя файла
            safe_word = "".join(c for c in word if c.isalnum() or c in (' ', '-', '_')).rstrip()
            safe_word = safe_word.replace(' ', '_')[:20]  # Ограничиваем длину
            
            temp_path = Path(self.temp_dir) / f"word_{safe_word}_{id(image)}.png"
            
            # Создаем директорию если не существует
            temp_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Сохраняем асинхронно
            def _save():
                image.save(temp_path, format='PNG', quality=95)
                return temp_path
            
            loop = asyncio.get_event_loop()
            saved_path = await loop.run_in_executor(None, _save)
            
            logger.debug(f"Temporary image saved to: {saved_path}")
            
            # Планируем удаление файла через 5 минут
            asyncio.create_task(self._cleanup_temp_file(saved_path, delay=300))
            
        except Exception as e:
            logger.debug(f"Could not save temporary file: {e}")
    
    async def _cleanup_temp_file(self, file_path: Path, delay: int = 300):
        """
        Удаляет временный файл через указанное время.
        
        Args:
            file_path: Путь к файлу
            delay: Задержка в секундах
        """
        try:
            await asyncio.sleep(delay)
            if file_path.exists():
                file_path.unlink()
                logger.debug(f"Cleaned up temporary file: {file_path}")
        except Exception as e:
            logger.debug(f"Could not cleanup temporary file {file_path}: {e}")


# Глобальный экземпляр генератора
_generator_instance = None


def get_big_word_generator() -> BigWordGenerator:
    """
    Получает глобальный экземпляр генератора изображений.
    
    Returns:
        BigWordGenerator: Экземпляр генератора
    """
    global _generator_instance
    if _generator_instance is None:
        _generator_instance = BigWordGenerator()
    return _generator_instance


async def generate_big_word(
    word: str, 
    transcription: Optional[str] = None,
) -> io.BytesIO:
    """
    Удобная функция для генерации изображения слова.
    
    Args:
        word: Слово для отображения
        transcription: Транскрипция (опционально)
        
    Returns:
        io.BytesIO: Изображение в памяти
    """
    generator = get_big_word_generator()
    return await generator.generate_big_word(word, transcription)
