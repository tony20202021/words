"""
Service for sound operations.
"""

import os
from typing import Optional

from fastapi import HTTPException

from hydra import compose, initialize
from omegaconf import OmegaConf

from app.utils.logger import setup_logger

# Configure logger
logger = setup_logger(__name__)


path = "../../conf/config"

print(f"Проверка конфигурации для sounds из пути {path}")
try:
    initialize(config_path=path, version_base=None)
    cfg = compose(config_name="default")
    print(OmegaConf.to_yaml(cfg))
    print("Конфигурация загружена успешно!")
except Exception as e:
    print(f"Ошибка при загрузке конфигурации: {e}")


class SoundService:
    """Service for handling sound operations."""

    async def get_sound(self, sound_name: str) -> Optional[bytes]:
        """
        Get the sound by name.

        Args:
            sound_name: Name of the sound file

        Returns:
            Sound bytes
        """
        logger.info(f"Getting sound by name={sound_name}")
        logger.info(f"Sound path: {cfg.sounds.sound_path}")

        try:
            # os.path.join сам по себе не защищает: sound_name вида ../../etc/x.mp3
            # уводит за пределы каталога звуков, а абсолютный путь просто
            # отбрасывает базу. Сверяем итоговый реальный путь с базовым.
            base = os.path.realpath(cfg.sounds.sound_path)
            sound_path = os.path.realpath(os.path.join(base, sound_name))
            if os.path.commonpath([base, sound_path]) != base:
                logger.error(f"Sound path escapes base dir: name={sound_name}")
                raise HTTPException(status_code=400, detail="Bad sound name")
            logger.info(f"Sound file exists: {os.path.exists(sound_path)}")
            if not os.path.exists(sound_path):
                logger.error(f"Sound file not found: {sound_path}")
                raise HTTPException(status_code=404, detail=f"Sound file not found: {sound_path}")
            
            with open(sound_path, "rb") as f:
                return f.read()

        except HTTPException:
            raise          # 400/404 — осмысленные ответы, не превращать в 500
        except Exception as e:
            logger.exception(f"Error getting sound by name={sound_name}: {e}")
            raise HTTPException(status_code=500, detail=f"Error getting sound by name={sound_name}: {e}")
