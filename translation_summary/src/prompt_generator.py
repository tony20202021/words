#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Модуль для генерации промптов для различных типов моделей.
"""

import logging

logger = logging.getLogger(__name__)

class PromptGenerator:
    """Класс для генерации промптов для различных моделей."""
    
    def __init__(self, model_name, model_type):
        self.model_name = model_name
        self.model_type = model_type
    
    def create_prompt(self, character, descriptions, use_description=True):
        """
        Создает промпт для языковой модели.
        
        Args:
            character (str): Китайский иероглиф или слово
            descriptions (list): Список строк с описаниями
            use_description (bool): Использовать ли описание в промпте
            
        Returns:
            str: Промпт для модели
        """
        # Для моделей seq2seq нет необходимости создавать сложный промпт
        if self.model_type == "seq2seq":
            return character
        
        # Подготавливаем текст описаний
        desc_text = self._prepare_descriptions(descriptions, use_description)
        
        # Генерируем промпт в зависимости от модели
        if "qwen3" in self.model_name.lower():
            return self._create_qwen3_prompt(character, desc_text, use_description)
        elif "qwen2.5" in self.model_name.lower() or "qwen2" in self.model_name.lower():
            return self._create_qwen_prompt(character, desc_text, use_description)
        elif "wenzhong" in self.model_name.lower() or "baichuan" in self.model_name.lower():
            return self._create_chinese_prompt(character, desc_text, use_description)
        elif "bloom" in self.model_name.lower():
            return self._create_bloom_prompt(character, desc_text, use_description)
        elif "llama" in self.model_name.lower():
            return self._create_llama_prompt(character, desc_text, use_description)
        elif "mistral" in self.model_name.lower():
            return self._create_mistral_prompt(character, desc_text, use_description)
        else:
            return self._create_universal_prompt(character, desc_text, use_description)
    
    def _prepare_descriptions(self, descriptions, use_description):
        """Подготавливает текст описаний."""
        if not use_description:
            return ""
        
        # Для китайских моделей ограничиваем количество описаний
        if "wenzhong" in self.model_name.lower() or "baichuan" in self.model_name.lower():
            # Берем только первые 3 описания для экономии токенов
            limited_descriptions = descriptions[:3] if len(descriptions) > 3 else descriptions
            return "\n".join([f"- {desc[:100]}" for desc in limited_descriptions])
        else:
            return "\n".join([f"- {desc}" for desc in descriptions])
    
    def _is_complex_character(self, character, descriptions):
        """
        Определяет, является ли иероглиф сложным для перевода.
        Для Qwen3 - помогает выбрать thinking mode.
        """
        # Сложным считается иероглиф, если:
        # 1. Состоит из нескольких символов
        # 2. Имеет много описаний
        # 3. Описания длинные и сложные
        
        if len(character) > 2:  # Многосимвольное слово
            return True
            
        if len(descriptions) > 3:  # Много значений
            return True
            
        # Проверяем сложность описаний
        total_desc_length = sum(len(desc) for desc in descriptions)
        if total_desc_length > 500:  # Длинные описания
            return True
            
        return False
    
    def _create_qwen3_prompt(self, character, desc_text, use_description):
        """Создает промпт для моделей Qwen3 с поддержкой thinking mode."""
        
        # Определяем, нужен ли thinking mode
        thinking_control = ""
        if use_description:
            is_complex = self._is_complex_character(character, desc_text.split('\n') if desc_text else [])
            if is_complex:
                thinking_control = "/think "  # Включаем thinking mode для сложных случаев
            else:
                thinking_control = "/no_think "  # Быстрый ответ для простых случаев
        else:
            thinking_control = "/no_think "  # Без описания всегда быстро
        
        if use_description:
            messages = [
                {
                    "role": "system", 
                    "content": "Ты - эксперт-синолог и профессиональный переводчик. Твоя специализация - создание точных и кратких переводов китайских иероглифов на русский язык. Ты умеешь выделять главное значение из сложных описаний и создавать лаконичные, но содержательные переводы."
                },
                {
                    "role": "user", 
                    "content": f"""{thinking_control}Переведи китайский иероглиф/слово: {character}

Контекст (подробное описание на русском):
{desc_text}

