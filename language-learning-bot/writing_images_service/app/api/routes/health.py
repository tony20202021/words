"""
Health check routes for Writing Service.
Роуты для проверки здоровья сервиса.
"""

import time
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
import torch

from app.services.writing_image_service import WritingImageService
from app.ai.models.gpu_manager import GPUManager
from app.utils.logger import get_module_logger

logger = get_module_logger(__name__)

router = APIRouter(tags=["health"])

# Глобальные сервисы (будут инициализированы при первом обращении)
_writing_service: Optional[WritingImageService] = None
_gpu_manager: Optional[GPUManager] = None

def get_writing_service() -> WritingImageService:
    """Get writing service instance."""
    global _writing_service
    if _writing_service is None:
        _writing_service = WritingImageService()
    return _writing_service

def get_gpu_manager() -> GPUManager:
    """Get GPU manager instance."""
    global _gpu_manager
    if _gpu_manager is None:
        try:
            _gpu_manager = GPUManager()
        except Exception as e:
            logger.error(f"Failed to initialize GPU manager: {e}")
            raise HTTPException(status_code=503, detail=f"GPU initialization failed: {e}")
    return _gpu_manager

@router.get("/health")
async def basic_health_check():
    """
    Basic health check endpoint.
    Базовая проверка здоровья сервиса.
    
    Returns:
        JSON response with basic service status
    """
    try:
        current_time = datetime.utcnow()
        
        # Базовая проверка CUDA
        cuda_available = torch.cuda.is_available()
        
        response = {
            "status": "healthy" if cuda_available else "degraded",
            "service": "writing_image_service",
            "timestamp": current_time.isoformat(),
            "uptime_seconds": int(time.time()),  # Будет пересчитан в сервисе
            "version": "1.0.0",
            "cuda_available": cuda_available
        }
        
        if not cuda_available:
            response["warnings"] = ["CUDA not available - AI generation will not work"]
        
        status_code = 200 if cuda_available else 503
        return JSONResponse(content=response, status_code=status_code)
        
    except Exception as e:
        logger.error(f"Basic health check failed: {e}")
        return JSONResponse(
            content={
                "status": "unhealthy",
                "service": "writing_image_service", 
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e)
            },
            status_code=503
        )

@router.get("/health/detailed")
async def detailed_health_check(
    writing_service: WritingImageService = Depends(get_writing_service),
    gpu_manager: GPUManager = Depends(get_gpu_manager)
):
    """
    Detailed health check with AI components status.
    Детальная проверка здоровья с статусом AI компонентов.
    
    Returns:
        Comprehensive service status including AI models and GPU
    """
    try:
        start_time = time.time()
        
        # Получаем статус сервиса
        service_status = await writing_service.get_service_status()
        
        # Получаем статус GPU
        gpu_status = gpu_manager.get_gpu_status()
        gpu_diagnostics = gpu_manager.get_diagnostics()
        
        # Проверяем компоненты PyTorch
        pytorch_info = {
            "version": torch.__version__,
            "cuda_version": torch.version.cuda,
            "cudnn_version": torch.backends.cudnn.version() if torch.backends.cudnn.is_available() else None,
            "cuda_available": torch.cuda.is_available(),
            "device_count": torch.cuda.device_count() if torch.cuda.is_available() else 0
        }
        
        if torch.cuda.is_available():
            pytorch_info["current_device"] = torch.cuda.current_device()
            pytorch_info["device_name"] = torch.cuda.get_device_name()
        
        # Проверяем доступность ключевых библиотек
        library_status = await _check_ai_libraries()
        
        # Определяем общий статус здоровья
        overall_status = _determine_overall_health(
            service_status, gpu_status, pytorch_info, library_status
        )
        
        check_duration = int((time.time() - start_time) * 1000)
        
        response = {
            "status": overall_status["status"],
            "service": "writing_image_service",
            "timestamp": datetime.utcnow().isoformat(),
            "check_duration_ms": check_duration,
            "version": "1.0.0",
            
            # Service components
            "service_status": service_status,
            "gpu_status": {
                "available": gpu_status.available,
                "device_name": gpu_status.device_name,
                "memory": {
                    "total_gb": gpu_status.total_memory_gb,
                    "used_gb": gpu_status.used_memory_gb,
                    "free_gb": gpu_status.free_memory_gb,
                    "utilization_percent": gpu_status.utilization_percent
                },
                "temperature_celsius": gpu_status.temperature_celsius,
                "power_usage_watts": gpu_status.power_usage_watts
            },
            "pytorch_info": pytorch_info,
            "library_status": library_status,
            "gpu_diagnostics": {
                "optimization_profile": gpu_diagnostics["optimization_profile"]["name"],
                "recommendations": gpu_diagnostics["recommendations"]
            },
            
            # Health summary
            "health_summary": overall_status,
            "warnings": overall_status.get("warnings", []),
            "errors": overall_status.get("errors", [])
        }
        
        status_code = 200 if overall_status["status"] == "healthy" else 503
        return JSONResponse(content=response, status_code=status_code)
        
    except Exception as e:
        logger.error(f"Detailed health check failed: {e}", exc_info=True)
        return JSONResponse(
            content={
                "status": "unhealthy",
                "service": "writing_image_service",
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e),
                "check_type": "detailed"
            },
            status_code=503
        )

