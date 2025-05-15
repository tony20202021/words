"""
Pydantic schemas for word data validation.
"""

from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field


class WordBase(BaseModel):
    """Base schema for word data."""
    language_id: str = Field(..., description="ID of the language this word belongs to")
    word_foreign: str = Field(..., description="Word in foreign language")
    translation: str = Field(..., description="Translation of the word to Russian")
    transcription: Optional[str] = Field(None, description="Phonetic transcription")
    word_number: int = Field(..., description="Sequential number in frequency list")
    sound_file_path: Optional[str] = Field(None, description="Path to sound file")


class WordCreate(WordBase):
    """Schema for creating a new word."""
    pass


class WordUpdate(BaseModel):
    """Schema for updating an existing word."""
    word_foreign: Optional[str] = Field(None, description="Word in foreign language")
    translation: Optional[str] = Field(None, description="Translation of the word to Russian")
    transcription: Optional[str] = Field(None, description="Phonetic transcription")
    word_number: Optional[int] = Field(None, description="Sequential number in frequency list")
    sound_file_path: Optional[str] = Field(None, description="Path to sound file")


class WordResponse(WordBase):
    """Schema for word response data."""
    id: str = Field(..., description="Word ID")
    created_at: Optional[datetime] = Field(None, description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")
    
    class Config:
        """Pydantic configuration."""
        orm_mode = True
        json_encoders = {
            datetime: lambda dt: dt.isoformat()
        }


class WordWithLanguageResponse(WordResponse):
    """Schema for word response with language information."""
    language_name_ru: str = Field(..., description="Russian name of the language")
    language_name_foreign: str = Field(..., description="Native name of the language")