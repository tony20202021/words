#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Минимальный тест для выявления проблемы с OpenAI
"""

import sys
import os
import traceback
from pathlib import Path

# Добавляем путь к src
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_step_by_step():
    """Тестируем по шагам, чтобы найти проблему."""
    
    print("🔍 Пошаговая диагностика")
    print("=" * 50)
    
    # Шаг 1: Импорт OpenAI
    try:
        from openai import OpenAI
        print("✅ Шаг 1: OpenAI импортирован")
    except Exception as e:
        print(f"❌ Шаг 1: Ошибка импорта OpenAI: {e}")
        return False
    
    # Шаг 2: Проверка API ключа
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("❌ Шаг 2: OPENAI_API_KEY не установлен")
        return False
    print("✅ Шаг 2: API ключ найден")
    
    # Шаг 3: Импорт конфигурации
    try:
        from model_config import is_openai_model, get_model_type
        print("✅ Шаг 3: model_config импортирован")
        
        # Проверяем функции
        print(f"  is_openai_model('gpt-4o'): {is_openai_model('gpt-4o')}")
        print(f"  get_model_type('gpt-4o'): {get_model_type('gpt-4o')}")
        
    except Exception as e:
        print(f"❌ Шаг 3: Ошибка импорта model_config: {e}")
        traceback.print_exc()
        return False
    
    # Шаг 4: Импорт OpenAI обработчика
    try:
        from openai_handler import OpenAIHandler
        print("✅ Шаг 4: OpenAIHandler импортирован")
    except Exception as e:
        print(f"❌ Шаг 4: Ошибка импорта OpenAIHandler: {e}")
        traceback.print_exc()
        return False
    
    # Шаг 5: Создание OpenAI обработчика
    try:
        handler = OpenAIHandler("gpt-3.5-turbo", api_key=api_key, temperature=0.1)
        print("✅ Шаг 5: OpenAIHandler создан")
    except Exception as e:
        print(f"❌ Шаг 5: Ошибка создания OpenAIHandler: {e}")
        traceback.print_exc()
        return False
    
    # Шаг 6: Импорт LLMTranslator
    try:
        from llm_translator import LLMTranslator
        print("✅ Шаг 6: LLMTranslator импортирован")
    except Exception as e:
        print(f"❌ Шаг 6: Ошибка импорта LLMTranslator: {e}")
        traceback.print_exc()
        return False
    
    # Шаг 7: Создание LLMTranslator
    try:
        print("🧪 Шаг 7: Создание LLMTranslator...")
        translator = LLMTranslator("gpt-3.5-turbo", temperature=0.1)
        print("✅ Шаг 7: LLMTranslator создан")
        
        # Проверяем атрибуты
        print(f"  model_name: {translator.model_name}")
        print(f"  model_type: {translator.model_type}")
        print(f"  has openai_handler: {hasattr(translator, 'openai_handler')}")
        if hasattr(translator, 'openai_handler'):
            print(f"  openai_handler is not None: {translator.openai_handler is not None}")
        
    except Exception as e:
        print(f"❌ Шаг 7: Ошибка создания LLMTranslator: {e}")
        traceback.print_exc()
        return False
    
    # Шаг 8: Тестовый перевод
    try:
        print("🧪 Шаг 8: Тестовый перевод...")
        result = translator.translate("我", ["я", "местоимение"], use_description=False)
        print(f"✅ Шаг 8: Перевод выполнен: '我' -> '{result}'")
    except Exception as e:
        print(f"❌ Шаг 8: Ошибка при переводе: {e}")
        traceback.print_exc()
        return False
    
    # Шаг 9: Статистика
    try:
        print("🧪 Шаг 9: Получение статистики...")
        stats = translator.get_statistics()
        print(f"✅ Шаг 9: Статистика получена: {stats}")
    except Exception as e:
        print(f"❌ Шаг 9: Ошибка при получении статистики: {e}")
        traceback.print_exc()
        return False
    
    print("\n✅ Все шаги успешно пройдены!")
    return True

if __name__ == "__main__":
    success = test_step_by_step()
    if not success:
        print("\n❌ Тест не пройден. Проверьте ошибки выше.")
        sys.exit(1)
    else:
        print("\n🎉 Все работает корректно!")
        sys.exit(0)
        