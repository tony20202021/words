#!/usr/bin/env python
"""
Entry point for the writing image generation service.
This module initializes and runs the FastAPI application for generating writing images.
"""

import logging
import argparse
import os
import sys
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from dotenv import load_dotenv

# Add the parent directory to sys.path to allow imports from other modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from hydra import compose, initialize
from hydra.core.global_hydra import GlobalHydra

from app.api.routes import writing_images, health
from app.utils.logger import setup_logger
from app.utils import config_holder

# Load environment variables
load_dotenv()

# Загрузка конфигурации Hydra (обязательно)
try:
    # Очищаем GlobalHydra если он уже инициализирован
    if GlobalHydra().is_initialized():
        GlobalHydra.instance().clear()
    
    # Initialize Hydra configuration
    initialize(config_path="../conf/config", version_base=None)
    cfg = compose(config_name="default")
    
    # Сохраняем в config_holder для совместимости
    config_holder.cfg = cfg
    
    print("✅ Hydra configuration loaded successfully")
    
except Exception as e:
    print(f"❌ ОШИБКА: Не удалось загрузить конфигурацию Hydra: {e}")
    print("Убедитесь, что:")
    print("  - Директория conf/config существует")
    print("  - Файл conf/config/default.yaml существует")
    print("  - Конфигурационные файлы корректны")
    sys.exit(1)

# Ensure logs directory exists
log_dir = cfg.logging.log_dir if hasattr(cfg, "logging") and hasattr(cfg.logging, "log_dir") else "logs"
os.makedirs(os.path.join(os.getcwd(), log_dir), exist_ok=True)

# Set up logging
log_level = cfg.logging.level if hasattr(cfg, "logging") and hasattr(cfg.logging, "level") else "INFO"
log_format = cfg.logging.format if hasattr(cfg, "logging") and hasattr(cfg.logging, "format") else "%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s"

logger = setup_logger(__name__, log_level=log_level, log_format=log_format, log_dir=log_dir)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler - выполняется при startup и shutdown."""
    
    # Startup
    pid = os.getpid()
    parent_pid = os.getppid()
    
    logger.info("=" * 50)
    logger.info("🚀 Writing Image Service Started")
    logger.info("=" * 50)
    logger.info(f"🆔 Process ID (PID): {pid}")
    logger.info(f"👨‍👦 Parent PID: {parent_pid}")
    logger.info(f"📁 Working directory: {os.getcwd()}")
    logger.info(f"🐍 Python: {sys.version}")
    logger.info(f"💻 Platform: {sys.platform}")
    logger.info(f"🔧 Config source: Hydra")
    logger.info(f"🏠 Host: {cfg.api.host}")
    logger.info(f"🔌 Port: {cfg.api.port}")
    logger.info(f"🔄 Debug mode: {cfg.api.debug}")
    logger.info(f"🌐 API docs: http://{cfg.api.host}:{cfg.api.port}{cfg.api.prefix}/docs")
    logger.info(f"❤️ Health check: http://{cfg.api.host}:{cfg.api.port}/health")
    logger.info("=" * 50)
    
    # Yield control to the application
    yield
    
    # Shutdown
    logger.info("🛑 Writing Image Service shutting down...")

def create_application() -> FastAPI:
    """Create and configure the FastAPI application."""
    
    # Получаем настройки из cfg (Hydra обязателен)
    api_prefix = cfg.api.prefix
    app_name = cfg.app.name
    app_environment = cfg.app.environment
    cors_origins = cfg.api.cors_origins
    
    # Парсим CORS origins
    if isinstance(cors_origins, str):
        cors_origins = cors_origins.split(",") if cors_origins != "*" else ["*"]
    
    app = FastAPI(
        title=app_name,
        description="Service for generating writing images for language learning",
        version="1.0.0",
        docs_url=f"{api_prefix}/docs",
        redoc_url=f"{api_prefix}/redoc",
        openapi_url=f"{api_prefix}/openapi.json",
        lifespan=lifespan  # Используем новый lifespan вместо on_event
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include routers
    app.include_router(writing_images.router, prefix=api_prefix)
    app.include_router(health.router)

    # Health check endpoint
    @app.get("/health", tags=["health"])
    async def health_check():
        return {
            "status": "healthy", 
            "service": "writing_image_service",
            "environment": app_environment,
            "config_source": "Hydra",
            "version": "1.0.0",
            "pid": os.getpid()
        }
    
    return app

app = create_application()

def run_server(port_override=None):
    """Run the server using uvicorn."""
    
    # Получаем настройки из cfg (Hydra обязателен)
    host = cfg.api.host
    port = int(cfg.api.port)
    debug_mode = bool(cfg.api.debug)
    
    # Override port if specified
    if port_override:
        port = port_override
        logger.info(f"Port overridden to: {port}")
    
    if debug_mode:
        # Development mode with specific reload directories
        uvicorn.run(
            "app.main_writing_service:app",
            host=host,
            port=port,
            reload=True,
            reload_dirs=["app"], 
            log_level="info"
            # отслеживаются только файлы *.py
            # при изменениях конфигурации в каталоге "conf" - перезапускать сервис руками
        )
    else:
        # Production mode without reload
        uvicorn.run(
            "app.main_writing_service:app",
            host=host,
            port=port,
            reload=False,
            log_level="info"
        )

if __name__ == "__main__":
    try:
        parser = argparse.ArgumentParser(description='Запуск сервиса генерации картинок написания')
        parser.add_argument('--process-name', type=str, help='Имя процесса для идентификации')
        parser.add_argument('--port', type=int, help='Порт для запуска сервиса')
        
        args, unknown = parser.parse_known_args()
        
        # Краткое логирование только основной информации
        if args.process_name:
            logger.info(f"🏷️ Process name: {args.process_name}")
        
        # Запускаем сервер (детальная информация будет в startup event)
        run_server(args.port)
        
    except KeyboardInterrupt:
        logger.info("⏹️ Interrupted")
    except Exception as e:
        logger.error(f"💥 Critical error: {e}", exc_info=True)
    finally:
        logger.info("🏁 Service stopped")
        
