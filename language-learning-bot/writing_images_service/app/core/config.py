"""
Configuration management for writing image service.
Управление конфигурацией для сервиса генерации картинок написания.
"""

import os
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class APIConfig:
    """API configuration settings."""
    host: str = "0.0.0.0"
    port: int = 8600
    prefix: str = "/api"
    debug: bool = True
    cors_origins: List[str] = field(default_factory=lambda: ["*"])
    enable_rate_limit: bool = False
    rate_limit_requests: int = 60
    rate_limit_period: int = 60


@dataclass
class GenerationConfig:
    """Image generation configuration settings."""
    default_width: int = 600
    default_height: int = 600
    default_quality: int = 90
    default_style: str = "traditional"
    show_guidelines: bool = True
    output_format: str = "png"
    max_word_length: int = 50
    min_width: int = 100
    max_width: int = 2048
    min_height: int = 100
    max_height: int = 2048
    generation_timeout: int = 30


@dataclass
class StubConfig:
    """Stub generation configuration settings."""
    width: int = 400
    height: int = 400
    background_color: tuple = (240, 240, 240)
    border_color: tuple = (180, 180, 180)
    text_color: tuple = (120, 120, 120)
    font_size: int = 24
    font_family: str = "Arial"


@dataclass
class LoggingConfig:
    """Logging configuration settings."""
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s"
    log_to_file: bool = True
    log_file: str = "logs/writing_service.log"
    log_dir: str = "logs"
    log_file_max_size: int = 5242880  # 5 MB
    log_file_backup_count: int = 3


@dataclass
class TempConfig:
    """Temporary files configuration settings."""
    images_dir: str = "./temp/generated_images"
    cleanup_interval: int = 300  # 5 minutes
    max_file_age: int = 1800  # 30 minutes


