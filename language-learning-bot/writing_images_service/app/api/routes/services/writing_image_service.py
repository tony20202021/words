"""
Writing image generation service.
Сервис генерации картинок написания.
REAL AI IMPLEMENTATION - uses actual AI models for generation.
ОБНОВЛЕНО: Добавлена поддержка пользовательской подсказки hint_writing
"""

import time
import asyncio
from typing import Dict, Any, Optional

from app.api.routes.models.requests import AIImageRequest
from app.api.routes.models.responses import AIGenerationMetadata
from app.utils.image_utils import get_image_processor
from app.utils import config_holder
from app.ai.ai_image_generator import AIImageGenerator, AIGenerationConfig
from app.utils.logger import get_module_logger

logger = get_module_logger(__name__)


class GenerationResult:
    """
    Result of image generation operation.
    Результат операции генерации изображения.
    ОБНОВЛЕНО: Добавлена поддержка метаданных пользовательской подсказки
    """
    
    def __init__(
        self, 
        success: bool, 
        image_data_base64: Optional[str] = None,
        format: str = "png",
        metadata: Optional[AIGenerationMetadata] = None,
        error: Optional[str] = None,
        base_image_base64: Optional[str] = None,
        conditioning_images_base64: Optional[Dict[str, Dict[str, str]]] = None,
        prompt_used: Optional[str] = None,
        # НОВОЕ: метаданные пользовательской подсказки
        user_hint_metadata: Optional[Dict[str, Any]] = None,
    ):
        self.success = success
        self.image_data_base64 = image_data_base64
        self.format = format
        self.metadata = metadata
        self.error = error
        self.base_image_base64 = base_image_base64
        self.conditioning_images_base64 = conditioning_images_base64
        self.prompt_used = prompt_used
        self.user_hint_metadata = user_hint_metadata or {}


