"""
Bot Test Framework - модуль для исполнения сценариев из структур данных.
"""

import os
import yaml
from typing import Dict, List, Any, Union, Optional


def execute_scenario_steps(scenario, steps: List[Dict[str, Any]]):
    """
    Добавляет шаги сценария тестирования из структуры данных
    
    Args:
        scenario: Объект сценария тестирования (BotTestScenario)
        steps: Список шагов в виде словарей
    
    Returns:
        Дополненный сценарий с шагами
        
    Example:
        scenario_steps = [
            {
                "type": "command",
                "name": "settings",
                "asserts": [
                    {
                        "type": "message_contains",
                        "text": "Настройки процесса обучения"
                    }
                ]
            },
            {
                "type": "callback",
                "data": "settings_toggle_skip_marked",
                "asserts": [
                    {
                        "type": "message_contains",
                        "text": "Настройки успешно обновлены"
                    },
                    {
                        "type": "state_contains",
                        "data": ("skip_marked", True)
                    }
                ]
            }
        ]
        
        execute_scenario_steps(scenario, scenario_steps)
    """
    for i, step in enumerate(steps):
        # Получаем имя шага или формируем его из типа и индекса
        step_name = step.get("name", f"{step['type']} #{i+1}")
        
        # Обработка шагов по типу
        if step["type"] == "command":
            scenario.add_command(step["name"], step.get("args", ""), step_name)
        elif step["type"] == "message":
            scenario.add_message(step["text"], step_name)
        elif step["type"] == "callback":
            scenario.add_callback(step["data"], step_name)
        elif step["type"] == "state_update":
            # Обрабатываем state_update особым образом - через API для обновления состояния
            # в YAML-файле продолжаем поддерживать этот формат, но внутри преобразуем в вызов
            # метода update_data для объекта FSMContext
            # Добавляем действие по прямому обновлению состояния через assert_state_contains
            for key, value in step["data"].items():
                scenario.assert_state_contains(key, value, step_name)
                
        # Обработка проверок если они есть
        if "asserts" in step:
            for j, assertion in enumerate(step["asserts"]):
                assertion_name = f"{step_name} - Проверка #{j+1}"
                if assertion["type"] == "message_contains":
                    scenario.assert_message_contains(assertion["text"], 
                                                  assertion.get("position", -1),
                                                  assertion_name)
                elif assertion["type"] == "state_contains":
                    key, value = assertion["data"]
                    scenario.assert_state_contains(key, value, assertion_name)
                elif assertion["type"] == "keyboard_contains":
                    scenario.assert_keyboard_contains(
                        button_text=assertion.get("button_text"),
                        callback_data=assertion.get("callback_data"),
                        should_exist=assertion.get("should_exist", True),
                        step_name=assertion_name
                    )
                elif assertion["type"] == "keyboard_not_contains":
                    scenario.assert_keyboard_contains(
                        button_text=assertion.get("button_text"),
                        callback_data=assertion.get("callback_data"),
                        should_exist=False,
                        step_name=assertion_name
                    )
                elif assertion["type"] == "keyboard_button_count":
                    scenario.assert_keyboard_button_count(
                        expected_count=assertion.get("count"),
                        step_name=assertion_name
                    )
    
    return scenario


def load_scenario_from_dict(scenario_creator, scenario_data: Dict[str, Any]):
    """
    Создает сценарий из словаря с описанием сценария
    
    Args:
        scenario_creator: Функция для создания сценария (create_test_scenario)
        scenario_data: Словарь с описанием сценария
        
    Returns:
        Объект сценария с добавленными шагами
        
    Example:
        scenario_data = {
            "name": "Loaded Scenario",
            "user_id": 123456789,
            "api_mock": "common",  # "common" или "study" или "errors" или пользовательская функция
            "auto_setup": True,
            "steps": [...]
        }
        
        scenario = load_scenario_from_dict(create_test_scenario, scenario_data)
    """
    # Создаем сценарий на основе загруженных данных
    scenario = scenario_creator(
        name=scenario_data["name"],
        user_id=scenario_data.get("user_id", 12345)
    )
    
    # Настраиваем API мок
    if "api_mock" in scenario_data:
        if scenario_data["api_mock"] == "common":
            scenario.with_common_api_mock()
        elif scenario_data["api_mock"] == "study":
            scenario.with_study_api_mock()
        elif scenario_data["api_mock"] == "errors":
            scenario.with_error_api_mock()
    
    # Настраиваем auto_setup
    if "auto_setup" in scenario_data:
        scenario.with_auto_setup(scenario_data["auto_setup"])
    
    # Применяем шаги к сценарию
    if "steps" in scenario_data:
        execute_scenario_steps(scenario, scenario_data["steps"])
    
    return scenario


def load_yaml_scenario(filename: str) -> Dict[str, Any]:
    """
    Загружает сценарий из YAML-файла
    
    Args:
        filename: Имя файла или полный путь к файлу сценария
        
    Returns:
        Словарь с данными сценария
        
    Raises:
        FileNotFoundError: Если файл не найден
        
    Example:
        scenario_data = load_yaml_scenario("settings_toggle.yaml")
        scenario = load_scenario_from_dict(create_test_scenario, scenario_data)
    """
    # Проверяем существование файла
    if not os.path.exists(filename):
        raise FileNotFoundError(f"Файл сценария {filename} не найден")
    
    # Загружаем сценарий из YAML файла
    with open(filename, 'r', encoding='utf-8') as file:
        return yaml.safe_load(file)