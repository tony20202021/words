"""
Models related to words.
"""

from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field

class WordBase(BaseModel):
    """Base model for word."""
    language_id: str = Field(..., description="ID of the language this word belongs to")
    word_foreign: str = Field(..., description="Word in foreign language")
    translation: str = Field(..., description="Translation of the word to Russian")
    transcription: Optional[str] = Field(None, description="Phonetic transcription")
    word_number: int = Field(..., description="Sequential number in frequency list")
    sound_file_path: Optional[str] = Field(None, description="Path to sound file")

class WordCreate(WordBase):
    """Create model for word."""
    pass

class WordUpdate(BaseModel):
    """Update model for word."""
    word_foreign: Optional[str] = Field(None, description="Word in foreign language")
    translation: Optional[str] = Field(None, description="Translation of the word to Russian")
    transcription: Optional[str] = Field(None, description="Phonetic transcription")
    word_number: Optional[int] = Field(None, description="Sequential number in frequency list")
    sound_file_path: Optional[str] = Field(None, description="Path to sound file")

class WordInDB(WordBase):
    """Database model for word."""
    id: str = Field(..., description="Unique identifier")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    class Config:
        from_attributes = True  # Updated from orm_mode to from_attributes
        json_schema_extra = {   # Updated from schema_extra to json_schema_extra
            "example": {
                "id": "5f9b3b3b9c9d440000b3b3b3",
                "language_id": "5f9b3b3b9c9d440000b3b3b3",
                "word_foreign": "hello",
                "translation": "привет",
                "transcription": "həˈləʊ",
                "word_number": 1,
                "sound_file_path": None,
                "created_at": "2020-10-29T12:00:00",
                "updated_at": "2020-10-29T12:00:00"
            }
        }

class Word(WordInDB):
    """Response model for word."""
    language_name_ru: Optional[str] = Field(None, description="Russian name of the language")
    language_name_foreign: Optional[str] = Field(None, description="Native name of the language")

    class Config:
        from_attributes = True  # Updated from orm_mode to from_attributes
        json_schema_extra = {   # Updated from schema_extra to json_schema_extra
            "example": {
                "id": "5f9b3b3b9c9d440000b3b3b3",
                "language_id": "5f9b3b3b9c9d440000b3b3b3",
                "word_foreign": "hello",
                "translation": "привет",
                "transcription": "həˈləʊ",
                "word_number": 1,
                "sound_file_path": None,
                "created_at": "2020-10-29T12:00:00",
                "updated_at": "2020-10-29T12:00:00",
                "language_name_ru": "Английский",
                "language_name_foreign": "English"
            }
        }

class WordForReview(BaseModel):
    """Model for word data for review."""
    word_id: str = Field(..., description="Word ID")
    language_id: str = Field(..., description="Language ID")
    word_foreign: str = Field(..., description="Word in foreign language")
    translation: str = Field(..., description="Translation of the word to Russian")
    transcription: Optional[str] = Field(None, description="Phonetic transcription")
    word_number: int = Field(..., description="Sequential number in frequency list")
    score: int = Field(0, description="Current score (0 or 1)")
    check_interval: int = Field(0, description="Current check interval in days")
    next_check_date: Optional[datetime] = Field(None, description="Next check date")
    hint_association: Optional[str] = Field(None, description="Association hint")
    hint_syllables: Optional[str] = Field(None, description="Syllables hint")
    hint_meaning: Optional[str] = Field(None, description="Meaning hint")
    hint_writing: Optional[str] = Field(None, description="Writing hint")