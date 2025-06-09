Семантический анализ иероглифов
как это делается?

Отличный вопрос! Семантический анализ иероглифов - это ключевой компонент для создания осмысленных промптов. Вот как это можно реализовать:

1. Источники данных для анализа
Unicode Database
python
import unicodedata

def get_unicode_info(character: str) -> dict:
    """Базовая информация из Unicode"""
    return {
        "name": unicodedata.name(character, "UNKNOWN"),
        "category": unicodedata.category(character),
        "block": unicodedata.name(character).split()[0] if unicodedata.name(character) != "UNKNOWN" else None
    }

# Пример для 火:
# {"name": "CJK UNIFIED IDEOGRAPH-706B", "category": "Lo", "block": "CJK"}
Unihan Database (самый богатый источник)
python
class UnihanDatabase:
    def __init__(self):
        # Загружаем Unihan данные (можно скачать с unicode.org)
        self.unihan_data = self._load_unihan_readings()
        self.unihan_meanings = self._load_unihan_meanings()
        self.unihan_variants = self._load_unihan_variants()
    
    def get_character_info(self, char: str) -> dict:
        """Получает полную информацию о иероглифе"""
        code_point = f"U+{ord(char):04X}"
        
        return {
            "definition": self.unihan_meanings.get(code_point, {}).get("kDefinition", ""),
            "mandarin": self.unihan_readings.get(code_point, {}).get("kMandarin", ""),
            "cantonese": self.unihan_readings.get(code_point, {}).get("kCantonese", ""),
            "japanese_on": self.unihan_readings.get(code_point, {}).get("kJapaneseOn", ""),
            "japanese_kun": self.unihan_readings.get(code_point, {}).get("kJapaneseKun", ""),
            "korean": self.unihan_readings.get(code_point, {}).get("kKorean", ""),
            "total_strokes": self.unihan_data.get(code_point, {}).get("kTotalStrokes", ""),
            "radical": self.unihan_data.get(code_point, {}).get("kRSUnicode", ""),
            "frequency": self.unihan_data.get(code_point, {}).get("kFrequency", "")
        }

# Пример для 火:
# {
#   "definition": "fire, flame; burn; anger, rage",
#   "mandarin": "huǒ",
#   "total_strokes": "4",
#   "radical": "86.0",
#   "frequency": "1"
# }
2. Радикальный анализ
Kangxi Radicals Database
python
class RadicalAnalyzer:
    def __init__(self):
        self.kangxi_radicals = self._load_kangxi_radicals()
        self.radical_meanings = {
            "火": {"meaning": "fire", "visual_elements": ["flames", "heat", "burning"], "colors": ["red", "orange", "yellow"]},
            "水": {"meaning": "water", "visual_elements": ["waves", "flow", "liquid"], "colors": ["blue", "cyan", "transparent"]},
            "木": {"meaning": "tree", "visual_elements": ["trunk", "branches", "leaves"], "colors": ["brown", "green"]},
            "金": {"meaning": "metal", "visual_elements": ["shine", "reflection", "hardness"], "colors": ["silver", "gold", "metallic"]},
            "土": {"meaning": "earth", "visual_elements": ["ground", "soil", "solid"], "colors": ["brown", "yellow", "earthy"]},
            # ... 214 радикалов Kangxi
        }
    
    def analyze_radicals(self, character: str) -> dict:
        """Анализирует радикалы в иероглифе"""
        radicals = self._decompose_to_radicals(character)
        
        analysis = {
            "primary_radical": None,
            "all_radicals": [],
            "semantic_elements": [],
            "visual_associations": [],
            "color_associations": []
        }
        
        for radical in radicals:
            if radical in self.radical_meanings:
                radical_info = self.radical_meanings[radical]
                analysis["all_radicals"].append({
                    "radical": radical,
                    "meaning": radical_info["meaning"],
                    "visual_elements": radical_info["visual_elements"],
                    "colors": radical_info["colors"]
                })
                
                # Собираем все визуальные ассоциации
                analysis["visual_associations"].extend(radical_info["visual_elements"])
                analysis["color_associations"].extend(radical_info["colors"])
        
        return analysis