@dataclass
class WritingServiceConfig:
    """Main configuration class for writing image service."""
    api: APIConfig = field(default_factory=APIConfig)
    generation: GenerationConfig = field(default_factory=GenerationConfig)
    stub: StubConfig = field(default_factory=StubConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    temp: TempConfig = field(default_factory=TempConfig)
    
    # App metadata
    app_name: str = "Writing Image Service"
    app_version: str = "1.0.0"
    app_environment: str = "development"


class ConfigManager:
    """
    Configuration manager for writing image service.
    Менеджер конфигурации для сервиса генерации картинок написания.
    """
    
    def __init__(self):
        """Initialize configuration manager."""
        self._config: Optional[WritingServiceConfig] = None
        self._hydra_available = False
        self._check_hydra_availability()
    
    def _check_hydra_availability(self):
        """Check if Hydra is available."""
        try:
            import hydra
            from omegaconf import OmegaConf
            self._hydra_available = True
            logger.info("Hydra configuration system is available")
        except ImportError:
            self._hydra_available = False
            logger.warning("Hydra not available, using environment variables and defaults")
    
    def load_config(self) -> WritingServiceConfig:
        """
        Load configuration from Hydra or environment variables.
        Загружает конфигурацию из Hydra или переменных окружения.
        
        Returns:
            WritingServiceConfig: Loaded configuration
        """
        if self._config is not None:
            return self._config
        
        if self._hydra_available:
            self._config = self._load_hydra_config()
        else:
            self._config = self._load_env_config()
        
        self._validate_config()
        return self._config
    
    def _load_hydra_config(self) -> WritingServiceConfig:
        """Load configuration using Hydra."""
        try:
            from hydra import compose, initialize
            
            # Try to initialize Hydra if not already done
            config_path = "../conf/config"
            if not Path(config_path).exists():
                config_path = "./conf/config"
            
            initialize(config_path=config_path, version_base=None)
            cfg = compose(config_name="default")
            
            logger.info("Successfully loaded Hydra configuration")
            return self._hydra_to_dataclass(cfg)
            
        except Exception as e:
            logger.error(f"Failed to load Hydra configuration: {e}")
            logger.info("Falling back to environment variables")
            return self._load_env_config()
    
    def _hydra_to_dataclass(self, hydra_cfg) -> WritingServiceConfig:
        """Convert Hydra config to dataclass."""
        config = WritingServiceConfig()
        
        # Load API configuration
        if hasattr(hydra_cfg, 'api'):
            api_cfg = hydra_cfg.api
            config.api = APIConfig(
                host=getattr(api_cfg, 'host', config.api.host),
                port=getattr(api_cfg, 'port', config.api.port),
                prefix=getattr(api_cfg, 'prefix', config.api.prefix),
                debug=getattr(api_cfg, 'debug', config.api.debug),
                cors_origins=self._parse_cors_origins(getattr(api_cfg, 'cors_origins', "*")),
                enable_rate_limit=getattr(api_cfg, 'enable_rate_limit', config.api.enable_rate_limit),
                rate_limit_requests=getattr(api_cfg, 'rate_limit_requests', config.api.rate_limit_requests),
                rate_limit_period=getattr(api_cfg, 'rate_limit_period', config.api.rate_limit_period)
            )
        
        # Load generation configuration
        if hasattr(hydra_cfg, 'generation'):
            gen_cfg = hydra_cfg.generation
            defaults = getattr(gen_cfg, 'defaults', {})
            limits = getattr(gen_cfg, 'limits', {})
            
            config.generation = GenerationConfig(
                default_width=defaults.get('width', config.generation.default_width),
                default_height=defaults.get('height', config.generation.default_height),
                default_quality=defaults.get('quality', config.generation.default_quality),
                default_style=defaults.get('style', config.generation.default_style),
                show_guidelines=defaults.get('show_guidelines', config.generation.show_guidelines),
                output_format=defaults.get('output_format', config.generation.output_format),
                max_word_length=limits.get('max_word_length', config.generation.max_word_length),
                min_width=limits.get('min_width', config.generation.min_width),
                max_width=limits.get('max_width', config.generation.max_width),
                min_height=limits.get('min_height', config.generation.min_height),
                max_height=limits.get('max_height', config.generation.max_height),
                generation_timeout=limits.get('generation_timeout', config.generation.generation_timeout)
            )
            
            # Load stub configuration
            if hasattr(gen_cfg, 'stub'):
                stub_cfg = gen_cfg.stub
                config.stub = StubConfig(
                    width=getattr(stub_cfg, 'width', config.stub.width),
                    height=getattr(stub_cfg, 'height', config.stub.height),
                    background_color=tuple(getattr(stub_cfg, 'background', config.stub.background_color)),
                    border_color=tuple(getattr(stub_cfg, 'border', config.stub.border_color)),
                    text_color=tuple(getattr(stub_cfg, 'text', config.stub.text_color)),
                    font_size=getattr(stub_cfg, 'font_size', config.stub.font_size),
                    font_family=getattr(stub_cfg, 'font_family', config.stub.font_family)
                )
        
        # Load logging configuration
        if hasattr(hydra_cfg, 'logging'):
            log_cfg = hydra_cfg.logging
            config.logging = LoggingConfig(
                level=getattr(log_cfg, 'level', config.logging.level),
                format=getattr(log_cfg, 'format', config.logging.format),
                log_to_file=getattr(log_cfg, 'log_to_file', config.logging.log_to_file),
                log_file=getattr(log_cfg, 'log_file', config.logging.log_file),
                log_dir=getattr(log_cfg, 'log_dir', config.logging.log_dir),
                log_file_max_size=getattr(log_cfg, 'log_file_max_size', config.logging.log_file_max_size),
                log_file_backup_count=getattr(log_cfg, 'log_file_backup_count', config.logging.log_file_backup_count)
            )
        
        # Load app configuration
        if hasattr(hydra_cfg, 'app'):
            app_cfg = hydra_cfg.app
            config.app_name = getattr(app_cfg, 'name', config.app_name)
            config.app_environment = getattr(app_cfg, 'environment', config.app_environment)
        
        # Load temp configuration
        if hasattr(hydra_cfg, 'temp'):
            temp_cfg = hydra_cfg.temp
            config.temp = TempConfig(
                images_dir=getattr(temp_cfg, 'images_dir', config.temp.images_dir),
                cleanup_interval=getattr(temp_cfg, 'cleanup_interval', config.temp.cleanup_interval),
                max_file_age=getattr(temp_cfg, 'max_file_age', config.temp.max_file_age)
            )
        
        return config
    
    def _load_env_config(self) -> WritingServiceConfig:
        """Load configuration from environment variables."""
        config = WritingServiceConfig()
        
        # Load API configuration from environment
        config.api = APIConfig(
            host=os.getenv("WRITING_SERVICE_HOST", config.api.host),
            port=int(os.getenv("WRITING_SERVICE_PORT", str(config.api.port))),
            prefix=os.getenv("API_PREFIX", config.api.prefix),
            debug=os.getenv("DEBUG", "true").lower() in ("true", "1", "t"),
            cors_origins=self._parse_cors_origins(os.getenv("CORS_ORIGINS", "*")),
            enable_rate_limit=os.getenv("ENABLE_RATE_LIMIT", "false").lower() in ("true", "1", "t"),
            rate_limit_requests=int(os.getenv("RATE_LIMIT_REQUESTS", str(config.api.rate_limit_requests))),
            rate_limit_period=int(os.getenv("RATE_LIMIT_PERIOD", str(config.api.rate_limit_period)))
        )
        
        # Load logging configuration from environment
        config.logging = LoggingConfig(
            level=os.getenv("LOG_LEVEL", config.logging.level),
            format=os.getenv("LOG_FORMAT", config.logging.format),
            log_to_file=os.getenv("LOG_TO_FILE", "true").lower() in ("true", "1", "t"),
            log_file=os.getenv("LOG_FILE", config.logging.log_file),
            log_dir=os.getenv("LOG_DIR", config.logging.log_dir)
        )
        
        # Load app configuration from environment
        config.app_name = os.getenv("APP_NAME", config.app_name)
        config.app_environment = os.getenv("ENVIRONMENT", config.app_environment)
        
        logger.info("Loaded configuration from environment variables")
        return config
    
    def _parse_cors_origins(self, cors_origins: str) -> List[str]:
        """Parse CORS origins from string."""
        if isinstance(cors_origins, list):
            return cors_origins
        
        if cors_origins == "*":
            return ["*"]
        
        return [origin.strip() for origin in cors_origins.split(",") if origin.strip()]
    
    def _validate_config(self):
        """Validate loaded configuration."""
        if not self._config:
            raise ValueError("Configuration not loaded")
        
        # Validate API configuration
        if self._config.api.port < 1 or self._config.api.port > 65535:
            raise ValueError(f"Invalid port: {self._config.api.port}")
        
        # Validate generation limits
        gen = self._config.generation
        if gen.min_width >= gen.max_width:
            raise ValueError("min_width must be less than max_width")
        
        if gen.min_height >= gen.max_height:
            raise ValueError("min_height must be less than max_height")
        
        # Create required directories
        os.makedirs(self._config.logging.log_dir, exist_ok=True)
        os.makedirs(self._config.temp.images_dir, exist_ok=True)
        
        logger.info("Configuration validation completed successfully")
    
    def get_config(self) -> WritingServiceConfig:
        """Get current configuration."""
        if self._config is None:
            return self.load_config()
        return self._config
    
    def reload_config(self) -> WritingServiceConfig:
        """Reload configuration."""
        self._config = None
        return self.load_config()


# Global configuration manager instance
_config_manager: Optional[ConfigManager] = None


def get_config_manager() -> ConfigManager:
    """
    Get global configuration manager instance.
    Получает глобальный экземпляр менеджера конфигурации.
    
    Returns:
        ConfigManager: Configuration manager instance
    """
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager


def get_config() -> WritingServiceConfig:
    """
    Get current service configuration.
    Получает текущую конфигурацию сервиса.
    
    Returns:
        WritingServiceConfig: Current configuration
    """
    return get_config_manager().get_config()


def reload_config() -> WritingServiceConfig:
    """
    Reload service configuration.
    Перезагружает конфигурацию сервиса.
    
    Returns:
        WritingServiceConfig: Reloaded configuration
    """
    return get_config_manager().reload_config()
