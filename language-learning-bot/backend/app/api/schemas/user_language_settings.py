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
    show_debug: bool = Field(False, description="Whether to show debug information")
    
    # Раздельные настройки для каждого типа подсказки
    show_hint_phoneticsound: bool = Field(True, description="Whether to show syllables hint button")
    show_hint_phoneticassociation: bool = Field(True, description="Whether to show association hint button") 
    show_hint_meaning: bool = Field(True, description="Whether to show meaning hint button")
    show_hint_writing: bool = Field(True, description="Whether to show writing hint button")


class UserLanguageSettingsCreate(UserLanguageSettingsBase):
    """Model for creating user language settings."""
    pass


class UserLanguageSettingsUpdate(BaseModel):
    """Model for updating user language settings."""
    start_word: Optional[int] = None
    skip_marked: Optional[bool] = None
    use_check_date: Optional[bool] = None
    show_debug: Optional[bool] = None
    
    # Раздельные настройки для каждого типа подсказки
    show_hint_phoneticsound: Optional[bool] = None
    show_hint_phoneticassociation: Optional[bool] = None
    show_hint_meaning: Optional[bool] = None
    show_hint_writing: Optional[bool] = None


class UserLanguageSettingsInDB(UserLanguageSettingsBase):
    """Model for user language settings as stored in the database."""
    id: str
    user_id: str
    language_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


class UserLanguageSettings(UserLanguageSettingsBase):
    """Model for user language settings responses."""
    id: str
    user_id: str
    language_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True
        