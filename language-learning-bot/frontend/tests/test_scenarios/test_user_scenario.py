"""
Примеры использования BotTestFramework для тестирования Telegram-бота
с загрузкой сценариев из YAML-файлов.
"""

import os
import pytest
from ..bot_test_framework import (
    create_test_scenario,
    load_scenario_from_dict,
    load_yaml_scenario
)

# Путь к директории с файлами сценариев
SCENARIOS_DIR = os.path.join(os.path.dirname(__file__), "scenarios")

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