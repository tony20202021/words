"""
Models related to user statistics.
"""

from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field

class UserStatisticsBase(BaseModel):
    """Base model for user statistics."""
    user_id: str = Field(..., description="User ID")
    word_id: str = Field(..., description="Word ID")
    language_id: str = Field(..., description="Language ID")
    hint_phoneticsound: Optional[str] = Field(None, description="Syllables hint")
    hint_phoneticassociation: Optional[str] = Field(None, description="Association hint")
    hint_meaning: Optional[str] = Field(None, description="Meaning hint")
    hint_writing: Optional[str] = Field(None, description="Writing hint")
    score: int = Field(0, description="Score (0 or 1)")
    is_skipped: bool = Field(False, description="Is word skipped")
    next_check_date: Optional[datetime] = Field(None, description="Next check date")
    check_interval: int = Field(0, description="Check interval in days")

class UserStatisticsCreate(BaseModel):
    """Create model for user statistics."""
    word_id: str = Field(..., description="Word ID")
    language_id: str = Field(..., description="Language ID")
    hint_phoneticsound: Optional[str] = Field(None, description="Syllables hint")
    hint_phoneticassociation: Optional[str] = Field(None, description="Association hint")
    hint_meaning: Optional[str] = Field(None, description="Meaning hint")
    hint_writing: Optional[str] = Field(None, description="Writing hint")
    score: int = Field(0, description="Score (0 or 1)")
    is_skipped: bool = Field(False, description="Is word skipped")

class UserStatisticsUpdate(BaseModel):
    """Update model for user statistics."""
    hint_phoneticsound: Optional[str] = Field(None, description="Syllables hint")
    hint_phoneticassociation: Optional[str] = Field(None, description="Association hint")
    hint_meaning: Optional[str] = Field(None, description="Meaning hint")
    hint_writing: Optional[str] = Field(None, description="Writing hint")
    score: Optional[int] = Field(None, description="Score (0 or 1)")
    is_skipped: Optional[bool] = Field(None, description="Is word skipped")
    check_interval: Optional[int] = Field(None, description="Check interval in days")
    next_check_date: Optional[datetime] = Field(None, description="Next check date")

class UserStatisticsInDB(UserStatisticsBase):
    """Database model for user statistics."""
    id: str = Field(..., description="Unique identifier")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    class Config:
        from_attributes = True  # Updated from orm_mode to from_attributes
        json_schema_extra = {   # Updated from schema_extra to json_schema_extra
            "example": {
                "id": "5f9b3b3b9c9d440000b3b3b3",
                "user_id": "5f9b3b3b9c9d440000b3b3b3",
                "word_id": "5f9b3b3b9c9d440000b3b3b3",
                "language_id": "5f9b3b3b9c9d440000b3b3b3",
                "hint_phoneticsound": "бон-жур",
                "hint_phoneticassociation": "бонус за журнал",
                "hint_meaning": "приветствие при встрече",
                "hint_writing": None,
                "score": 1,
                "is_skipped": False,
                "next_check_date": "2020-11-05T00:00:00",
                "check_interval": 4,
                "created_at": "2020-10-29T12:00:00",
                "updated_at": "2020-10-29T12:00:00"
            }
        }

class UserStatistics(UserStatisticsInDB):
    """Response model for user statistics."""
    word_foreign: Optional[str] = Field(None, description="Word in foreign language")
    translation: Optional[str] = Field(None, description="Translation of the word")
    transcription: Optional[str] = Field(None, description="Transcription of the word")
    word_number: Optional[int] = Field(None, description="Word number in frequency list")

class UserProgress(BaseModel):
    """Model for user progress."""
    user_id: str = Field(..., description="User ID")
    language_id: str = Field(..., description="Language ID")
    language_name_ru: str = Field(..., description="Russian name of the language")
    language_name_foreign: str = Field(..., description="Native name of the language")
    total_words: int = Field(0, description="Total number of words")
    words_studied: int = Field(0, description="Number of words studied")
    words_known: int = Field(0, description="Number of words known")
    words_skipped: int = Field(0, description="Number of words skipped")
    words_for_today: int = Field(0, description="Number of words for today")
    progress_percentage: float = Field(0.0, description="Percentage of progress")
    last_study_date: Optional[datetime] = Field(None, description="Last study date")