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
        if "wenzhong" in self.model_name.lower() or "baichuan" in self.model_name.lower():
            return self._create_chinese_prompt(character, desc_text, use_description)
        elif "qwen" in self.model_name.lower():
            return self._create_qwen_prompt(character, desc_text, use_description)
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
        """Создает промпт для моделей Qwen."""
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


#     def _create_mistral_prompt(self, character, desc_text, use_description):
#             """Создает промпт для моделей Mistral."""
#             if use_description:
#                 return f"""<s>[INST] Создай краткий перевод (максимум 5 слов) для китайского слова/иероглифа: {character}

# Вот подробное описание этого слова на русском:
# {desc_text}

# Дай только сам перевод, максимум 5 слов, без дополнительных пояснений. [/INST]"""
#             else:
#                 return f"""<s>[INST] Переведи китайское слово/иероглиф на русский язык: {character}

# Дай только сам перевод, максимум 5 слов, без дополнительных пояснений. [/INST]"""
     
#     def _create_mistral_prompt(self, character, desc_text, use_description):
#         """Создает промпт для моделей Mistral."""
#         if use_description:
#             return f"""<s>[INST] Переведи китайское слово "{character}" на русский язык.

# Описание слова:
# {desc_text}

# Дай только краткий перевод, максимум 5 слов, без объяснений. [/INST]

# Перевод:"""
#         else:
#             return f"""<s>[INST] Переведи китайское слово "{character}" на русский язык.

# Дай только краткий перевод, максимум 5 слов, без объяснений. [/INST]

# Перевод:"""
    
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
    # Удаляем служебные токены различных моделей
    cleanup_tokens = [
        "<|im_start|>", "<|im_end|>", "<s>", "</s>", "[INST]", "[/INST]",
        "assistant", "user", "system", "<|endoftext|>", "ST]"
    ]
    
    for token in cleanup_tokens:
        response_text = response_text.replace(token, "")
    
    # Для моделей Qwen извлекаем текст после последнего system/user/assistant
    if "qwen" in model_name.lower():
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
