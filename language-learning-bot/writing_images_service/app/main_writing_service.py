#!/usr/bin/env python
"""
Entry point for the writing image generation service with AI capabilities.
This module initializes and runs the FastAPI application for generating writing images using real AI models.
"""

# lsof -i :8600

import logging
import argparse
import os
import sys
import time
import asyncio
from pathlib import Path
from contextlib import asynccontextmanager
from typing import Dict, Any, Optional

import torch
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

# Add the parent directory and project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from common.version import __version__ as PROJECT_VERSION

from hydra import compose, initialize
from hydra.core.global_hydra import GlobalHydra

from app.api.routes import writing_images, health
from app.utils.logger import setup_logger
from app.utils import config_holder
from app.ai.models.gpu_manager import GPUManager
from app.api.routes.services.writing_image_service import WritingImageService

# Глобальные сервисы
gpu_manager: Optional[GPUManager] = None
writing_service: Optional[WritingImageService] = None

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

async def _check_system_requirements():
    """Проверяет системные требования для AI генерации."""
    logger.info("🔍 Checking system requirements...")
    
    # Проверяем Python версию
    python_version = sys.version_info
    if python_version < (3, 8):
        raise RuntimeError(f"Python 3.8+ required, got {python_version.major}.{python_version.minor}")
    
    # Проверяем CUDA
    cuda_available = torch.cuda.is_available()
    if not cuda_available:
        raise RuntimeError("CUDA not available. GPU is required for AI image generation.")
    
    # Получаем информацию о GPU
    device_count = torch.cuda.device_count()
    device_name = torch.cuda.get_device_name(0)
    total_memory = torch.cuda.get_device_properties(0).total_memory / 1024**3
    
    logger.info(f"✅ System requirements check passed:")
    logger.info(f"   🐍 Python: {python_version.major}.{python_version.minor}.{python_version.micro}")
    logger.info(f"   🎮 CUDA: {torch.version.cuda}")
    logger.info(f"   🔥 PyTorch: {torch.__version__}")
    logger.info(f"   🖥️ GPU: {device_name}")
    logger.info(f"   💾 GPU Memory: {total_memory:.1f}GB")
    logger.info(f"   🔢 GPU Count: {device_count}")
    
    # Проверяем критичные библиотеки
    critical_libraries = ["transformers", "diffusers", "accelerate", "safetensors"]
    missing_libraries = []
    
    for lib_name in critical_libraries:
        try:
            lib = __import__(lib_name)
            version = getattr(lib, "__version__", "unknown")
            logger.info(f"   📚 {lib_name}: {version}")
        except ImportError:
            missing_libraries.append(lib_name)
    
    if missing_libraries:
        raise RuntimeError(f"Critical AI libraries missing: {', '.join(missing_libraries)}")

async def _initialize_gpu_manager():
    """Инициализирует GPU Manager."""
    global gpu_manager
    
    logger.info("🎮 Initializing GPU Manager...")
    
    try:
        gpu_manager = GPUManager()
        
        # Получаем статус GPU
        gpu_status = gpu_manager.get_gpu_status()
        
        logger.info(f"✅ GPU Manager initialized:")
        logger.info(f"   📊 Memory: {gpu_status.used_memory_gb:.1f}GB / {gpu_status.total_memory_gb:.1f}GB")
        logger.info(f"   🌡️ Temperature: {gpu_status.temperature_celsius}°C" if gpu_status.temperature_celsius else "   🌡️ Temperature: N/A")
        logger.info(f"   ⚡ Power: {gpu_status.power_usage_watts}W" if gpu_status.power_usage_watts else "   ⚡ Power: N/A")
        logger.info(f"   🏗️ Optimization Profile: {gpu_manager.optimization_profile.name}")
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize GPU Manager: {e}")
        raise

