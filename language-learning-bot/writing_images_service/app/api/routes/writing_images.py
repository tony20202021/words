"""
API routes for writing image generation.
Роуты API для генерации картинок написания.
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
    
    Args:
        request: Writing image generation request
        writing_service: Writing image service
        validation_service: Validation service
        
    Returns:
        WritingImageResponse: Generated image response
        
    Raises:
        HTTPException: If generation fails
    """
    try:
        logger.info(f"Generating writing image for word: '{request.word}'")
        logger.info(f"request: '{request}'")
        
        # Validate request
        validation_result = await validation_service.validate_request(request)
        if not validation_result.is_valid:
            logger.warning(f"Invalid request: {validation_result.errors}")
            raise HTTPException(
                status_code=400, 
                detail=f"Validation failed: {', '.join(validation_result.errors)}"
            )
        
        # Generate image
        generation_result = await writing_service.generate_image(request)
        
        if not generation_result.success:
            logger.error(f"Generation failed: {generation_result.error}")
            raise HTTPException(
                status_code=500,
                detail=f"Image generation failed: {generation_result.error}"
            )
        
        logger.info(f"Successfully generated writing image for: {request.word}")
        
        result = AIImageResponse(
            success=True,
            status=GenerationStatus.SUCCESS,
            generated_image=generation_result.image_data_base64,
            generation_metadata=generation_result.metadata,
            conditioning_images=generation_result.conditioning_images,
            prompt_used=generation_result.prompt_used,
            semantic_analysis=generation_result.semantic_analysis,
            error=generation_result.error,
            warnings=generation_result.warnings,
        )
        
        logger.info(f"result.success: '{result.success}'")
        logger.info(f"result.status: '{result.status}'")
        logger.info(f"result.len(generated_image): '{len(result.generated_image)}'")
        logger.info(f"result.generation_metadata: '{result.generation_metadata}'")
        logger.info(f"result.conditioning_images: '{result.conditioning_images}'")
        logger.info(f"result.prompt_used: '{result.prompt_used}'")
        logger.info(f"result.semantic_analysis: '{result.semantic_analysis}'")
        logger.info(f"result.error: '{result.error}'")
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
    
    Args:
        request: Writing image generation request
        writing_service: Writing image service
        validation_service: Validation service
        
    Returns:
        Response: Binary image data
        
    Raises:
        HTTPException: If generation fails
    """
    try:
        logger.info(f"Generating binary writing image for word: '{request.word}', language: '{request.language}'")
        
        # Validate request
        validation_result = await validation_service.validate_request(request)
        if not validation_result.is_valid:
            logger.warning(f"Invalid request: {validation_result.errors}")
            raise HTTPException(
                status_code=400, 
                detail=f"Validation failed: {', '.join(validation_result.errors)}"
            )
        
        # Generate image
        generation_result = await writing_service.generate_image(request)
        
        if not generation_result.success:
            logger.error(f"Generation failed: {generation_result.error}")
            raise HTTPException(
                status_code=500,
                detail=f"Image generation failed: {generation_result.error}"
            )
        
        logger.info(f"Successfully generated binary writing image for: {request.word}")
        
        # Return binary response
        media_type = f"image/{generation_result.format}"
        return Response(
            content=generation_result.image_data,
            media_type=media_type,
            headers={
                "Content-Disposition": f"attachment; filename=writing_{request.word}.{generation_result.format}",
                "X-Word": request.word,
                "X-Language": request.language,
                "X-Style": request.style
            }
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