Требования:
- Максимум 5 слов в переводе
- Выбери самое важное и частое значение
- Перевод должен быть понятным русскоговорящему
- Только сам перевод, никаких пояснений

Перевод:"""
                }
            ]
        else:
            messages = [
                {
                    "role": "system",
                    "content": "Ты - эксперт по китайскому языку. Создавай краткие точные переводы китайских иероглифов на русский язык."
                },
                {
                    "role": "user",
                    "content": f"""{thinking_control}Переведи китайский иероглиф/слово: {character}

Требования:
- Максимум 5 слов
- Самое основное значение
- Только перевод, без объяснений

Перевод:"""
                }
            ]
        
        # Преобразуем в строку (для совместимости с текущим кодом)
        prompt_parts = []
        for msg in messages:
            if msg["role"] == "system":
                prompt_parts.append(f"System: {msg['content']}")
            elif msg["role"] == "user":
                prompt_parts.append(f"User: {msg['content']}")
        
        return "\n\n".join(prompt_parts) + "\n\nAssistant: "
    
    def _create_chinese_prompt(self, character, desc_text, use_description):
        """Создает промпт для китайских моделей (Wenzhong, Baichuan)."""
        if use_description:
            return f"""请将中文词语/字符翻译成俄语: {character}

这个词的详细描述（俄语）:
{desc_text}

简短翻译（最多5个单词）: """
        else:
            return f"""请将中文词语/字符翻译成俄语: {character}

简短翻译（最多5个单词）: """
    
    def _create_qwen_prompt(self, character, desc_text, use_description):
        """Создает промпт для моделей Qwen2/Qwen2.5 (старый формат)."""
        if use_description:
            return f"""<|im_start|>system
Ты - лингвист-синолог, специализирующийся на китайском языке и переводах. Твоя задача - создать краткий и точный перевод китайского слова или иероглифа на русский язык.
<|im_end|>

<|im_start|>user
Мне нужен краткий перевод (не более 5 слов) китайского слова/иероглифа: {character}

Вот подробное описание этого слова на русском:
{desc_text}

Создай очень краткий перевод (максимум 5 слов), который точно передает основное значение и функцию этого китайского слова. Не нужно объяснений, только сам перевод.
<|im_end|>

<|im_start|>assistant
"""
        else:
            return f"""<|im_start|>system
Ты - лингвист-синолог, специализирующийся на китайском языке и переводах. Твоя задача - создать краткий и точный перевод китайского слова или иероглифа на русский язык.
<|im_end|>

<|im_start|>user
Переведи китайское слово/иероглиф на русский язык: {character}

Дай краткий перевод (не более 5 слов). Только сам перевод, без объяснений.
<|im_end|>

<|im_start|>assistant
"""
    
    def _create_bloom_prompt(self, character, desc_text, use_description):
        """Создает промпт для моделей BLOOM."""
        if use_description:
            return f"""Я - профессиональный переводчик с китайского на русский. 

Задача: создать краткий перевод (не более 5 слов) для китайского слова/иероглифа "{character}".

Подробное описание слова:
{desc_text}

Мой краткий перевод (максимум 5 слов): """
        else:
            return f"""Я - профессиональный переводчик с китайского на русский. 

Задача: перевести китайское слово/иероглиф "{character}" на русский язык.

Мой краткий перевод (максимум 5 слов): """
    
    def _create_llama_prompt(self, character, desc_text, use_description):
        """Создает промпт для моделей LLaMA."""
        if use_description:
            return f"""<s>[INST] <<SYS>>
Ты - профессиональный лингвист, специализирующийся на китайском языке. Ты создаешь краткие и точные переводы китайских слов на русский язык.
<</SYS>>

Создай краткий перевод (не более 5 слов) для китайского слова/иероглифа: {character}

Вот подробное описание этого слова на русском:
{desc_text}

Дай только сам перевод без объяснений и не более 5 слов. [/INST]"""
        else:
            return f"""<s>[INST] <<SYS>>
Ты - профессиональный лингвист, специализирующийся на китайском языке. Ты создаешь краткие и точные переводы китайских слов на русский язык.
<</SYS>>

Переведи китайское слово/иероглиф на русский язык: {character}

