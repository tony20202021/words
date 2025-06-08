# Техническая документация по генерации изображений

## Содержание
1. [Архитектура модуля](#архитектура-модуля)
2. [Общие утилиты шрифтов](#общие-утилиты-шрифтов)
3. [Алгоритм генерации изображений](#алгоритм-генерации-изображений)
4. [Поддержка Unicode шрифтов](#поддержка-unicode-шрифтов)
5. [Конфигурация системы](#конфигурация-системы)
6. [API и интеграция](#api-и-интеграция)
7. [Производительность и оптимизация](#производительность-и-оптимизация)

## Архитектура модуля

### Основные компоненты

```python
# Общий модуль для всех сервисов
from common.utils.font_utils import get_font_manager

class BigWordGenerator:
    """Генератор изображений слов с Unicode поддержкой"""
    
    def __init__(self):
        self.font_manager = get_font_manager()  # Общий FontManager
    
    async def generate_big_word(self, word: str, transcription: str = "") -> BytesIO:
        """Основной метод генерации изображения"""
        pass
```

### Структура файлов

```
common/utils/
└── font_utils.py               # Общий модуль управления шрифтами

frontend/app/utils/
├── big_word_generator.py       # Генератор крупных изображений слов
├── config_holder.py           # Держатель конфигурации
```

## Общие утилиты шрифтов

### FontManager - универсальный менеджер шрифтов

```python
# common/utils/font_utils.py

class FontManager:
    """Управление шрифтами с поддержкой всех языков"""
    
    def get_unicode_font_paths(self) -> List[str]:
        """Поиск Unicode-совместимых шрифтов в системе"""
        pass
    
    async def auto_fit_font_size(self, text: str, max_width: int, max_height: int) -> Tuple:
        """Автоматический подбор размера шрифта для любого языка"""
        pass
    
    def _load_and_test_font(self, font_path: str, size: int) -> Optional[ImageFont]:
        """Тестирование Unicode поддержки со всеми языками"""
        pass

# Convenience functions
async def get_unicode_font_async(size: int) -> ImageFont:
    """Удобная функция получения Unicode шрифта"""
    pass
```


## Алгоритм генерации изображений

### Основной процесс с FontManager

```python
async def generate_big_word(self, word: str, transcription: str = "") -> BytesIO:
    """Генерация с использованием общего FontManager"""
    
    # Автоподбор размера шрифта для слова (любой язык)
    word_font, actual_word_font_size, word_width, word_height = await self.font_manager.auto_fit_font_size(
        word,
        available_width,
        self.height // 2,
        self.word_font_size,
        min_font_size
    )
    
    # Автоподбор для транскрипции (если есть)
    if transcription:
        trans_font, actual_trans_font_size, trans_width, trans_height = await self.font_manager.auto_fit_font_size(
            f"[{transcription}]",
            available_width,
            self.height // 4,
            self.transcription_font_size,
            min_font_size
        )
    
    # Создание и отрисовка изображения
    image = Image.new('RGB', (self.width, self.height), self.bg_color)
    draw = ImageDraw.Draw(image)
    
    # Использование готовых шрифтов
    draw.text((word_x, word_y), word, font=word_font, fill=self.text_color)
    if transcription:
        draw.text((trans_x, trans_y), f"[{transcription}]", font=trans_font, fill=self.transcription_color)
```

## Поддержка Unicode шрифтов

### Универсальный поиск шрифтов

```python
def get_unicode_font_paths(self) -> List[str]:
    """Поиск шрифтов для всех языков и платформ"""
    
    unicode_font_paths = [
        # Windows
        "C:/Windows/Fonts/msyh.ttc",           # Microsoft YaHei
        "C:/Windows/Fonts/simsun.ttc",         # SimSun
        "C:/Windows/Fonts/arial.ttf",
        
        # macOS
        "/System/Library/Fonts/PingFang.ttc",  # Chinese
        "/System/Library/Fonts/Arial.ttf",
        "/System/Library/Fonts/Hiragino Sans GB.ttc",
        
        # Linux - Noto fonts (лучшая Unicode поддержка)
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]
    
    return [path for path in unicode_font_paths if os.path.exists(path)]
```

### Тестирование поддержки всех языков

```python
def _load_and_test_font(self, font_path: str, size: int) -> Optional[ImageFont]:
    """Тестирование с символами разных языков"""
    
    # Расширенный набор тестовых символов
    test_chars = ["得", "あ", "한", "ا", "य", "А", "ñ", "ü"]
    
    font = ImageFont.truetype(font_path, size)
    unicode_support_count = 0
    
    for test_char in test_chars:
        bbox = draw.textbbox((0, 0), test_char, font=font)
        if bbox[2] > bbox[0] and bbox[3] > bbox[1]:
            unicode_support_count += 1
    
    # Шрифт хорош, если поддерживает хотя бы 3 из 8 символов
    return font if unicode_support_count >= 3 else None
```

## Конфигурация системы

### Обновленная структура bot.yaml

```yaml
# Настройки генерации изображений слов
word_images:
  enabled: true
  temp_dir: "temp"
  
  # Размеры изображения
  width: 800
  height: 400
  
  # Размеры шрифтов (автоподбираются для любого языка)
  fonts:
    word_size: 240
    transcription_size: 240
  
  # Цветовая схема (RGB)
  colors:
    background: [255, 255, 255]      # Белый фон
    text: [50, 50, 50]               # Темно-серый текст
    transcription: [100, 100, 100]   # Серый для транскрипции
  
  # Настройки производительности
  cleanup_delay: 300                 # Очистка временных файлов (сек)
  save_debug_files: false           # Сохранение для отладки
  
  # Универсальная поддержка языков
  universal_language_support: true   # Все языки поддерживаются
  auto_font_detection: true          # Автоматический выбор шрифта
```

## Производительность и оптимизация

### Кэширование в FontManager

```python
class FontManager:
    def __init__(self):
        self._font_cache: Dict[Tuple[str, int], ImageFont] = {}
        self._font_paths_cache: Optional[List[str]] = None
    
    def get_font(self, size: int, font_path: Optional[str] = None) -> ImageFont:
        """Получение шрифта с кэшированием"""
        
        cache_key = (font_path or "auto", size)
        
        if cache_key in self._font_cache:
            return self._font_cache[cache_key]
        
        # Загрузка и кэширование нового шрифта
        font = self._load_best_unicode_font(size, font_path)
        self._font_cache[cache_key] = font
        
        return font
```

### Асинхронная обработка

```python
async def generate_big_word(self, word: str, transcription: str = "") -> BytesIO:
    """Асинхронная генерация с общими утилитами"""
    
    # CPU-интенсивные операции в thread pool
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None, 
        self._generate_image_sync, 
        word, 
        transcription
    )
```
