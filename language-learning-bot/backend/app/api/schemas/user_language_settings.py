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
    show_big: bool = Field(False, description="Whether to show big word")
    show_writing_images: bool = Field(True, description="Whether to show writing images")

    # Раздельные настройки для каждого типа подсказки
    show_hint_phoneticsound: bool = Field(True, description="Whether to show syllables hint button")
    show_hint_phoneticassociation: bool = Field(True, description="Whether to show association hint button") 
    show_hint_meaning: bool = Field(True, description="Whether to show meaning hint button")
    show_hint_writing: bool = Field(True, description="Whether to show writing hint button")
    show_short_captions: bool = Field(True, description="Whether to show short captions")

    receive_messages: bool = Field(True, description="Whether to receive messages")

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
    show_big: Optional[bool] = None
    show_writing_images: Optional[bool] = None
    
    # Раздельные настройки для каждого типа подсказки
    show_hint_phoneticsound: Optional[bool] = None
    show_hint_phoneticassociation: Optional[bool] = None
    show_hint_meaning: Optional[bool] = None
    show_hint_writing: Optional[bool] = None
    show_short_captions: Optional[bool] = None
    receive_messages: Optional[bool] = None
    
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
        