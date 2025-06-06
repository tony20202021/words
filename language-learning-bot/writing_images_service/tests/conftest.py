"""
Pytest configuration for writing image service tests.
Конфигурация pytest для тестов сервиса генерации картинок написания.
"""

import pytest
import sys
import os
from pathlib import Path
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient

# Add the parent directory to sys.path to allow imports from app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

# Mock configuration holder to avoid Hydra dependency issues in tests
@pytest.fixture(autouse=True)
def mock_config_holder():
    """Mock config_holder to provide default configuration for tests."""
    with patch('app.utils.config_holder') as mock_holder:
        # Create mock configuration object
        mock_config = Mock()
        
        # API configuration
        mock_config.api = Mock()
        mock_config.api.host = "localhost"
        mock_config.api.port = 8600
        mock_config.api.prefix = "/api"
        mock_config.api.debug = True
        mock_config.api.cors_origins = ["*"]
        mock_config.api.enable_rate_limit = False
        mock_config.api.rate_limit_requests = 60
        mock_config.api.rate_limit_period = 60
        
        # App configuration
        mock_config.app = Mock()
        mock_config.app.name = "Writing Image Service"
        mock_config.app.environment = "test"
        
        # Generation configuration
        mock_config.generation = Mock()
        
        # Generation defaults
        mock_config.generation.defaults = Mock()
        mock_config.generation.defaults.width = 600
        mock_config.generation.defaults.height = 600
        mock_config.generation.defaults.quality = 90
        mock_config.generation.defaults.style = "traditional"
        mock_config.generation.defaults.show_guidelines = True
        mock_config.generation.defaults.output_format = "png"
        
        # Generation limits
        mock_config.generation.limits = Mock()
        mock_config.generation.limits.max_word_length = 50
        mock_config.generation.limits.min_width = 100
        mock_config.generation.limits.max_width = 2048
        mock_config.generation.limits.min_height = 100
        mock_config.generation.limits.max_height = 2048
        mock_config.generation.limits.generation_timeout = 30
        
        # Stub configuration
        mock_config.generation.stub = Mock()
        mock_config.generation.stub.width = 400
        mock_config.generation.stub.height = 400
        mock_config.generation.stub.background = [240, 240, 240]
        mock_config.generation.stub.border = [180, 180, 180]
        mock_config.generation.stub.text = [120, 120, 120]
        mock_config.generation.stub.font_size = 24
        mock_config.generation.stub.font_family = "Arial"
        
        # Languages configuration
        mock_config.generation.languages = Mock()
        languages = {}
        
        # Chinese
        chinese = Mock()
        chinese.name = "Chinese"
        chinese.styles = ["traditional", "simplified", "calligraphy"]
        chinese.default_style = "traditional"
        languages["chinese"] = chinese
        
        # Japanese  
        japanese = Mock()
        japanese.name = "Japanese"
        japanese.styles = ["hiragana", "katakana", "kanji"]
        japanese.default_style = "kanji"
        languages["japanese"] = japanese
        
        # Korean
        korean = Mock()
        korean.name = "Korean"
        korean.styles = ["hangul"]
        korean.default_style = "hangul"
        languages["korean"] = korean
        
        # English
        english = Mock()
        english.name = "English"
        english.styles = ["print", "cursive"]
        english.default_style = "print"
        languages["english"] = english
        
        # Provide languages as dict for iteration
        mock_config.generation.languages.keys.return_value = languages.keys()
        for lang, config in languages.items():
            setattr(mock_config.generation.languages, lang, config)
        
        # Logging configuration
        mock_config.logging = Mock()
        mock_config.logging.level = "INFO"
        mock_config.logging.format = "%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s"
        mock_config.logging.log_to_file = False  # Disable file logging in tests
        mock_config.logging.log_file = "logs/writing_service.log"
        mock_config.logging.log_dir = "logs"
        
        # Temp configuration
        mock_config.temp = Mock()
        mock_config.temp.images_dir = "./temp/test_generated_images"
        mock_config.temp.cleanup_interval = 300
        mock_config.temp.max_file_age = 1800
        
        # Set the mock config as the module's cfg
        mock_holder.cfg = mock_config
        
        yield mock_holder


@pytest.fixture
def temp_directory(tmp_path):
    """Create temporary directory for test files."""
    temp_dir = tmp_path / "generated_images"
    temp_dir.mkdir(exist_ok=True)
    
    # Patch the temp directory in tests
    with patch('app.utils.image_utils.ImageProcessor.temp_dir', str(temp_dir)):
        yield temp_dir


@pytest.fixture
def sample_writing_request():
    """Provide a sample writing image request for tests."""
    from app.api.models.requests import WritingImageRequest
    
    return WritingImageRequest(
        word="测试",
        language="chinese",
        style="traditional",
        width=600,
        height=600,
        show_guidelines=True,
        quality=90
    )


@pytest.fixture
def sample_batch_request():
    """Provide a sample batch writing image request for tests."""
    from app.api.models.requests import BatchWritingImageRequest
    
    return BatchWritingImageRequest(
        words=["测试", "学习", "语言"],
        language="chinese",
        style="traditional",
        width=600,
        height=600,
        show_guidelines=True,
        quality=90
    )


