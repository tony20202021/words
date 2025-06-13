"""
API routes for writing image generation.
Роуты API для генерации картинок написания.
ОБНОВЛЕНО: Добавлена поддержка пользовательской подсказки hint_writing
"""

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import Response

from app.api.routes.models.requests import AIImageRequest
from app.api.routes.models.responses import AIImageResponse, GenerationStatus
from app.api.routes.services.writing_image_service import WritingImageService
from app.api.routes.services.validation_service import ValidationService
from app.core.exceptions import ValidationError, GenerationError
from app.utils.logger import get_module_logger

logger = get_module_logger(__name__)

router = APIRouter(prefix="/writing", tags=["writing_images"])

# Dependency injection
def get_writing_image_service() -> WritingImageService:
    """Get writing image service instance."""
    return WritingImageService()

def get_validation_service() -> ValidationService:
    """Get validation service instance."""
    return ValidationService()

@router.post("/generate-writing-image", response_model=AIImageResponse)
async def generate_writing_image(
    request: AIImageRequest,
    writing_service: WritingImageService = Depends(get_writing_image_service),
    validation_service: ValidationService = Depends(get_validation_service)
):
    """
    Generate writing image for a word.
    Генерирует картинку написания для слова.
    ОБНОВЛЕНО: Поддержка пользовательской подсказки hint_writing
    
    Args:
        request: Writing image generation request with optional user hint
        writing_service: Writing image service
        validation_service: Validation service
        
    Returns:
        AIImageResponse: Generated image response
        
    Raises:
        HTTPException: If generation fails
    """
    try:
        # Логируем информацию о запросе с подсказкой
        hint_info = f", hint: '{request.hint_writing}'" if request.has_user_hint() else ""
        logger.info(f"Generating writing image for word: '{request.word}'{hint_info}")
        logger.debug(f"Full request: {request.to_dict()}")
        
        # Validate request
        validation_result = await validation_service.validate_request(request)
        if not validation_result.is_valid:
            logger.warning(f"Invalid request: {validation_result.errors}")
            raise HTTPException(
                status_code=400, 
                detail=f"Validation failed: {', '.join(validation_result.errors)}"
            )
        
        # Validate user hint if provided
        if request.has_user_hint():
            hint_validation = await validation_service.validate_user_hint(request.hint_writing)
            if not hint_validation.is_valid:
                logger.warning(f"Invalid user hint: {hint_validation.errors}")
                raise HTTPException(
                    status_code=400,
                    detail=f"User hint validation failed: {', '.join(hint_validation.errors)}"
                )
        
        # Generate image with user hint support
        generation_result = await writing_service.generate_image(request)
        
        if not generation_result.success:
            logger.error(f"Generation failed: {generation_result.error}")
            raise HTTPException(
                status_code=500,
                detail=f"Image generation failed: {generation_result.error}"
            )
        
        # Логируем успешную генерацию с информацией о подсказке
        hint_used_info = ""
        if request.has_user_hint():
            metadata = generation_result.metadata
            if metadata and hasattr(metadata, 'user_hint_translated'):
                hint_used_info = f" (hint translated: '{metadata.user_hint_translated}')"
            else:
                hint_used_info = f" (hint: '{request.hint_writing}')"
        
        logger.info(f"Successfully generated writing image for: {request.word}{hint_used_info}")
        
        # Prepare response with hint metadata
        result = AIImageResponse(
            success=True,
            status=GenerationStatus.SUCCESS,
            generated_image_base64=generation_result.image_data_base64,
            base_image_base64=generation_result.base_image_base64,
            conditioning_images_base64=generation_result.conditioning_images_base64,
            prompt_used=generation_result.prompt_used,
            generation_metadata=generation_result.metadata,
            error=generation_result.error,
            warnings=None,
        )
        
        # Логируем детали результата
        logger.debug(f"Result details: success={result.success}, status={result.status}")
        if hasattr(result.generation_metadata, 'user_hint_used'):
            logger.debug(f"User hint processing: {result.generation_metadata.user_hint_used}")
        
        return result
    
    except ValidationError as e:
        logger.warning(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
        
    except GenerationError as e:
        logger.error(f"Generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
        
    except Exception as e:
        logger.error(f"Unexpected error in writing image generation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/generate-writing-image-binary")
async def generate_writing_image_binary(
    request: AIImageRequest,
    writing_service: WritingImageService = Depends(get_writing_image_service),
    validation_service: ValidationService = Depends(get_validation_service)
):
    """
    Generate writing image and return as binary data.
    Генерирует картинку написания и возвращает как бинарные данные.
    ОБНОВЛЕНО: Поддержка пользовательской подсказки hint_writing
    
    Args:
        request: Writing image generation request with optional user hint
        writing_service: Writing image service
        validation_service: Validation service
        
    Returns:
        Response: Binary image data with hint metadata in headers
        
    Raises:
        HTTPException: If generation fails
    """
    try:
        hint_info = f", hint: '{request.hint_writing}'" if request.has_user_hint() else ""
        logger.info(f"Generating binary writing image for word: '{request.word}'{hint_info}")
        
        # Validate request including user hint
        validation_result = await validation_service.validate_request(request)
        if not validation_result.is_valid:
            logger.warning(f"Invalid request: {validation_result.errors}")
            raise HTTPException(
                status_code=400, 
                detail=f"Validation failed: {', '.join(validation_result.errors)}"
            )
        
        # Validate user hint if provided
        if request.has_user_hint():
            hint_validation = await validation_service.validate_user_hint(request.hint_writing)
            if not hint_validation.is_valid:
                logger.warning(f"Invalid user hint: {hint_validation.errors}")
                raise HTTPException(
                    status_code=400,
                    detail=f"User hint validation failed: {', '.join(hint_validation.errors)}"
                )
        
        # Generate image
        generation_result = await writing_service.generate_image(request)
        
        if not generation_result.success:
            logger.error(f"Generation failed: {generation_result.error}")
            raise HTTPException(
                status_code=500,
                detail=f"Image generation failed: {generation_result.error}"
            )
        
        logger.info(f"Successfully generated binary writing image for: {request.word}{hint_info}")
        
        # Prepare response headers with hint metadata
        headers = {
            "Content-Disposition": f"attachment; filename=writing_{request.word}.{generation_result.format}",
            "X-Word": request.word,
            "X-Translation": request.translation or "",
            "X-Style": getattr(request, 'style', 'comic'),
        }
        
        # Add hint-related headers if user hint was provided
        if request.has_user_hint():
            headers["X-User-Hint"] = request.hint_writing
            
            # Add translated hint if available
            if (generation_result.metadata and 
                hasattr(generation_result.metadata, 'user_hint_translated')):
                headers["X-User-Hint-Translated"] = generation_result.metadata.user_hint_translated
                headers["X-User-Hint-Used"] = "true"
            else:
                headers["X-User-Hint-Used"] = "false"
        
        # Add generation metadata headers
        if generation_result.metadata:
            if hasattr(generation_result.metadata, 'generation_time_ms'):
                headers["X-Generation-Time-Ms"] = str(generation_result.metadata.generation_time_ms)
            if hasattr(generation_result.metadata, 'ai_model_used'):
                headers["X-AI-Model-Used"] = generation_result.metadata.ai_model_used
            if hasattr(generation_result.metadata, 'translation_used'):
                headers["X-Translation-Used"] = generation_result.metadata.translation_used
                headers["X-Translation-Source"] = getattr(generation_result.metadata, 'translation_source', 'unknown')
        
        # Return binary response
        media_type = f"image/{generation_result.format}"
        return Response(
            content=generation_result.image_data,
            media_type=media_type,
            headers=headers
        )
        
    except ValidationError as e:
        logger.warning(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
        
    except GenerationError as e:
        logger.error(f"Generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
        
    except Exception as e:
        logger.error(f"Unexpected error in binary writing image generation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/validate-hint")
async def validate_user_hint(
    hint_data: dict,
    validation_service: ValidationService = Depends(get_validation_service)
):
    """
    Validate user hint before generation.
    Валидирует пользовательскую подсказку перед генерацией.
    
    Args:
        hint_data: Dictionary with 'hint_writing' field
        validation_service: Validation service
        
    Returns:
        Dict with validation result
    """
    try:
        hint_writing = hint_data.get('hint_writing', '')
        
        if not hint_writing or not hint_writing.strip():
            return {
                "valid": True,
                "message": "Empty hint is valid",
                "suggestions": []
            }
        
        validation_result = await validation_service.validate_user_hint(hint_writing)
        
        return {
            "valid": validation_result.is_valid,
            "message": "Hint is valid" if validation_result.is_valid else "Hint validation failed",
            "errors": validation_result.errors if not validation_result.is_valid else [],
            "suggestions": validation_result.suggestions if hasattr(validation_result, 'suggestions') else [],
            "processed_hint": hint_writing.strip()
        }
        
    except Exception as e:
        logger.error(f"Error validating user hint: {e}")
        return {
            "valid": False,
            "message": f"Validation error: {str(e)}",
            "errors": [str(e)]
        }

@router.get("/hint-examples")
async def get_hint_examples():
    """
    Get examples of good user hints.
    Возвращает примеры хороших пользовательских подсказок.
    
    Returns:
        Dict with hint examples
    """
    return {
        "examples": {
            "descriptive": [
                "красивый рисунок с цветами",
                "в стиле японской каллиграфии", 
                "с золотыми элементами",
                "на фоне заката"
            ],
            "style": [
                "минималистичный дизайн",
                "в стиле акварели",
                "как древняя картина",
                "современный цифровой арт"
            ],
            "mood": [
                "спокойная атмосфера",
                "энергичный и яркий",
                "мистическое настроение",
                "радостная композиция"
            ],
            "elements": [
                "добавить птиц",
                "включить воду",
                "с горным пейзажем",
                "в окружении природы"
            ]
        },
        "tips": [
            "Используйте описательные прилагательные",
            "Упоминайте конкретные стили или техники",
            "Добавляйте детали окружения или настроения",
            "Избегайте слишком сложных или противоречивых описаний"
        ],
        "max_length": 200,
        "supported_languages": ["русский", "english"]
    }
