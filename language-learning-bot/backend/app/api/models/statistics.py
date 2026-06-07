"""
Models related to user statistics.
"""

from typing import Optional, List, Tuple
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

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
    next_check_date: Optional[datetime] = Field(None, description="Next check date")
    check_interval: int = Field(0, description="Check interval in days")
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

    model_config = ConfigDict(from_attributes=True)

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
    word_numbers_for_today: List[int] = Field(default_factory=list, description="Word numbers for today review")
    word_numbers_unknown: List[int] = Field(default_factory=list, description="Unknown word numbers (score=0, not skipped)")
    word_check_interval: List[Tuple[int, Optional[int]]] = Field(default_factory=list, description="Word check interval (word_number, check_interval)")

# class UserDailyStats(BaseModel):
#     """Model for user daily stats."""
#     user_id: str = Field(..., description="User ID")
#     language_id: str = Field(..., description="Language ID")
#     date: datetime = Field(..., description="Date")
#     words_studied: int = Field(0, description="Number of words studied")
#     words_known: int = Field(0, description="Number of words known")
#     words_skipped: int = Field(0, description="Number of words skipped")
#     words_for_today: int = Field(0, description="Number of words for today")

# class UserMonthlyStats(BaseModel):
#     """Model for user monthly stats."""
#     user_id: str = Field(..., description="User ID")
#     language_id: str = Field(..., description="Language ID")
#     stats: List[UserDailyStats] = Field(..., description="List of daily stats")


# В app/api/models/statistics.py - добавить эти модели:

class UserDailyStatsBase(BaseModel):
    """Base model for user daily statistics."""
    user_id: str = Field(..., description="User ID")
    language_id: str = Field(..., description="Language ID")
    date: datetime = Field(..., description="Date of statistics")
    words_studied: int = Field(0, description="Number of words studied")
    words_known: int = Field(0, description="Number of words known")
    words_skipped: int = Field(0, description="Number of words skipped")
    words_for_today: int = Field(0, description="Number of words for today")
    max_word_number: Optional[int] = Field(None, description="Max word_number processed this day")
    is_seeded: Optional[bool] = Field(None, description="True=seeded snapshot, False=real session completion")

class UserDailyStatsCreate(UserDailyStatsBase):
    """Create model for user daily statistics."""
    pass

class UserDailyStatsUpdate(BaseModel):
    """Update model for user daily statistics."""
    words_studied: Optional[int] = Field(None, description="Number of words studied")
    words_known: int = Field(0, description="Number of words known")
    words_skipped: int = Field(0, description="Number of words skipped")
    words_for_today: int = Field(0, description="Number of words for today")
    max_word_number: Optional[int] = Field(None, description="Max word_number processed this day")
    is_seeded: Optional[bool] = Field(None, description="True=seeded snapshot, False=real session completion")

class UserDailyStatsInDB(UserDailyStatsBase):
    """Database model for user daily statistics."""
    id: str = Field(..., description="Unique identifier")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    type: str = Field(..., description="Type of statistics")

    model_config = ConfigDict(from_attributes=True)

class UserMonthlyStats(BaseModel):
    """Model for user monthly stats aggregation."""
    user_id: str = Field(..., description="User ID")
    language_id: str = Field(..., description="Language ID")
    date: datetime = Field(..., description="Date of statistics")
    daily_stats: List[UserDailyStatsInDB] = Field(..., description="List of daily stats for the month")