async def _initialize_writing_service():
    """Инициализирует Writing Service (без загрузки AI моделей)."""
    global writing_service
    
    logger.info("🤖 Initializing Writing Service...")
    
    try:
        writing_service = WritingImageService()
        
        # Проверяем статус сервиса
        service_status = await writing_service.get_service_status()
        
        logger.info(f"✅ Writing Service initialized:")
        logger.info(f"   🔧 Implementation: {service_status.get('implementation', 'unknown')}")
        logger.info(f"   📊 Generation count: {service_status.get('total_generations', 0)}")
        logger.info(f"   🏗️ AI Status: {service_status.get('ai_status', {}).get('initialized', 'not_initialized')}")
        logger.info("   ⏳ AI models will be loaded on first request (lazy initialization)")
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize Writing Service: {e}")
        raise

async def _log_service_configuration():
    """Логирует конфигурацию сервиса."""
    logger.info("⚙️ Service Configuration:")
    
    # API конфигурация
    logger.info(f"   🌐 API Host: {cfg.api.host}")
    logger.info(f"   🔌 API Port: {cfg.api.port}")
    logger.info(f"   🔄 Debug Mode: {cfg.api.debug}")
    logger.info(f"   🔗 API Prefix: {cfg.api.prefix}")
    
    # AI конфигурация (если доступна)
    if hasattr(cfg, 'ai_generation'):
        ai_cfg = cfg.ai_generation
        if hasattr(ai_cfg, 'models'):
            logger.info(f"   🤖 Base Model: {ai_cfg.models.base_model}")
    
    # GPU конфигурация
    if gpu_manager:
        memory_info = gpu_manager.get_memory_usage()
        logger.info(f"   💾 GPU Memory Available: {memory_info.get('free_gb', 0):.1f}GB")
        logger.info(f"   📦 Recommended Batch Size: {gpu_manager.get_recommended_batch_size()}")

