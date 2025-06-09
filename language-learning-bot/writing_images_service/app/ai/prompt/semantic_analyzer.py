"""
Semantic Analyzer - семантический анализ китайских иероглифов.
Анализирует значения, этимологию, радикалы и визуальные ассоциации.
"""

import time
import asyncio
from typing import Dict, Any, Optional, List, Tuple, Union
from dataclasses import dataclass
import logging
import unicodedata
import re

from app.utils.logger import get_module_logger
from app.ai.prompt.radical_analyzer import RadicalAnalyzer
from app.ai.prompt.etymology_analyzer import EtymologyAnalyzer
from app.ai.prompt.visual_association_analyzer import VisualAssociationAnalyzer

logger = get_module_logger(__name__)


@dataclass
class SemanticConfig:
    """Конфигурация семантического анализа"""
    # Источники данных
    enable_unihan_database: bool = True
    enable_radical_analysis: bool = True
    enable_etymology_analysis: bool = True
    enable_visual_associations: bool = True
    
    # Языковые настройки
    target_language: str = "en"
    include_pronunciations: bool = True
    include_variants: bool = True
    
    # Глубина анализа
    analysis_depth: str = "standard"  # minimal, standard, full, comprehensive
    max_meanings: int = 5
    max_associations: int = 10
    
    # Уверенность и фильтрация
    min_confidence_threshold: float = 0.3
    filter_obscure_meanings: bool = True


@dataclass
class SemanticResult:
    """Результат семантического анализа"""
    success: bool
    character: str = ""
    analysis_data: Optional[Dict[str, Any]] = None
    
    # Метаданные анализа
    analysis_time_ms: int = 0
    sources_used: List[str] = None
    confidence_scores: Dict[str, float] = None
    
    # Ошибки и предупреждения
    error_message: Optional[str] = None
    warnings: List[str] = None
    limitations: List[str] = None
    
    def __post_init__(self):
        """Инициализация после создания"""
        if self.sources_used is None:
            self.sources_used = []
        if self.confidence_scores is None:
            self.confidence_scores = {}
        if self.warnings is None:
            self.warnings = []
        if self.limitations is None:
            self.limitations = []


