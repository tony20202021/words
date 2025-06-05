# Организация роутеров и обработчиков в aiogram 3.x

## Содержание
1. [Принципы организации роутеров](#принципы-организации-роутеров)
2. [Иерархия роутеров в проекте](#иерархия-роутеров-в-проекте)
3. [Приоритеты и порядок обработки](#приоритеты-и-порядок-обработки)
4. [Модульная архитектура обработчиков](#модульная-архитектура-обработчиков)
5. [Лучшие практики](#лучшие-практики)
6. [Отладка и диагностика](#отладка-и-диагностика)

## Принципы организации роутеров

### 1. Специфичность перед общностью
Более специфичные обработчики должны проверяться перед более общими:

```python
# ✅ Правильно: специфичная команда перед общим обработчиком
@router.message(Command("cancel"), StateFilter(SomeState))  # Специфично
@router.message(StateFilter(SomeState))                     # Общее

# ❌ Неправильно: общий обработчик перехватит все сообщения
@router.message(StateFilter(SomeState))                     # Общее
@router.message(Command("cancel"), StateFilter(SomeState))  # Никогда не сработает
```

### 2. Команды перед состояниями
Команды имеют приоритет над состояниями FSM:

```python
# ✅ Правильно
@router.message(Command("help"))           # Команда
@router.message(StateFilter(StudyStates))  # Состояние

# ❌ Неправильно
@router.message(StateFilter(StudyStates))  # Состояние
@router.message(Command("help"))           # Команда не сработает в состоянии
```

### 3. Использование приоритетов
В aiogram 3.x можно устанавливать явные приоритеты:

```python
@router.message(Command("cancel"), flags={"priority": 100})  # Высокий приоритет
@router.message(Command("help"), flags={"priority": 90})     # Средний приоритет
@router.message(flags={"priority": 0})                       # Низкий приоритет
```

## Иерархия роутеров в проекте

### Главная иерархия

```python
# main_frontend.py - регистрация роутеров в главном диспетчере

dp.include_router(common_router)      # Приоритет 1: Meta-состояния
dp.include_router(user_router)        # Приоритет 2: Пользовательские команды
dp.include_router(admin_router)       # Приоритет 3: Административные команды
dp.include_router(language_router)    # Приоритет 4: Выбор языка
dp.include_router(study_router)       # Приоритет 5: Изучение слов
```

### Структура пользовательских роутеров

```python
# user_handlers.py - объединение пользовательских роутеров

user_router = Router()

# Порядок включения имеет значение!
user_router.include_router(basic_router)      # /start, основные команды
user_router.include_router(help_router)       # /help, справка
user_router.include_router(settings_router)   # /settings, настройки
user_router.include_router(stats_router)      # /stats, статистика
user_router.include_router(hint_router)       # /hint, информация о подсказках
```

### Структура административных роутеров

```python
# admin_handlers.py - объединение административных роутеров

admin_router = Router()

admin_router.include_router(admin_basic_router)     # Базовые команды
admin_router.include_router(admin_language_router)  # Управление языками
admin_router.include_router(admin_word_router)      # Управление словами
admin_router.include_router(admin_upload_router)    # Загрузка файлов
```

### Структура роутеров изучения

```python
# study_handlers.py - объединение роутеров изучения

study_router = Router()

study_router.include_router(study_commands_router)     # Команды изучения
study_router.include_router(study_words_router)        # Отображение слов
study_router.include_router(study_word_actions_router) # Действия со словами
study_router.include_router(study_hint_router)         # Подсказки
```

## Приоритеты и порядок обработки

### Уровень 1: Meta-состояния (наивысший приоритет)

```python
# common_handlers.py
common_router = Router()

@common_router.message(StateFilter(CommonStates.handling_api_error))
@common_router.message(StateFilter(CommonStates.connection_lost))
@common_router.message(StateFilter(CommonStates.unknown_command))
```

**Назначение:** Обработка системных ошибок и исключительных ситуаций

### Уровень 2: Универсальные команды

```python
# В различных роутерах с высоким приоритетом
@router.message(Command("cancel"), flags={"priority": 100})
@router.message(Command("start"), flags={"priority": 95})
@router.message(Command("help"), flags={"priority": 90})
```

**Назначение:** Команды, которые должны работать в любом контексте

### Уровень 3: Специфичные команды и состояния

```python
# Специфичные обработчики с нормальным приоритетом
@router.message(Command("study"), StateFilter(None))
@router.message(F.text == "✅ Знаю, к следующему", StudyStates.studying)
@router.callback_query(F.data.startswith("hint_"))
```

### Уровень 4: Fallback обработчики

```python
# Обработчики "по умолчанию" с низким приоритетом
@router.message(StateFilter(StudyStates), flags={"priority": 0})
@router.callback_query(flags={"priority": 0})
```

## Модульная архитектура обработчиков

### Подмодули для сложных функций

#### study/hint/ - Обработка подсказок

```python
# study_hint_handlers.py - главный роутер подсказок
hint_router = Router()

# Включение подроутеров в правильном порядке
hint_router.include_router(hint_common_router)    # Общие функции (/cancel)
hint_router.include_router(hint_create_router)    # Создание подсказок
hint_router.include_router(hint_edit_router)      # Редактирование
hint_router.include_router(hint_toggle_router)    # Переключение видимости
hint_router.include_router(hint_unknown_router)   # Обработка неожиданных сообщений
```

#### study/word_actions/ - Действия со словами

```python
# study_word_actions.py - главный роутер действий
word_actions_router = Router()

# Включение специализированных роутеров
word_actions_router.include_router(word_display_router)     # Показ слов и изображений
word_actions_router.include_router(word_evaluation_router)  # Оценка знаний
word_actions_router.include_router(word_navigation_router)  # Навигация между словами
word_actions_router.include_router(word_utility_router)     # Утилитарные действия
```

#### admin/file_upload/ - Загрузка файлов

```python
# admin_upload_handlers.py - главный роутер загрузки
upload_router = Router()

upload_router.include_router(upload_language_router)     # Выбор языка
upload_router.include_router(upload_file_router)         # Обработка файлов
upload_router.include_router(upload_column_router)       # Настройка колонок
upload_router.include_router(upload_settings_router)     # Параметры загрузки
```

### Принципы разделения ответственности

#### Один роутер - одна ответственность

```python
# ✅ Правильно: четкое разделение
# word_display_actions.py - только показ слов
@router.message(Command("show_big"))
@router.callback_query(F.data == "show_word_image")

# word_evaluation_actions.py - только оценка слов  
@router.callback_query(F.data == "word_know")
@router.callback_query(F.data == "word_dont_know")

# ❌ Неправильно: смешивание ответственности
# В одном файле и показ, и оценка, и навигация
```

#### Логическая группировка

```python
# Группировка по функциональности, а не по типу события
# ✅ Правильно: hint_create_handlers.py
@router.callback_query(F.data.startswith("hint_create_"))  # Callback
@router.message(StateFilter(HintStates.creating))          # Text message
@router.message(F.content_type == "voice", HintStates.creating)  # Voice message

# ❌ Неправильно: разделение по типу события
# callback_handlers.py - все callback'и
# message_handlers.py - все сообщения
```

## Лучшие практики

### 1. Именование роутеров

```python
# ✅ Правильно: понятные имена
study_commands_router = Router()
hint_create_router = Router()
admin_word_router = Router()

# ❌ Неправильно: непонятные имена
router1 = Router()
handler = Router()
r = Router()
```

### 2. Документирование порядка включения

```python
# study_handlers.py
study_router = Router()

# ВАЖНО: Порядок включения роутеров имеет значение!
# 1. Команды должны быть перед состояниями
# 2. Специфичные обработчики перед общими
# 3. Подроутеры включаются в порядке приоритета

study_router.include_router(study_commands_router)     # Команды (/study)
study_router.include_router(study_word_actions_router) # Действия со словами
study_router.include_router(study_hint_router)         # Подсказки
study_router.include_router(study_words_router)        # Общие обработчики
```

### 3. Использование middleware на уровне роутеров

```python
# Применение middleware к конкретным роутерам
admin_router.message.middleware(AdminOnlyMiddleware())
study_router.message.middleware(UserRegistrationMiddleware())

# Вместо глобального применения ко всем роутерам
```

### 4. Фильтрация на уровне роутера

```python
# ✅ Правильно: фильтр на уровне роутера
admin_router = Router()
admin_router.message.filter(F.from_user.id.in_(ADMIN_IDS))

# ❌ Неправильно: проверка в каждом обработчике
@router.message(Command("admin"))
async def admin_command(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    # обработка...
```

## Отладка и диагностика

### Логирование регистрации обработчиков

```python
import logging
logger = logging.getLogger(__name__)

def register_handlers():
    """Регистрация обработчиков с логированием"""
    
    logger.info("Registering main routers...")
    
    # Регистрация с логированием
    dp.include_router(common_router)
    logger.info("✓ Common handlers registered")
    
    dp.include_router(user_router)
    logger.info("✓ User handlers registered")
    
    dp.include_router(admin_router)
    logger.info("✓ Admin handlers registered")
    
    dp.include_router(study_router)
    logger.info("✓ Study handlers registered")
    
    logger.info("All handlers registered successfully")
```

### Диагностика конфликтов обработчиков

```python
# Добавление отладочной информации в обработчики
@router.message(Command("test"))
async def debug_handler(message: Message):
    logger.debug(f"Handler triggered: {__name__}.debug_handler")
    logger.debug(f"Message: {message.text}")
    logger.debug(f"State: {await state.get_state()}")
```

### Анализ порядка обработки

```python
# Создание middleware для отслеживания порядка обработки
class HandlerOrderMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        logger.debug(f"Handler order: {handler.__name__}")
        return await handler(event, data)

# Применение к роутерам для анализа
router.message.middleware(HandlerOrderMiddleware())
```

### Инструменты для отладки

```python
# Создание специального debug роутера
debug_router = Router()

@debug_router.message(Command("debug_routes"))
async def show_router_info(message: Message):
    """Показать информацию о зарегистрированных роутерах"""
    
    info = []
    info.append("🔍 Registered routers:")
    info.append(f"- Common router: {len(common_router.message.handlers)} handlers")
    info.append(f"- User router: {len(user_router.message.handlers)} handlers")
    info.append(f"- Admin router: {len(admin_router.message.handlers)} handlers")
    info.append(f"- Study router: {len(study_router.message.handlers)} handlers")
    
    await message.answer("\n".join(info))

# Регистрация debug роутера в development режиме
if os.getenv("ENVIRONMENT") == "development":
    dp.include_router(debug_router)
```

---

**Правильная организация роутеров критически важна для масштабируемости и поддерживаемости проекта. Следуйте принципам специфичности, документируйте порядок включения и используйте модульную архитектуру для сложных функций.**
