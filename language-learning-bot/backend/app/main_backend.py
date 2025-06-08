#!/usr/bin/env python
"""
Entry point for the backend API application.
This module initializes and runs the FastAPI application with all routes and middleware.
"""

import logging
import argparse
import os
import sys
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from dotenv import load_dotenv

# Add the parent directory to sys.path to allow imports from other modules
sys.path.insert(0, str(Path(__file__).parent.parent))

# Попытка импорта Hydra - если он доступен, будет использоваться для конфигурации
try:
    from hydra import compose, initialize
    from omegaconf import OmegaConf
    hydra_available = True
except ImportError:
    hydra_available = False

from app.api.routes import languages, users, words, statistics
from app.api.routes.user_language_settings import router as user_language_settings_router
from app.db.database import connect_to_mongo, close_mongo_connection
from app.utils.logger import setup_logger

# Load environment variables
load_dotenv()

# Загрузка конфигурации
if hydra_available:
    try:
        # Initialize Hydra configuration
        initialize(config_path="../conf/config", version_base=None)
        cfg = compose(config_name="default")
        using_hydra = True
    except Exception as e:
        print(f"Warning: Failed to load Hydra configuration: {e}")
        using_hydra = False
else:
    using_hydra = False
    print("Warning: Hydra is not available, using environment variables")

# Ensure logs directory exists
log_dir = "logs"
if using_hydra and hasattr(cfg, "logging") and hasattr(cfg.logging, "log_dir"):
    log_dir = cfg.logging.log_dir

os.makedirs(os.path.join(os.getcwd(), log_dir), exist_ok=True)

# Set up logging
log_level = os.getenv("LOG_LEVEL", "INFO")
log_format = os.getenv("LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s")

if using_hydra:
    if hasattr(cfg, "logging") and hasattr(cfg.logging, "level"):
        log_level = cfg.logging.level
    if hasattr(cfg, "logging") and hasattr(cfg.logging, "format"):
        log_format = cfg.logging.format

logger = setup_logger(__name__, log_level=log_level, log_format=log_format, log_dir=log_dir)

# Получение настроек
def get_api_settings():
    """
    Get API settings from Hydra or environment variables.
    
    Returns:
        dict: API settings
    """
    # Значения по умолчанию
    settings = {
        "api_prefix": os.getenv("API_PREFIX", "/api"),
        "host": os.getenv("BACKEND_HOST", "0.0.0.0"),
        "port": int(os.getenv("BACKEND_PORT", "8000")),
        "debug_mode": os.getenv("DEBUG", "False").lower() in ("true", "1", "t"),
        "cors_origins": os.getenv("CORS_ORIGINS", "*").split(","),
        "app_name": os.getenv("APP_NAME", "Language Learning Bot"),
        "app_environment": os.getenv("ENVIRONMENT", "development")
    }
    
    # Если используется Hydra, переопределяем значения из конфигурации
    if using_hydra:
        if hasattr(cfg, "api"):
            if hasattr(cfg.api, "prefix"):
                settings["api_prefix"] = cfg.api.prefix
            if hasattr(cfg.api, "host"):
                settings["host"] = cfg.api.host
            if hasattr(cfg.api, "port"):
                settings["port"] = int(cfg.api.port)
            if hasattr(cfg.api, "cors_origins"):
                settings["cors_origins"] = cfg.api.cors_origins.split(",") if isinstance(cfg.api.cors_origins, str) else cfg.api.cors_origins
        
        if hasattr(cfg, "app"):
            if hasattr(cfg.app, "name"):
                settings["app_name"] = cfg.app.name
            if hasattr(cfg.app, "environment"):
                settings["app_environment"] = cfg.app.environment
                settings["debug_mode"] = cfg.app.environment == "development"
    
    return settings

def create_application() -> FastAPI:
    """
    Create and configure the FastAPI application.
    
    Returns:
        Configured FastAPI application
    """
    # Получение настроек из конфигурации
    settings = get_api_settings()
    api_prefix = settings["api_prefix"]
    app_name = settings["app_name"]
    app_environment = settings["app_environment"]
    cors_origins = settings["cors_origins"]
    
    app = FastAPI(
        title=f"{app_name} API",
        description=f"Backend API for {app_name}",
        version="1.0.0",
        docs_url=f"{api_prefix}/docs",
        redoc_url=f"{api_prefix}/redoc",
        openapi_url=f"{api_prefix}/openapi.json"
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins if cors_origins != ["*"] else ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Add event handlers for startup and shutdown
    app.add_event_handler("startup", connect_to_mongo)
    app.add_event_handler("shutdown", close_mongo_connection)
    
    # Include all routers with API prefix
    app.include_router(languages.router, prefix=api_prefix)
    app.include_router(users.router, prefix=api_prefix)
    app.include_router(words.router, prefix=api_prefix)
    app.include_router(statistics.router, prefix=api_prefix)
    app.include_router(user_language_settings_router, prefix="/api")

    # Add health check endpoint
    @app.get("/health", tags=["health"])
    async def health_check():
        """Health check endpoint that always returns 200 OK."""
        return {
            "status": "ok", 
            "environment": app_environment,
            "config_source": "Hydra" if using_hydra else "Environment Variables"
        }
    
    return app

app = create_application()

def run_server(port_override=None):
    """
    Run the server using uvicorn.
    
    Args:
        port_override (int, optional): Override port from command line argument
    """
    # Получение настроек сервера
    settings = get_api_settings()
    host = settings["host"]
    port = port_override if port_override else settings["port"]
    debug_mode = settings["debug_mode"]
    
    logger.info(f"Starting backend server at {host}:{port}")
    logger.info(f"Configuration source: {'Hydra' if using_hydra else 'Environment Variables'}")
    
    # Run the server using uvicorn
    uvicorn.run(
        "app.main_backend:app",
        host=host,
        port=port,
        reload=debug_mode,
        log_level="info"
    )

if __name__ == "__main__":
    """
    Run the application if this module is executed directly.
    """
    try:
        parser = argparse.ArgumentParser(description='Запуск бэкенд API')
        
        # Добавляем аргумент process-name для идентификации процесса
        parser.add_argument('--process-name', type=str, help='Имя процесса для идентификации')
        
        # Добавляем аргумент для порта (может переопределить переменную окружения)
        parser.add_argument('--port', type=int, help='Порт для запуска сервера')
        
        # Парсим аргументы, но не выходим при ошибке для обратной совместимости
        args, unknown = parser.parse_known_args()
        
        # Логируем информацию о запуске
        if args.process_name:
            logger.info(f"Запуск бэкенда с идентификатором: {args.process_name}")
        else:
            logger.info("Запуск бэкенда без идентификатора")
        
        # Логируем информацию о процессе
        pid = os.getpid()
        logger.info(f"ID процесса (PID): {pid}")
        logger.info(f"Рабочий каталог: {os.getcwd()}")
        
        # Запускаем сервер с переопределением порта, если он указан
        port_override = args.port
        if port_override:
            logger.info(f"Используется порт из аргументов командной строки: {port_override}")
        
        run_server(port_override)
        
    except KeyboardInterrupt:
        logger.info("Получен сигнал прерывания.")
        logger.info("Завершение...")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}", exc_info=True)
    finally:
        logger.info("Процесс завершен!")
        