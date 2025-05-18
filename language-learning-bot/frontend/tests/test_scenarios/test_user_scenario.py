"""
Примеры использования BotTestFramework для тестирования Telegram-бота
с загрузкой сценариев из YAML-файлов.
"""

import os
import pytest
from unittest.mock import AsyncMock
from ..bot_test_framework import (
    create_test_scenario,
    load_scenario_from_dict,
    load_yaml_scenario
)

# Путь к директории с файлами сценариев
SCENARIOS_DIR = os.path.join(os.path.dirname(__file__), "scenarios")

# Настройки мока для работы с несколькими языками
def setup_multilanguage_api_mock(api_client: AsyncMock):
    """Настраивает мок API для тестирования работы с несколькими языками."""
    # Базовая настройка из стандартного мока
    from ..bot_test_framework.api_mock_setup import setup_api_mock_for_common_scenarios
    setup_api_mock_for_common_scenarios(api_client)
    
    # Словарь для хранения настроек по языкам
    language_settings = {
        "eng": {"start_word": 1, "skip_marked": False, "use_check_date": True, "show_hints": True, "show_debug": False},
        "fra": {"start_word": 1, "skip_marked": False, "use_check_date": True, "show_hints": True, "show_debug": False}
    }
    
    # Переопределение метода для получения настроек
    async def get_user_language_settings(user_id, language_id):
        return {
            "success": True,
            "status": 200,
            "result": language_settings.get(language_id, {"start_word": 1, "skip_marked": False, "use_check_date": True, "show_hints": True, "show_debug": False}),
            "error": None
        }
    
    # Переопределение метода для обновления настроек
    async def update_user_language_settings(user_id, language_id, settings):
        language_settings[language_id] = settings
        return {
            "success": True,
            "status": 200,
            "result": settings,
            "error": None
        }
    
    # Добавляем второй язык в список языков
    api_client.get_languages.return_value = {
        "success": True,
        "status": 200,
        "result": [
            {"id": "eng", "name_ru": "Английский", "name_foreign": "English"},
            {"id": "fra", "name_ru": "Французский", "name_foreign": "Français"}
        ],
        "error": None
    }
    
    # Применяем кастомные методы
    api_client.get_user_language_settings.side_effect = get_user_language_settings
    api_client.update_user_language_settings.side_effect = update_user_language_settings

# Настройки мока для проверки интервалов повторения
def setup_intervals_api_mock(api_client: AsyncMock):
    """Настраивает мок API для тестирования интервалов повторения."""
    # Базовая настройка из стандартного мока
    from ..bot_test_framework.api_mock_setup import setup_api_mock_for_study_testing
    setup_api_mock_for_study_testing(api_client)
    
    # Счетчик вызовов update_user_word_data для возврата разных интервалов
    calls = {"count": 0}
    
    # Переопределение метода update_user_word_data для симуляции интервалов
    async def dynamic_update_word_data(user_id, word_id, data):
        calls["count"] += 1
        
        # Если устанавливается оценка 1 (слово известно)
        if "score" in data and data["score"] == 1:
            # Вычисляем интервал в зависимости от номера вызова
            if calls["count"] == 1:
                check_interval = 1
            elif calls["count"] == 2:
                check_interval = 2
            elif calls["count"] == 3:
                check_interval = 4
            elif calls["count"] == 4:
                check_interval = 8
            else:
                check_interval = 16
                
            return {
                "success": True,
                "status": 200,
                "result": {
                    "word_id": word_id,
                    "score": 1,
                    "check_interval": check_interval,
                    "next_check_date": f"2025-05-{12 + check_interval}T00:00:00.000Z",
                    "is_skipped": False
                },
                "error": None
            }
        elif "score" in data and data["score"] == 0:
            # Если слово не известно, сбрасываем интервал
            return {
                "success": True,
                "status": 200,
                "result": {
                    "word_id": word_id,
                    "score": 0,
                    "check_interval": 0,
                    "next_check_date": None,
                    "is_skipped": False
                },
                "error": None
            }
        else:
            # Базовый случай
            return {
                "success": True,
                "status": 200,
                "result": {
                    "word_id": word_id,
                    "score": 0,
                    "check_interval": 0,
                    "next_check_date": None,
                    "is_skipped": False
                },
                "error": None
            }
    
    # Применяем кастомный метод
    api_client.update_user_word_data.side_effect = dynamic_update_word_data

