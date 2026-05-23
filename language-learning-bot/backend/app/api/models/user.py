"""
Models related to users.
"""

from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

class UserBase(BaseModel):
    """Base model for user."""
    telegram_id: int = Field(..., description="Telegram ID of the user")
    username: Optional[str] = Field(None, description="Telegram username")
    first_name: str = Field(..., description="First name")
    last_name: Optional[str] = Field(None, description="Last name")
    is_admin: bool = Field(False, description="Is user an admin")

class UserCreate(UserBase):
    """Create model for user."""
    pass

class UserUpdate(BaseModel):
    """Update model for user."""
    username: Optional[str] = Field(None, description="Telegram username")
    first_name: Optional[str] = Field(None, description="First name")
    last_name: Optional[str] = Field(None, description="Last name")
    is_admin: Optional[bool] = Field(None, description="Is user an admin")

class UserInDB(UserBase):
    """Database model for user."""
    id: str = Field(..., description="Unique identifier")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    model_config = ConfigDict(from_attributes=True)

class User(UserInDB):
    """Response model for user."""
    pass

class UserLanguage(BaseModel):
    """Model for language that user is learning."""
    id: str = Field(..., description="Language ID")
    name_ru: str = Field(..., description="Russian name of the language")
    name_foreign: str = Field(..., description="Native name of the language")
    word_count: int = Field(0, description="Total number of words")
    words_studied: int = Field(0, description="Number of words studied")
    words_known: int = Field(0, description="Number of words known")
    progress_percentage: float = Field(0.0, description="Percentage of progress")