class WritingImageService:
    """
    Service for generating writing images using real AI models.
    Сервис для генерации картинок написания с использованием реальных AI моделей.
    ОБНОВЛЕНО: Поддержка пользовательских подсказок hint_writing
    """
    
    def __init__(self):
        """Initialize the writing image service."""
        self.generation_count = 0
        self.hint_usage_count = 0  # НОВОЕ: счетчик использования подсказок
        self.start_time = time.time()
        self.image_processor = get_image_processor()
        
        # Load configuration
        self._load_config()
        
        # Initialize AI Generator
        self.ai_generator = None
        self._ai_initialization_lock = asyncio.Lock()
        self._ai_initialized = False
        
        logger.info("WritingImageService initialized with real AI generation and hint support")
    
    def _load_config(self):
        """Load configuration from Hydra config."""
        # Default values
        self.default_width = 1024
        self.default_height = 1024
        self.show_guidelines_default = True
        
        # AI Generation defaults
        self.ai_config = AIGenerationConfig()
        
        # НОВОЕ: настройки для пользовательских подсказок
        self.hint_config = {
            "max_hint_length": 200,
            "translate_hints": True,
            "include_hints_in_prompt": True,
            "hint_weight": 0.3,  # Вес подсказки в финальном промпте
        }
        
        try:
            if hasattr(config_holder, 'cfg'):
                cfg = config_holder.cfg
                
                # Load generation defaults
                if hasattr(cfg, 'generation') and hasattr(cfg.generation, 'generation_defaults'):
                    defaults = cfg.generation.generation_defaults
                    self.default_width = defaults.get('width', self.default_width)
                    self.default_height = defaults.get('height', self.default_height)
                    self.show_guidelines_default = defaults.get('show_guidelines', self.show_guidelines_default)
                
                # Load AI generation config if available
                if hasattr(cfg, 'ai_generation'):
                    ai_cfg = cfg.ai_generation
                    
                    # Update models
                    if hasattr(ai_cfg, 'models'):
                        models_cfg = ai_cfg.models
                        if hasattr(models_cfg, 'base_model'):
                            self.ai_config.base_model = models_cfg.base_model
                        
                        # UPDATED: Load union controlnet model
                        if hasattr(models_cfg, 'controlnet_models'):
                            self.ai_config.controlnet_models = dict(models_cfg.controlnet_models)
                    
                    # Update generation parameters
                    if hasattr(ai_cfg, 'generation'):
                        gen_cfg = ai_cfg.generation
                        self.ai_config.width = gen_cfg.get('width', 1024)
                        self.ai_config.height = gen_cfg.get('height', 1024)
                        self.ai_config.batch_size = gen_cfg.get('batch_size', 1)
                    
                    # Update GPU settings
                    if hasattr(ai_cfg, 'gpu'):
                        gpu_cfg = ai_cfg.gpu
                        self.ai_config.device = gpu_cfg.get('device', 'cuda')
                        self.ai_config.memory_efficient = gpu_cfg.get('memory_efficient', True)
                        self.ai_config.enable_attention_slicing = gpu_cfg.get('enable_attention_slicing', True)
                        self.ai_config.enable_cpu_offload = gpu_cfg.get('enable_cpu_offload', False)
                
                # НОВОЕ: Load hint configuration
                if hasattr(cfg, 'user_hints'):
                    hint_cfg = cfg.user_hints
                    self.hint_config.update({
                        "max_hint_length": hint_cfg.get('max_length', 200),
                        "translate_hints": hint_cfg.get('translate', True),
                        "include_hints_in_prompt": hint_cfg.get('include_in_prompt', True),
                        "hint_weight": hint_cfg.get('weight', 0.3),
                    })
                
                # UPDATED: Log union model info + hint support
                controlnet_info = "Union ControlNet" if "union" in self.ai_config.controlnet_models else "Separate ControlNets"
                logger.info(f"Loaded AI config: model={self.ai_config.base_model}, "
                           f"controlnet={controlnet_info}, "
                           f"device={self.ai_config.device}, "
                           f"hint_support=enabled")
                
        except Exception as e:
            logger.warning(f"Could not load full AI config, using defaults: {e}")
    
    async def _ensure_ai_initialized(self):
        """
        Ensures AI Generator is initialized.
        
        Raises:
            RuntimeError: If AI initialization fails
        """
        async with self._ai_initialization_lock:
            if self._ai_initialized and self.ai_generator:
                return
            
            try:
                logger.info("Initializing AI Image Generator with ControlNet Union + hint support...")
                start_time = time.time()
                
                # Create AI Generator with config (now includes hint support)
                self.ai_generator = AIImageGenerator(self.ai_config)
                
                init_time = time.time() - start_time
                self._ai_initialized = True
                
                logger.info(f"✓ AI Image Generator with ControlNet Union + hint support initialized successfully in {init_time:.1f}s")
                
                # Log AI status
                ai_status = await self.ai_generator.get_generation_status()
                controlnet_model = ai_status.get('controlnet_model', 'unknown')
                logger.info(f"AI Status: models_loaded={ai_status.get('models_loaded')}, "
                           f"pipeline_ready={ai_status.get('pipeline_ready')}, "
                           f"controlnet_model={controlnet_model}, "
                           f"hint_support=true")
                
            except Exception as e:
                logger.error(f"Failed to initialize AI Image Generator: {e}")
                self._ai_initialized = False
                self.ai_generator = None
                raise RuntimeError(f"AI initialization failed: {e}")
    
    async def generate_image(self, request: AIImageRequest) -> GenerationResult:
        """
        Generate writing image for the given request using real AI models.
        ОБНОВЛЕНО: Поддержка пользовательской подсказки hint_writing
        
        Args:
            request: Writing image generation request with optional user hint
            
        Returns:
            GenerationResult: Result of generation with hint metadata
            
        Raises:
            RuntimeError: If generation fails
        """
        start_time = time.time()
        
        try:
            # Логируем с информацией о подсказке
            hint_info = f", hint: '{request.hint_writing}'" if request.has_user_hint() else ""
            logger.info(f"Generating AI image for word: '{request.word}', translation: '{request.translation}'{hint_info}")
            
            # Ensure AI is initialized
            await self._ensure_ai_initialized()
            
            if not self.ai_generator:
                raise RuntimeError("AI Generator not available")
            
            # Use requested dimensions or defaults
            width = request.width if request.width else self.default_width
            height = request.height if request.height else self.default_height
            
            # Prepare generation parameters
            generation_params = {
                'width': width,
                'height': height,
            }
            
            # Extract seed if provided
            seed = getattr(request, 'seed', None)
            
            # НОВОЕ: Extract style if provided
            style = getattr(request, 'style', 'comic')
            
            logger.debug(f"Generation params: {generation_params}")
            logger.debug(f"Seed: {seed}, Style: {style}")
            
            # НОВОЕ: Prepare hint data
            hint_data = None
            if request.has_user_hint():
                hint_data = {
                    "hint_writing": request.hint_writing,
                    "translate": self.hint_config["translate_hints"],
                    "include_in_prompt": self.hint_config["include_hints_in_prompt"],
                    "weight": self.hint_config["hint_weight"]
                }
                logger.debug(f"User hint data: {hint_data}")
            
            # ОБНОВЛЕНО: Generate AI image with hint support
            ai_result = await self.ai_generator.generate_character_image(
                character=request.word,
                translation=request.translation,
                user_hint=request.hint_writing if request.has_user_hint() else None,  # НОВОЕ
                style=style,  # НОВОЕ
                include_conditioning_images=request.include_conditioning_images,
                include_prompt=request.include_prompt,
                seed=seed,
                **generation_params
            )
            
            if not ai_result.success:
                raise RuntimeError(f"AI generation failed: {ai_result.error_message}")
            
            # Calculate generation time
            generation_time_ms = int((time.time() - start_time) * 1000)
            
            # ОБНОВЛЕНО: Create metadata with union model info + hint metadata
            metadata = AIGenerationMetadata(
                generation_time_ms=generation_time_ms,
                ai_model_used=self.ai_config.base_model,
                controlnet_model_used="union",  # UPDATED: Union model
                conditioning_types_used=list(ai_result.generation_metadata.get('conditioning_methods_used', {}).keys()),
                seed_used=seed,
                image_dimensions=(width, height),
                total_processing_time_ms=ai_result.generation_metadata.get('generation_time_ms', 0)
            )
            
            # НОВОЕ: Add hint metadata to main metadata
            if request.has_user_hint():
                # Добавляем метаданные о подсказке в основной объект metadata
                hint_metadata = ai_result.generation_metadata.get('user_hint_metadata', {})
                metadata.user_hint_original = request.hint_writing
                metadata.user_hint_translated = hint_metadata.get('translated_hint', request.hint_writing)
                metadata.user_hint_used = hint_metadata.get('used_in_prompt', False)
                metadata.translation_source = hint_metadata.get('translation_source', 'fallback')
                
                # Обновляем счетчик использования подсказок
                self.hint_usage_count += 1
            
            # Update statistics
            self.generation_count += 1
            
            # Логируем с информацией о подсказке
            hint_result_info = ""
            if request.has_user_hint():
                translated_hint = getattr(metadata, 'user_hint_translated', request.hint_writing)
                hint_used = getattr(metadata, 'user_hint_used', False)
                hint_result_info = f" (hint: '{request.hint_writing}' -> '{translated_hint}', used: {hint_used})"
            
            logger.info(f"✓ Generated AI image for word: {request.word} "
                       f"(total_time: {generation_time_ms}ms, "
                       f"ai_time: {ai_result.generation_metadata.get('generation_time_ms')}ms, "
                       f"size: {len(ai_result.generated_image_base64)} chars{hint_result_info})")
            
            return GenerationResult(
                success=True,
                image_data_base64=ai_result.generated_image_base64,
                format="png",
                metadata=metadata,
                base_image_base64=ai_result.base_image_base64,
                conditioning_images_base64=ai_result.conditioning_images_base64,
                prompt_used=ai_result.prompt_used,
                user_hint_metadata=ai_result.generation_metadata.get('user_hint_metadata', {})  # НОВОЕ
            )
            
        except Exception as e:
            logger.error(f"Error generating AI image: {e}", exc_info=True)
            
            # Calculate error time
            error_time_ms = int((time.time() - start_time) * 1000)
            
            return GenerationResult(
                success=False,
                error=f"AI generation failed: {str(e)}",
                metadata=AIGenerationMetadata(
                    generation_time_ms=error_time_ms,
                    error=True
                )
            )
    
    async def get_service_status(self) -> Dict[str, Any]:
        """
        Get service status information including AI components and hint support.
        Получает информацию о статусе сервиса включая AI компоненты и поддержку подсказок.
        
        Returns:
            Dict with service status
        """
        uptime_seconds = int(time.time() - self.start_time)
        
        base_status = {
            "service": "writing_image_service",
            "status": "healthy",
            "version": "1.5.1",  # ОБНОВЛЕНО: версия с поддержкой подсказок
            "uptime_seconds": uptime_seconds,
            "total_generations": self.generation_count,
            "hint_usage_count": self.hint_usage_count,  # НОВОЕ
            "hint_usage_percentage": (
                (self.hint_usage_count / self.generation_count * 100) 
                if self.generation_count > 0 else 0
            ),  # НОВОЕ
            "implementation": "real_ai_generation_union_with_hints",  # UPDATED
            "supported_formats": ["png"],
            "max_image_size": {"width": 2048, "height": 2048},
            "default_image_size": {"width": self.default_width, "height": self.default_height},
            "features": {
                "ai_generation": True,
                "controlnet_union": True,  # UPDATED: Union ControlNet
                "multi_controlnet": False,  # UPDATED: Not using separate models
                "conditioning_types": ["canny", "depth", "segmentation", "scribble"],
                "prompt_engineering": True,
                "style_variations": True,
                "seed_control": True,
                "universal_language_support": True,
                "user_hints": True,  # НОВОЕ
                "hint_translation": self.hint_config["translate_hints"],  # НОВОЕ
                "translation_service": True  # НОВОЕ
            },
            "hint_config": self.hint_config  # НОВОЕ
        }
        
        # Add AI status if available
        if self.ai_generator and self._ai_initialized:
            try:
                ai_status = await self.ai_generator.get_generation_status()
                base_status["ai_status"] = ai_status
                base_status["status"] = "healthy_with_ai_and_hints"
            except Exception as e:
                logger.warning(f"Could not get AI status: {e}")
                base_status["ai_status"] = {"error": str(e)}
                base_status["status"] = "healthy_ai_warning"
        else:
            base_status["ai_status"] = {
                "initialized": self._ai_initialized,
                "available": self.ai_generator is not None
            }
            if not self._ai_initialized:
                base_status["status"] = "initializing"
        
        # UPDATED: Add configuration info for union model + hints
        base_status["ai_config"] = {
            "base_model": self.ai_config.base_model,
            "device": self.ai_config.device,
            "controlnet_model": "union",  # UPDATED: Single union model
            "controlnet_types_supported": ["canny", "depth", "segmentation", "scribble"],
            "image_size": (self.ai_config.width, self.ai_config.height),
            "hint_support": True,  # НОВОЕ
            "max_hint_length": self.hint_config["max_hint_length"]  # НОВОЕ
        }
        
        return base_status
    
    async def warmup_ai(self) -> Dict[str, Any]:
        """
        Warm up AI models for faster generation.
        Прогревает AI модели для более быстрой генерации.
        ОБНОВЛЕНО: Включает тестирование подсказок
        
        Returns:
            Dict with warmup results
        """
        try:
            logger.info("Starting AI warmup with ControlNet Union + hint support...")
            start_time = time.time()
            
            # Ensure AI is initialized
            await self._ensure_ai_initialized()
            
            if not self.ai_generator:
                return {"success": False, "error": "AI Generator not available"}
            
            # Perform a few warmup generations including hints
            warmup_data = [
                {"char": "测", "hint": ""},
                {"char": "试", "hint": "красивый рисунок"},
                {"char": "验", "hint": ""}
            ]
            warmup_results = []
            
            for data in warmup_data:
                try:
                    char = data["char"]
                    hint = data["hint"]
                    hint_info = f" with hint: '{hint}'" if hint else ""
                    logger.debug(f"Warming up with character: {char}{hint_info}")
                    char_start = time.time()
                    
                    result = await self.ai_generator.generate_character_image(
                        character=char,
                        translation=f"warmup_{char}",
                        user_hint=hint if hint else None,  # НОВОЕ: тестируем подсказки
                        include_conditioning_images=False,
                        include_prompt=False
                    )
                    
                    char_time = int((time.time() - char_start) * 1000)
                    warmup_results.append({
                        "character": char,
                        "hint": hint,
                        "success": result.success,
                        "time_ms": char_time,
                        "error": result.error_message if not result.success else None,
                        "hint_used": bool(hint and result.success)  # НОВОЕ
                    })
                    
                except Exception as e:
                    logger.warning(f"Warmup failed for character {data['char']}: {e}")
                    warmup_results.append({
                        "character": data["char"],
                        "hint": data["hint"],
                        "success": False,
                        "error": str(e),
                        "hint_used": False
                    })
            
            total_warmup_time = int((time.time() - start_time) * 1000)
            successful_warmups = sum(1 for r in warmup_results if r["success"])
            hint_warmups = sum(1 for r in warmup_results if r.get("hint_used", False))
            
            logger.info(f"✓ AI warmup with ControlNet Union + hint support completed: "
                       f"{successful_warmups}/{len(warmup_data)} successful, "
                       f"{hint_warmups} with hints tested, "
                       f"in {total_warmup_time}ms")
            
            return {
                "success": True,
                "total_time_ms": total_warmup_time,
                "successful_warmups": successful_warmups,
                "total_warmups": len(warmup_data),
                "hint_warmups_tested": hint_warmups,  # НОВОЕ
                "warmup_results": warmup_results,
                "controlnet_model": "union",  # UPDATED
                "hint_support": True  # НОВОЕ
            }
            
        except Exception as e:
            logger.error(f"AI warmup failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "total_time_ms": int((time.time() - start_time) * 1000) if 'start_time' in locals() else 0
            }
    
    async def cleanup(self):
        """Clean up AI resources."""
        try:
            logger.info("Cleaning up Writing Image Service...")
            
            if self.ai_generator:
                await self.ai_generator.cleanup()
                self.ai_generator = None
            
            self._ai_initialized = False
            
            logger.info("✓ Writing Image Service cleanup completed")
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
    
    def __del__(self):
        """Destructor to ensure cleanup."""
        if hasattr(self, 'ai_generator') and self.ai_generator:
            # Note: We can't call async cleanup in __del__
            # This is just a safety net for garbage collection
            logger.warning("WritingImageService deleted without explicit cleanup")
            