# Настройки мока для тестирования пропуска слов
def setup_skip_words_api_mock(api_client: AsyncMock):
    """Настраивает мок API для тестирования пропуска слов."""
    # Базовая настройка из стандартного мока
    from ..bot_test_framework.api_mock_setup import setup_api_mock_for_study_testing
    setup_api_mock_for_study_testing(api_client)
    
    # Словарь для хранения состояния слов
    words_state = {
        "word123": {"is_skipped": False},
        "word124": {"is_skipped": False}
    }
    
    # Счетчик вызовов get_study_words
    calls = {"count": 0}
    
    # Переопределение метода update_user_word_data для обновления флага пропуска
    async def dynamic_update_word_data(user_id, word_id, data):
        if "is_skipped" in data:
            words_state[word_id]["is_skipped"] = data["is_skipped"]
            
        return {
            "success": True,
            "status": 200,
            "result": {
                "word_id": word_id,
                "score": 0,
                "check_interval": 0,
                "next_check_date": None,
                "is_skipped": words_state[word_id]["is_skipped"]
            },
            "error": None
        }
    
    # Переопределение метода get_study_words для возврата разных списков слов
    async def dynamic_get_study_words(user_id, language_id, params, limit):
        calls["count"] += 1
        
        # Первый вызов - возвращаем все слова
        if calls["count"] == 1:
            return {
                "success": True,
                "status": 200,
                "result": [
                    {
                        "id": "word123",
                        "language_id": "eng",
                        "word_foreign": "house",
                        "translation": "дом",
                        "transcription": "haʊs",
                        "word_number": 10,
                        "user_word_data": {"is_skipped": words_state["word123"]["is_skipped"]}
                    },
                    {
                        "id": "word124",
                        "language_id": "eng",
                        "word_foreign": "car",
                        "translation": "машина",
                        "transcription": "kɑr",
                        "word_number": 11,
                        "user_word_data": {"is_skipped": words_state["word124"]["is_skipped"]}
                    }
                ],
                "error": None
            }
        else:
            # Последующие вызовы - фильтруем пропущенные слова
            result = []
            words = [
                {
                    "id": "word123",
                    "language_id": "eng",
                    "word_foreign": "house",
                    "translation": "дом",
                    "transcription": "haʊs",
                    "word_number": 10,
                    "user_word_data": {"is_skipped": words_state["word123"]["is_skipped"]}
                },
                {
                    "id": "word124",
                    "language_id": "eng",
                    "word_foreign": "car",
                    "translation": "машина",
                    "transcription": "kɑr",
                    "word_number": 11,
                    "user_word_data": {"is_skipped": words_state["word124"]["is_skipped"]}
                }
            ]
            
            # Если включен пропуск помеченных слов, фильтруем
            if params.get("skip_marked"):
                result = [word for word in words if not word["user_word_data"]["is_skipped"]]
            else:
                result = words
                
            return {
                "success": True,
                "status": 200,
                "result": result,
                "error": None
            }
    
    # Применяем кастомные методы
    api_client.update_user_word_data.side_effect = dynamic_update_word_data
    api_client.get_study_words.side_effect = dynamic_get_study_words

# Настройки мока для проверки статистики
def setup_statistics_api_mock(api_client: AsyncMock):
    """Настраивает мок API для тестирования отслеживания статистики."""
    # Базовая настройка из стандартного мока
    from ..bot_test_framework.api_mock_setup import setup_api_mock_for_study_testing
    setup_api_mock_for_study_testing(api_client)
    
    # Статистика изучения
    stats = {
        "words_studied": 0,
        "words_known": 0
    }
    
    # Переопределение метода update_user_word_data для обновления статистики
    async def dynamic_update_word_data(user_id, word_id, data):
        if "score" in data:
            # Увеличиваем счетчик изученных слов
            stats["words_studied"] += 1
            
            # Если оценка 1, увеличиваем счетчик известных слов
            if data["score"] == 1:
                stats["words_known"] += 1
            
        return {
            "success": True,
            "status": 200,
            "result": {
                "word_id": word_id,
                "score": data.get("score", 0),
                "check_interval": 1 if data.get("score") == 1 else 0,
                "next_check_date": "2025-05-12T00:00:00.000Z" if data.get("score") == 1 else None,
                "is_skipped": False
            },
            "error": None
        }
    
    # Переопределение метода get_user_progress для возврата статистики
    async def dynamic_get_user_progress(user_id, language_id):
        return {
            "success": True,
            "status": 200,
            "result": {
                'user_id': user_id,
                'language_id': language_id,
                'language_name_ru': 'Английский',
                'language_name_foreign': 'English',
                'total_words': 1000,
                'words_studied': stats["words_studied"],
                'words_known': stats["words_known"],
                'words_skipped': 0,
                'progress_percentage': (stats["words_known"] / 1000) * 100 if stats["words_known"] > 0 else 0,
                'last_study_date': "2025-05-12T00:00:00.000Z"
            },
            "error": None
        }
    
    # Применяем кастомные методы
    api_client.update_user_word_data.side_effect = dynamic_update_word_data
    api_client.get_user_progress.side_effect = dynamic_get_user_progress

