"""
Writing image generation service.
Сервис генерации картинок написания.
REAL AI IMPLEMENTATION - uses actual AI models for generation.
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
    ):
        self.success = success
        self.image_data_base64 = image_data_base64
        self.format = format
        self.metadata = metadata
        self.error = error
        self.base_image_base64 = base_image_base64
        self.conditioning_images_base64 = conditioning_images_base64
        self.prompt_used = prompt_used


class WritingImageService:
    """
    Service for generating writing images using real AI models.
    Сервис для генерации картинок написания с использованием реальных AI моделей.
    """
    
    def __init__(self):
        """Initialize the writing image service."""
        self.generation_count = 0
        self.start_time = time.time()
        self.image_processor = get_image_processor()
        
        # Load configuration
        self._load_config()
        
        # Initialize AI Generator
        self.ai_generator = None
        self._ai_initialization_lock = asyncio.Lock()
        self._ai_initialized = False
        
        logger.info("WritingImageService initialized with real AI generation (ControlNet Union)")
    
    def _load_config(self):
        """Load configuration from Hydra config."""
        # Default values
        self.default_width = 1024
        self.default_height = 1024
        self.show_guidelines_default = True
        
        # AI Generation defaults
        self.ai_config = AIGenerationConfig()
        
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
                        self.ai_config.num_inference_steps = gen_cfg.get('num_inference_steps', 30)
                        self.ai_config.guidance_scale = gen_cfg.get('guidance_scale', 7.5)
                        self.ai_config.width = gen_cfg.get('width', 1024)
                        self.ai_config.height = gen_cfg.get('height', 1024)
                        self.ai_config.batch_size = gen_cfg.get('batch_size', 1)
                    
                    # Update conditioning weights
                    if hasattr(ai_cfg, 'conditioning_weights'):
                        self.ai_config.conditioning_weights = dict(ai_cfg.conditioning_weights)
                    
                    # Update GPU settings
                    if hasattr(ai_cfg, 'gpu'):
                        gpu_cfg = ai_cfg.gpu
                        self.ai_config.device = gpu_cfg.get('device', 'cuda')
                        self.ai_config.memory_efficient = gpu_cfg.get('memory_efficient', True)
                        self.ai_config.enable_attention_slicing = gpu_cfg.get('enable_attention_slicing', True)
                        self.ai_config.enable_cpu_offload = gpu_cfg.get('enable_cpu_offload', False)
                
                # UPDATED: Log union model info
                controlnet_info = "Union ControlNet" if "union" in self.ai_config.controlnet_models else "Separate ControlNets"
                logger.info(f"Loaded AI config: model={self.ai_config.base_model}, "
                           f"controlnet={controlnet_info}, "
                           f"device={self.ai_config.device}, "
                           f"steps={self.ai_config.num_inference_steps}")
                
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
                logger.info("Initializing AI Image Generator with ControlNet Union...")
                start_time = time.time()
                
                # Create AI Generator with config
                self.ai_generator = AIImageGenerator(self.ai_config)
                
                # Pre-load models to check if everything works
                # This will trigger model loading and pipeline setup
                test_character = "测"
                test_translation = "test"
                
                logger.info("Testing AI pipeline with test character...")
                test_result = await self.ai_generator.generate_character_image(
                    character=test_character,
                    translation=test_translation,
                    include_conditioning_images=False,
                    include_prompt=False
                )
                
                if not test_result.success:
                    raise RuntimeError(f"AI pipeline test failed: {test_result.error_message}")
                
                init_time = time.time() - start_time
                self._ai_initialized = True
                
                logger.info(f"✓ AI Image Generator with ControlNet Union initialized successfully in {init_time:.1f}s")
                
                # Log AI status
                ai_status = await self.ai_generator.get_generation_status()
                controlnet_model = ai_status.get('controlnet_model', 'unknown')
                logger.info(f"AI Status: models_loaded={ai_status.get('models_loaded')}, "
                           f"pipeline_ready={ai_status.get('pipeline_ready')}, "
                           f"controlnet_model={controlnet_model}")
                
            except Exception as e:
                logger.error(f"Failed to initialize AI Image Generator: {e}")
                self._ai_initialized = False
                self.ai_generator = None
                raise RuntimeError(f"AI initialization failed: {e}")
    
    async def generate_image(self, request: AIImageRequest) -> GenerationResult:
        """
        Generate writing image for the given request using real AI models.
        
        Args:
            request: Writing image generation request
            
        Returns:
            GenerationResult: Result of generation
            
        Raises:
            RuntimeError: If generation fails
        """
        start_time = time.time()
        
        try:
            logger.info(f"Generating AI image for word: '{request.word}', translation: '{request.translation}'")
            
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
                'num_inference_steps': getattr(request, 'num_inference_steps', self.ai_config.num_inference_steps),
                'guidance_scale': getattr(request, 'guidance_scale', self.ai_config.guidance_scale),
            }
            
            # Extract conditioning weights if provided
            conditioning_weights = None
            if hasattr(request, 'conditioning_weights') and request.conditioning_weights:
                conditioning_weights = request.conditioning_weights
            
            # Extract seed if provided
            seed = getattr(request, 'seed', None)
            
            logger.debug(f"Generation params: {generation_params}")
            logger.debug(f"Conditioning weights: {conditioning_weights}")
            logger.debug(f"Seed: {seed}")
            
            # Generate AI image
            ai_result = await self.ai_generator.generate_character_image(
                character=request.word,
                translation=request.translation,
                conditioning_weights=conditioning_weights,
                include_conditioning_images=request.include_conditioning_images,
                include_prompt=request.include_prompt,
                include_semantic_analysis=request.include_semantic_analysis,
                seed=seed,
                **generation_params
            )
            
            if not ai_result.success:
                raise RuntimeError(f"AI generation failed: {ai_result.error_message}")
            
            # Calculate generation time
            generation_time_ms = int((time.time() - start_time) * 1000)
            
            # UPDATED: Create metadata with union model info
            metadata = AIGenerationMetadata(
                generation_time_ms=generation_time_ms,
                ai_model_used=self.ai_config.base_model,
                controlnet_model_used="union",  # UPDATED: Union model
                conditioning_types_used=list(ai_result.generation_metadata.get('conditioning_methods_used', {}).keys()),
                inference_steps_used=generation_params.get('num_inference_steps'),
                guidance_scale_used=generation_params.get('guidance_scale'),
                seed_used=seed,
                image_dimensions=(width, height),
                total_processing_time_ms=ai_result.generation_metadata.get('generation_time_ms', 0)
            )
            
            # Update statistics
            self.generation_count += 1
            
            logger.info(f"✓ Generated AI image for word: {request.word} "
                       f"(total_time: {generation_time_ms}ms, "
                       f"ai_time: {ai_result.generation_metadata.get('generation_time_ms')}ms, "
                       f"size: {len(ai_result.generated_image_base64)} chars)")
            
            return GenerationResult(
                success=True,
                image_data_base64=ai_result.generated_image_base64,
                format="png",
                metadata=metadata,
                base_image_base64=ai_result.base_image_base64,
                conditioning_images_base64=ai_result.conditioning_images_base64,
                prompt_used=ai_result.prompt_used,
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
        Get service status information including AI components.
        Получает информацию о статусе сервиса включая AI компоненты.
        
        Returns:
            Dict with service status
        """
        uptime_seconds = int(time.time() - self.start_time)
        
        base_status = {
            "service": "writing_image_service",
            "status": "healthy",
            "version": "1.0.0",
            "uptime_seconds": uptime_seconds,
            "total_generations": self.generation_count,
            "implementation": "real_ai_generation_union",  # UPDATED
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
                "universal_language_support": True
            }
        }
        
        # Add AI status if available
        if self.ai_generator and self._ai_initialized:
            try:
                ai_status = await self.ai_generator.get_generation_status()
                base_status["ai_status"] = ai_status
                base_status["status"] = "healthy_with_ai"
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
        
        # UPDATED: Add configuration info for union model
        base_status["ai_config"] = {
            "base_model": self.ai_config.base_model,
            "device": self.ai_config.device,
            "controlnet_model": "union",  # UPDATED: Single union model
            "controlnet_types_supported": ["canny", "depth", "segmentation", "scribble"],
            "inference_steps": self.ai_config.num_inference_steps,
            "guidance_scale": self.ai_config.guidance_scale,
            "image_size": (self.ai_config.width, self.ai_config.height)
        }
        
        return base_status
    
    async def warmup_ai(self) -> Dict[str, Any]:
        """
        Warm up AI models for faster generation.
        Прогревает AI модели для более быстрой генерации.
        
        Returns:
            Dict with warmup results
        """
        try:
            logger.info("Starting AI warmup with ControlNet Union...")
            start_time = time.time()
            
            # Ensure AI is initialized
            await self._ensure_ai_initialized()
            
            if not self.ai_generator:
                return {"success": False, "error": "AI Generator not available"}
            
            # Perform a few warmup generations
            warmup_characters = ["测", "试", "验"]
            warmup_results = []
            
            for char in warmup_characters:
                try:
                    logger.debug(f"Warming up with character: {char}")
                    char_start = time.time()
                    
                    result = await self.ai_generator.generate_character_image(
                        character=char,
                        translation=f"warmup_{char}",
                        include_conditioning_images=False,
                        include_prompt=False
                    )
                    
                    char_time = int((time.time() - char_start) * 1000)
                    warmup_results.append({
                        "character": char,
                        "success": result.success,
                        "time_ms": char_time,
                        "error": result.error_message if not result.success else None
                    })
                    
                except Exception as e:
                    logger.warning(f"Warmup failed for character {char}: {e}")
                    warmup_results.append({
                        "character": char,
                        "success": False,
                        "error": str(e)
                    })
            
            total_warmup_time = int((time.time() - start_time) * 1000)
            successful_warmups = sum(1 for r in warmup_results if r["success"])
            
            logger.info(f"✓ AI warmup with ControlNet Union completed: {successful_warmups}/{len(warmup_characters)} successful "
                       f"in {total_warmup_time}ms")
            
            return {
                "success": True,
                "total_time_ms": total_warmup_time,
                "successful_warmups": successful_warmups,
                "total_warmups": len(warmup_characters),
                "warmup_results": warmup_results,
                "controlnet_model": "union"  # UPDATED
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
            