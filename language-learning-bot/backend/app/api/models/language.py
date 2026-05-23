"""
Models related to languages.
"""

from typing import Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

class LanguageBase(BaseModel):
    """Base model for language."""
    name_ru: str = Field(..., description="Russian name of the language")
    name_foreign: str = Field(..., description="Native name of the language")

class LanguageCreate(LanguageBase):
    """Create model for language."""
    pass

class LanguageUpdate(BaseModel):
    """Update model for language."""
    name_ru: Optional[str] = Field(None, description="Russian name of the language")
    name_foreign: Optional[str] = Field(None, description="Native name of the language")

class LanguageInDB(LanguageBase):
    """Database model for language."""
    id: str = Field(..., description="Unique identifier")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    model_config = ConfigDict(from_attributes=True)

class Language(LanguageInDB):
    """Response model for language."""
    word_count: Optional[int] = Field(0, description="Number of words for this language")