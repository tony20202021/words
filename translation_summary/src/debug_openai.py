#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Скрипт для диагностики проблем с OpenAI API
"""

import os
import sys
import traceback
from pathlib import Path

# Добавляем путь к пакету
sys.path.append(str(Path(__file__).parent))

def check_openai_library():
    """Проверяет наличие и версию библиотеки OpenAI."""
    try:
        import openai
        print(f"✅ OpenAI библиотека установлена, версия: {openai.__version__}")
        return True
    except ImportError as e:
        print(f"❌ OpenAI библиотека не установлена: {e}")
        print("Установите командой: pip install openai>=1.0.0")
        return False

def check_api_key():
    """Проверяет наличие API ключа."""
    api_key = os.getenv('OPENAI_API_KEY')
    if api_key:
        print(f"✅ OPENAI_API_KEY найден (длина: {len(api_key)})")
        # Проверяем формат ключа
        if api_key.startswith('sk-') and len(api_key) > 20:
            print("✅ Формат API ключа выглядит корректно")
            return api_key
        else:
            print("⚠️  Формат API ключа может быть некорректным")
            return api_key
    else:
        print("❌ OPENAI_API_KEY не установлен")
        print("Установите командой: export OPENAI_API_KEY=your_key")
        return None

def test_openai_client(api_key):
    """Тестирует создание OpenAI клиента."""
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        print("✅ OpenAI клиент создан успешно")
        return client
    except Exception as e:
        print(f"❌ Ошибка при создании OpenAI клиента: {e}")
        traceback.print_exc()
        return None

def test_openai_handler():
    """Тестирует наш OpenAI обработчик."""
    try:
        # Пробуем различные варианты импорта
        try:
            from src.openai_handler import OpenAIHandler
        except ImportError:
            try:
                from openai_handler import OpenAIHandler
            except ImportError:
                # Добавляем текущий каталог в путь
                current_dir = Path(__file__).parent
                sys.path.insert(0, str(current_dir))
                from openai_handler import OpenAIHandler
        
        api_key = check_api_key()
        if not api_key:
            return False
        
        print("\n🧪 Тестирование OpenAI обработчика...")
        handler = OpenAIHandler("gpt-3.5-turbo", api_key=api_key, temperature=0.1)
        print("✅ OpenAI обработчик создан успешно")
        
        # Тестовый перевод
        print("🧪 Тестовый перевод...")
        result = handler.translate("我", ["я", "местоимение первого лица"], use_description=False)
        print(f"✅ Тестовый перевод успешен: '我' -> '{result}'")
        
        # Статистика
        stats = handler.get_statistics()
        print(f"📊 Статистика: {stats}")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка в OpenAI обработчике: {e}")
        traceback.print_exc()
        return False

def test_llm_translator():
    """Тестирует основной LLM переводчик с OpenAI."""
    try:
        # Пробуем различные варианты импорта
        try:
            from src.llm_translator import LLMTranslator
        except ImportError:
            try:
                from llm_translator import LLMTranslator
            except ImportError:
                # Добавляем родительский каталог в путь
                parent_dir = Path(__file__).parent.parent
                sys.path.insert(0, str(parent_dir))
                from src.llm_translator import LLMTranslator
        
        api_key = check_api_key()
        if not api_key:
            return False
        
        print("\n🧪 Тестирование LLM переводчика с OpenAI...")
        translator = LLMTranslator("gpt-3.5-turbo", temperature=0.1)
        print("✅ LLM переводчик создан успешно")
        
        # Тестовый перевод
        print("🧪 Тестовый перевод через LLM переводчик...")
        result = translator.translate("我", ["я", "местоимение первого лица"], use_description=False)
        print(f"✅ Тестовый перевод успешен: '我' -> '{result}'")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка в LLM переводчике: {e}")
        traceback.print_exc()
        return False

def main():
    """Основная функция диагностики."""
    print("🔍 Диагностика OpenAI интеграции")
    print("=" * 50)
    
    # 1. Проверяем библиотеку
    if not check_openai_library():
        return 1
    
    # 2. Проверяем API ключ
    api_key = check_api_key()
    if not api_key:
        return 1
    
    # 3. Тестируем клиент
    client = test_openai_client(api_key)
    if not client:
        return 1
    
    # 4. Тестируем наш обработчик
    if not test_openai_handler():
        return 1
    
    # 5. Тестируем основной переводчик
    if not test_llm_translator():
        return 1
    
    print("\n✅ Все тесты прошли успешно!")
    print("OpenAI интеграция работает корректно.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
    