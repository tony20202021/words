"""
Tests for voice_recognition module.
"""

import pytest
import os
from unittest.mock import AsyncMock, MagicMock, patch, mock_open

from app.utils.voice_recognition import (
    get_whisper_model,
    recognize_speech_async,
    process_telegram_voice
)

class TestGetWhisperModel:
    
    def test_get_whisper_model_success(self):
        # Setup
        mock_whisper_model = MagicMock()
        
        # Патчим модуль whisper для возврата mock модели
        with patch('app.utils.voice_recognition.whisper') as mock_whisper:
            mock_whisper.load_model.return_value = mock_whisper_model
            
            # В первый раз загрузка модели должна произойти
            model = get_whisper_model()
            
            # Verify
            assert model == mock_whisper_model
            mock_whisper.load_model.assert_called_once_with("small")
            
            # При повторном вызове модель должна браться из кэша
            mock_whisper.load_model.reset_mock()
            cached_model = get_whisper_model()
            
            assert cached_model == mock_whisper_model
            # Проверяем, что load_model не вызывался второй раз
            mock_whisper.load_model.assert_not_called()


class TestRecognizeSpeechAsync:
    
    @pytest.mark.asyncio
    async def test_recognize_speech_async_success(self):
        # Setup
        file_path = "test_audio.wav"
        language = "ru"
        mock_whisper_model = MagicMock()
        mock_whisper_model.transcribe.return_value = {"text": "Тестовый текст"}
        
        # Создаем future для имитации асинхронного результата
        future = AsyncMock()
        future.return_value = "Тестовый текст"
        
        # Патчим функции, которые будут вызываться внутри
        with patch('app.utils.voice_recognition.get_whisper_model', return_value=mock_whisper_model), \
             patch('app.utils.voice_recognition.get_audio_info', return_value={"codec": "pcm_s16le", "sample_rate": "16000", "channels": 1}), \
             patch('asyncio.get_event_loop') as mock_loop:
            
            # Настраиваем event loop для выполнения функции асинхронно
            mock_loop.return_value = AsyncMock()
            mock_loop.return_value.run_in_executor = AsyncMock(return_value="Тестовый текст")
            
            # Execute
            result = await recognize_speech_async(file_path, model_size="small", language=language)
            
            # Verify
            assert result == "Тестовый текст"
            # Проверяем, что run_in_executor был вызван хотя бы один раз
            mock_loop.return_value.run_in_executor.assert_called_once()


class TestProcessTelegramVoice:
    
    @pytest.mark.asyncio
    async def test_process_telegram_voice_success(self):
        # Setup
        bot = AsyncMock()
        voice_message = MagicMock(file_id="file123", file_unique_id="unique123")
        temp_dir = "temp"
        
        # Патчим os.path.exists два раза с разными возвращаемыми значениями
        path_exists_mock = MagicMock(side_effect=[False, True])
        
        # Патчим все необходимые функции
        with patch('os.path.exists', path_exists_mock), \
             patch('os.makedirs') as mock_makedirs, \
             patch('app.utils.voice_recognition.recognize_speech_async', return_value="Распознанный текст"), \
             patch('os.remove') as mock_remove, \
             patch('os.path.getsize', return_value=1024):
            
            # Настраиваем мок бота для скачивания файла
            file_info = MagicMock()
            file_info.file_path = "path/to/file.ogg"
            bot.get_file.return_value = file_info
            
            # Execute
            result = await process_telegram_voice(bot, voice_message, temp_dir)
            
            # Verify
            assert result == "Распознанный текст"
            mock_makedirs.assert_called_once_with(temp_dir)
            bot.get_file.assert_called_once_with("file123")
            bot.download_file.assert_called_once_with("path/to/file.ogg", f"{temp_dir}/unique123.ogg")
            mock_remove.assert_called_once()