async def _cleanup_services():
    """Очищает ресурсы сервисов."""
    global writing_service, gpu_manager
    
    logger.info("🧹 Cleaning up services...")
    
    try:
        # Очищаем Writing Service
        if writing_service:
            await writing_service.cleanup()
            writing_service = None
            logger.info("✅ Writing Service cleaned up")
        
        # Очищаем GPU Manager
        if gpu_manager:
            gpu_manager.clear_cache(aggressive=True)
            gpu_manager = None
            logger.info("✅ GPU Manager cleaned up")
        
        # Финальная очистка GPU памяти
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            logger.info("✅ GPU cache cleared")
        
    except Exception as e:
        logger.error(f"❌ Error during cleanup: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan event handler для управления запуском и остановкой сервиса.
    Инициализирует AI компоненты при старте и корректно очищает ресурсы при остановке.
    """
    
    # ============ STARTUP ============
    startup_start = time.time()
    pid = os.getpid()
    parent_pid = os.getppid()
    
    logger.info("=" * 60)
    logger.info("🚀 WRITING IMAGE SERVICE WITH AI GENERATION")
    logger.info("=" * 60)
    logger.info(f"🆔 Process ID (PID): {pid}")
    logger.info(f"👨‍👦 Parent PID: {parent_pid}")
    logger.info(f"📁 Working directory: {os.getcwd()}")
    logger.info(f"🐍 Python: {sys.version}")
    logger.info(f"💻 Platform: {sys.platform}")
    logger.info(f"🔧 Config source: Hydra")
    
    try:
        # 1. Проверяем системные требования
        await _check_system_requirements()
        
        # 2. Инициализируем GPU Manager
        await _initialize_gpu_manager()
        
        # 3. Инициализируем Writing Service (без загрузки AI моделей)
        await _initialize_writing_service()
        
        # 4. Логируем конфигурацию
        await _log_service_configuration()
        
        startup_time = time.time() - startup_start
        
        logger.info("=" * 60)
        logger.info(f"✅ SERVICE STARTED SUCCESSFULLY in {startup_time:.2f}s")
        logger.info(f"🌐 API docs: http://{cfg.api.host}:{cfg.api.port}{cfg.api.prefix}/docs")
        logger.info(f"❤️ Health check: http://{cfg.api.host}:{cfg.api.port}/health")
        logger.info(f"🤖 AI models will load on first request")
        logger.info(f"💡 Press Ctrl+C to stop the service")
        logger.info("=" * 60)
        
        yield  # Сервис работает
        
    except Exception as e:
        logger.error(f"❌ FAILED TO START SERVICE: {e}")
        logger.error("Service will not be available for requests")
        raise
    
    # ============ SHUTDOWN ============
    shutdown_start = time.time()
    logger.info("🛑 SHUTTING DOWN Writing Image Service...")
    
    try:
        # Очищаем ресурсы
        await _cleanup_services()
        
        shutdown_time = time.time() - shutdown_start
        logger.info(f"✅ SERVICE SHUT DOWN GRACEFULLY in {shutdown_time:.2f}s")
        
    except Exception as e:
        logger.error(f"❌ Error during shutdown: {e}")

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
        title=f"{app_name} (AI Generation)",
        description="Service for generating writing images using real AI models for language learning",
        version=PROJECT_VERSION,
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
    
    # Глобальный exception handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request, exc):
        logger.error(f"Unhandled exception: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "detail": str(exc) if cfg.api.debug else "An unexpected error occurred"
            }
        )
    
    # Include routers
    app.include_router(writing_images.router, prefix=api_prefix)
    app.include_router(health.router)  # Health checks на корневом уровне
    
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
        # Получаем настройки reload из конфигурации
        reload_dirs = ["app"]  # По умолчанию
        
        if hasattr(cfg.api, 'development') and hasattr(cfg.api.development, 'reload_dirs'):
            reload_dirs = list(cfg.api.development.reload_dirs)
            logger.info(f"📂 Using reload dirs from config: {reload_dirs}")
        
        # Проверяем существование путей и конвертируем в абсолютные
        valid_reload_dirs = []
        current_dir = Path(__file__).parent
        
        for reload_dir in reload_dirs:
            if reload_dir.startswith("../"):
                # Относительный путь от текущего файла
                abs_path = (current_dir / reload_dir).resolve()
            else:
                # Относительный путь от рабочей директории
                abs_path = Path(reload_dir).resolve()
            
            if abs_path.exists():
                valid_reload_dirs.append(str(abs_path))
                logger.info(f"✅ Watching: {abs_path}")
            else:
                logger.warning(f"⚠️ Path not found, skipping: {abs_path}")
        
        # Development mode with specific reload directories
        logger.info("🔄 Starting in DEVELOPMENT mode with auto-reload")
        
        uvicorn.run(
            "app.main_writing_service:app",
            host=host,
            port=port,
            reload=True,
            reload_dirs=valid_reload_dirs,
            log_level="info"
        )
    else:
        # Production mode without reload
        logger.info("🏭 Starting in PRODUCTION mode")
        uvicorn.run(
            "app.main_writing_service:app",
            host=host,
            port=port,
            reload=False,
            log_level="info",
            workers=1  # AI модели не поддерживают multi-worker
        )
            
if __name__ == "__main__":
    try:
        parser = argparse.ArgumentParser(description='Запуск сервиса генерации картинок написания с AI')
        parser.add_argument('--process-name', type=str, help='Имя процесса для идентификации')
        parser.add_argument('--port', type=int, help='Порт для запуска сервиса')
        
        args, unknown = parser.parse_known_args()
        
        # Краткое логирование только основной информации
        if args.process_name:
            logger.info(f"🏷️ Process name: {args.process_name}")
        
        # Запускаем сервер (детальная информация будет в startup event)
        run_server(args.port)
        
    except KeyboardInterrupt:
        logger.info("⏹️ Service interrupted by user")
    except Exception as e:
        logger.error(f"💥 Critical error starting service: {e}", exc_info=True)
    finally:
        logger.info("🏁 Service stopped")
