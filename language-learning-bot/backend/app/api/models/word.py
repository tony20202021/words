"""
Models related to words.
"""

from typing import Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

class WordBase(BaseModel):
    """Base model for word."""
    language_id: str = Field(..., description="ID of the language this word belongs to")
    word_foreign: str = Field(..., description="Word in foreign language")
    translation: str = Field(..., description="Translation of the word to Russian")
    transcription: Optional[str] = Field(None, description="Phonetic transcription")
    word_number: int = Field(..., description="Sequential number in frequency list")
    radicals: Optional[str] = Field(None, description="Radicals of the word")
    references: Optional[str] = Field(None, description="References to the word")
    tones: Optional[str] = Field(None, description="Tones of the word")
    part_of_speech: Optional[str] = Field(None, description="Часть речи: сущ, глаг, прил…")
    lemma: Optional[str] = Field(None, description="Словарная форма, если отличается от самого слова")
    sounds: Optional[str] = Field(None, description="List of sounds files")
    word_foreign_unit_count: Optional[int] = Field(None, description="Unit count of word_foreign (CJK: char count, other: word count)")
    transcription_unit_count: Optional[int] = Field(None, description="Syllable count in transcription")

class WordCreate(WordBase):
    """Create model for word."""
    pass

class WordUpdate(BaseModel):
    """Update model for word."""
    word_foreign: Optional[str] = Field(None, description="Word in foreign language")
    translation: Optional[str] = Field(None, description="Translation of the word to Russian")
    transcription: Optional[str] = Field(None, description="Phonetic transcription")
    word_number: Optional[int] = Field(None, description="Sequential number in frequency list")
    radicals: Optional[str] = Field(None, description="Radicals of the word")
    references: Optional[str] = Field(None, description="References to the word")
    tones: Optional[str] = Field(None, description="Tones of the word")
    part_of_speech: Optional[str] = Field(None, description="Часть речи: сущ, глаг, прил…")
    lemma: Optional[str] = Field(None, description="Словарная форма, если отличается от самого слова")
    sounds: Optional[str] = Field(None, description="List of sounds files")

class WordInDB(WordBase):
    """Database model for word."""
    id: str = Field(..., description="Unique identifier")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    model_config = ConfigDict(from_attributes=True)

class Word(WordInDB):
    """Response model for word."""
    language_name_ru: Optional[str] = Field(None, description="Russian name of the language")
    language_name_foreign: Optional[str] = Field(None, description="Native name of the language")

class WordForReview(BaseModel):
    """Model for word data for review."""
    word_id: str = Field(..., description="Word ID")
    language_id: str = Field(..., description="Language ID")
    word_foreign: str = Field(..., description="Word in foreign language")
    translation: str = Field(..., description="Translation of the word to Russian")
    transcription: Optional[str] = Field(None, description="Phonetic transcription")
    word_number: int = Field(..., description="Sequential number in frequency list")
    radicals: Optional[str] = Field(None, description="Radicals of the word")
    references: Optional[str] = Field(None, description="References to the word")
    tones: Optional[str] = Field(None, description="Tones of the word")
    part_of_speech: Optional[str] = Field(None, description="Часть речи: сущ, глаг, прил…")
    lemma: Optional[str] = Field(None, description="Словарная форма, если отличается от самого слова")
    sounds: Optional[str] = Field(None, description="List of sounds files")
    score: int = Field(0, description="Current score (0 or 1)")
    check_interval: int = Field(0, description="Current check interval in days")
    next_check_date: Optional[datetime] = Field(None, description="Next check date")
    hint_phoneticassociation: Optional[str] = Field(None, description="Association hint")
    hint_phoneticsound: Optional[str] = Field(None, description="Syllables hint")
    hint_meaning: Optional[str] = Field(None, description="Meaning hint")
    hint_writing: Optional[str] = Field(None, description="Writing hint")