# Существующие тесты
@pytest.mark.asyncio
async def test_start_help_settings_scenario():
    """
    Тестирование сценария взаимодействия: /start -> /help -> /settings -> изменение start_word
    Загружает сценарий из YAML-файла
    """
    # Формируем путь к файлу сценария
    scenario_path = os.path.join(SCENARIOS_DIR, "start_help_settings.yaml")
    
    # Загружаем сценарий из файла с использованием функции из фреймворка
    scenario_data = load_yaml_scenario(scenario_path)
    
    # Создаем сценарий на основе загруженных данных
    scenario = load_scenario_from_dict(create_test_scenario, scenario_data)
    
    # Выполняем сценарий
    await scenario.execute()

@pytest.mark.asyncio
async def test_settings_toggle_scenario():
    """
    Тестирование сценария: /settings -> включение/выключение режимов
    Загружает сценарий из YAML-файла
    """
    # Формируем путь к файлу сценария
    scenario_path = os.path.join(SCENARIOS_DIR, "settings_toggle.yaml")
    
    # Загружаем сценарий из файла с использованием функции из фреймворка
    scenario_data = load_yaml_scenario(scenario_path)
    
    # Создаем сценарий на основе загруженных данных
    scenario = load_scenario_from_dict(create_test_scenario, scenario_data)
    
    # Выполняем сценарий
    await scenario.execute()

@pytest.mark.asyncio
async def test_settings_preserve_language_scenario():
    """
    Тестирование сценария: выбор языка -> изменение начального слова -> проверка, что язык сохранен
    Проверяет, что сценарий не теряет выбранный язык при изменении настроек.
    Загружает сценарий из YAML-файла.
    """
    # Формируем путь к файлу сценария
    scenario_path = os.path.join(SCENARIOS_DIR, "settings_preserve_language.yaml")
    
    # Загружаем сценарий из файла с использованием функции из фреймворка
    scenario_data = load_yaml_scenario(scenario_path)
    
    # Создаем сценарий на основе загруженных данных
    scenario = load_scenario_from_dict(create_test_scenario, scenario_data)
    
    # Выполняем сценарий
    await scenario.execute()

@pytest.mark.asyncio
async def test_study_word_learning_scenario():
    """
    Тестирование сценария изучения слов.
    Загружает сценарий из YAML-файла.
    """
    # Формируем путь к файлу сценария
    scenario_path = os.path.join(SCENARIOS_DIR, "study_word_learning.yaml")
    
    # Загружаем сценарий из файла с использованием функции из фреймворка
    scenario_data = load_yaml_scenario(scenario_path)
    
    # Создаем сценарий на основе загруженных данных
    scenario = load_scenario_from_dict(create_test_scenario, scenario_data)
    
    # Выполняем сценарий
    await scenario.execute()

@pytest.mark.asyncio
async def test_hint_creation_scenario():
    """
    Тестирование сценария создания и редактирования подсказок.
    Загружает сценарий из YAML-файла.
    """
    # Формируем путь к файлу сценария
    scenario_path = os.path.join(SCENARIOS_DIR, "hint_creation.yaml")
    
    # Загружаем сценарий из файла с использованием функции из фреймворка
    try:
        scenario_data = load_yaml_scenario(scenario_path)
        
        # Создаем сценарий на основе загруженных данных
        scenario = load_scenario_from_dict(create_test_scenario, scenario_data)
        
        # Выполняем сценарий
        await scenario.execute()
    except FileNotFoundError:
        pytest.skip("Файл сценария hint_creation.yaml не найден. Создайте его для тестирования")