# Пример для 烧 (жечь):
# {
#   "all_radicals": [
#     {"radical": "火", "meaning": "fire", "visual_elements": ["flames", "heat"], "colors": ["red", "orange"]},
#     {"radical": "尧", "meaning": "high", "visual_elements": ["height", "elevation"], "colors": []}
#   ],
#   "visual_associations": ["flames", "heat", "height", "elevation"],
#   "color_associations": ["red", "orange"]
# }
Идеографическое описание последовательностей (IDS)
python
class IDSAnalyzer:
    """Анализ структуры иероглифа через Ideographic Description Sequences"""
    
    def __init__(self):
        self.ids_database = self._load_ids_database()
        self.composition_types = {
            "⿰": "left_right",      # 左右结构
            "⿱": "top_bottom",      # 上下结构  
            "⿲": "left_middle_right", # 左中右结构
            "⿳": "top_middle_bottom", # 上中下结构
            "⿴": "surround",        # 全包围结构
            "⿵": "surround_three",  # 上三包围
            "⿶": "surround_bottom", # 下三包围
            "⿷": "surround_left",   # 左三包围
        }
    
    def analyze_structure(self, character: str) -> dict:
        """Анализирует структурную композицию иероглифа"""
        ids = self._get_ids_sequence(character)
        
        if not ids:
            return {"structure": "unknown", "components": []}
        
        structure_type = ids[0] if ids[0] in self.composition_types else "unknown"
        components = self._parse_ids_components(ids[1:])
        
        return {
            "structure": self.composition_types.get(structure_type, "unknown"),
            "ids_sequence": ids,
            "components": components,
            "layout_hints": self._get_layout_hints(structure_type)
        }
    
    def _get_layout_hints(self, structure_type: str) -> dict:
        """Подсказки для визуальной композиции"""
        layout_hints = {
            "left_right": {"split": "vertical", "emphasis": "balanced"},
            "top_bottom": {"split": "horizontal", "emphasis": "top_heavy"},
            "surround": {"split": "center_focus", "emphasis": "outer_frame"},
        }
        return layout_hints.get(structure_type, {})

# Пример для 明 (яркий):
# {
#   "structure": "left_right",
#   "ids_sequence": "⿰日月", 
#   "components": ["日", "月"],
#   "layout_hints": {"split": "vertical", "emphasis": "balanced"}
# }
3. Семантические базы данных
CC-CEDICT для значений
python
class CEDICTAnalyzer:
    def __init__(self):
        self.cedict = self._load_cedict_database()
    
    def get_meanings(self, character: str) -> list:
        """Получает все значения иероглифа из CEDICT"""
        meanings = []
        
        for entry in self.cedict:
            if character in entry["simplified"] or character in entry["traditional"]:
                meanings.extend(entry["definitions"])
        
        return list(set(meanings))  # Убираем дубликаты

# Пример для 火:
# ["fire", "flame", "burn", "anger", "rage", "ammunition"]
HanziCraft для этимологии
python
class EtymologyAnalyzer:
    def __init__(self):
        self.etymology_db = self._load_etymology_database()
    
    def get_etymology(self, character: str) -> dict:
        """Получает этимологическую информацию"""
        etymology = self.etymology_db.get(character, {})
        
        return {
            "origin": etymology.get("origin", ""),
            "pictographic": etymology.get("is_pictographic", False),
            "ideographic": etymology.get("is_ideographic", False), 
            "original_meaning": etymology.get("original_meaning", ""),
            "evolution": etymology.get("character_evolution", []),
            "visual_origin": etymology.get("visual_origin_description", "")
        }