@router.get("/health/ready")
async def readiness_check(
    writing_service: WritingImageService = Depends(get_writing_service)
):
    """
    Readiness check - verifies service is ready to handle requests.
    Проверка готовности - проверяет что сервис готов обрабатывать запросы.
    
    Returns:
        Ready status with AI initialization state
    """
    try:
        start_time = time.time()
        
        # Проверяем базовые требования
        cuda_available = torch.cuda.is_available()
        if not cuda_available:
            return JSONResponse(
                content={
                    "ready": False,
                    "reason": "CUDA not available",
                    "timestamp": datetime.utcnow().isoformat(),
                    "requirements_met": False
                },
                status_code=503
            )
        
        # Получаем статус сервиса
        service_status = await writing_service.get_service_status()
        
        # Проверяем готовность AI компонентов
        ai_ready = False
        ai_status = "unknown"
        
        if "ai_status" in service_status:
            ai_status_data = service_status["ai_status"]
            if isinstance(ai_status_data, dict):
                ai_ready = (
                    ai_status_data.get("models_loaded", False) and
                    ai_status_data.get("pipeline_ready", False)
                )
                ai_status = "initialized" if ai_ready else "not_initialized"
            else:
                ai_status = "error"
        
        check_duration = int((time.time() - start_time) * 1000)
        
        # Сервис готов если CUDA доступен (AI инициализируется при первом запросе)
        ready = cuda_available
        
        response = {
            "ready": ready,
            "timestamp": datetime.utcnow().isoformat(),
            "check_duration_ms": check_duration,
            "components": {
                "cuda": cuda_available,
                "ai_models": ai_ready,
                "ai_status": ai_status
            },
            "initialization": {
                "lazy_loading": True,
                "ai_models_preloaded": ai_ready,
                "ready_for_requests": ready
            }
        }
        
        if not ready:
            response["reason"] = "CUDA not available"
        elif not ai_ready:
            response["note"] = "AI models will be loaded on first request (lazy initialization)"
        
        status_code = 200 if ready else 503
        return JSONResponse(content=response, status_code=status_code)
        
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        return JSONResponse(
            content={
                "ready": False,
                "reason": f"Health check error: {str(e)}",
                "timestamp": datetime.utcnow().isoformat(),
                "error": True
            },
            status_code=503
        )

@router.get("/health/live")
async def liveness_check():
    """
    Liveness check - verifies service is alive and responsive.
    Проверка жизнеспособности - проверяет что сервис живой и отвечает.
    
    Returns:
        Basic liveness status
    """
    try:
        start_time = time.time()
        
        # Простая проверка что сервис отвечает
        current_time = datetime.utcnow()
        
        # Проверяем что PyTorch загружен
        pytorch_loaded = hasattr(torch, '__version__')
        
        check_duration = int((time.time() - start_time) * 1000)
        
        response = {
            "alive": True,
            "timestamp": current_time.isoformat(),
            "check_duration_ms": check_duration,
            "service": "writing_image_service",
            "pytorch_loaded": pytorch_loaded
        }
        
        return JSONResponse(content=response, status_code=200)
        
    except Exception as e:
        logger.error(f"Liveness check failed: {e}")
        return JSONResponse(
            content={
                "alive": False,
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e),
                "service": "writing_image_service"
            },
            status_code=503
        )