@pytest.mark.asyncio
async def test_hint_types_scenario():
    """
    Тестирование сценария работы с различными типами подсказок.
    Загружает сценарий из YAML-файла.
    """
    # Формируем путь к файлу сценария
    scenario_path = os.path.join(SCENARIOS_DIR, "hint_types.yaml")
    
    # Загружаем сценарий из файла с использованием функции из фреймворка
    try:
        scenario_data = load_yaml_scenario(scenario_path)
        
        # Создаем сценарий на основе загруженных данных
        scenario = load_scenario_from_dict(create_test_scenario, scenario_data)
        
        # Выполняем сценарий
        await scenario.execute()
    except FileNotFoundError:
        pytest.skip("Файл сценария hint_types.yaml не найден. Создайте его для тестирования")

# Новые тесты

@pytest.mark.asyncio
async def test_cancel_operations_scenario():
    """
    Тестирование сценария отмены операций.
    Проверяет, что команда /cancel корректно прерывает текущие операции.
    """
    # Формируем путь к файлу сценария
    scenario_path = os.path.join(SCENARIOS_DIR, "cancel_operations.yaml")
    
    # Загружаем сценарий из файла с использованием функции из фреймворка
    try:
        scenario_data = load_yaml_scenario(scenario_path)
        
        # Создаем сценарий на основе загруженных данных
        scenario = load_scenario_from_dict(create_test_scenario, scenario_data)
        
        # Выполняем сценарий
        await scenario.execute()
    except FileNotFoundError:
        pytest.skip("Файл сценария cancel_operations.yaml не найден. Создайте его для тестирования")

@pytest.mark.asyncio
async def test_boundary_values_scenario():
    """
    Тестирование сценария проверки граничных значений.
    Проверяет обработку некорректного ввода и граничных значений.
    """
    # Формируем путь к файлу сценария
    scenario_path = os.path.join(SCENARIOS_DIR, "boundary_values.yaml")
    
    # Загружаем сценарий из файла с использованием функции из фреймворка
    try:
        scenario_data = load_yaml_scenario(scenario_path)
        
        # Создаем сценарий на основе загруженных данных
        scenario = load_scenario_from_dict(create_test_scenario, scenario_data)
        
        # Выполняем сценарий
        await scenario.execute()
    except FileNotFoundError:
        pytest.skip("Файл сценария boundary_values.yaml не найден. Создайте его для тестирования")

@pytest.mark.asyncio
async def test_api_errors_scenario():
    """
    Тестирование сценария обработки ошибок API.
    Проверяет корректную обработку ошибок от API.
    """
    # Формируем путь к файлу сценария
    scenario_path = os.path.join(SCENARIOS_DIR, "api_errors.yaml")
    
    # Загружаем сценарий из файла с использованием функции из фреймворка
    try:
        scenario_data = load_yaml_scenario(scenario_path)
        
        # Создаем сценарий на основе загруженных данных
        scenario = load_scenario_from_dict(create_test_scenario, scenario_data)
        
        # Выполняем сценарий
        await scenario.execute()
    except FileNotFoundError:
        pytest.skip("Файл сценария api_errors.yaml не найден. Создайте его для тестирования")

@pytest.mark.asyncio
async def test_multi_session_learning_scenario():
    """
    Тестирование сценария обучения в течение нескольких сессий.
    Проверяет сохранение прогресса между сессиями.
    """
    # Формируем путь к файлу сценария
    scenario_path = os.path.join(SCENARIOS_DIR, "multi_session_learning.yaml")
    
    # Загружаем сценарий из файла с использованием функции из фреймворка
    try:
        scenario_data = load_yaml_scenario(scenario_path)
        
        # Создаем сценарий на основе загруженных данных
        scenario = load_scenario_from_dict(create_test_scenario, scenario_data)
        
        # Применяем кастомный мок API
        scenario.with_api_mock(setup_statistics_api_mock)
        
        # Выполняем сценарий
        await scenario.execute()
    except FileNotFoundError:
        pytest.skip("Файл сценария multi_session_learning.yaml не найден. Создайте его для тестирования")

@pytest.mark.asyncio
async def test_skip_words_scenario():
    """
    Тестирование сценария пропуска слов.
    Проверяет, что помеченные слова пропускаются при соответствующей настройке.
    """
    # Формируем путь к файлу сценария
    scenario_path = os.path.join(SCENARIOS_DIR, "skip_words.yaml")
    
    # Загружаем сценарий из файла с использованием функции из фреймворка
    try:
        scenario_data = load_yaml_scenario(scenario_path)
        
        # Создаем сценарий на основе загруженных данных
        scenario = load_scenario_from_dict(create_test_scenario, scenario_data)
        
        # Применяем кастомный мок API
        scenario.with_api_mock(setup_skip_words_api_mock)
        
        # Выполняем сценарий
        await scenario.execute()
    except FileNotFoundError:
        pytest.skip("Файл сценария skip_words.yaml не найден. Создайте его для тестирования")