# Пример для 火:
# {
#   "origin": "pictographic",
#   "pictographic": true,
#   "original_meaning": "flames rising from burning wood",
#   "visual_origin": "stylized representation of flickering flames"
# }
4. Контекстуальный анализ
Анализ частотности и контекста
python
class ContextAnalyzer:
    def __init__(self):
        self.word_frequency = self._load_frequency_data()
        self.collocation_data = self._load_collocation_data()
        self.domain_classifications = self._load_domain_data()
    
    def analyze_context(self, character: str) -> dict:
        """Анализирует контекстуальное использование"""
        
        # Найти общие слова с этим иероглифом
        common_words = self._find_common_words(character)
        
        # Определить семантические домены
        domains = self._classify_domains(common_words)
        
        # Найти типичные коллокации
        collocations = self._get_collocations(character)
        
        return {
            "frequency_rank": self.word_frequency.get(character, 9999),
            "common_words": common_words[:10],  # Топ 10
            "semantic_domains": domains,
            "typical_collocations": collocations,
            "usage_context": self._determine_usage_context(domains)
        }

# Пример для 火:
# {
#   "frequency_rank": 150,
#   "common_words": ["火车", "火箭", "生火", "火灾"],
#   "semantic_domains": ["transportation", "disaster", "cooking", "anger"],
#   "usage_context": ["daily_life", "technology", "emotions"]
# }
5. Визуальные ассоциации
Мультимодальный анализ
python
class VisualAssociationAnalyzer:
    def __init__(self):
        self.shape_patterns = self._load_shape_patterns()
        self.color_associations = self._load_color_associations()
        self.texture_patterns = self._load_texture_patterns()
        self.motion_patterns = self._load_motion_patterns()
    
    def analyze_visual_properties(self, character: str, meaning: str) -> dict:
        """Анализирует визуальные свойства на основе значения"""
        
        visual_analysis = {
            "primary_colors": [],
            "secondary_colors": [],
            "textures": [],
            "shapes": [],
            "motion": [],
            "lighting": [],
            "atmosphere": []
        }
        
        # Анализ по ключевым словам значения
        meaning_words = meaning.lower().split()
        
        for word in meaning_words:
            if word in self.color_associations:
                visual_analysis["primary_colors"].extend(self.color_associations[word])
            
            if word in self.texture_patterns:
                visual_analysis["textures"].extend(self.texture_patterns[word])
            
            if word in self.motion_patterns:
                visual_analysis["motion"].extend(self.motion_patterns[word])
        
        # Убираем дубликаты
        for key in visual_analysis:
            visual_analysis[key] = list(set(visual_analysis[key]))
        
        return visual_analysis

# Пример конфигурации ассоциаций:
color_associations = {
    "fire": ["red", "orange", "yellow", "bright"],
    "water": ["blue", "cyan", "transparent", "clear"],
    "wood": ["brown", "green", "natural"],
    "metal": ["silver", "gold", "metallic", "shiny"],
    "earth": ["brown", "yellow", "muddy", "earthy"]
}

