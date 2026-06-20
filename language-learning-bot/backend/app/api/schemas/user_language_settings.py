"""
Pydantic models for user language settings.
These models define the structure of user language settings in the API.
"""

from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field


class UserLanguageSettingsBase(BaseModel):
    """Base model for user language settings."""
    start_word: int = Field(1, description="Word number to start learning from")
    skip_marked: bool = Field(False, description="Whether to skip marked words")
    use_check_date: bool = Field(True, description="Whether to use check date for spaced repetition")
    show_check_date: bool = Field(True, description="Whether to show check date")
    show_debug: bool = Field(False, description="Whether to show debug information")
    show_charts: bool = Field(False, description="Whether to show chart")    
    show_big: bool = Field(False, description="Whether to show big word")
    show_writing_images: bool = Field(True, description="Whether to show writing images")
    show_radicals: bool = Field(True, description="Whether to show radicals")
    show_references: bool = Field(True, description="Whether to show references")
    show_tones: bool = Field(True, description="Whether to show tones")
    show_sounds: bool = Field(True, description="Whether to show sounds")
    show_skip_button: bool = Field(True, description="Whether to show skip button")
    random_foreign: bool = Field(True, description="Whether to randomly show foreign words")
    random_transcription: bool = Field(True, description="Whether to randomly show transcriptions")
    random_sound: bool = Field(True, description="Whether to randomly show sound")

    # Раздельные настройки для каждого типа подсказки
    show_hint_phoneticsound: bool = Field(True, description="Whether to show syllables hint button")
    show_hint_phoneticassociation: bool = Field(True, description="Whether to show association hint button") 
    show_hint_meaning: bool = Field(True, description="Whether to show meaning hint button")
    show_hint_writing: bool = Field(True, description="Whether to show writing hint button")
    show_short_captions: bool = Field(True, description="Whether to show short captions")

    receive_messages: bool = Field(True, description="Whether to receive messages")

    reset_same_day_hours: int = Field(16, description="Hours of inactivity within same day before session reset")
    reset_cross_midnight_hours: int = Field(6, description="Hour of day (0-23) after midnight crossing before session reset")
    unknown_limit_new_words: int = Field(10, description="Number of unknown words to learn per day")
    max_check_interval: int = Field(32, description="Maximum spaced-repetition interval in days")

class UserLanguageSettingsCreate(UserLanguageSettingsBase):
    """Model for creating user language settings."""
    pass


class UserLanguageSettingsUpdate(BaseModel):
    """Model for updating user language settings."""
    start_word: Optional[int] = None
    skip_marked: Optional[bool] = None
    use_check_date: Optional[bool] = None
    show_check_date: Optional[bool] = None
    show_debug: Optional[bool] = None
    show_charts: Optional[bool] = None
    show_big: Optional[bool] = None
    show_writing_images: Optional[bool] = None
    show_radicals: Optional[bool] = None
    show_references: Optional[bool] = None
    show_tones: Optional[bool] = None
    show_sounds: Optional[bool] = None
    show_skip_button: Optional[bool] = None
    random_foreign: Optional[bool] = None
    random_transcription: Optional[bool] = None
    random_sound: Optional[bool] = None
    
    # Раздельные настройки для каждого типа подсказки
    show_hint_phoneticsound: Optional[bool] = None
    show_hint_phoneticassociation: Optional[bool] = None
    show_hint_meaning: Optional[bool] = None
    show_hint_writing: Optional[bool] = None
    
    show_short_captions: Optional[bool] = None
    receive_messages: Optional[bool] = None
    reset_same_day_hours: Optional[int] = None
    reset_cross_midnight_hours: Optional[int] = None
    unknown_limit_new_words: Optional[int] = None
    max_check_interval: Optional[int] = None

class UserLanguageSettingsInDB(UserLanguageSettingsBase):
    """Model for user language settings as stored in the database."""
    id: str
    user_id: str
    language_id: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class UserLanguageSettings(UserLanguageSettingsBase):
    """Model for user language settings responses."""
    id: str
    user_id: str
    language_id: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
        