class SemanticAnalyzer:
    """
    Семантический анализатор китайских иероглифов.
    Объединяет анализ радикалов, этимологии и визуальных ассоциаций.
    """
    
    def __init__(self, config: Optional[SemanticConfig] = None):
        """
        Инициализация семантического анализатора.
        
        Args:
            config: Конфигурация анализа
        """
        self.config = config or SemanticConfig()
        
        # Компоненты анализа
        self.radical_analyzer = RadicalAnalyzer()
        self.etymology_analyzer = EtymologyAnalyzer()
        self.visual_analyzer = VisualAssociationAnalyzer()
        
        # Базы данных
        self._unihan_data = {}
        self._frequency_data = {}
        self._variant_data = {}
        
        
        # Инициализация
        asyncio.create_task(self._initialize_databases())
        
        logger.info("SemanticAnalyzer initialized")
    
    async def analyze_character(
        self,
        character: str,
        include_etymology: bool = True,
        include_radical_analysis: bool = True,
        include_visual_associations: bool = True,
        include_cultural_context: bool = True,
        analysis_depth: Optional[str] = None
    ) -> SemanticResult:
        """
        Выполняет полный семантический анализ иероглифа.
        
        Args:
            character: Иероглиф для анализа
            include_etymology: Включать этимологический анализ
            include_radical_analysis: Включать анализ радикалов
            include_visual_associations: Включать визуальные ассоциации
            include_cultural_context: Включать культурный контекст
            analysis_depth: Глубина анализа
            
        Returns:
            SemanticResult: Результат семантического анализа
        """
        start_time = time.time()
        
        try:
            # Валидация входных данных
            if not self._validate_character(character):
                return SemanticResult(
                    success=False,
                    character=character,
                    error_message="Invalid character or not a Chinese character"
                )
            
            # Выполняем анализ
            analysis_data = await self._perform_comprehensive_analysis(
                character=character,
                include_etymology=include_etymology,
                include_radical_analysis=include_radical_analysis,
                include_visual_associations=include_visual_associations,
                include_cultural_context=include_cultural_context,
                depth=analysis_depth or self.config.analysis_depth
            )
            
            # Подсчет времени
            analysis_time_ms = int((time.time() - start_time) * 1000)
            
            # Создание результата
            result = SemanticResult(
                success=True,
                character=character,
                analysis_data=analysis_data,
                analysis_time_ms=analysis_time_ms,
                sources_used=self._get_sources_used(analysis_data),
                confidence_scores=self._calculate_confidence_scores(analysis_data)
            )
            
            logger.info(f"Analyzed character '{character}' in {analysis_time_ms}ms")
            
            return result
            
        except Exception as e:
            logger.error(f"Error analyzing character {character}: {e}", exc_info=True)
            
            return SemanticResult(
                success=False,
                character=character,
                error_message=str(e),
                analysis_time_ms=int((time.time() - start_time) * 1000)
            )
    
    async def _perform_comprehensive_analysis(
        self,
        character: str,
        include_etymology: bool,
        include_radical_analysis: bool,
        include_visual_associations: bool,
        include_cultural_context: bool,
        depth: str
    ) -> Dict[str, Any]:
        """
        Выполняет комплексный анализ иероглифа.
        
        Args:
            character: Иероглиф
            include_etymology: Включать этимологию
            include_radical_analysis: Включать анализ радикалов
            include_visual_associations: Включать визуальные ассоциации
            include_cultural_context: Включать культурный контекст
            depth: Глубина анализа
            
        Returns:
            Dict[str, Any]: Результаты анализа
        """
        analysis_data = {}
        
        # 1. Базовая информация о иероглифе
        analysis_data.update(await self._get_basic_character_info(character))
        
        # 2. Унихан данные
        if self.config.enable_unihan_database:
            unihan_data = await self._get_unihan_data(character)
            if unihan_data:
                analysis_data['unihan'] = unihan_data
        
        # 3. Анализ радикалов
        if include_radical_analysis and self.config.enable_radical_analysis:
            radical_data = await self.radical_analyzer.analyze_radicals(character)
            if radical_data.success:
                analysis_data['radicals'] = radical_data.analysis_data
        
        # 4. Этимологический анализ
        if include_etymology and self.config.enable_etymology_analysis:
            etymology_data = await self.etymology_analyzer.analyze_etymology(character)
            if etymology_data.success:
                analysis_data['etymology'] = etymology_data.analysis_data
        
        # 5. Визуальные ассоциации
        if include_visual_associations and self.config.enable_visual_associations:
            visual_data = await self.visual_analyzer.analyze_visual_associations(character)
            if visual_data.success:
                analysis_data['visual_associations'] = visual_data.analysis_data
        
        # 6. Значения и переводы
        meanings_data = await self._extract_meanings(character, analysis_data)
        analysis_data['meanings'] = meanings_data
        
        # 7. Произношения
        if self.config.include_pronunciations:
            pronunciations = await self._extract_pronunciations(character, analysis_data)
            analysis_data['pronunciations'] = pronunciations
        
        # 8. Культурный контекст
        if include_cultural_context:
            cultural_data = await self._analyze_cultural_context(character, analysis_data)
            analysis_data['cultural_context'] = cultural_data
        
        # 9. Семантические домены
        semantic_domains = await self._extract_semantic_domains(character, analysis_data)
        analysis_data['semantic_domains'] = semantic_domains
        
        # 10. Цветовые и текстурные ассоциации
        color_associations = await self._extract_color_associations(character, analysis_data)
        texture_associations = await self._extract_texture_associations(character, analysis_data)
        analysis_data['color_associations'] = color_associations
        analysis_data['texture_associations'] = texture_associations
        
        # 11. Символическое значение
        symbolic_meaning = await self._extract_symbolic_meaning(character, analysis_data)
        if symbolic_meaning:
            analysis_data['symbolic_meaning'] = symbolic_meaning
        
        return analysis_data
    
    async def _get_basic_character_info(self, character: str) -> Dict[str, Any]:
        """
        Получает базовую информацию о иероглифе.
        
        Args:
            character: Иероглиф
            
        Returns:
            Dict[str, Any]: Базовая информация
        """
        info = {
            'character': character,
            'unicode_code': ord(character),
            'unicode_name': unicodedata.name(character, 'UNKNOWN'),
            'unicode_category': unicodedata.category(character),
            'stroke_count': self._estimate_stroke_count(character),
            'is_simplified': self._is_simplified_character(character),
            'is_traditional': self._is_traditional_character(character)
        }
        
        return info
    
    async def _get_unihan_data(self, character: str) -> Optional[Dict[str, Any]]:
        """
        Получает данные из базы Unihan.
        
        Args:
            character: Иероглиф
            
        Returns:
            Optional[Dict[str, Any]]: Данные Unihan
        """
        try:
            # TODO: Интеграция с реальной базой данных Unihan
            # Пока используем заглушку с базовыми данными
            
            unihan_data = {
                'definition': self._get_basic_definition(character),
                'mandarin_reading': self._get_basic_pronunciation(character),
                'cantonese_reading': self._get_basic_cantonese(character),
                'japanese_on': self._get_basic_japanese_on(character),
                'japanese_kun': self._get_basic_japanese_kun(character),
                'korean_reading': self._get_basic_korean(character),
                'total_strokes': self._estimate_stroke_count(character)
            }
            
            # Фильтруем пустые значения
            unihan_data = {k: v for k, v in unihan_data.items() if v}
            
            return unihan_data if unihan_data else None
            
        except Exception as e:
            logger.warning(f"Error getting Unihan data for {character}: {e}")
            return None
    
    async def _extract_meanings(self, character: str, analysis_data: Dict[str, Any]) -> List[str]:
        """
        Извлекает значения иероглифа из различных источников.
        
        Args:
            character: Иероглиф
            analysis_data: Данные анализа
            
        Returns:
            List[str]: Список значений
        """
        meanings = []
        
        # Из Unihan данных
        unihan = analysis_data.get('unihan', {})
        if 'definition' in unihan:
            definition = unihan['definition']
            if isinstance(definition, str):
                # Разбиваем определение на отдельные значения
                meaning_parts = re.split(r'[;,]', definition)
                meanings.extend([part.strip() for part in meaning_parts if part.strip()])
        
        # Из этимологических данных
        etymology = analysis_data.get('etymology', {})
        if 'modern_meanings' in etymology:
            meanings.extend(etymology['modern_meanings'])
        
        # Из анализа радикалов
        radicals = analysis_data.get('radicals', {})
        if 'semantic_contributions' in radicals:
            for contribution in radicals['semantic_contributions']:
                if 'meaning' in contribution:
                    meanings.append(contribution['meaning'])
        
        # Удаляем дубликаты и ограничиваем количество
        unique_meanings = list(dict.fromkeys(meanings))
        return unique_meanings[:self.config.max_meanings]
    
    async def _extract_pronunciations(self, character: str, analysis_data: Dict[str, Any]) -> Dict[str, str]:
        """
        Извлекает произношения иероглифа.
        
        Args:
            character: Иероглиф
            analysis_data: Данные анализа
            
        Returns:
            Dict[str, str]: Произношения по языкам
        """
        pronunciations = {}
        
        # Из Unihan данных
        unihan = analysis_data.get('unihan', {})
        if 'mandarin_reading' in unihan:
            pronunciations['mandarin'] = unihan['mandarin_reading']
        if 'cantonese_reading' in unihan:
            pronunciations['cantonese'] = unihan['cantonese_reading']
        if 'japanese_on' in unihan:
            pronunciations['japanese_on'] = unihan['japanese_on']
        if 'japanese_kun' in unihan:
            pronunciations['japanese_kun'] = unihan['japanese_kun']
        if 'korean_reading' in unihan:
            pronunciations['korean'] = unihan['korean_reading']
        
        return pronunciations
    
    async def _analyze_cultural_context(self, character: str, analysis_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Анализирует культурный контекст иероглифа.
        
        Args:
            character: Иероглиф
            analysis_data: Данные анализа
            
        Returns:
            Dict[str, Any]: Культурный контекст
        """
        cultural_context = {}
        
        # Философские ассоциации
        meanings = analysis_data.get('meanings', [])
        philosophy_keywords = ['wisdom', 'virtue', 'harmony', 'balance', 'peace', 'strength', 'courage']
        
        philosophical_connections = []
        for meaning in meanings:
            for keyword in philosophy_keywords:
                if keyword.lower() in meaning.lower():
                    philosophical_connections.append(keyword)
        
        if philosophical_connections:
            cultural_context['philosophical_associations'] = list(set(philosophical_connections))
        
        # Природные элементы (Wu Xing)
        nature_elements = {
            'fire': ['fire', 'flame', 'burn', 'heat', 'light'],
            'water': ['water', 'river', 'sea', 'rain', 'flow'],
            'wood': ['tree', 'wood', 'forest', 'bamboo', 'plant'],
            'metal': ['metal', 'gold', 'iron', 'weapon', 'tool'],
            'earth': ['earth', 'soil', 'mountain', 'stone', 'ground']
        }
        
        detected_elements = []
        for meaning in meanings:
            meaning_lower = meaning.lower()
            for element, keywords in nature_elements.items():
                if any(keyword in meaning_lower for keyword in keywords):
                    detected_elements.append(element)
        
        if detected_elements:
            cultural_context['wu_xing_elements'] = list(set(detected_elements))
        
        # Социальные роли и отношения
        social_keywords = ['family', 'father', 'mother', 'child', 'friend', 'teacher', 'student', 'king', 'minister']
        social_connections = []
        
        for meaning in meanings:
            meaning_lower = meaning.lower()
            for keyword in social_keywords:
                if keyword in meaning_lower:
                    social_connections.append(keyword)
        
        if social_connections:
            cultural_context['social_associations'] = list(set(social_connections))
        
        # Временные аспекты
        temporal_keywords = ['ancient', 'modern', 'old', 'new', 'past', 'future', 'time', 'season']
        temporal_connections = []
        
        etymology = analysis_data.get('etymology', {})
        if 'historical_period' in etymology:
            temporal_connections.append(etymology['historical_period'])
        
        for meaning in meanings:
            meaning_lower = meaning.lower()
            for keyword in temporal_keywords:
                if keyword in meaning_lower:
                    temporal_connections.append(keyword)
        
        if temporal_connections:
            cultural_context['temporal_associations'] = list(set(temporal_connections))
        
        return cultural_context
    
    async def _extract_semantic_domains(self, character: str, analysis_data: Dict[str, Any]) -> List[str]:
        """
        Извлекает семантические домены иероглифа.
        
        Args:
            character: Иероглиф
            analysis_data: Данные анализа
            
        Returns:
            List[str]: Семантические домены
        """
        domains = []
        meanings = analysis_data.get('meanings', [])
        
        # Определяем семантические домены на основе значений
        domain_mappings = {
            'nature': ['tree', 'water', 'fire', 'earth', 'mountain', 'river', 'sea', 'sky', 'sun', 'moon'],
            'human': ['person', 'man', 'woman', 'child', 'family', 'body', 'heart', 'mind'],
            'emotion': ['love', 'joy', 'anger', 'fear', 'sad', 'happy', 'peace', 'calm'],
            'action': ['walk', 'run', 'see', 'hear', 'speak', 'eat', 'drink', 'work', 'study'],
            'abstract': ['wisdom', 'virtue', 'beauty', 'truth', 'justice', 'freedom', 'time'],
            'material': ['house', 'tool', 'weapon', 'food', 'clothing', 'money', 'book'],
            'social': ['king', 'minister', 'teacher', 'student', 'friend', 'enemy', 'law', 'rule']
        }
        
        for meaning in meanings:
            meaning_lower = meaning.lower()
            for domain, keywords in domain_mappings.items():
                if any(keyword in meaning_lower for keyword in keywords):
                    domains.append(domain)
        
        # Удаляем дубликаты
        return list(set(domains))
    
    async def _extract_color_associations(self, character: str, analysis_data: Dict[str, Any]) -> List[str]:
        """
        Извлекает цветовые ассоциации иероглифа.
        
        Args:
            character: Иероглиф
            analysis_data: Данные анализа
            
        Returns:
            List[str]: Цветовые ассоциации
        """
        color_associations = []
        
        # Из визуального анализа
        visual_data = analysis_data.get('visual_associations', {})
        if 'color_mappings' in visual_data:
            color_associations.extend(visual_data['color_mappings'])
        
        # На основе значений
        meanings = analysis_data.get('meanings', [])
        color_mappings = {
            'red': ['fire', 'blood', 'love', 'anger', 'passion'],
            'blue': ['water', 'sky', 'sea', 'calm', 'peace'],
            'green': ['tree', 'leaf', 'grass', 'nature', 'growth'],
            'yellow': ['sun', 'gold', 'earth', 'harvest', 'emperor'],
            'white': ['snow', 'pure', 'clean', 'bright', 'holy'],
            'black': ['night', 'dark', 'deep', 'mystery', 'power'],
            'brown': ['wood', 'earth', 'soil', 'stable', 'warm'],
            'golden': ['gold', 'precious', 'valuable', 'rich', 'divine']
        }
        
        for meaning in meanings:
            meaning_lower = meaning.lower()
            for color, keywords in color_mappings.items():
                if any(keyword in meaning_lower for keyword in keywords):
                    color_associations.append(color)
        
        # Из Wu Xing элементов
        cultural_context = analysis_data.get('cultural_context', {})
        wu_xing_colors = {
            'fire': ['red', 'orange'],
            'water': ['blue', 'black'],
            'wood': ['green', 'blue'],
            'metal': ['white', 'gold'],
            'earth': ['yellow', 'brown']
        }
        
        wu_xing_elements = cultural_context.get('wu_xing_elements', [])
        for element in wu_xing_elements:
            if element in wu_xing_colors:
                color_associations.extend(wu_xing_colors[element])
        
        # Удаляем дубликаты и ограничиваем количество
        unique_colors = list(dict.fromkeys(color_associations))
        return unique_colors[:self.config.max_associations]
    
    async def _extract_texture_associations(self, character: str, analysis_data: Dict[str, Any]) -> List[str]:
        """
        Извлекает текстурные ассоциации иероглифа.
        
        Args:
            character: Иероглиф
            analysis_data: Данные анализа
            
        Returns:
            List[str]: Текстурные ассоциации
        """
        texture_associations = []
        
        # Из визуального анализа
        visual_data = analysis_data.get('visual_associations', {})
        if 'texture_mappings' in visual_data:
            texture_associations.extend(visual_data['texture_mappings'])
        
        # На основе значений
        meanings = analysis_data.get('meanings', [])
        texture_mappings = {
            'smooth': ['water', 'silk', 'jade', 'polished', 'calm'],
            'rough': ['stone', 'bark', 'mountain', 'raw', 'wild'],
            'soft': ['cloud', 'fur', 'feather', 'gentle', 'tender'],
            'hard': ['metal', 'stone', 'bone', 'strong', 'firm'],
            'flowing': ['water', 'wind', 'river', 'movement', 'dance'],
            'crystalline': ['ice', 'crystal', 'clear', 'pure', 'transparent'],
            'organic': ['wood', 'plant', 'natural', 'living', 'growing'],
            'metallic': ['gold', 'silver', 'iron', 'shiny', 'gleaming']
        }
        
        for meaning in meanings:
            meaning_lower = meaning.lower()
            for texture, keywords in texture_mappings.items():
                if any(keyword in meaning_lower for keyword in keywords):
                    texture_associations.append(texture)
        
        # Из Wu Xing элементов
        cultural_context = analysis_data.get('cultural_context', {})
        wu_xing_textures = {
            'fire': ['flickering', 'dancing', 'bright'],
            'water': ['flowing', 'smooth', 'reflective'],
            'wood': ['organic', 'textured', 'natural'],
            'metal': ['metallic', 'hard', 'shiny'],
            'earth': ['rough', 'solid', 'granular']
        }
        
        wu_xing_elements = cultural_context.get('wu_xing_elements', [])
        for element in wu_xing_elements:
            if element in wu_xing_textures:
                texture_associations.extend(wu_xing_textures[element])
        
        # Удаляем дубликаты и ограничиваем количество
        unique_textures = list(dict.fromkeys(texture_associations))
        return unique_textures[:self.config.max_associations]
    
    async def _extract_symbolic_meaning(self, character: str, analysis_data: Dict[str, Any]) -> Optional[str]:
        """
        Извлекает символическое значение иероглифа.
        
        Args:
            character: Иероглиф
            analysis_data: Данные анализа
            
        Returns:
            Optional[str]: Символическое значение
        """
        meanings = analysis_data.get('meanings', [])
        cultural_context = analysis_data.get('cultural_context', {})
        
        # Проверяем наличие философских или духовных значений
        symbolic_keywords = [
            'wisdom', 'enlightenment', 'harmony', 'balance', 'virtue', 
            'strength', 'courage', 'peace', 'unity', 'prosperity',
            'fortune', 'longevity', 'happiness', 'success'
        ]
        
        symbolic_meanings = []
        for meaning in meanings:
            meaning_lower = meaning.lower()
            for keyword in symbolic_keywords:
                if keyword in meaning_lower:
                    symbolic_meanings.append(keyword)
        
        # Добавляем философские ассоциации
        philosophical = cultural_context.get('philosophical_associations', [])
        symbolic_meanings.extend(philosophical)
        
        if symbolic_meanings:
            # Возвращаем наиболее значимое символическое значение
            return symbolic_meanings[0]
        
        return None
    
    # Вспомогательные методы
    
    def _validate_character(self, character: str) -> bool:
        """Валидирует что символ является китайским иероглифом."""
        if not character or len(character) != 1:
            return False
        
        # Проверяем Unicode блоки китайских иероглифов
        code = ord(character)
        chinese_blocks = [
            (0x4E00, 0x9FFF),  # CJK Unified Ideographs
            (0x3400, 0x4DBF),  # CJK Extension A
            (0x20000, 0x2A6DF), # CJK Extension B
            (0x2A700, 0x2B73F), # CJK Extension C
            (0x2B740, 0x2B81F), # CJK Extension D
            (0x2B820, 0x2CEAF), # CJK Extension E
            (0x2CEB0, 0x2EBEF), # CJK Extension F
        ]
        
        return any(start <= code <= end for start, end in chinese_blocks)
    
    def _estimate_stroke_count(self, character: str) -> int:
        """Оценивает количество штрихов в иероглифе."""
        # TODO: Интеграция с базой данных штрихов
        # Пока используем простую эвристику на основе Unicode блока
        code = ord(character)
        
        if 0x4E00 <= code <= 0x9FFF:  # Основные иероглифы
            # Простая эвристика: чем выше код, тем сложнее иероглиф
            return min(30, max(1, (code - 0x4E00) // 1000 + 1))
        
        return 10  # Значение по умолчанию
    
    def _is_simplified_character(self, character: str) -> bool:
        """Проверяет является ли иероглиф упрощенным."""
        # TODO: Интеграция с базой данных упрощенных/традиционных иероглифов
        # Пока возвращаем True для большинства иероглифов
        return True
    
    def _is_traditional_character(self, character: str) -> bool:
        """Проверяет является ли иероглиф традиционным."""
        # TODO: Интеграция с базой данных упрощенных/традиционных иероглифов
        return not self._is_simplified_character(character)
    
    # Заглушки для базовых данных (до интеграции с реальными БД)
    
    def _get_basic_definition(self, character: str) -> Optional[str]:
        """Получает базовое определение иероглифа."""
        # TODO: Интеграция с реальной базой данных
        basic_definitions = {
            '火': 'fire, flame, burn',
            '水': 'water, liquid, river',
            '木': 'tree, wood, timber',
            '金': 'gold, metal, money',
            '土': 'earth, soil, ground',
            '人': 'person, human, people',
            '心': 'heart, mind, soul',
            '手': 'hand, arm, manual',
            '目': 'eye, look, see',
            '日': 'sun, day, solar',
            '月': 'moon, month, lunar',
            '山': 'mountain, hill, peak',
            '川': 'river, stream, flow',
            '学': 'study, learn, school',
            '爱': 'love, affection, like',
            '家': 'home, family, house'
        }
        return basic_definitions.get(character)
    
    def _get_basic_pronunciation(self, character: str) -> Optional[str]:
        """Получает базовое произношение пиньинь."""
        basic_pronunciations = {
            '火': 'huǒ',
            '水': 'shuǐ', 
            '木': 'mù',
            '金': 'jīn',
            '土': 'tǔ',
            '人': 'rén',
            '心': 'xīn',
            '手': 'shǒu',
            '目': 'mù',
            '日': 'rì',
            '月': 'yuè',
            '山': 'shān',
            '川': 'chuān',
            '学': 'xué',
            '爱': 'ài',
            '家': 'jiā'
        }
        return basic_pronunciations.get(character)
    
    def _get_basic_cantonese(self, character: str) -> Optional[str]:
        """Получает базовое кантонское произношение."""
        basic_cantonese = {
            '火': 'fo2',
            '水': 'seoi2',
            '木': 'muk6',
            '金': 'gam1',
            '土': 'tou2',
            '人': 'jan4',
            '心': 'sam1',
            '手': 'sau2',
            '目': 'muk6',
            '日': 'jat6',
            '月': 'jyut6',
            '山': 'saan1',
            '川': 'cyun1',
            '学': 'hok6',
            '爱': 'oi3',
            '家': 'gaa1'
        }
        return basic_cantonese.get(character)
    
    def _get_basic_japanese_on(self, character: str) -> Optional[str]:
        """Получает базовое японское чтение ОН."""
        basic_japanese_on = {
            '火': 'カ',
            '水': 'スイ',
            '木': 'モク',
            '金': 'キン',
            '土': 'ド',
            '人': 'ジン',
            '心': 'シン',
            '手': 'シュ',
            '目': 'モク',
            '日': 'ニチ',
            '月': 'ゲツ',
            '山': 'サン',
            '川': 'セン',
            '学': 'ガク',
            '爱': 'アイ',
            '家': 'カ'
        }
        return basic_japanese_on.get(character)
    
    def _get_basic_japanese_kun(self, character: str) -> Optional[str]:
        """Получает базовое японское чтение КУН."""
        basic_japanese_kun = {
            '火': 'ひ',
            '水': 'みず',
            '木': 'き',
            '金': 'かね',
            '土': 'つち',
            '人': 'ひと',
            '心': 'こころ',
            '手': 'て',
            '目': 'め',
            '日': 'ひ',
            '月': 'つき',
            '山': 'やま',
            '川': 'かわ',
            '学': 'まな.ぶ',
            '爱': None,  # Упрощенный иероглиф
            '家': 'いえ'
        }
        return basic_japanese_kun.get(character)
    
    def _get_basic_korean(self, character: str) -> Optional[str]:
        """Получает базовое корейское произношение."""
        basic_korean = {
            '火': '화',
            '水': '수',
            '木': '목',
            '金': '금',
            '土': '토',
            '人': '인',
            '心': '심',
            '手': '수',
            '目': '목',
            '日': '일',
            '月': '월',
            '山': '산',
            '川': '천',
            '学': '학',
            '爱': '애',
            '家': '가'
        }
        return basic_korean.get(character)
    
    # Методы инициализации и кэширования
    
    async def _initialize_databases(self):
        """Инициализирует базы данных."""
        try:
            logger.info("Initializing semantic analysis databases...")
            
            # TODO: Загрузка реальных баз данных
            # await self._load_unihan_database()
            # await self._load_frequency_database()
            # await self._load_variant_database()
            
            logger.info("Semantic databases initialized")
            
        except Exception as e:
            logger.warning(f"Error initializing databases: {e}")
    
    def _get_sources_used(self, analysis_data: Dict[str, Any]) -> List[str]:
        """Определяет использованные источники данных."""
        sources = []
        
        if 'unihan' in analysis_data:
            sources.append('unihan_database')
        if 'radicals' in analysis_data:
            sources.append('radical_analysis')
        if 'etymology' in analysis_data:
            sources.append('etymology_analysis')
        if 'visual_associations' in analysis_data:
            sources.append('visual_association_analysis')
        
        return sources
    
    def _calculate_confidence_scores(self, analysis_data: Dict[str, Any]) -> Dict[str, float]:
        """Вычисляет оценки уверенности для разных аспектов анализа."""
        confidence_scores = {}
        
        # Базовая информация - всегда высокая уверенность
        confidence_scores['basic_info'] = 0.95
        
        # Unihan данные
        if 'unihan' in analysis_data:
            unihan_data = analysis_data['unihan']
            # Больше данных = выше уверенность
            data_completeness = len(unihan_data) / 7  # 7 основных полей
            confidence_scores['unihan'] = min(0.9, 0.4 + data_completeness * 0.5)
        
        # Радикальный анализ
        if 'radicals' in analysis_data:
            confidence_scores['radicals'] = 0.8  # Обычно надежен
        
        # Этимология
        if 'etymology' in analysis_data:
            confidence_scores['etymology'] = 0.7  # Менее определенна
        
        # Визуальные ассоциации
        if 'visual_associations' in analysis_data:
            confidence_scores['visual_associations'] = 0.6  # Субъективны
        
        # Значения
        meanings = analysis_data.get('meanings', [])
        if meanings:
            # Больше значений = выше уверенность
            meaning_confidence = min(0.9, 0.3 + len(meanings) * 0.15)
            confidence_scores['meanings'] = meaning_confidence
        
        # Произношения
        pronunciations = analysis_data.get('pronunciations', {})
        if pronunciations:
            pronunciation_confidence = min(0.95, 0.5 + len(pronunciations) * 0.1)
            confidence_scores['pronunciations'] = pronunciation_confidence
        
        return confidence_scores
    def get_supported_features(self) -> Dict[str, bool]:
        """Возвращает поддерживаемые функции анализатора."""
        return {
            "unihan_database": self.config.enable_unihan_database,
            "radical_analysis": self.config.enable_radical_analysis,
            "etymology_analysis": self.config.enable_etymology_analysis,
            "visual_associations": self.config.enable_visual_associations,
            "pronunciations": self.config.include_pronunciations,
            "cultural_context": True,
            "semantic_domains": True,
            "color_associations": True,
            "texture_associations": True,
            "symbolic_meaning": True,
        }
    