@pytest.mark.asyncio
async def test_statistics_tracking_scenario():
    """
    Тестирование сценария отслеживания статистики.
    Проверяет корректное обновление статистики изучения.
    """
    # Формируем путь к файлу сценария
    scenario_path = os.path.join(SCENARIOS_DIR, "statistics_tracking.yaml")
    
    # Загружаем сценарий из файла с использованием функции из фреймворка
    try:
        scenario_data = load_yaml_scenario(scenario_path)
        
        # Создаем сценарий на основе загруженных данных
        scenario = load_scenario_from_dict(create_test_scenario, scenario_data)
        
        # Применяем кастомный мок API
        scenario.with_api_mock(setup_statistics_api_mock)
        
        # Выполняем сценарий
        await scenario.execute()
    except FileNotFoundError:
        pytest.skip("Файл сценария statistics_tracking.yaml не найден. Создайте его для тестирования")

@pytest.mark.asyncio
async def test_multiple_languages_scenario():
    """
    Тестирование сценария работы с несколькими языками.
    Проверяет отдельные настройки для каждого языка.
    """
    # Формируем путь к файлу сценария
    scenario_path = os.path.join(SCENARIOS_DIR, "multiple_languages.yaml")
    
    # Загружаем сценарий из файла с использованием функции из фреймворка
    try:
        scenario_data = load_yaml_scenario(scenario_path)
        
        # Создаем сценарий на основе загруженных данных
        scenario = load_scenario_from_dict(create_test_scenario, scenario_data)
        
        # Применяем кастомный мок API
        scenario.with_api_mock(setup_multilanguage_api_mock)
        
        # Выполняем сценарий
        await scenario.execute()
    except FileNotFoundError:
        pytest.skip("Файл сценария multiple_languages.yaml не найден. Создайте его для тестирования")

@pytest.mark.asyncio
async def test_debug_mode_scenario():
    """
    Тестирование сценария отладочного режима.
    Проверяет отображение отладочной информации.
    """
    # Формируем путь к файлу сценария
    scenario_path = os.path.join(SCENARIOS_DIR, "debug_mode.yaml")
    
    # Загружаем сценарий из файла с использованием функции из фреймворка
    try:
        scenario_data = load_yaml_scenario(scenario_path)
        
        # Создаем сценарий на основе загруженных данных
        scenario = load_scenario_from_dict(create_test_scenario, scenario_data)
        
        # Выполняем сценарий
        await scenario.execute()
    except FileNotFoundError:
        pytest.skip("Файл сценария debug_mode.yaml не найден. Создайте его для тестирования")

@pytest.mark.asyncio
async def test_hint_command_scenario():
    """
    Тестирование сценария команды /hint.
    Проверяет вывод информации о подсказках.
    """
    # Формируем путь к файлу сценария
    scenario_path = os.path.join(SCENARIOS_DIR, "hint_command.yaml")
    
    # Загружаем сценарий из файла с использованием функции из фреймворка
    try:
        scenario_data = load_yaml_scenario(scenario_path)
        
        # Создаем сценарий на основе загруженных данных
        scenario = load_scenario_from_dict(create_test_scenario, scenario_data)
        
        # Выполняем сценарий
        await scenario.execute()
    except FileNotFoundError:
        pytest.skip("Файл сценария hint_command.yaml не найден. Создайте его для тестирования")

@pytest.mark.asyncio
async def test_repeat_intervals_scenario():
    """
    Тестирование сценария интервалов повторения.
    Проверяет корректное изменение интервалов при изучении слов.
    """
    # Формируем путь к файлу сценария
    scenario_path = os.path.join(SCENARIOS_DIR, "repeat_intervals.yaml")
    
    # Загружаем сценарий из файла с использованием функции из фреймворка
    try:
        scenario_data = load_yaml_scenario(scenario_path)
        
        # Создаем сценарий на основе загруженных данных
        scenario = load_scenario_from_dict(create_test_scenario, scenario_data)
        
        # Применяем кастомный мок API для проверки интервалов
        scenario.with_api_mock(setup_intervals_api_mock)
        
        # Выполняем сценарий
        await scenario.execute()
    except FileNotFoundError:
        pytest.skip("Файл сценария repeat_intervals.yaml не найден. Создайте его для тестирования")
