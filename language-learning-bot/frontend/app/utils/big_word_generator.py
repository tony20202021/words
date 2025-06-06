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

logger = setup_logger(__name__)


class BigWordGenerator:
    """Генератор изображений для слов с транскрипцией."""
    
    def __init__(self):
        """
        Инициализация генератора.
        
        Args:
            temp_dir: Директория для временных файлов (из конфига)
            config: Конфигурация для настройки параметров
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
            
            # АВТОПОДБОР РАЗМЕРА ШРИФТА ДЛЯ СЛОВА
            word_font = None
            word_width = 0
            word_height = 0
            word_top_offset = 0
            actual_word_font_size = self.word_font_size
            
            logger.info(f"Starting word font size: {actual_word_font_size}")
            logger.info(f"Available width: {available_width}")
            
            current_font_size = self.word_font_size
            while current_font_size >= min_font_size:
                word_font = await self._get_font_async(size=current_font_size)
                word_bbox = draw.textbbox((0, 0), word, font=word_font)
                word_width = word_bbox[2] - word_bbox[0]
                
                if word_width <= available_width:
                    # Размер подходит
                    actual_word_font_size = current_font_size
                    word_height = word_bbox[3] - word_bbox[1]
                    word_top_offset = word_bbox[1]
                    break
                
                # Уменьшаем размер на 10%
                current_font_size = int(current_font_size * 0.9)
                logger.info(f"Word too wide ({word_width}px), trying smaller font: {current_font_size}")
            
            logger.info(f"Final word font size: {actual_word_font_size}")
            logger.info(f"Final word width: {word_width}px (available: {available_width}px)")
            
            # АВТОПОДБОР РАЗМЕРА ШРИФТА ДЛЯ ТРАНСКРИПЦИИ
            trans_bbox = None
            trans_width = 0
            trans_height = 0
            trans_top_offset = 0
            transcription_text = ""
            transcription_font = None
            actual_transcription_font_size = self.transcription_font_size
            
            if transcription:
                transcription_text = f"[{transcription}]"
                
                logger.info(f"Starting transcription font size: {actual_transcription_font_size}")
                
                current_font_size = self.transcription_font_size
                while current_font_size >= min_font_size:
                    transcription_font = await self._get_font_async(size=current_font_size)
                    trans_bbox = draw.textbbox((0, 0), transcription_text, font=transcription_font)
                    trans_width = trans_bbox[2] - trans_bbox[0]
                    
                    if trans_width <= available_width:
                        # Размер подходит
                        actual_transcription_font_size = current_font_size
                        trans_height = trans_bbox[3] - trans_bbox[1]
                        trans_top_offset = trans_bbox[1]
                        break
                    
                    # Уменьшаем размер на 10%
                    current_font_size = int(current_font_size * 0.9)
                    logger.info(f"Transcription too wide ({trans_width}px), trying smaller font: {current_font_size}")
                
                logger.info(f"Final transcription font size: {actual_transcription_font_size}")
                logger.info(f"Final transcription width: {trans_width}px (available: {available_width}px)")
            
            # Динамический расчет отступов в зависимости от размеров шрифтов
            gap_between_elements = max(actual_word_font_size * 0.2, actual_transcription_font_size * 0.3)
            gap_between_elements = int(gap_between_elements)
            
            # Общая высота контента (слово + отступ + транскрипция)
            if transcription:
                total_content_height = word_height + gap_between_elements + trans_height
            else:
                total_content_height = word_top_offset + word_height
            
            # Позиция слова:
            # Горизонтально - по центру
            word_x = (self.width - word_width) // 2
            
            # Вертикально - позиционируем слово в верхней части
            content_start_y = (self.height - total_content_height) // 2
            word_y = content_start_y - word_top_offset
            
            logger.info(f"Final font sizes: word={actual_word_font_size}, transcription={actual_transcription_font_size}")
            logger.info(f"Content heights: word={word_height}, transcription={trans_height}, gap={gap_between_elements}")
            logger.info(f"word_bbox={word_bbox}, trans_bbox={trans_bbox}")
            logger.info(f"Total content height: {total_content_height}, content_start_y: {content_start_y}")
            logger.info(f"Final word position: x={word_x}, y={word_y}")
            
            # Рисуем слово
            draw.text((word_x, word_y), word, font=word_font, fill=self.text_color)
            
            # Рисуем транскрипцию если есть
            if transcription and transcription_font:
                # Позиция транскрипции:
                # Горизонтально - по центру
                trans_x = (self.width - trans_width) // 2
                
                # Вертикально - под словом с динамическим отступом
                trans_y = word_y + word_top_offset + word_height + gap_between_elements - trans_top_offset
                
                logger.info(f"Final transcription position: x={trans_x}, y={trans_y}")
                
                draw.text(
                    (trans_x, trans_y), 
                    transcription_text, 
                    font=transcription_font, 
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
                                                    
    async def _get_font_async(self, size: int) -> ImageFont.ImageFont:
        """
        Асинхронно получает шрифт нужного размера.
        
        Args:
            size: Размер шрифта
            
        Returns:
            ImageFont: Объект шрифта
        """
        def _load_font():
            return self._get_font(size)
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _load_font)
    
    def _get_font(self, size: int) -> ImageFont.ImageFont:
        """
        Получает шрифт нужного размера с поддержкой Unicode.
        
        Args:
            size: Размер шрифта
            
        Returns:
            ImageFont: Объект шрифта
        """
        try:
            # Шрифты с поддержкой Unicode (включая китайские иероглифы)
            unicode_font_paths = [
                # Windows - Unicode шрифты
                "C:/Windows/Fonts/msyh.ttc",           # Microsoft YaHei
                "C:/Windows/Fonts/simsun.ttc",         # SimSun
                "C:/Windows/Fonts/arial.ttf",          # Arial (частичная поддержка)
                
                # macOS - Unicode шрифты  
                "/System/Library/Fonts/PingFang.ttc",  # PingFang SC
                "/System/Library/Fonts/Arial.ttf",
                "/System/Library/Fonts/Helvetica.ttc",
                
                # Linux - Noto шрифты (отличная поддержка Unicode)
                "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
                "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
                "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
                "/usr/share/fonts/truetype/noto/NotoSerifCJK-Regular.ttc",
                
                # Linux - дополнительные Unicode шрифты
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
                "/usr/share/fonts/truetype/ubuntu/Ubuntu-R.ttf",
                "/usr/share/fonts/truetype/droid/DroidSansFallback.ttf",
                "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
                
                # Linux - системные пути
                "/usr/share/fonts/TTF/DejaVuSans.ttf",
                "/usr/share/fonts/TTF/arial.ttf",
                "/usr/local/share/fonts/arial.ttf",
                
                # Дополнительные пути для китайских шрифтов
                "/usr/share/fonts/chinese/TrueType/uming.ttf",
                "/usr/share/fonts/truetype/arphic/uming.ttf",
            ]
            
            for font_path in unicode_font_paths:
                if os.path.exists(font_path):
                    try:
                        font = ImageFont.truetype(font_path, size)
                        
                        # Тестируем шрифт на китайском символе
                        test_char = "得"
                        temp_img = Image.new('RGB', (100, 100), (255, 255, 255))
                        temp_draw = ImageDraw.Draw(temp_img)
                        
                        try:
                            bbox = temp_draw.textbbox((0, 0), test_char, font=font)
                            # Если bbox имеет ненулевые размеры, шрифт поддерживает символ
                            if bbox[2] > bbox[0] and bbox[3] > bbox[1]:
                                logger.info(f"Using Unicode font: {font_path} (size: {size})")
                                return font
                            else:
                                logger.debug(f"Font {font_path} doesn't support Unicode characters")
                        except Exception:
                            logger.debug(f"Font {font_path} failed Unicode test")
                            
                    except Exception as e:
                        logger.debug(f"Could not load font {font_path}: {e}")
                        continue
            
            # Если Unicode шрифты не найдены, пробуем системные
            logger.warning("No Unicode fonts found, trying system fonts...")
            basic_fonts = [
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
            ]
            
            for font_path in basic_fonts:
                if os.path.exists(font_path):
                    try:
                        font = ImageFont.truetype(font_path, size)
                        logger.warning(f"Using basic font: {font_path} (may not support all characters)")
                        return font
                    except Exception:
                        continue
            
            # Последний resort - дефолтный шрифт
            logger.error("No suitable fonts found, using default font (limited Unicode support)")
            return ImageFont.load_default()
            
        except Exception as e:
            logger.error(f"Error loading font: {e}")
            return ImageFont.load_default()
    
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
    
    Args:
        temp_dir: Директория для временных файлов
        config: Конфигурация генератора
        
    Returns:
        WordImageGenerator: Экземпляр генератора
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
        temp_dir: Директория для временных файлов
        config: Конфигурация генератора (включая размеры шрифтов)
        
    Returns:
        io.BytesIO: Изображение в памяти
    """
    generator = get_big_word_generator()
    return await generator.generate_big_word(word, transcription)