Дай только сам перевод без объяснений и не более 5 слов. [/INST]"""

    def _create_mistral_prompt(self, character, desc_text, use_description):
        """Создает промпт для моделей Mistral."""
        if use_description:
            return f"""<s>[INST] Создай краткий перевод (максимум 5 слов) для китайского слова/иероглифа: {character}

Вот подробное описание этого слова на русском:
{desc_text}

Дай только сам перевод, максимум 5 слов, без дополнительных пояснений. [/INST]"""
        else:
            return f"""<s>[INST] Переведи китайское слово/иероглиф на русский язык: {character}

Дай только сам перевод, максимум 5 слов, без дополнительных пояснений. [/INST]"""
    
    def _create_universal_prompt(self, character, desc_text, use_description):
        """Создает универсальный промпт для остальных моделей."""
        if use_description:
            return f"""Задача: создать краткий перевод (не более 5 слов) для китайского слова/иероглифа "{character}".

Подробное описание слова:
{desc_text}

Краткий перевод (максимум 5 слов): """
        else:
            return f"""Задача: перевести китайское слово/иероглиф "{character}" на русский язык.

Краткий перевод (максимум 5 слов): """

def process_response(response_text, model_name):
    """
    Обрабатывает ответ модели для извлечения перевода.
    
    Args:
        response_text (str): Ответ модели
        model_name (str): Название модели
        
    Returns:
        str: Очищенный перевод
    """
    # Специальная обработка для Qwen3 (может содержать thinking блоки)
    if "qwen3" in model_name.lower():
        response_text = _process_qwen3_response(response_text)
    
    # Удаляем служебные токены различных моделей
    cleanup_tokens = [
        "<|im_start|>", "<|im_end|>", "<s>", "</s>", "[INST]", "[/INST]",
        "assistant", "user", "system", "<|endoftext|>", "ST]"
    ]
    
    for token in cleanup_tokens:
        response_text = response_text.replace(token, "")
    
    # Для моделей Qwen2/2.5 извлекаем текст после последнего system/user/assistant
    if "qwen2" in model_name.lower() and "qwen3" not in model_name.lower():
        parts = response_text.split("<|im_start|>assistant")
        if len(parts) > 1:
            response_text = parts[-1]
    
    # Для моделей Mistral дополнительная очистка
    if "mistral" in model_name.lower():
        # Убираем остатки инструкций
        response_text = response_text.replace("Дай только сам перевод", "")
        response_text = response_text.replace("максимум 5 слов", "")
        response_text = response_text.replace("без дополнительных пояснений", "")
        response_text = response_text.replace("без объяснений", "")
        
        # Если есть двоеточие, берем текст после него
        if ":" in response_text:
            parts = response_text.split(":")
            if len(parts) > 1:
                response_text = parts[-1].strip()
    
    # Удаляем лишние пробелы и переносы строк
    response_text = response_text.strip()
    
    # Возьмем только первую строку текста (часто содержит основной ответ)
    if "\n" in response_text:
        response_text = response_text.split("\n")[0]
    
    # Удаляем лишние знаки препинания в начале и конце
    response_text = response_text.strip(".,;:!?-")
    
    # Ограничиваем длину до 5 слов
    words = response_text.split()
    if len(words) > 5:
        response_text = " ".join(words[:5])
    
    # Финальная очистка
    response_text = response_text.strip()
    
    return response_text

def _process_qwen3_response(response_text):
    """
    Специальная обработка ответов Qwen3 с thinking блоками.
    
    Args:
        response_text (str): Ответ модели Qwen3
        
    Returns:
        str: Очищенный ответ без thinking блоков
    """
    # Удаляем thinking блоки
    import re
    
    # Убираем блоки <think>...</think>
    response_text = re.sub(r'<think>.*?</think>', '', response_text, flags=re.DOTALL)
    
    # Убираем управляющие токены thinking mode
    response_text = response_text.replace("/think", "")
    response_text = response_text.replace("/no_think", "")
    
    # Ищем текст после "Перевод:" или аналогичных маркеров
    markers = ["Перевод:", "перевод:", "Ответ:", "ответ:", "Translation:", "Answer:"]
    for marker in markers:
        if marker in response_text:
            parts = response_text.split(marker)
            if len(parts) > 1:
                response_text = parts[-1].strip()
                break
    
    return response_text
    