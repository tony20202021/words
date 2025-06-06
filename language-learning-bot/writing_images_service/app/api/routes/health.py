"""
Health check routes for writing image service.
Роуты проверки здоровья сервиса генерации картинок написания.
"""

import logging
import time
import os
from datetime import datetime
from fastapi import APIRouter
from typing import Dict, Any

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])

# Service start time for uptime calculation
_service_start_time = time.time()

@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """
    Basic health check endpoint.
    Базовая проверка здоровья сервиса.
    
    Returns:
        Dict with health status information
    """
    try:
        current_time = time.time()
        uptime_seconds = int(current_time - _service_start_time)
        
        return {
            "status": "healthy",
            "service": "writing_image_service",
            "timestamp": datetime.now().isoformat(),
            "uptime_seconds": uptime_seconds,
            "version": "1.0.0"
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {e}", exc_info=True)
        return {
            "status": "unhealthy",
            "service": "writing_image_service",
            "timestamp": datetime.now().isoformat(),
            "error": str(e)
        }

@router.get("/health/detailed")
async def detailed_health_check() -> Dict[str, Any]:
    """
    Detailed health check with system information.
    Детальная проверка здоровья с системной информацией.
    
    Returns:
        Dict with detailed health status information
    """
    try:
        current_time = time.time()
        uptime_seconds = int(current_time - _service_start_time)
        
        # Check temp directory
        temp_dir_status = "ok"
        temp_dir_path = "./temp/generated_images"
        try:
            os.makedirs(temp_dir_path, exist_ok=True)
            if not os.access(temp_dir_path, os.W_OK):
                temp_dir_status = "not_writable"
        except Exception as e:
            temp_dir_status = f"error: {e}"
        
        # Get system info
        try:
            import psutil
            memory_info = psutil.virtual_memory()
            disk_info = psutil.disk_usage('.')
            system_info = {
                "memory_percent": memory_info.percent,
                "disk_percent": disk_info.percent,
                "available_memory_mb": memory_info.available // (1024 * 1024),
                "available_disk_gb": disk_info.free // (1024 * 1024 * 1024)
            }
        except ImportError:
            system_info = {"note": "psutil not available for system metrics"}
        except Exception as e:
            system_info = {"error": str(e)}
        
        return {
            "status": "healthy",
            "service": "writing_image_service",
            "timestamp": datetime.now().isoformat(),
            "uptime_seconds": uptime_seconds,
            "version": "1.0.0",
            "components": {
                "temp_directory": temp_dir_status,
                "image_generation": "ready"
            },
            "system": system_info,
            "configuration": {
                "default_image_size": "600x600",
                "supported_formats": ["png", "jpg"],
                "max_concurrent_generations": 5
            }
        }
        
    except Exception as e:
        logger.error(f"Detailed health check failed: {e}", exc_info=True)
        return {
            "status": "unhealthy",
            "service": "writing_image_service",
            "timestamp": datetime.now().isoformat(),
            "error": str(e)
        }

@router.get("/health/ready")
async def readiness_check() -> Dict[str, Any]:
    """
    Readiness check for container orchestration.
    Проверка готовности для оркестрации контейнеров.
    
    Returns:
        Dict with readiness status
    """
    try:
        # Check if service is ready to accept requests
        temp_dir_path = "./temp/generated_images"
        os.makedirs(temp_dir_path, exist_ok=True)
        
        # Simple write test
        test_file = os.path.join(temp_dir_path, ".health_check")
        with open(test_file, 'w') as f:
            f.write("health_check")
        os.remove(test_file)
        
        return {
            "status": "ready",
            "service": "writing_image_service",
            "timestamp": datetime.now().isoformat(),
            "checks": {
                "temp_directory": "writable",
                "image_generation": "available"
            }
        }
        
    except Exception as e:
        logger.error(f"Readiness check failed: {e}", exc_info=True)
        return {
            "status": "not_ready",
            "service": "writing_image_service",
            "timestamp": datetime.now().isoformat(),
            "error": str(e)
        }

@router.get("/health/live")
async def liveness_check() -> Dict[str, Any]:
    """
    Liveness check for container orchestration.
    Проверка жизнеспособности для оркестрации контейнеров.
    
    Returns:
        Dict with liveness status
    """
    try:
        return {
            "status": "alive",
            "service": "writing_image_service",
            "timestamp": datetime.now().isoformat(),
            "pid": os.getpid()
        }
        
    except Exception as e:
        logger.error(f"Liveness check failed: {e}", exc_info=True)
        return {
            "status": "dead",
            "service": "writing_image_service",
            "timestamp": datetime.now().isoformat(),
            "error": str(e)
        }
    