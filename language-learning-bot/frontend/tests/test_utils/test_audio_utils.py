"""
Tests for audio_utils module.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, mock_open
import subprocess
import os

from app.utils.audio_utils import (
    get_ffmpeg_path,
    get_audio_info,
    convert_audio_format
)

class TestGetFFmpegPath:
    
    def test_get_ffmpeg_path_success(self):
        # Setup - создаем мок для imageio_ffmpeg
        mock_ffmpeg_path = "/path/to/ffmpeg"
        
        # Патчим imageio_ffmpeg.get_ffmpeg_exe
        with patch('imageio_ffmpeg.get_ffmpeg_exe', return_value=mock_ffmpeg_path):
            # Execute
            result = get_ffmpeg_path()
            
            # Verify
            assert result == mock_ffmpeg_path


class TestGetAudioInfo:
    
    def test_get_audio_info_success(self):
        # Setup
        file_path = "audio.mp3"
        ffmpeg_path = "/path/to/ffmpeg"
        
        # Создаем мок для результата выполнения ffmpeg
        stderr_output = """
        Input #0, mp3, from 'audio.mp3':
            Duration: 00:03:45.51, start: 0.000000, bitrate: 128 kb/s
            Stream #0:0: Audio: mp3, 44100 Hz, stereo, fltp, 128 kb/s
        """
        
        # Патчим необходимые функции
        with patch('app.utils.audio_utils.get_ffmpeg_path', return_value=ffmpeg_path), \
             patch('subprocess.Popen') as mock_popen:
            
            # Настраиваем mock для Popen
            process_mock = MagicMock()
            process_mock.communicate.return_value = (b"", stderr_output.encode('utf-8'))
            mock_popen.return_value = process_mock
            
            # Execute
            result = get_audio_info(file_path)
            
            # Verify
            assert result is not None
            assert "codec" in result
            assert "mp3" in result.get("codec", "")
            assert result.get("channels") == 2  # stereo
            assert "44100" in result.get("sample_rate", "")
            
            # Проверяем параметры вызова Popen
            mock_popen.assert_called_once()
            args, kwargs = mock_popen.call_args
            command = args[0]
            assert ffmpeg_path in command
            assert file_path in command
            assert "-i" in command
    
    def test_get_audio_info_error(self):
        # Setup
        file_path = "nonexistent.mp3"
        
        # Патчим get_ffmpeg_path, чтобы вернуть None (ошибка)
        with patch('app.utils.audio_utils.get_ffmpeg_path', return_value=None):
            # Execute
            result = get_audio_info(file_path)
            
            # Verify
            assert result is None


class TestConvertAudioFormat:
    
    @pytest.mark.asyncio
    async def test_convert_audio_format_success(self):
        # Setup
        input_file = "input.ogg"
        output_file = "output.wav"
        ffmpeg_path = "/path/to/ffmpeg"
        
        # Патчим необходимые функции
        with patch('app.utils.audio_utils.get_ffmpeg_path', return_value=ffmpeg_path), \
             patch('subprocess.Popen') as mock_popen, \
             patch('os.path.exists', return_value=True), \
             patch('os.path.getsize', return_value=1024):  # Размер файла > 0
            
            # Настраиваем mock для Popen
            process_mock = MagicMock()
            process_mock.returncode = 0
            process_mock.communicate.return_value = (b"", b"")
            mock_popen.return_value = process_mock
            
            # Execute
            result = await convert_audio_format(input_file, output_file)
            
            # Verify
            assert result == output_file
            
            # Проверяем параметры вызова Popen
            mock_popen.assert_called_once()
            args, kwargs = mock_popen.call_args
            command = args[0]
            assert ffmpeg_path in command
            assert input_file in command
            assert output_file in command
            assert "-ar" in command  # Проверка частоты дискретизации
            assert "16000" in command  # Проверка значения частоты
            assert "-ac" in command  # Проверка числа каналов
            assert "1" in command  # Моно аудио
    
    @pytest.mark.asyncio
    async def test_convert_audio_format_auto_output_file(self):
        # Setup
        input_file = "input.ogg"
        expected_output = "input.wav"  # По умолчанию должен заменить расширение
        ffmpeg_path = "/path/to/ffmpeg"
        
        # Патчим необходимые функции
        with patch('app.utils.audio_utils.get_ffmpeg_path', return_value=ffmpeg_path), \
             patch('subprocess.Popen') as mock_popen, \
             patch('os.path.exists', return_value=True), \
             patch('os.path.getsize', return_value=1024):  # Размер файла > 0
            
            # Настраиваем mock для Popen
            process_mock = MagicMock()
            process_mock.returncode = 0
            process_mock.communicate.return_value = (b"", b"")
            mock_popen.return_value = process_mock
            
            # Execute
            result = await convert_audio_format(input_file)  # Без указания output_file
            
            # Verify
            assert result == expected_output
            
            # Проверяем параметры вызова Popen
            mock_popen.assert_called_once()
            args, kwargs = mock_popen.call_args
            command = args[0]
            assert ffmpeg_path in command
            assert input_file in command
            assert expected_output in command
    
    @pytest.mark.asyncio
    async def test_convert_audio_format_error(self):
        # Setup
        input_file = "input.ogg"
        output_file = "output.wav"
        
        # Патчим get_ffmpeg_path, чтобы вернуть None (ошибка)
        with patch('app.utils.audio_utils.get_ffmpeg_path', return_value=None):
            # Execute
            result = await convert_audio_format(input_file, output_file)
            
            # Verify
            assert result is None
            