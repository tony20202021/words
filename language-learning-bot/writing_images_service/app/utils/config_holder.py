"""
Configuration holder for backward compatibility.
Держатель конфигурации для обратной совместимости.
"""

import logging
from typing import Optional, Any

logger = logging.getLogger(__name__)

# Global configuration object
cfg: Optional[Any] = None


def initialize_config():
    """
    Initialize configuration from Hydra or environment variables.
    Инициализирует конфигурацию из Hydra или переменных окружения.
    """
    global cfg
    
    if cfg is not None:
        return cfg
    
    try:
        # Try to load Hydra configuration
        from hydra import compose, initialize
        from pathlib import Path
        
        # Find config directory
        config_path = "../conf/config"
        if not Path(config_path).exists():
            config_path = "./conf/config"
        
        if Path(config_path).exists():
            initialize(config_path=config_path, version_base=None)
            cfg = compose(config_name="default")
            logger.info("Loaded Hydra configuration successfully")
        else:
            logger.warning("Config directory not found, using defaults")
            cfg = create_default_config()
            
    except ImportError:
        logger.warning("Hydra not available, using default configuration")
        cfg = create_default_config()
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        cfg = create_default_config()
    
    return cfg


def create_default_config():
    """
    Create default configuration object.
    Создает объект конфигурации по умолчанию.
    """
    from types import SimpleNamespace
    
    # Create configuration structure similar to Hydra
    config = SimpleNamespace()
    
    # API configuration
    config.api = SimpleNamespace()
    config.api.host = "0.0.0.0"
    config.api.port = 8600
    config.api.prefix = "/api"
    config.api.debug = True
    config.api.cors_origins = "*"
    config.api.enable_rate_limit = False
    config.api.rate_limit_requests = 60
    config.api.rate_limit_period = 60
    
    # App configuration
    config.app = SimpleNamespace()
    config.app.name = "Writing Image Service"
    config.app.environment = "development"
    
    # Generation configuration
    config.generation = SimpleNamespace()
    
    # Generation defaults
    config.generation.defaults = SimpleNamespace()
    config.generation.defaults.width = 600
    config.generation.defaults.height = 600
    config.generation.defaults.quality = 90
    config.generation.defaults.style = "traditional"
    config.generation.defaults.show_guidelines = True
    config.generation.defaults.output_format = "png"
    
    # Generation limits
    config.generation.limits = SimpleNamespace()
    config.generation.limits.max_word_length = 50
    config.generation.limits.min_width = 100
    config.generation.limits.max_width = 2048
    config.generation.limits.min_height = 100
    config.generation.limits.max_height = 2048
    config.generation.limits.generation_timeout = 30
    
    # Stub configuration
    config.generation.stub = SimpleNamespace()
    config.generation.stub.width = 400
    config.generation.stub.height = 400
    config.generation.stub.background = [240, 240, 240]
    config.generation.stub.border = [180, 180, 180]
    config.generation.stub.text = [120, 120, 120]
    config.generation.stub.font_size = 24
    config.generation.stub.font_family = "Arial"
    
    # Languages configuration
    config.generation.languages = SimpleNamespace()
    config.generation.languages.chinese = SimpleNamespace()
    config.generation.languages.chinese.name = "Chinese"
    config.generation.languages.chinese.styles = ["traditional", "simplified", "calligraphy"]
    config.generation.languages.chinese.default_style = "traditional"
    
    config.generation.languages.japanese = SimpleNamespace()
    config.generation.languages.japanese.name = "Japanese"
    config.generation.languages.japanese.styles = ["hiragana", "katakana", "kanji"]
    config.generation.languages.japanese.default_style = "kanji"
    
    config.generation.languages.korean = SimpleNamespace()
    config.generation.languages.korean.name = "Korean"
    config.generation.languages.korean.styles = ["hangul"]
    config.generation.languages.korean.default_style = "hangul"
    
    config.generation.languages.english = SimpleNamespace()
    config.generation.languages.english.name = "English"
    config.generation.languages.english.styles = ["print", "cursive"]
    config.generation.languages.english.default_style = "print"
    
    # Logging configuration
    config.logging = SimpleNamespace()
    config.logging.level = "INFO"
    config.logging.format = "%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s"
    config.logging.log_to_file = True
    config.logging.log_file = "logs/writing_service.log"
    config.logging.log_dir = "logs"
    config.logging.log_file_max_size = 5242880  # 5 MB
    config.logging.log_file_backup_count = 3
    
    # Temp configuration
    config.temp = SimpleNamespace()
    config.temp.images_dir = "./temp/generated_images"
    config.temp.cleanup_interval = 300  # 5 minutes
    config.temp.max_file_age = 1800  # 30 minutes
    
    logger.info("Created default configuration")
    return config


def get_config():
    """
    Get current configuration.
    Получает текущую конфигурацию.
    """
    global cfg
    if cfg is None:
        cfg = initialize_config()
    return cfg


def reload_config():
    """
    Reload configuration.
    Перезагружает конфигурацию.
    """
    global cfg
    cfg = None
    return initialize_config()


# Initialize configuration on import
try:
    cfg = initialize_config()
except Exception as e:
    logger.error(f"Failed to initialize configuration on import: {e}")
    cfg = create_default_config()
    