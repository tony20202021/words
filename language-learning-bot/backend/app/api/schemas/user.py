"""
Pydantic schemas for user
UPDATED: Support for individual hint settings.
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field


class UserBase(BaseModel):
    """Base user schema."""
    telegram_id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    is_admin: bool = False


class UserCreate(UserBase):
    """Schema for creating a user."""
    pass


class UserUpdate(BaseModel):
    """Schema for updating a user."""
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    is_admin: Optional[bool] = None


class User(UserBase):
    """Schema for user response."""
    id: str
    created_at: datetime
    updated_at: datetime


class UserInDB(User):
    """Schema for user in database."""
    pass


class UserLanguage(BaseModel):
    """Schema for user language progress."""
    id: str
    name_ru: str
    name_foreign: str
    word_count: int = 0
    words_studied: int = 0
    words_known: int = 0
    progress_percentage: float = 0.0


# НОВОЕ: Схемы для настроек языка пользователя
class UserLanguageSettingsBase(BaseModel):
    """Base schema for user language settings."""
    start_word: int = Field(default=1, ge=1, description="Starting word number")
    skip_marked: bool = Field(default=False, description="Skip marked words")
    use_check_date: bool = Field(default=True, description="Use check date for word repetition")
    show_check_date: bool = Field(default=True, description="Show check date")
    show_debug: bool = Field(default=False, description="Show debug information")
    show_big: bool = Field(default=False, description="Show big word")
    show_writing_images: bool = Field(default=True, description="Show writing images")
    show_short_captions: bool = Field(default=True, description="Show short captions")
    # НОВОЕ: Индивидуальные настройки подсказок
    show_hint_meaning: bool = Field(default=True, description="Show meaning hint buttons")
    show_hint_phoneticassociation: bool = Field(default=True, description="Show phonetic association hint buttons")
    show_hint_phoneticsound: bool = Field(default=True, description="Show phonetic sound hint buttons")
    show_hint_writing: bool = Field(default=True, description="Show writing hint buttons")


class UserLanguageSettingsCreate(UserLanguageSettingsBase):
    """Schema for creating user language settings."""
    user_id: str
    language_id: str


class UserLanguageSettingsUpdate(BaseModel):
    """Schema for updating user language settings."""
    start_word: Optional[int] = Field(None, ge=1, description="Starting word number")
    skip_marked: Optional[bool] = Field(None, description="Skip marked words")
    use_check_date: Optional[bool] = Field(None, description="Use check date for word repetition")
    show_check_date: Optional[bool] = Field(None, description="Show check date")
    show_debug: Optional[bool] = Field(None, description="Show debug information")
    show_big: Optional[bool] = Field(None, description="Show big word")
    show_writing_images: Optional[bool] = Field(None, description="Show writing images")

    # НОВОЕ: Индивидуальные настройки подсказок
    show_hint_meaning: Optional[bool] = Field(None, description="Show meaning hint buttons")
    show_hint_phoneticassociation: Optional[bool] = Field(None, description="Show phonetic association hint buttons")
    show_hint_phoneticsound: Optional[bool] = Field(None, description="Show phonetic sound hint buttons")  
    show_hint_writing: Optional[bool] = Field(None, description="Show writing hint buttons")
    show_short_captions: Optional[bool] = Field(None, description="Show short captions")

class UserLanguageSettings(UserLanguageSettingsBase):
    """Schema for user language settings response."""
    id: str
    user_id: str
    language_id: str
    created_at: datetime
    updated_at: datetime


class UserLanguageSettingsInDB(UserLanguageSettings):
    """Schema for user language settings in database."""
    pass


# НОВОЕ: Схемы для миграции настроек
class LegacySettingsUpdate(BaseModel):
    """Schema for updating legacy settings during migration."""
    show_hints: bool = Field(description="Legacy show hints setting")


class SettingsMigrationResponse(BaseModel):
    """Schema for settings migration response."""
    migrated: bool
    old_settings: Dict[str, Any]
    new_settings: Dict[str, Any]
    message: str


# НОВОЕ: Схемы для статистики настроек
class HintSettingsStats(BaseModel):
    """Schema for hint settings statistics."""
    total_users: int
    users_with_individual_settings: int
    users_with_legacy_settings: int
    migration_percentage: float
    
    # Статистика по типам подсказок
    meaning_enabled_count: int
    phoneticassociation_enabled_count: int
    phoneticsound_enabled_count: int
    writing_enabled_count: int
    
    # Процентное соотношение
    meaning_enabled_percentage: float
    phoneticassociation_enabled_percentage: float
    phoneticsound_enabled_percentage: float
    writing_enabled_percentage: float


class UserSettingsSummary(BaseModel):
    """Schema for user settings summary."""
    user_id: str
    languages_count: int
    settings_per_language: List[Dict[str, Any]]
    total_hints_enabled: int
    most_used_hint_types: List[str]
    least_used_hint_types: List[str]


# НОВОЕ: Схемы для валидации настроек
class SettingsValidationError(BaseModel):
    """Schema for settings validation error."""
    field: str
    value: Any
    error: str
    suggestion: Optional[str] = None


class SettingsValidationResponse(BaseModel):
    """Schema for settings validation response."""
    valid: bool
    errors: List[SettingsValidationError] = []
    warnings: List[str] = []
    corrected_settings: Optional[Dict[str, Any]] = None


# НОВОЕ: Схемы для экспорта/импорта настроек
class UserSettingsExport(BaseModel):
    """Schema for exporting user settings."""
    user_id: str
    telegram_id: int
    username: Optional[str]
    export_date: datetime
    language_settings: List[UserLanguageSettings]


class UserSettingsImport(BaseModel):
    """Schema for importing user settings."""
    user_id: str
    language_settings: List[UserLanguageSettingsCreate]
    overwrite_existing: bool = False


class SettingsImportResponse(BaseModel):
    """Schema for settings import response."""
    success: bool
    imported_count: int
    skipped_count: int
    error_count: int
    errors: List[str] = []
    message: str
    