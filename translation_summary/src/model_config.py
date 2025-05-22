#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Конфигурация доступных моделей для перевода китайских слов.
"""

# Словарь доступных моделей
AVAILABLE_MODELS = {
    # АКТИВНЫЕ МОДЕЛИ - дают хорошие результаты
    
    # Qwen2.5 модели (рекомендуемые для китайского языка) - стабильная серия
    "qwen2.5-7b": "Qwen/Qwen2.5-7B-Instruct",     # хорошее качество, средняя скорость
    "qwen2.5-14b": "Qwen/Qwen2.5-14B-Instruct",   # лучшее качество (требует 24+ ГБ памяти)
    # "qwen2.5-32b": "Qwen/Qwen2.5-32B-Instruct",   # очень хорошее качество (требует 48+ ГБ памяти)
    # "qwen2.5-72b": "Qwen/Qwen2.5-72B-Instruct",   # топовое качество (требует 80+ ГБ памяти)
    
    # Qwen3 модели (новейшие, 2025) - стабильные, post-trained (аналог Instruct)
    "qwen3-8b": "Qwen/Qwen3-8B",                   # новейшая архитектура с thinking mode
    "qwen3-14b": "Qwen/Qwen3-14B",                 # очень хорошее качество с thinking mode  
    # "qwen3-32b": "Qwen/Qwen3-32B",                 # топовая модель с thinking mode
    
    # MBart модели (быстрые модели перевода)
    "mbart-50": "facebook/mbart-large-50-one-to-many-mmt",  # результат лучше среднего, много ошибок, зато очень быстро
    
    # ЗАКОММЕНТИРОВАННЫЕ МОДЕЛИ - оставляем для справки, но не используем
    
    # Qwen2 (старая серия) - заменена на Qwen2.5
    # "qwen2-7b": "Qwen/Qwen2-7B-Instruct",        # заменена на qwen2.5-7b
    # "qwen2-72b": "Qwen/Qwen2-72B-Instruct",      # заменена на qwen2.5-72b
    
    # результат хороший, но долго
    # "mistral-7b": "mistralai/Mistral-7B-Instruct-v0.2", 

    # остальные модели выдают слабые результаты
    # "mbart-cc25": "facebook/mbart-large-cc25",               # альтернативная версия MBart
    # "qwen2-1.5b": "Qwen/Qwen2-1.5B-Instruct",
    # "bloom-7b1": "bigscience/bloom-7b1",
    # "bloom-3b": "bigscience/bloom-3b",
    # "mgpt": "ai-forever/mGPT",
    # "llama3.1-8b": "meta-llama/Llama-3.1-8B-Instruct",
    # "falcon-7b": "tiiuae/falcon-7b-instruct",
    
    # Русские модели
    # "saiga2-7b": "IlyaGusev/saiga2_7b",
    # "rugpt3-ai": "ai-forever/rugpt3large_based_on_gpt2",
    # "rugpt3-sber": "sberbank-ai/rugpt3large_based_on_gpt2",
    
    # Модели для перевода (seq2seq)
    # "nllb-600m": "facebook/nllb-200-distilled-600M",
    # "nllb-1.3b": "facebook/nllb-200-1.3B",
    # "m2m100": "facebook/m2m100_1.2B",
    # "opus-mt-zh-en": "Helsinki-NLP/opus-mt-zh-en",
    
    # Дополнительные модели для китайского языка
    # "bloomz-7b": "bigscience/bloomz-7b1",
    # "wenzhong": "IDEA-CCNL/Wenzhong2.0-GPT2-3.5B-chinese",
    # "baichuan-7b": "baichuan-inc/Baichuan2-7B-Base"
}

# Словарь типов моделей (разделяем модели на causal LM и seq2seq)
MODEL_TYPES = {
    # АКТИВНЫЕ МОДЕЛИ
    # Qwen2.5 серия
    "qwen2.5-7b": "causal",
    "qwen2.5-14b": "causal", 
    "qwen2.5-32b": "causal",
    "qwen2.5-72b": "causal",
    
    # Qwen3 серия
    "qwen3-8b": "causal",
    "qwen3-14b": "causal",
    "qwen3-32b": "causal",
    
    # MBart серия
    "mbart-50": "seq2seq",
    "mbart-cc25": "seq2seq",
    
    # ЗАКОММЕНТИРОВАННЫЕ МОДЕЛИ
    "qwen2-7b": "causal",
    "qwen2-1.5b": "causal", 
    "bloom-7b1": "causal",
    "bloom-3b": "causal",
    "mgpt": "causal",
    "llama3-8b": "causal",
    "mistral-7b": "causal",
    "falcon-7b": "causal",
    
    # Русские модели
    "saiga2-7b": "causal",
    "rugpt3-ai": "causal",
    "rugpt3-sber": "causal",
    
    # Модели seq2seq для перевода
    "nllb-600m": "seq2seq",
    "nllb-1.3b": "seq2seq",
    "m2m100": "seq2seq",
    "opus-mt-zh-en": "seq2seq",
    
    # Дополнительные китайские модели
    "bloomz-7b": "causal",
    "wenzhong": "causal",
    "baichuan-7b": "causal",
}

# Модели, требующие trust_remote_code=True
TRUST_REMOTE_CODE_MODELS = [
    "baichuan-7b",
    "wenzhong", 
    "saiga2-7b"
]

# Модели, требующие много видеопамяти (в ГБ)
GPU_MEMORY_REQUIREMENTS = {
    # Qwen2.5 серия
    "qwen2.5-7b": 16,        # 7B модель
    "qwen2.5-14b": 24,       # 14B модель  
    "qwen2.5-32b": 48,       # 32B модель
    "qwen2.5-72b": 80,       # 72B модель (требует несколько GPU)
    
    # Qwen3 серия (более эффективные)
    "qwen3-8b": 16,          # 8B модель с улучшенной архитектурой
    "qwen3-14b": 24,         # 14B модель
    "qwen3-32b": 48,         # 32B модель с thinking mode
    
    # MBart серия (seq2seq, более эффективные)
    "mbart-50": 8,           # seq2seq модель
    "mbart-cc25": 8,         # seq2seq модель
}

# Рекомендуемые модели по качеству (от лучших к хорошим)
RECOMMENDED_MODELS = {
    "best_quality": ["qwen3-32b", "qwen2.5-72b", "qwen2.5-32b"],          # Лучшее качество
    "balanced": ["qwen3-14b", "qwen2.5-14b", "qwen3-8b", "qwen2.5-7b"],   # Баланс качества и скорости  
    "fast": ["mbart-50", "mbart-cc25"]                                     # Быстрые переводы
}

def get_available_models():
    """
    Возвращает список доступных моделей.
    
    Returns:
        dict: Словарь доступных моделей
    """
    return AVAILABLE_MODELS

def get_model_type(model_name):
    """
    Возвращает тип модели (causal или seq2seq).
    
    Args:
        model_name (str): Название модели
        
    Returns:
        str: Тип модели
    """
    return MODEL_TYPES.get(model_name, "causal")

def needs_trust_remote_code(model_name):
    """
    Проверяет, нужен ли параметр trust_remote_code для модели.
    
    Args:
        model_name (str): Название модели
        
    Returns:
        bool: True если нужен trust_remote_code
    """
    return any(pattern in model_name.lower() for pattern in TRUST_REMOTE_CODE_MODELS)

def get_gpu_memory_requirement(model_name):
    """
    Возвращает примерное требование к видеопамяти для модели.
    
    Args:
        model_name (str): Название модели
        
    Returns:
        int: Требуемая видеопамять в ГБ
    """
    return GPU_MEMORY_REQUIREMENTS.get(model_name, 8)  # По умолчанию 8 ГБ

def get_recommended_models_by_gpu(gpu_memory_gb):
    """
    Возвращает рекомендуемые модели в зависимости от объема видеопамяти.
    
    Args:
        gpu_memory_gb (int): Объем видеопамяти в ГБ
        
    Returns:
        list: Список рекомендуемых моделей
    """
    recommended = []
    for model_name in AVAILABLE_MODELS.keys():
        if get_gpu_memory_requirement(model_name) <= gpu_memory_gb:
            recommended.append(model_name)
    return recommended

def get_recommended_models_by_category(category="balanced"):
    """
    Возвращает рекомендуемые модели по категории.
    
    Args:
        category (str): Категория ('best_quality', 'balanced', 'fast')
        
    Returns:
        list: Список рекомендуемых моделей
    """
    return RECOMMENDED_MODELS.get(category, [])

def get_model_info(model_name):
    """
    Возвращает подробную информацию о модели.
    
    Args:
        model_name (str): Название модели
        
    Returns:
        dict: Информация о модели
    """
    return {
        "hf_name": AVAILABLE_MODELS.get(model_name, "Unknown"),
        "type": get_model_type(model_name),
        "gpu_memory_gb": get_gpu_memory_requirement(model_name),
        "needs_trust_remote_code": needs_trust_remote_code(model_name),
        "series": "qwen3" if "qwen3" in model_name else 
                 "qwen2.5" if "qwen2.5" in model_name else
                 "mbart" if "mbart" in model_name else "other"
    }
