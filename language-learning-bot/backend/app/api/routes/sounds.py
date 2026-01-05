"""
API routes for sound operations.
This module contains all the API endpoints for managing sounds in the system.
"""

from urllib.parse import unquote

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from app.utils.logger import setup_logger
from app.core.dependencies import get_sound_service
from app.services.sound_service import SoundService

# Create router for sound operations
router = APIRouter(prefix="/sounds", tags=["sounds"])

# Configure logger
logger = setup_logger(__name__)


@router.get("/{sound_name:path}")
async def get_sound(
    sound_name: str,
    sound_service: SoundService = Depends(get_sound_service)
):
    """
    Get the sound by name.

    Args:
        sound_name: Name of the sound to retrieve
        sound_service: Sound service dependency

    Returns:
        Sound bytes
    """
    # Decode URL-encoded sound name (e.g., %2E -> .)
    decoded_sound_name = unquote(sound_name)
    
    try:
        logger.info(f"Getting sound by name={decoded_sound_name} (original: {sound_name})")
        sound = await sound_service.get_sound(decoded_sound_name)
        if sound is None:
            raise HTTPException(status_code=404, detail=f"Sound file not found: {decoded_sound_name}")
        
        # Determine content type based on file extension
        if decoded_sound_name.endswith(".mp3"):
            content_type = "audio/mpeg"
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported sound file extension: {decoded_sound_name}")
        
        logger.info(f"Returning sound with content type={content_type}")
        return Response(content=sound, media_type=content_type)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error getting sound by name={decoded_sound_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting sound by name={decoded_sound_name}")