@router.post("/health/warmup")
async def warmup_ai_models(
    writing_service: WritingImageService = Depends(get_writing_service)
):
    """
    Warm up AI models for faster generation.
    Прогрев AI моделей для более быстрой генерации.
    
    Returns:
        Warmup results and performance metrics
    """
    try:
        logger.info("Starting AI warmup via health endpoint...")
        
        # Запускаем прогрев
        warmup_result = await writing_service.warmup_ai()
        
        if warmup_result["success"]:
            logger.info(f"✓ AI warmup completed successfully in {warmup_result['total_time_ms']}ms")
            status_code = 200
        else:
            logger.warning(f"AI warmup failed: {warmup_result.get('error')}")
            status_code = 503
        
        response = {
            "warmup_completed": warmup_result["success"],
            "timestamp": datetime.utcnow().isoformat(),
            "warmup_results": warmup_result
        }
        
        return JSONResponse(content=response, status_code=status_code)
        
    except Exception as e:
        logger.error(f"AI warmup failed: {e}")
        return JSONResponse(
            content={
                "warmup_completed": False,
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e)
            },
            status_code=503
        )

async def _check_ai_libraries() -> Dict[str, Any]:
    """Проверяет доступность ключевых AI библиотек."""
    library_status = {}
    
    # Список критичных библиотек
    critical_libraries = [
        "transformers",
        "diffusers", 
        "accelerate",
        "safetensors",
        "controlnet_aux"
    ]
    
    # Список оптимизационных библиотек
    optimization_libraries = [
        "xformers",
        "triton"
    ]
    
    # Проверяем критичные библиотеки
    for lib_name in critical_libraries:
        try:
            lib = __import__(lib_name)
            library_status[lib_name] = {
                "available": True,
                "version": getattr(lib, "__version__", "unknown"),
                "critical": True
            }
        except ImportError as e:
            library_status[lib_name] = {
                "available": False,
                "error": str(e),
                "critical": True
            }
    
    # Проверяем оптимизационные библиотеки
    for lib_name in optimization_libraries:
        try:
            lib = __import__(lib_name)
            library_status[lib_name] = {
                "available": True,
                "version": getattr(lib, "__version__", "unknown"),
                "critical": False
            }
        except ImportError as e:
            library_status[lib_name] = {
                "available": False,
                "error": str(e),
                "critical": False
            }
    
    return library_status

def _determine_overall_health(
    service_status: Dict[str, Any],
    gpu_status,
    pytorch_info: Dict[str, Any],
    library_status: Dict[str, Any]
) -> Dict[str, Any]:
    """Определяет общий статус здоровья сервиса."""
    
    warnings = []
    errors = []
    status = "healthy"
    
    # Проверяем CUDA
    if not pytorch_info.get("cuda_available", False):
        errors.append("CUDA not available - AI generation will not work")
        status = "unhealthy"
    
    # Проверяем критичные библиотеки
    missing_critical = [
        lib for lib, info in library_status.items()
        if info.get("critical", False) and not info.get("available", False)
    ]
    
    if missing_critical:
        errors.append(f"Critical libraries missing: {', '.join(missing_critical)}")
        status = "unhealthy"
    
    # Проверяем GPU память
    if gpu_status.available:
        memory_usage = gpu_status.utilization_percent
        if memory_usage > 90:
            warnings.append(f"High GPU memory usage: {memory_usage}%")
            if status == "healthy":
                status = "degraded"
        elif memory_usage > 75:
            warnings.append(f"Moderate GPU memory usage: {memory_usage}%")
    
    # Проверяем температуру GPU
    if gpu_status.temperature_celsius and gpu_status.temperature_celsius > 85:
        warnings.append(f"High GPU temperature: {gpu_status.temperature_celsius}°C")
        if status == "healthy":
            status = "degraded"
    
    # Проверяем статус AI
    ai_status = service_status.get("ai_status", {})
    if isinstance(ai_status, dict):
        if not ai_status.get("models_loaded", False):
            warnings.append("AI models not yet loaded (lazy initialization)")
        if not ai_status.get("pipeline_ready", False):
            warnings.append("AI pipeline not ready")
    
    # Проверяем оптимизационные библиотеки
    missing_optimizations = [
        lib for lib, info in library_status.items()
        if not info.get("critical", True) and not info.get("available", False)
    ]
    
    if missing_optimizations:
        warnings.append(f"Performance optimizations missing: {', '.join(missing_optimizations)}")
    
    return {
        "status": status,
        "warnings": warnings,
        "errors": errors,
        "components_checked": len(library_status) + 3,  # libraries + GPU + CUDA + PyTorch
        "critical_components_ok": len(errors) == 0
    }
