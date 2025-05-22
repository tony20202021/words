#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Сервис транскрипции на основе библиотеки g2p_en и g2p
"""

import logging
from typing import Dict, List, Optional

from .base import TranscriptionService

logger = logging.getLogger(__name__)

class G2PService(TranscriptionService):
    """Сервис транскрипции на основе библиотеки g2p"""

    def __init__(self):
        self.g2p_available = False
        self.g2p_en_available = False
        self.g2p_general_available = False
        
        # Проверка доступности g2p_en
        try:
            from g2p_en import G2p
            self.g2p_en = G2p()
            self.g2p_en_available = True
            logger.info("g2p_en успешно импортирован")
        except ImportError as e:
            logger.warning(f"Библиотека g2p_en не установлена: {e}. Установите её с помощью: pip install g2p-en")
        except Exception as e:
            logger.error(f"Ошибка при импорте g2p_en: {e}")
        
        # Проверка доступности общей g2p библиотеки
        try:
            from g2p import Transliterator
            self.transliterator = Transliterator()
            self.g2p_general_available = True
            logger.info("g2p успешно импортирован")
        except ImportError as e:
            logger.warning(f"Библиотека g2p не установлена: {e}. Установите её с помощью: pip install g2p")
        except Exception as e:
            logger.error(f"Ошибка при импорте g2p: {e}")
            
        # Устанавливаем общую доступность сервиса
        self.g2p_available = self.g2p_en_available or self.g2p_general_available
            
    def _convert_arpabet_to_ipa(self, phonemes: List[str]) -> str:
        """
        Преобразует фонемы ARPAbet в формат IPA.
        
        Args:
            phonemes: Список фонем в формате ARPAbet
            
        Returns:
            Строка с фонемами в формате IPA
        """
        # Отображение ARPAbet -> IPA
        arpabet_to_ipa = {
            'AA': 'ɑ', 'AE': 'æ', 'AH': 'ʌ', 'AO': 'ɔ', 'AW': 'aʊ', 'AY': 'aɪ', 
            'B': 'b', 'CH': 'tʃ', 'D': 'd', 'DH': 'ð', 'EH': 'ɛ', 'ER': 'ɝ', 
            'EY': 'eɪ', 'F': 'f', 'G': 'ɡ', 'HH': 'h', 'IH': 'ɪ', 'IY': 'i', 
            'JH': 'dʒ', 'K': 'k', 'L': 'l', 'M': 'm', 'N': 'n', 'NG': 'ŋ', 
            'OW': 'oʊ', 'OY': 'ɔɪ', 'P': 'p', 'R': 'ɹ', 'S': 's', 'SH': 'ʃ', 
            'T': 't', 'TH': 'θ', 'UH': 'ʊ', 'UW': 'u', 'V': 'v', 'W': 'w', 
            'Y': 'j', 'Z': 'z', 'ZH': 'ʒ'
        }
        
        # Преобразуем ARPAbet в IPA
        ipa_phonemes = []
        for phoneme in phonemes:
            # Убираем цифры ударения, если они есть
            if len(phoneme) > 0 and phoneme[-1].isdigit():
                phoneme = phoneme[:-1]
            
            if phoneme in arpabet_to_ipa:
                ipa_phonemes.append(arpabet_to_ipa[phoneme])
            else:
                ipa_phonemes.append(phoneme)
        
        return ''.join(ipa_phonemes)
    
    def get_transcription(self, word: str, lang_code: str) -> Optional[str]:
        """
        Получает транскрипцию с помощью g2p.
        
        Args:
            word: Слово для транскрибирования
            lang_code: Код языка
            
        Returns:
            Строка с транскрипцией или None, если язык не поддерживается
        """
        if not self.g2p_available:
            logger.warning("g2p не доступен")
            return None
        
        try:
            # g2p_en в основном поддерживает только английский
            if self.g2p_en_available:
                if lang_code == 'en':
                    phonemes = self.g2p_en(word)
                    transcription = self._convert_arpabet_to_ipa(phonemes)
                    formatted_transcription = f"/{transcription}/"
                    
                    logger.debug(f"Получена транскрипция через g2p_en для '{word}': {formatted_transcription}")
                    return formatted_transcription
                else:
                    logger.warning(f"Язык {lang_code} не поддерживается общей g2p библиотекой")
                    return None
            
            # Общая g2p библиотека для других языков
            elif self.g2p_general_available:
                # Проверяем, поддерживается ли язык
                supported_langs = ['en']  # Список поддерживаемых языков
                
                if lang_code in supported_langs:
                    try:
                        phonemes = self.transliterator.transliterate(word, lang=lang_code)
                        transcription = ' '.join(phonemes) if isinstance(phonemes, list) else phonemes
                        formatted_transcription = f"/{transcription.replace(' ', '')}/"
                        
                        logger.debug(f"Получена транскрипция через g2p для '{word}': {formatted_transcription}")
                        return formatted_transcription
                    except Exception as e:
                        logger.error(f"Ошибка при вызове transliterate для '{word}': {e}")
                        return None
                else:
                    logger.warning(f"Язык {lang_code} не поддерживается общей g2p библиотекой")
                    return None
            
            else:
                logger.warning("Ни один из вариантов g2p не инициализирован")
                return None
                
        except Exception as e:
            logger.error(f"Ошибка при получении транскрипции через g2p для '{word}': {e}")
            return None
            