texture_patterns = {
    "fire": ["flickering", "dancing", "glowing", "bright"],
    "water": ["flowing", "rippling", "smooth", "wet"],
    "rough": ["coarse", "bumpy", "uneven"],
    "smooth": ["polished", "sleek", "glossy"]
}
6. Главный семантический анализатор
Объединяющий класс
python
class CharacterSemanticAnalyzer:
    def __init__(self):
        self.unihan = UnihanDatabase()
        self.radical_analyzer = RadicalAnalyzer()
        self.ids_analyzer = IDSAnalyzer()
        self.cedict = CEDICTAnalyzer()
        self.etymology = EtymologyAnalyzer()
        self.context = ContextAnalyzer()
        self.visual = VisualAssociationAnalyzer()
    
    def analyze_character(self, character: str) -> dict:
        """Полный семантический анализ иероглифа"""
        
        # Базовая информация
        basic_info = self.unihan.get_character_info(character)
        
        # Структурный анализ
        radical_analysis = self.radical_analyzer.analyze_radicals(character)
        structure_analysis = self.ids_analyzer.analyze_structure(character)
        
        # Семантический анализ
        meanings = self.cedict.get_meanings(character)
        etymology_info = self.etymology.get_etymology(character)
        context_info = self.context.analyze_context(character)
        
        # Визуальный анализ
        primary_meaning = meanings[0] if meanings else basic_info.get("definition", "")
        visual_properties = self.visual.analyze_visual_properties(character, primary_meaning)
        
        # Объединяем все в единую структуру
        return {
            "character": character,
            "basic_info": basic_info,
            "meanings": meanings,
            "primary_meaning": primary_meaning,
            
            "structure": {
                "radicals": radical_analysis,
                "composition": structure_analysis,
                "etymology": etymology_info
            },
            
            "context": context_info,
            "visual_properties": visual_properties,
            
            # Сводные данные для промпта
            "prompt_elements": self._extract_prompt_elements(
                meanings, radical_analysis, visual_properties, context_info
            )
        }
    
    def _extract_prompt_elements(self, meanings, radicals, visual, context) -> dict:
        """Извлекает ключевые элементы для построения промпта"""
        return {
            "core_concepts": meanings[:3],  # Топ 3 значения
            "visual_elements": visual["shapes"] + visual["textures"],
            "colors": visual["primary_colors"] + visual["secondary_colors"],
            "atmosphere": visual["atmosphere"],
            "semantic_domains": context["semantic_domains"],
            "cultural_context": context["usage_context"]
        }

# Полный анализ для 火:
# {
#   "character": "火",
#   "primary_meaning": "fire",
#   "meanings": ["fire", "flame", "burn", "anger"],
#   "structure": {
#     "radicals": [{"radical": "火", "meaning": "fire", "colors": ["red", "orange"]}],
#     "composition": {"structure": "pictographic"},
#     "etymology": {"pictographic": true, "visual_origin": "flames"}
#   },
#   "visual_properties": {
#     "primary_colors": ["red", "orange", "yellow"],
#     "textures": ["flickering", "dancing", "glowing"],
#     "motion": ["upward", "dancing", "consuming"]
#   },
#   "prompt_elements": {
#     "core_concepts": ["fire", "flame", "burn"],
#     "visual_elements": ["flickering", "dancing", "glowing"],
#     "colors": ["red", "orange", "yellow"],
#     "atmosphere": ["warm", "bright", "energetic"]
#   }
# }
7. Интеграция с промпт-билдером
Использование семантического анализа
python
class SemanticPromptBuilder:
    def __init__(self):
        self.semantic_analyzer = CharacterSemanticAnalyzer()
    
    def build_contextual_prompt(self, character: str, translation: str, style: str) -> str:
        """Строит промпт на основе семантического анализа"""
        
        analysis = self.semantic_analyzer.analyze_character(character)
        prompt_elements = analysis["prompt_elements"]
        
        # Базовый промпт
        base_prompt = f"A {style} style illustration representing {translation}"
        
        # Добавляем семантические элементы
        visual_elements = ", ".join(prompt_elements["visual_elements"][:3])
        colors = ", ".join(prompt_elements["colors"][:3])
        atmosphere = ", ".join(prompt_elements["atmosphere"][:2])
        
        enhanced_prompt = f"{base_prompt}, featuring {visual_elements}, with {colors} colors, {atmosphere} atmosphere"
        
        # Добавляем культурный контекст
        if "traditional" in prompt_elements.get("cultural_context", []):
            enhanced_prompt += ", traditional Chinese art style"
        
        return enhanced_prompt

# Пример для 火, "fire", "comic":
# "A comic style illustration representing fire, featuring flickering, dancing, glowing, 
#  with red, orange, yellow colors, warm, bright atmosphere, traditional Chinese art style"
Этот подход обеспечивает глубокое понимание иероглифов и создание контекстуально точных промптов для AI генерации!