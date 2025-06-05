# Техническая документация по генерации изображений

## Содержание
1. [Архитектура модуля](#архитектура-модуля)
2. [Алгоритм генерации изображений](#алгоритм-генерации-изображений)
3. [Поддержка Unicode шрифтов](#поддержка-unicode-шрифтов)
4. [Конфигурация системы](#конфигурация-системы)
5. [API и интеграция](#api-и-интеграция)
6. [Производительность и оптимизация](#производительность-и-оптимизация)
7. [Тестирование](#тестирование)

## Архитектура модуля

### Основные компоненты

```python
class WordImageGenerator:
    """Генератор изображений слов с Unicode поддержкой"""
    
    def __init__(self, config: DictConfig):
        self.config = config
        self.available_fonts = self._find_unicode_fonts()
    
    async def generate_word_image(self, word: str, transcription: str = "") -> BytesIO:
        """Основной метод генерации изображения"""
        pass
    
    def _find_unicode_fonts(self) -> List[str]:
        """Поиск Unicode-совместимых шрифтов в системе"""
        pass
    
    def _auto_fit_font_size(self, text: str, font_path: str, max_width: int, initial_size: int) -> int:
        """Автоподбор размера шрифта"""
        pass
```

### Структура файлов

```
frontend/app/utils/
├── word_image_generator.py     # Основной модуль генерации
├── config_holder.py           # Держатель конфигурации
└── message_utils.py           # Утилиты для отправки сообщений

frontend/app/bot/handlers/study/word_actions/
└── word_display_actions.py    # Обработчики команд и callback'ов

frontend/conf/config/
└── bot.yaml                   # Конфигурация генерации изображений
```

## Алгоритм генерации изображений

### Основной процесс

```python
async def generate_word_image(self, word: str, transcription: str = "") -> BytesIO:
    """
    1. Валидация входных данных
    2. Поиск подходящего Unicode шрифта
    3. Автоподбор размеров шрифтов
    4. Расчет позиций элементов
    5. Создание изображения
    6. Сохранение в BytesIO
    """
    
    # Валидация
    if not word.strip():
        raise ValueError("Word cannot be empty")
    
    # Поиск шрифта
    font_path = self._get_best_font_for_text(word)
    
    # Автоподбор размеров
    word_font_size = self._auto_fit_font_size(
        word, font_path, available_width, self.config.fonts.word_size
    )
    
    transcription_font_size = self._auto_fit_font_size(
        transcription, font_path, available_width, self.config.fonts.transcription_size
    ) if transcription else 0
    
    # Создание изображения
    image = Image.new('RGB', (self.config.width, self.config.height), tuple(self.config.colors.background))
    draw = ImageDraw.Draw(image)
    
    # Отрисовка элементов
    self._draw_text_centered(draw, word, word_font, word_y_position)
    if transcription:
        self._draw_text_centered(draw, transcription, transcription_font, transcription_y_position)
    
    # Сохранение
    buffer = BytesIO()
    image.save(buffer, format='PNG', quality=95, optimize=True)
    buffer.seek(0)
    
    return buffer
```

### Автоподбор размера шрифта

```python
def _auto_fit_font_size(self, text: str, font_path: str, max_width: int, initial_size: int) -> int:
    """
    Итеративное уменьшение размера шрифта до помещения в доступную ширину
    
    Алгоритм:
    1. Начинаем с initial_size
    2. Проверяем, помещается ли текст в max_width
    3. Если нет - уменьшаем на 10%
    4. Повторяем до помещения или достижения минимального размера
    """
    
    current_size = initial_size
    min_size = 12  # Минимальный читаемый размер
    
    while current_size >= min_size:
        try:
            font = ImageFont.truetype(font_path, current_size)
            text_width = draw.textbbox((0, 0), text, font=font)[2]
            
            if text_width <= max_width:
                return current_size
                
            current_size = int(current_size * 0.9)  # Уменьшаем на 10%
            
        except Exception as e:
            logger.error(f"Error fitting font size: {e}")
            return min_size
    
    return min_size
```

## Поддержка Unicode шрифтов

### Поиск системных шрифтов

```python
def _find_unicode_fonts(self) -> List[str]:
    """Поиск Unicode-совместимых шрифтов в системе"""
    
    font_paths = []
    
    # Windows
    windows_fonts = [
        "C:/Windows/Fonts/msyh.ttc",      # Microsoft YaHei
        "C:/Windows/Fonts/simsun.ttc",   # SimSun
        "C:/Windows/Fonts/arial.ttf"     # Arial
    ]
    
    # macOS
    macos_fonts = [
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/Arial.ttf",
        "/System/Library/Fonts/Helvetica.ttc"
    ]
    
    # Linux
    linux_fonts = [
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"
    ]
    
    all_possible_fonts = windows_fonts + macos_fonts + linux_fonts
    
    for font_path in all_possible_fonts:
        if os.path.exists(font_path):
            if self._test_font_unicode_support(font_path):
                font_paths.append(font_path)
    
    return font_paths
```

### Тестирование поддержки Unicode

```python
def _test_font_unicode_support(self, font_path: str) -> bool:
    """Тестирование поддержки Unicode символов шрифтом"""
    
    test_chars = ["得", "مرحبا", "हैलो", "Ж"]  # Китайский, арабский, хинди, кириллица
    
    try:
        font = ImageFont.truetype(font_path, 24)
        
        # Создаем тестовое изображение
        test_image = Image.new('RGB', (100, 100), 'white')
        draw = ImageDraw.Draw(test_image)
        
        for char in test_chars:
            try:
                # Пытаемся отрисовать символ
                draw.text((10, 10), char, font=font, fill='black')
                
                # Проверяем, что символ действительно отрисовался
                bbox = draw.textbbox((0, 0), char, font=font)
                if bbox[2] - bbox[0] <= 0:  # Нулевая ширина = не поддерживается
                    continue
                    
            except Exception:
                continue
        
        return True  # Если хотя бы один символ отрисовался
        
    except Exception as e:
        logger.debug(f"Font test failed for {font_path}: {e}")
        return False
```

## Конфигурация системы

### Структура конфигурации в bot.yaml

```yaml
word_images:
  # Основные настройки
  enabled: true
  temp_dir: "temp"
  
  # Размеры изображения
  width: 800
  height: 400
  
  # Стартовые размеры шрифтов (автоподбираются)
  fonts:
    word_size: 240
    transcription_size: 240
  
  # Цветовая схема (RGB)
  colors:
    background: [255, 255, 255]      # Белый фон
    text: [50, 50, 50]               # Темно-серый текст
    transcription: [100, 100, 100]   # Серый для транскрипции
    border: [200, 200, 200]          # Светло-серая рамка (если нужна)
  
  # Настройки производительности
  cleanup_delay: 300                 # Очистка временных файлов (сек)
  save_debug_files: false           # Сохранение файлов для отладки
  
  # Настройки отступов
  padding:
    horizontal: 20                   # Отступы по бокам
    vertical: 20                     # Отступы сверху/снизу
    between_elements: 20             # Между словом и транскрипцией
```

### Загрузка конфигурации

```python
from app.utils import config_holder

class WordImageGenerator:
    def __init__(self):
        self.config = config_holder.cfg.bot.word_images
        
        # Валидация конфигурации
        self._validate_config()
    
    def _validate_config(self):
        """Валидация конфигурации генератора"""
        
        if not self.config.enabled:
            raise RuntimeError("Word image generation is disabled")
        
        if self.config.width <= 0 or self.config.height <= 0:
            raise ValueError("Image dimensions must be positive")
        
        if len(self.config.colors.background) != 3:
            raise ValueError("Background color must be RGB triplet")
```

## API и интеграция

### Интеграция с обработчиками

```python
# study/word_actions/word_display_actions.py

@study_word_actions_router.message(Command("show_big"), StudyStates.studying)
async def cmd_show_big_word(message: Message, state: FSMContext):
    """Команда показа крупного изображения слова"""
    
    try:
        # Получение данных текущего слова
        state_data = await state.get_data()
        word_state = UserWordState.from_dict(state_data)
        
        if not word_state.word_data:
            await message.answer("❌ Нет текущего слова для отображения")
            return
        
        # Генерация и отправка изображения
        await _show_word_image(message, word_state, state)
        
    except Exception as e:
        logger.error(f"Error in cmd_show_big_word: {e}")
        await message.answer("❌ Ошибка при генерации изображения")

async def _show_word_image(message_obj, word_state: UserWordState, state: FSMContext):
    """Общая функция генерации и отправки изображения слова"""
    
    try:
        # Извлечение данных
        word_foreign = word_state.word_data.get('word_foreign', '')
        transcription = word_state.word_data.get('transcription', '')
        
        # Генерация изображения
        generator = WordImageGenerator()
        image_buffer = await generator.generate_word_image(word_foreign, transcription)
        
        # Создание файла для Telegram
        image_file = BufferedInputFile(
            image_buffer.getvalue(),
            filename=f"word_{word_foreign}_{int(time.time())}.png"
        )
        
        # Отправка с клавиатурой
        keyboard = create_word_image_keyboard()
        await message_obj.answer_photo(
            image_file,
            caption=f"📝 **{word_foreign}**" + (f"\n🔊 [{transcription}]" if transcription else ""),
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        
        # Переход в состояние просмотра изображения
        await state.set_state(StudyStates.viewing_word_image)
        
    except Exception as e:
        logger.error(f"Error generating word image: {e}")
        await message_obj.answer("❌ Ошибка при создании изображения слова")
```

### Callback обработчики

```python
@study_word_actions_router.callback_query(F.data == CallbackData.SHOW_WORD_IMAGE)
async def process_show_word_image_callback(callback: CallbackQuery, state: FSMContext):
    """Обработка нажатия кнопки показа изображения"""
    
    await callback.answer()
    
    state_data = await state.get_data()
    word_state = UserWordState.from_dict(state_data)
    
    await _show_word_image(callback.message, word_state, state)

@study_word_actions_router.callback_query(F.data == CallbackData.BACK_FROM_IMAGE)
async def process_back_from_image(callback: CallbackQuery, state: FSMContext):
    """Возврат от изображения к изучению"""
    
    await callback.answer()
    
    # Определение состояния для возврата
    state_data = await state.get_data()
    word_state = UserWordState.from_dict(state_data)
    
    if word_state.flags.get('word_shown', False):
        await state.set_state(StudyStates.viewing_word_details)
    else:
        await state.set_state(StudyStates.studying)
    
    # Показ слова без изображения
    await show_study_word(callback.message, word_state, state, edit_message=True)
```

## Производительность и оптимизация

### Оптимизация генерации

```python
class WordImageGenerator:
    def __init__(self):
        # Кэширование шрифтов
        self._font_cache = {}
        self._available_fonts = self._find_unicode_fonts()
    
    def _get_font(self, font_path: str, size: int) -> ImageFont.FreeTypeFont:
        """Получение шрифта с кэшированием"""
        
        cache_key = f"{font_path}:{size}"
        
        if cache_key not in self._font_cache:
            try:
                self._font_cache[cache_key] = ImageFont.truetype(font_path, size)
            except Exception as e:
                logger.error(f"Error loading font {font_path} size {size}: {e}")
                # Fallback на системный шрифт
                self._font_cache[cache_key] = ImageFont.load_default()
        
        return self._font_cache[cache_key]
    
    async def generate_word_image(self, word: str, transcription: str = "") -> BytesIO:
        """Асинхронная генерация изображения"""
        
        # Выполняем CPU-интенсивную операцию в thread pool
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, 
            self._generate_word_image_sync, 
            word, 
            transcription
        )
```

### Управление памятью

```python
def _generate_word_image_sync(self, word: str, transcription: str = "") -> BytesIO:
    """Синхронная генерация с управлением памятью"""
    
    image = None
    draw = None
    
    try:
        # Создание изображения
        image = Image.new(
            'RGB', 
            (self.config.width, self.config.height), 
            tuple(self.config.colors.background)
        )
        draw = ImageDraw.Draw(image)
        
        # ... логика отрисовки ...
        
        # Сохранение в память
        buffer = BytesIO()
        image.save(buffer, format='PNG', quality=95, optimize=True)
        buffer.seek(0)
        
        return buffer
        
    finally:
        # Явная очистка памяти
        if draw:
            del draw
        if image:
            image.close()
            del image
```

## Тестирование

### Unit тесты

```python
# frontend/tests/test_utils/test_word_image_generator.py

import pytest
from unittest.mock import Mock, patch
from app.utils.word_image_generator import WordImageGenerator

class TestWordImageGenerator:
    
    @pytest.fixture
    def generator(self):
        """Создание генератора для тестов"""
        with patch('app.utils.config_holder.cfg') as mock_cfg:
            # Мокаем конфигурацию
            mock_cfg.bot.word_images = Mock(
                enabled=True,
                width=800,
                height=400,
                fonts=Mock(word_size=240, transcription_size=240),
                colors=Mock(
                    background=[255, 255, 255],
                    text=[50, 50, 50],
                    transcription=[100, 100, 100]
                )
            )
            return WordImageGenerator()
    
    @pytest.mark.asyncio
    async def test_generate_simple_word(self, generator):
        """Тест генерации простого слова"""
        
        result = await generator.generate_word_image("hello")
        
        assert result is not None
        assert result.tell() > 0  # Проверяем, что есть данные
        
        # Проверяем, что это PNG
        result.seek(0)
        header = result.read(8)
        assert header == b'\x89PNG\r\n\x1a\n'
    
    @pytest.mark.asyncio
    async def test_generate_unicode_word(self, generator):
        """Тест генерации Unicode слова"""
        
        result = await generator.generate_word_image("得", "dé")
        
        assert result is not None
        assert result.tell() > 0
    
    def test_auto_fit_font_size(self, generator):
        """Тест автоподбора размера шрифта"""
        
        # Мокаем шрифт и метод измерения текста
        with patch.object(generator, '_get_font') as mock_font:
            mock_font.return_value = Mock()
            
            with patch('PIL.ImageDraw.Draw') as mock_draw:
                mock_draw_instance = Mock()
                mock_draw.return_value = mock_draw_instance
                
                # Мокаем размер текста
                mock_draw_instance.textbbox.return_value = (0, 0, 100, 30)
                
                result = generator._auto_fit_font_size("test", "font.ttf", 200, 240)
                
                assert result == 240  # Должен поместиться
    
    def test_font_unicode_support(self, generator):
        """Тест проверки Unicode поддержки шрифта"""
        
        with patch('PIL.ImageFont.truetype') as mock_truetype:
            with patch('PIL.Image.new') as mock_image:
                with patch('PIL.ImageDraw.Draw') as mock_draw:
                    
                    # Настройка моков
                    mock_font = Mock()
                    mock_truetype.return_value = mock_font
                    
                    mock_draw_instance = Mock()
                    mock_draw.return_value = mock_draw_instance
                    mock_draw_instance.textbbox.return_value = (0, 0, 20, 20)  # Ненулевая ширина
                    
                    result = generator._test_font_unicode_support("test_font.ttf")
                    
                    assert result is True
```

### Интеграционные тесты

```python
@pytest.mark.integration
async def test_full_image_generation_workflow():
    """Интеграционный тест полного процесса"""
    
    # Тестируем весь workflow от команды до отправки изображения
    with patch('app.utils.word_image_generator.WordImageGenerator') as mock_generator:
        mock_instance = Mock()
        mock_generator.return_value = mock_instance
        
        # Мокаем генерацию изображения
        mock_buffer = BytesIO(b'fake_image_data')
        mock_instance.generate_word_image.return_value = mock_buffer
        
        # Создаем тестовое сообщение
        message = Mock()
        message.answer_photo = AsyncMock()
        
        state = AsyncMock()
        state.get_data.return_value = {
            'word_data': {'word_foreign': 'test', 'transcription': 'test'}
        }
        
        # Выполняем команду
        await cmd_show_big_word(message, state)
        
        # Проверяем вызовы
        mock_instance.generate_word_image.assert_called_once_with('test', 'test')
        message.answer_photo.assert_called_once()
```
