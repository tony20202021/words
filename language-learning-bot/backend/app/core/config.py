"""
Configuration module for the backend application.
This module contains the configuration settings using Pydantic's BaseSettings.
"""

import os
from typing import List
from functools import lru_cache
from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    """Settings for the application using environment variables."""
    
    # API settings
    api_prefix: str = Field("/api", env="API_PREFIX")
    debug_mode: bool = Field(False, env="DEBUG_MODE")
    host: str = Field("0.0.0.0", env="HOST")
    port: int = Field(8000, env="PORT")
    
    # CORS settings
    cors_origins: List[str] = Field(["*"], env="CORS_ORIGINS")
    
    # MongoDB settings
    mongodb_url: str = Field("mongodb://localhost:27017", env="MONGODB_URL")
    mongodb_db_name: str = Field("language_learning_bot", env="MONGODB_DB_NAME")
    mongodb_max_pool_size: int = Field(10, env="MONGODB_MAX_POOL_SIZE")
    mongodb_min_pool_size: int = Field(1, env="MONGODB_MIN_POOL_SIZE")
    
    # Application specific settings
    default_pagination_limit: int = Field(100, env="DEFAULT_PAGINATION_LIMIT")
    max_pagination_limit: int = Field(1000, env="MAX_PAGINATION_LIMIT")
    
    class Config:
        """Pydantic settings configuration."""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """
    Get the application settings using a cache to avoid reloading.
    
    Returns:
        Settings instance
    """
    return Settings()