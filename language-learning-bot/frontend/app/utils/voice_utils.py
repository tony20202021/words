"""
Utilities for handling voice messages in the bot.
Provides common functions for voice recognition and processing.
"""

import logging
from typing import Optional, Union
from aiogram.types import Message, Voice

from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class VoiceProcessor:
    """Class for processing voice messages."""
    
    def __init__(self):
        self.recognition_available = self._check_recognition_availability()
    
    def _check_recognition_availability(self) -> bool:
        """Check if voice recognition is available."""
        try:
            from app.utils.voice_recognition import process_telegram_voice
            return True
        except ImportError:
            logger.warning("Voice recognition module not available")
            return False
    
    async def process_voice_message(
        self, 
        message: Message, 
        processing_message: str = "🎙️ Распознаю ваше голосовое сообщение...",
        success_template: str = "✅ Распознано из голосового сообщения:\n\n<code>{text}</code>",
        show_recognized_text: bool = True
    ) -> Optional[str]:
        """
        Process voice message and return recognized text.
        
        Args:
            message: The message containing voice
            processing_message: Message to show while processing
            success_template: Template for success message (use {text} placeholder)
            show_recognized_text: Whether to show recognized text to user
            
        Returns:
            Recognized text or None if recognition failed
        """
        if not message.voice:
            await message.answer("⚠️ Пожалуйста, отправьте голосовое сообщение")
            return None
        
        if not self.recognition_available:
            await message.answer("❌ Распознавание речи недоступно. Пожалуйста, отправьте текст.")
            return None
        
        # Show processing message
        processing_msg = await message.answer(processing_message)
        
        try:
            # Import and use voice recognition
            from app.utils.voice_recognition import process_telegram_voice
            
            # Recognize voice message
            recognized_text = await process_telegram_voice(message.bot, message.voice)
            
            # Delete processing message
            await processing_msg.delete()
            
            if recognized_text:
                # Show success message if requested
                if show_recognized_text:
                    success_message = success_template.format(text=recognized_text)
                    await message.answer(success_message, parse_mode="HTML")
                
                logger.info(f"Successfully recognized voice message: {recognized_text[:50]}...")
                return recognized_text
            else:
                await message.answer("❌ Не удалось распознать голосовое сообщение. Пожалуйста, отправьте текст или попробуйте еще раз.")
                return None
                
        except Exception as e:
            logger.error(f"Error processing voice message: {e}", exc_info=True)
            await processing_msg.delete()
            await message.answer("❌ Ошибка при распознавании голосового сообщения. Пожалуйста, попробуйте еще раз или отправьте текст.")
            return None
    
    async def get_text_or_voice(
        self, 
        message: Message, 
        voice_processing_message: str = "🎙️ Распознаю голосовое сообщение...",
        show_voice_result: bool = True
    ) -> Optional[str]:
        """
        Get text from message (either text or voice).
        
        Args:
            message: The message object
            voice_processing_message: Message to show while processing voice
            show_voice_result: Whether to show voice recognition result
            
        Returns:
            Text content or None if neither text nor voice available
        """
        if message.text:
            return message.text.strip()
        elif message.voice:
            return await self.process_voice_message(
                message, 
                processing_message=voice_processing_message,
                show_recognized_text=show_voice_result
            )
        else:
            await message.answer("⚠️ Пожалуйста, отправьте текст или голосовое сообщение")
            return None


# Global voice processor instance
voice_processor = VoiceProcessor()


# Convenience functions for backward compatibility
async def process_voice_message(
    message: Message, 
    processing_message: str = "🎙️ Распознаю ваше голосовое сообщение...",
    success_template: str = "✅ Распознано из голосового сообщения:\n\n<code>{text}</code>",
    show_recognized_text: bool = True
) -> Optional[str]:
    """
    Process voice message and return recognized text.
    
    Args:
        message: The message containing voice
        processing_message: Message to show while processing
        success_template: Template for success message
        show_recognized_text: Whether to show recognized text to user
        
    Returns:
        Recognized text or None if recognition failed
    """
    return await voice_processor.process_voice_message(
        message, processing_message, success_template, show_recognized_text
    )


async def get_text_or_voice(
    message: Message, 
    voice_processing_message: str = "🎙️ Распознаю голосовое сообщение...",
    show_voice_result: bool = True
) -> Optional[str]:
    """
    Get text from message (either text or voice).
    
    Args:
        message: The message object
        voice_processing_message: Message to show while processing voice
        show_voice_result: Whether to show voice recognition result
        
    Returns:
        Text content or None if neither text nor voice available
    """
    return await voice_processor.get_text_or_voice(
        message, voice_processing_message, show_voice_result
    )


async def is_voice_recognition_available() -> bool:
    """
    Check if voice recognition is available.
    
    Returns:
        True if voice recognition is available, False otherwise
    """
    return voice_processor.recognition_available


# Example usage for hints
async def process_hint_input(
    message: Message,
    hint_name: str,
    success_callback = None
) -> Optional[str]:
    """
    Process hint input (text or voice) with specific messaging for hints.
    
    Args:
        message: The message object
        hint_name: Name of the hint being created/edited
        success_callback: Optional callback to call on success
        
    Returns:
        Hint text or None if processing failed
    """
    hint_text = await get_text_or_voice(
        message,
        voice_processing_message=f"🎙️ Распознаю голосовую подсказку для «{hint_name}». Ожидаемое время: 10 секунд...",
        show_voice_result=False  # We'll show custom message
    )
    
    if hint_text and message.voice:
        # Custom success message for voice hints
        await message.answer(
            f"✅ Подсказка «{hint_name}» распознана из голосового сообщения:\n\n"
            f"<code>{hint_text}</code>",
            parse_mode="HTML"
        )
    
    if hint_text and success_callback:
        await success_callback(hint_text)
    
    return hint_text
