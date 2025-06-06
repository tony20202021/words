"""
Заглушка генератора картинок написания для разработки.
Создает пустые изображения для имитации работы сервиса генерации картинок написания.
"""

import io
import asyncio
from typing import Optional
from PIL import Image, ImageDraw, ImageFont

from app.utils import config_holder
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class WritingImageGenerator:
    """Заглушка генератора картинок написания."""
    
    def __init__(self):
        """Инициализация генератора с настройками из конфига."""
        # Настройки по умолчанию
        self.width = 400
        self.height = 400
        self.bg_color = (240, 240, 240)  # Светло-серый фон
        self.border_color = (180, 180, 180)  # Серая рамка
        self.text_color = (120, 120, 120)  # Серый текст
        self.font_size = 24
        
        # Применяем конфигурацию если есть
        if hasattr(config_holder.cfg, 'writing_image_service'):
            writing_config = config_holder.cfg.writing_images
            
            # Настройки заглушки
            if hasattr(writing_config, 'development'):
                dev_config = writing_config.development
                
                # Размеры
                if hasattr(dev_config, 'stub_size'):
                    self.width = dev_config.stub_size.get('width', self.width)
                    self.height = dev_config.stub_size.get('height', self.height)
                
                # Цвета
                if hasattr(dev_config, 'stub_colors'):
                    colors = dev_config.stub_colors
                    self.bg_color = tuple(colors.get('background', self.bg_color))
                    self.border_color = tuple(colors.get('border', self.border_color))
                    self.text_color = tuple(colors.get('text', self.text_color))
                
                # Шрифт
                if hasattr(dev_config, 'stub_fonts'):
                    self.font_size = dev_config.stub_fonts.get('size', self.font_size)
                
        logger.info(f"WritingImageGenerator initialized: {self.width}x{self.height}")

    async def generate_writing_image(
        self, 
        word: str, 
        language: Optional[str] = None
    ) -> io.BytesIO:
        """
        Генерирует заглушку картинки написания.
        
        Args:
            word: Слово для которого нужна картинка написания
            language: Язык (пока не используется в заглушке)
            
        Returns:
            io.BytesIO: Изображение заглушки в памяти
        """
        try:
            logger.info(f"Generating writing image stub for word: '{word}', language: '{language}'")
            
            # Создаем изображение заглушки
            image = Image.new('RGB', (self.width, self.height), self.bg_color)
            draw = ImageDraw.Draw(image)
            
            # Рисуем рамку
            border_width = 2
            draw.rectangle(
                [border_width, border_width, self.width-border_width, self.height-border_width],
                outline=self.border_color,
                width=border_width
            )
            
            # Добавляем текст заглушки
            try:
                # Пытаемся использовать шрифт по умолчанию
                font = ImageFont.load_default()
            except Exception:
                font = None
            
            # Основной текст
            main_text = "Writing Image"
            if font:
                bbox = draw.textbbox((0, 0), main_text, font=font)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]
            else:
                text_width, text_height = 80, 20  # Примерные размеры
            
            main_x = (self.width - text_width) // 2
            main_y = (self.height - text_height) // 2 - 30
            
            draw.text(
                (main_x, main_y),
                main_text,
                fill=self.text_color,
                font=font
            )
            
            # Текст со словом
            word_text = f"Word: {word}"
            if font:
                bbox = draw.textbbox((0, 0), word_text, font=font)
                text_width = bbox[2] - bbox[0]
            else:
                text_width = len(word_text) * 8
            
            word_x = (self.width - text_width) // 2
            word_y = main_y + 40
            
            draw.text(
                (word_x, word_y),
                word_text,
                fill=self.text_color,
                font=font
            )
            
            # Текст "Stub"
            stub_text = "(Development Stub)"
            if font:
                bbox = draw.textbbox((0, 0), stub_text, font=font)
                text_width = bbox[2] - bbox[0]
            else:
                text_width = len(stub_text) * 6
            
            stub_x = (self.width - text_width) // 2
            stub_y = word_y + 30
            
            draw.text(
                (stub_x, stub_y),
                stub_text,
                fill=self.text_color,
                font=font
            )
            
            # Сохраняем в BytesIO
            image_buffer = io.BytesIO()
            image.save(image_buffer, format='PNG', quality=95, optimize=True)
            image_buffer.seek(0)
            
            logger.info(f"Generated writing image stub for word: {word} (size: {len(image_buffer.getvalue())} bytes)")
            return image_buffer
            
        except Exception as e:
            logger.error(f"Error generating writing image stub: {e}", exc_info=True)
            raise


# Глобальный экземпляр генератора
_generator_instance = None


def get_writing_image_generator() -> WritingImageGenerator:
    """
    Получает глобальный экземпляр генератора картинок написания.
    
    Returns:
        WritingImageGenerator: Экземпляр генератора
    """
    global _generator_instance
    if _generator_instance is None:
        _generator_instance = WritingImageGenerator()
    return _generator_instance


async def generate_writing_image(
    word: str, 
    language: Optional[str] = None
) -> io.BytesIO:
    """
    Удобная функция для генерации картинки написания.
    
    Args:
        word: Слово для которого нужна картинка написания
        language: Язык (опционально)
        
    Returns:
        io.BytesIO: Изображение в памяти
    """
    generator = get_writing_image_generator()
    return await generator.generate_writing_image(word, language)