@pytest.fixture
def mock_pil_image():
    """Mock PIL Image for tests."""
    with patch('app.services.writing_image_service.Image') as mock_image, \
         patch('app.services.writing_image_service.ImageDraw') as mock_draw, \
         patch('app.services.writing_image_service.ImageFont') as mock_font:
        
        # Mock image object
        mock_img = Mock()
        mock_img.size = (600, 600)
        mock_image.new.return_value = mock_img
        
        # Mock draw object
        mock_draw_obj = Mock()
        mock_draw_obj.textbbox.return_value = (0, 0, 100, 20)
        mock_draw.Draw.return_value = mock_draw_obj
        
        # Mock font
        mock_font_obj = Mock()
        mock_font.load_default.return_value = mock_font_obj
        
        yield {
            'image': mock_image,
            'draw': mock_draw,
            'font': mock_font,
            'image_obj': mock_img,
            'draw_obj': mock_draw_obj,
            'font_obj': mock_font_obj
        }


@pytest.fixture
def disable_actual_file_operations():
    """Disable actual file operations during tests."""
    with patch('os.makedirs'), \
         patch('os.path.exists', return_value=True), \
         patch('os.access', return_value=True), \
         patch('os.remove'), \
         patch('builtins.open'), \
         patch('os.listdir', return_value=[]):
        yield


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    import asyncio
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_logger():
    """Mock logger to avoid log file creation in tests."""
    with patch('app.utils.logger.setup_logger') as mock_setup, \
         patch('logging.getLogger') as mock_get_logger:
        
        mock_logger_obj = Mock()
        mock_get_logger.return_value = mock_logger_obj
        mock_setup.return_value = mock_logger_obj
        
        yield mock_logger_obj


# Test data fixtures
@pytest.fixture
def sample_languages():
    """Sample languages data for tests."""
    return {
        "chinese": {
            "name": "Chinese",
            "styles": ["traditional", "simplified", "calligraphy"],
            "default_style": "traditional"
        },
        "japanese": {
            "name": "Japanese",
            "styles": ["hiragana", "katakana", "kanji"],
            "default_style": "kanji"
        },
        "english": {
            "name": "English", 
            "styles": ["print", "cursive"],
            "default_style": "print"
        }
    }


@pytest.fixture
def sample_validation_errors():
    """Sample validation errors for tests."""
    return [
        "Word cannot be empty",
        "Width must be at least 100 pixels",
        "Height cannot exceed 2048 pixels",
        "Quality must be between 1 and 100"
    ]


@pytest.fixture
def sample_image_metadata():
    """Sample image metadata for tests."""
    from app.api.models.responses import WritingImageMetadata
    
    return WritingImageMetadata(
        word="测试",
        language="chinese",
        style="traditional",
        width=600,
        height=600,
        format="png",
        size_bytes=15234,
        generation_time_ms=1500,
        quality=90,
        show_guidelines=True
    )


# Mock external dependencies
@pytest.fixture(autouse=True)
def mock_external_dependencies():
    """Mock external dependencies that might not be available in test environment."""
    
    # Mock psutil if not available
    try:
        import psutil
    except ImportError:
        with patch.dict('sys.modules', {'psutil': Mock()}):
            yield
    else:
        yield


# Environment setup
@pytest.fixture(autouse=True)
def test_environment():
    """Set up test environment variables."""
    test_env = {
        'ENVIRONMENT': 'test',
        'LOG_LEVEL': 'DEBUG',
        'WRITING_SERVICE_PORT': '8600',
        'DEBUG': 'true'
    }
    
    with patch.dict(os.environ, test_env):
        yield


# Cleanup fixtures
@pytest.fixture(autouse=True)
def cleanup_temp_files():
    """Clean up any temporary files created during tests."""
    yield
    
    # Clean up test temp directories
    import shutil
    test_temp_dirs = [
        "./temp/test_generated_images",
        "./test_temp",
        "./logs/test"
    ]
    
    for temp_dir in test_temp_dirs:
        if os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
            except Exception:
                pass  # Ignore cleanup errors


# Performance testing fixtures
@pytest.fixture
def performance_timer():
    """Timer fixture for performance testing."""
    import time
    
    class Timer:
        def __init__(self):
            self.start_time = None
            self.end_time = None
        
        def start(self):
            self.start_time = time.time()
        
        def stop(self):
            self.end_time = time.time()
        
        @property
        def elapsed(self):
            if self.start_time and self.end_time:
                return self.end_time - self.start_time
            return None
    
    return Timer()


# Async test helpers
@pytest.fixture
def async_mock():
    """Helper to create async mocks."""
    from unittest.mock import AsyncMock
    return AsyncMock


# Custom markers
def pytest_configure(config):
    """Configure custom pytest markers."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "unit: marks tests as unit tests"
    )
    config.addinivalue_line(
        "markers", "api: marks tests as API tests"
    )
    