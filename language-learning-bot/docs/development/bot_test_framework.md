# Фреймворк для тестирования Telegram-бота

## Содержание
1. [Обзор фреймворка](#обзор-фреймворка)
2. [Структура фреймворка](#структура-фреймворка)
3. [Основные компоненты](#основные-компоненты)
4. [Создание тестов](#создание-тестов)
5. [YAML-сценарии](#yaml-сценарии)
6. [Настройка API моков](#настройка-api-моков)
7. [Работа с FSM](#работа-с-fsm)
8. [Лучшие практики](#лучшие-практики)
9. [Устранение проблем](#устранение-проблем)

## Обзор фреймворка

Фреймворк для тестирования Telegram-бота представляет собой модульную систему, позволяющую писать и выполнять интеграционные тесты для бота без необходимости реального взаимодействия с Telegram API. Он имитирует поведение пользователя (отправку команд, сообщений и нажатия на inline-кнопки) и анализирует ответы бота.

## Структура фреймворка

Фреймворк разделен на несколько модулей:

```
frontend/tests/
├── conftest.py                    # Конфигурация pytest
└── bot_test_framework/            # Пакет с тестовым фреймворком
    ├── __init__.py                # Инициализация пакета
    ├── bot_actions.py             # Классы действий
    ├── bot_test_context.py        # Основной контекст тестирования
    ├── command_handler.py         # Обработчик команд
    ├── message_handler.py         # Обработчик сообщений
    ├── callback_handler.py        # Обработчик callback-запросов
    ├── bot_test_scenario.py       # Класс сценария
    ├── bot_test_framework.py      # Основной модуль с фикстурой
    ├── scenario_executor.py       # Модуль для выполнения сценариев
    └── handlers_setup.py          # Утилиты для настройки обработчиков
```

## Основные компоненты

### Действия (BotAction)

Базовый класс `BotAction` и его наследники определяют действия, которые может выполнить пользователь:

- `CommandAction` - отправка команды боту (например, `/start`)
- `MessageAction` - отправка текстового сообщения
- `CallbackAction` - имитация нажатия на inline-кнопку
- `AssertionAction` - проверка состояния или результата

### Контекст тестирования (BotTestContext)

Класс `BotTestContext` управляет состоянием тестирования, включая:

- Мок-объекты для бота, пользователя и чата
- Состояние FSM (Finite State Machine)
- Историю взаимодействий с ботом
- Обработчики команд, сообщений и callback'ов

### Обработчики

- `CommandHandler` - обработка команд
- `MessageHandler` - обработка обычных сообщений
- `CallbackHandler` - обработка callback-запросов от inline-кнопок

### Сценарий тестирования (BotTestScenario)

Класс `BotTestScenario` позволяет определить последовательность действий для тестирования. Он предоставляет fluent-интерфейс для построения сценариев:

```python
scenario = bot_test(
    name="Test Scenario",
    handler_modules=["app.bot.handlers.user_handlers"]
).with_api_mock(setup_api_mock)

scenario.add_command("start")
scenario.assert_message_contains("Здравствуйте")
scenario.add_callback("settings_toggle_skip_marked")
scenario.assert_state_contains("skip_marked", True)
```

### Исполнитель сценариев (ScenarioExecutor)

Модуль `scenario_executor.py` содержит функции для работы с декларативными сценариями:

- `execute_scenario_steps(scenario, steps)` - добавляет шаги сценария
- `load_scenario_from_dict(scenario_creator, scenario_data)` - создает сценарий из словаря
- `load_yaml_scenario(filename)` - загружает сценарий из YAML-файла

## Создание тестов

### 1. Создание тестового сценария программным способом

```python
@pytest.mark.asyncio
async def test_settings_toggle_scenario(bot_test):
    # Настройка мока для API-клиента
    def setup_api_mock(api_client):
        api_client.get_user_by_telegram_id.return_value = {
            "success": True,
            "status": 200,
            "result": [{"id": "user123"}],
            "error": None
        }
    
    # Создание сценария
    scenario = bot_test(
        name="Settings Toggle Scenario",
        handler_modules=["app.bot.handlers.user_handlers"],
        user_id=123456789
    ).with_api_mock(setup_api_mock)
    
    # Настройка обработчиков
    def setup_handlers(context):
        import app.bot.handlers.user_handlers as user_handlers
        context.command_handlers = {
            'settings': user_handlers.cmd_settings
        }
        context.callback_handlers = {
            'settings_toggle_skip_marked': user_handlers.process_settings_toggle_skip_marked,
            'settings_toggle_check_date': user_handlers.process_settings_toggle_check_date,
            'settings_start_word': user_handlers.process_settings_start_word
        }
        if context.api_client:
            context.bot.api_client = context.api_client
    
    # Добавление настройки обработчиков в сценарий
    scenario.setup_handlers = setup_handlers
    
    # Добавление действий в сценарий
    scenario.add_command("settings")
    scenario.assert_message_contains("Настройки процесса обучения")
    
    # Переключение настройки skip_marked
    scenario.add_callback("settings_toggle_skip_marked")
    scenario.assert_message_contains("Настройки успешно обновлены")
    scenario.assert_state_contains("skip_marked", True)
    
    # Выполнение сценария
    await scenario.execute()
```

### 2. Создание тестового сценария из YAML-файла

#### Создание YAML-файла сценария

Создайте файл `settings_toggle.yaml` в директории `scenarios`:

```yaml
name: Settings Toggle Scenario
user_id: 123456789
api_mock: common
auto_setup: true
steps:
  - type: command
    name: settings
    asserts:
      - type: message_contains
        text: "Настройки процесса обучения"
  
  - type: callback
    data: settings_toggle_skip_marked
    asserts:
      - type: message_contains
        text: "Настройки успешно обновлены"
      - type: state_contains
        data: ["skip_marked", true]
```

#### Загрузка и выполнение сценария из YAML-файла

```python
@pytest.mark.asyncio
async def test_settings_toggle_scenario():
    # Формируем путь к файлу сценария
    scenario_path = os.path.join(SCENARIOS_DIR, "settings_toggle.yaml")
    
    # Загружаем сценарий из файла
    scenario_data = load_yaml_scenario(scenario_path)
    
    # Создаем сценарий на основе загруженных данных
    scenario = load_scenario_from_dict(create_test_scenario, scenario_data)
    
    # Выполняем сценарий
    await scenario.execute()
```

## YAML-сценарии

YAML-файлы сценариев имеют следующую структуру:

```yaml
# Основные параметры сценария
name: "Название сценария"
user_id: 123456789         # ID пользователя Telegram
api_mock: "common"         # Тип API-мока: "common" или пользовательская функция
auto_setup: true           # Автоматическая настройка обработчиков

# Шаги сценария
steps:
  # Команда
  - type: command
    name: "start"          # Имя команды
    args: "параметры"      # Опциональные параметры команды
    asserts:               # Проверки после выполнения
      - type: message_contains
        text: "Текст для проверки"
        position: -1       # Позиция сообщения (-1 = последнее)
      
  # Сообщение
  - type: message
    text: "Текст сообщения"
    asserts:
      - type: message_contains
        text: "Ожидаемый ответ"
      
  # Callback
  - type: callback
    data: "callback_data"
    asserts:
        - type: state_contains
          data: ["ключ", значение]
```

### Доступные проверки

- `assert_message_contains(text, position=-1)` - проверка, что сообщение содержит указанный текст
- `assert_state_contains(key, value=None)` - проверка, что состояние содержит указанный ключ и значение

## Настройка API моков

### 1. Пользовательская настройка мока API

```python
def setup_api_mock(api_client):
    # Настройка ответа для get_user_by_telegram_id
    api_client.get_user_by_telegram_id.return_value = {
        "success": True,
        "status": 200,
        "result": [{"id": "user123"}],
        "error": None
    }
    
    # Настройка ответа для get_languages
    api_client.get_languages.return_value = {
        "success": True,
        "status": 200,
        "result": [
            {"id": "eng", "name_ru": "Английский", "name_foreign": "English"},
            {"id": "fra", "name_ru": "Французский", "name_foreign": "Français"}
        ],
        "error": None
    }
```

### 2. Использование стандартного мока API

Для частых сценариев можно использовать предварительно настроенный мок API:

```python
# Использование стандартного мока API
scenario = create_test_scenario(
    name="Standard API Mock Scenario"
).with_common_api_mock()
```

Стандартный мок настроен на типичные запросы, такие как получение пользователя, языков и слов.

## Работа с FSM

### Настройка начального состояния

```python
# Настройка начального состояния FSM
await scenario.context.state.update_data({
    "current_language": {
        "id": "eng", 
        "name_ru": "Английский", 
        "name_foreign": "English"
    },
    "db_user_id": "user123"
})
```

### Проверка состояния

```python
# Проверка состояния после выполнения действия
scenario.assert_state_contains("skip_marked", True)
```

### Отслеживание истории изменений состояния

```python
# Проверка истории изменений состояния
@pytest.mark.asyncio
async def test_state_history_tracking(bot_test):
    context = bot_test(name="State History Test").context
    
    # Серия обновлений
    await context.state.update_data({"score": 0})
    await context.state.update_data({"score": 1})
    await context.state.update_data({"check_interval": 2})
    
    # Проверка истории изменений
    assert len(context.state_history) == 3
    assert context.state_history[0]["score"] == 0
    assert context.state_history[1]["score"] == 1
    assert context.state_history[2]["check_interval"] == 2
```

### Работа с моделями состояний

```python
# Пример работы с UserWordState
@pytest.mark.asyncio
async def test_with_state_models(bot_test):
    context = bot_test(name="State Models Test").context
    
    # Настройка состояния
    await context.state.update_data({
        "current_word": {"id": "word123", "word_foreign": "test"},
        "current_word_id": "word123",
        "db_user_id": "user123"
    })
    
    # Создание модели из состояния
    from app.utils.state_models import UserWordState
    user_word_state = await UserWordState.from_state(context.state)
    
    # Проверка данных
    assert user_word_state.word_id == "word123"
    
    # Модификация данных
    user_word_state.current_study_index = 5
    
    # Сохранение обратно в состояние
    await user_word_state.save_to_state(context.state)
    
    # Проверка обновленного состояния
    assert context.state_data["current_study_index"] == 5
```

## Лучшие практики

### 1. Изолируйте тесты

Каждый тест должен быть независимым от других и проверять только одну конкретную функциональность:

```python
# Плохо: тест проверяет несколько функций сразу
@pytest.mark.asyncio
async def test_everything(bot_test):
    scenario = bot_test(name="Test All")
    scenario.add_command("start")
    scenario.add_command("settings")
    scenario.add_command("language")
    await scenario.execute()

# Хорошо: каждый тест проверяет одну функцию
@pytest.mark.asyncio
async def test_start_command(bot_test):
    scenario = bot_test(name="Test Start")
    scenario.add_command("start")
    await scenario.execute()

@pytest.mark.asyncio
async def test_settings_command(bot_test):
    scenario = bot_test(name="Test Settings")
    scenario.add_command("settings")
    await scenario.execute()
```

### 2. Используйте явное указание обработчиков

Для сложных сценариев рекомендуется явно указывать соответствие между командами, callback-данными и их обработчиками:

```python
def setup_handlers(context):
    from app.bot.handlers.language_handlers import cmd_language, process_language_selection
    from app.bot.handlers.study.study_commands import cmd_study
    
    context.command_handlers = {
        'language': cmd_language,
        'study': cmd_study
    }
    
    context.callback_handlers = {
        'lang_select_eng': process_language_selection
    }
```

### 3. Используйте YAML-файлы для повторяющихся сценариев

Для стандартных сценариев используйте YAML-файлы, что упрощает их поддержку и обновление:

```python
# Загрузка сценария из YAML-файла
scenario_path = os.path.join(SCENARIOS_DIR, "common_scenario.yaml")
scenario = load_scenario_from_dict(
    create_test_scenario,
    load_yaml_scenario(scenario_path)
)
```

### 4. Создавайте фикстуры для общих компонентов

Используйте фикстуры pytest для часто используемых компонентов:

```python
@pytest.fixture
def api_client_for_study():
    # Создание и настройка API клиента для тестов изучения слов
    api_client = AsyncMock()
    # Настройка методов
    # ...
    return api_client

@pytest.mark.asyncio
async def test_study_word(bot_test, api_client_for_study):
    scenario = bot_test(name="Study Test").with_custom_api_mock(
        lambda mock: mock.update(api_client_for_study)
    )
    # ...
```

### 5. Организуйте тесты по функциональности

Структурируйте тесты в соответствии с функциональностью бота:

```
tests/
├── test_admin/          # Тесты админских функций
├── test_user/           # Тесты пользовательских функций
├── test_language/       # Тесты выбора языка
└── test_study/          # Тесты изучения слов
```

## Устранение проблем

### Проблема: Обработчики команд не вызываются

#### Симптомы:
- В логах сообщение "Обработчик для команды /X не найден"
- Тест проходит, но ожидаемые действия не выполняются

#### Решения:
1. Проверьте пути к модулям в `handler_modules`
2. Явно укажите обработчики через `setup_handlers`
3. Проверьте формат команды (не должна содержать пробелы или спецсимволы)

### Проблема: Callback-обработчики не вызываются

#### Симптомы:
- Нажатия на кнопки не вызывают ожидаемых действий
- В логах сообщение "Обработчик для callback X не найден"

#### Решения:
1. Явно указать соответствие callback-данных и обработчиков через `setup_handlers`
2. Проверить, что формат callback-данных совпадает с ожидаемым
3. Проверить наличие функций с именами вида `process_{callback_data}`

### Проблема: Ошибки при проверке состояния

#### Симптомы:
- Ошибки AssertionError при проверке состояния
- Состояние не содержит ожидаемых данных

#### Решения:
1. Проверить, что обработчик правильно обновляет состояние
2. Добавить логирование для отладки изменений состояния
3. Проверить формат обновления состояния (словарь или именованные аргументы)

### Проблема: Ошибки при работе с YAML-сценариями

#### Симптомы:
- Ошибки при загрузке YAML-файла
- Неправильное выполнение шагов сценария

#### Решения:
1. Проверить синтаксис YAML-файла
2. Убедиться, что все обязательные поля указаны
3. Проверить соответствие типов данных (строки, числа, логические значения)