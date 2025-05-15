"""
Models related to users.
"""

from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field

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

    class Config:
        from_attributes = True  # Updated from orm_mode to from_attributes
        json_schema_extra = {   # Updated from schema_extra to json_schema_extra
            "example": {
                "id": "5f9b3b3b9c9d440000b3b3b3",
                "telegram_id": 123456789,
                "username": "john_doe",
                "first_name": "John",
                "last_name": "Doe",
                "is_admin": False,
                "created_at": "2020-10-29T12:00:00",
                "updated_at": "2020-10-29T12:00:00"
            }
        }

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