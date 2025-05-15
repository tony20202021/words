# Руководство по тестированию

## Содержание
1. [Обзор системы тестирования](#обзор-системы-тестирования)
2. [Типы тестов](#типы-тестов)
3. [Запуск тестов](#запуск-тестов)
4. [Написание тестов](#написание-тестов)
5. [Тестирование бота](#тестирование-бота)
6. [Тестирование API](#тестирование-api)
7. [Тестирование с моками](#тестирование-с-моками)
8. [Советы по тестированию](#советы-по-тестированию)

## Обзор системы тестирования

Система тестирования проекта Language Learning Bot основана на фреймворке pytest и поддерживает различные типы тестов:

- Модульные тесты для отдельных компонентов
- Интеграционные тесты для проверки взаимодействия компонентов
- Сценарные тесты для проверки пользовательских сценариев
- Тесты API для проверки интерфейса бэкенда

## Типы тестов

### 1. Модульные тесты

Модульные тесты проверяют отдельные компоненты системы (функции, классы, методы) в изоляции. Для этого часто используются моки для замены внешних зависимостей.

**Расположение**:
- `frontend/tests/utils/` - тесты утилит фронтенда
- `backend/tests/services/` - тесты сервисов бэкенда
- `backend/tests/repositories/` - тесты репозиториев бэкенда

### 2. Интеграционные тесты

Интеграционные тесты проверяют взаимодействие нескольких компонентов системы и их корректную работу вместе.

**Расположение**:
- `frontend/tests/test_handlers/` - тесты обработчиков бота
- `backend/tests/test_api/` - тесты API эндпоинтов

### 3. Сценарные тесты

Сценарные тесты проверяют сценарии использования бота пользователями. Они используют специальный фреймворк для тестирования Telegram-бота.

**Расположение**:
- `frontend/tests/test_scenarios/` - тесты сценариев взаимодействия с ботом
- `frontend/tests/test_scenarios/scenarios/` - YAML-файлы сценариев

### 4. Тесты API

Тесты API проверяют работу REST API бэкенда, включая форматы запросов, ответов и обработку ошибок.

**Расположение**:
- `backend/tests/test_api/` - тесты API эндпоинтов

## Запуск тестов

### Запуск всех тестов

Для запуска всех тестов используйте скрипт `run_tests.sh`:

```bash
# Сделать скрипт исполняемым
chmod +x run_tests.sh

# Запустить все тесты
./run_tests.sh
```

### Запуск тестов для отдельного компонента

```bash
# Запуск только тестов фронтенда
./run_tests.sh --component frontend

# Запуск только тестов бэкенда
./run_tests.sh --component backend
```

### Запуск с отчетом о покрытии кода

```bash
# Запуск с отчетом о покрытии
./run_tests.sh --coverage

# Запуск с HTML-отчетом о покрытии
./run_tests.sh --coverage --html
```

### Запуск конкретного теста или модуля

```bash
# Запуск конкретного теста или модуля
./run_tests.sh --specific frontend/tests/test_main.py

# Запуск конкретного тестового метода
./run_tests.sh --specific frontend/tests/test_main.py::TestMain::test_main_successful_startup
```

### Запуск в режиме отладки

```bash
# Запуск с подробным выводом
./run_tests.sh --verbose
```

## Написание тестов

### Структура теста

Все тесты в проекте используют pytest и следуют общему формату:

```python
import pytest
from unittest.mock import MagicMock, AsyncMock, patch

# Импорт тестируемых модулей
from app.some_module import some_function

# Фикстуры (при необходимости)
@pytest.fixture
def some_fixture():
    # Подготовка данных для теста
    data = {...}
    # Возврат данных
    return data

# Тестовый класс (опционально)
class TestSomeClass:
    
    # Тестовый метод
    @pytest.mark.asyncio  # Для асинхронных тестов
    async def test_some_function(self, some_fixture):
        # Подготовка
        input_data = {...}
        
        # Действие
        result = await some_function(input_data)
        
        # Проверка
        assert result == expected_result
```

### Использование фикстур

Фикстуры в pytest используются для подготовки данных или ресурсов для тестов:

```python
@pytest.fixture
def api_client_mock():
    # Создаем мок API клиента
    client = AsyncMock()
    
    # Настраиваем ответы методов
    client.get_languages.return_value = {
        "success": True,
        "result": [{"id": "eng", "name_ru": "Английский"}]
    }
    
    return client

# Использование фикстуры
@pytest.mark.asyncio
async def test_get_languages(api_client_mock):
    # Тестируемая функция получает мок API клиента
    result = await get_languages_function(api_client_mock)
    
    # Проверки
    assert len(result) == 1
    assert result[0]["name_ru"] == "Английский"
```

### Моки и патчи

Для изоляции тестируемого кода от внешних зависимостей используются моки и патчи:

```python
# Использование патча для замены функции
@patch("app.api.client.APIClient", return_value=AsyncMock())
async def test_with_patched_client(mock_client):
    # Настройка мока
    mock_client.return_value.get_languages.return_value = {
        "success": True,
        "result": [{"id": "eng", "name_ru": "Английский"}]
    }
    
    # Вызов функции, использующей API клиент
    result = await some_function()
    
    # Проверка, что мок был вызван
    mock_client.return_value.get_languages.assert_called_once()
```

## Тестирование бота

### Фреймворк для тестирования бота

Для тестирования Telegram-бота используется специальный фреймворк, который позволяет:

- Моделировать отправку команд и сообщений пользователем
- Моделировать нажатия на inline-кнопки
- Проверять ответы бота
- Проверять состояние FSM

### Создание тестового сценария

#### Вариант 1: Программное создание сценария

```python
@pytest.mark.asyncio
async def test_start_command(bot_test):
    # Настройка мока для API-клиента
    def setup_api_mock(api_client):
        api_client.get_user_by_telegram_id.return_value = {
            "success": True,
            "result": [],
            "error": None
        }
    
    # Создание сценария
    scenario = bot_test(
        name="Start Command Test",
        handler_modules=["app.bot.handlers.user_handlers"],
        user_id=123456789
    ).with_api_mock(setup_api_mock)
    
    # Добавление действий
    scenario.add_command("start")
    scenario.assert_message_contains("Здравствуйте")
    
    # Выполнение сценария
    await scenario.execute()
```

#### Вариант 2: Использование YAML-файлов

Создание YAML-файла сценария (`scenarios/start_command.yaml`):

```yaml
name: Start Command Test
user_id: 123456789
api_mock: common
auto_setup: true
steps:
  - type: command
    name: start
    asserts:
      - type: message_contains
        text: "Здравствуйте"
      - type: message_contains
        text: "Добро пожаловать"
```

Запуск сценария из YAML-файла:

```python
@pytest.mark.asyncio
async def test_start_command_from_yaml():
    # Загрузка сценария из файла
    scenario_path = os.path.join(SCENARIOS_DIR, "start_command.yaml")
    scenario_data = load_yaml_scenario(scenario_path)
    
    # Создание сценария
    scenario = load_scenario_from_dict(create_test_scenario, scenario_data)
    
    # Выполнение сценария
    await scenario.execute()
```

## Тестирование API

### Тестирование API эндпоинтов

Тесты API эндпоинтов проверяют корректную работу бэкенда:

```python
@pytest.mark.asyncio
async def test_get_languages_endpoint(client):
    # Выполнение запроса к API
    response = await client.get("/api/languages")
    
    # Проверка статуса
    assert response.status_code == 200
    
    # Проверка формата ответа
    data = response.json()
    assert "success" in data
    assert data["success"] is True
    assert "result" in data
    assert isinstance(data["result"], list)
```

### Тестирование с использованием тестового клиента

Для тестирования API используется тестовый клиент FastAPI:

```python
@pytest.fixture
async def client():
    # Создание тестового клиента для приложения FastAPI
    app = create_test_app()
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client
```

## Тестирование с моками

### Мокирование API клиента

```python
def setup_api_mock(api_client):
    # Настройка ответа для get_user_by_telegram_id
    api_client.get_user_by_telegram_id.return_value = {
        "success": True,
        "status": 200,
        "result": [{"id": "user123"}],
        "error": None
    }
    
    # Настройка ответа для get_language
    api_client.get_language.return_value = {
        "success": True,
        "status": 200,
        "result": {
            "id": "lang123",
            "name_ru": "Английский",
            "name_foreign": "English"
        },
        "error": None
    }
```

### Мокирование MongoDB

```python
@pytest.fixture
def mongo_mock():
    # Создание мока для MongoDB
    db = MagicMock()
    collection = AsyncMock()
    
    # Настройка ответов
    collection.find_one.return_value = {"_id": "123", "name": "Test"}
    collection.find.return_value.to_list.return_value = [
        {"_id": "123", "name": "Test1"},
        {"_id": "456", "name": "Test2"}
    ]
    
    # Настройка доступа к коллекциям
    db.__getitem__.return_value = collection
    
    return db
```

## Советы по тестированию

1. **Изолируйте тесты**: Каждый тест должен быть независимым и проверять только один аспект функциональности.

2. **Используйте говорящие имена тестов**: Имя теста должно отражать, что именно он проверяет.

3. **Следуйте паттерну AAA** (Arrange-Act-Assert):
   - Arrange - подготовка данных и ресурсов
   - Act - выполнение тестируемого действия
   - Assert - проверка результатов

4. **Тестируйте граничные случаи**: Проверяйте не только стандартные сценарии, но и граничные случаи и обработку ошибок.

5. **Используйте фикстуры для повторного использования кода**: Фикстуры помогают избежать дублирования кода в тестах.

6. **Группируйте связанные тесты**: Используйте классы для группировки связанных тестов.

7. **Включайте тесты в CI/CD**: Автоматическое выполнение тестов при каждом изменении кода помогает рано обнаруживать проблемы.

8. **Периодически проверяйте и обновляйте тесты**: Тесты должны эволюционировать вместе с кодом.

9. **Используйте декларативные сценарии**: Для тестирования бота рекомендуется использовать YAML-файлы сценариев, которые легче поддерживать и обновлять.