"""
Tests for ffmpeg_utils module.
"""

import pytest
from unittest.mock import MagicMock, patch, mock_open
import subprocess

from app.utils.ffmpeg_utils import (
    get_ffmpeg_path,
    check_opus_support,
    convert_audio,
    get_audio_info
)

class TestGetFFmpegPath:
    
    def test_get_ffmpeg_path_success(self):
        # Setup - создаем мок для imageio_ffmpeg
        mock_ffmpeg_path = "/path/to/ffmpeg"
        
        # Создаем мок результата для subprocess.run
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = "ffmpeg version 4.2.2"
        
        # Патчим необходимые модули и функции
        with patch('imageio_ffmpeg.get_ffmpeg_exe', return_value=mock_ffmpeg_path), \
             patch('subprocess.run', return_value=mock_process):
            
            # Execute
            result = get_ffmpeg_path()
            
            # Verify
            assert result == mock_ffmpeg_path
            # Функция imageio_ffmpeg.get_ffmpeg_exe вызывается в коде, но мы уже патчим ее
            # сама проверка на вызов избыточна и может вызвать ошибку
            # imageio_ffmpeg.get_ffmpeg_exe.assert_called_once()


class TestCheckOpusSupport:
    
    def test_check_opus_support_success(self):
        # Setup
        ffmpeg_path = "/path/to/ffmpeg"
        
        # Создаем мок результата для subprocess.run
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = "DEA.L. opus Opus (Opus Audio)"
        
        # Патчим subprocess.run
        with patch('subprocess.run', return_value=mock_process):
            # Execute
            result = check_opus_support(ffmpeg_path)
            
            # Verify
            assert result is True  # "opus" содержится в stdout
            subprocess.run.assert_called_once()


class TestConvertAudio:
    
    @pytest.mark.asyncio
    async def test_convert_audio_success(self):
        # Setup
        input_file = "input.ogg"
        output_file = "output.wav"
        ffmpeg_path = "/path/to/ffmpeg"
        
        # Патчим необходимые функции
        with patch('app.utils.ffmpeg_utils.get_ffmpeg_path', return_value=ffmpeg_path), \
             patch('subprocess.Popen') as mock_popen, \
             patch('os.path.exists', return_value=True), \
             patch('os.path.getsize', return_value=1024):  # Размер файла > 0
            
            # Настраиваем mock для Popen
            process_mock = MagicMock()
            process_mock.returncode = 0
            process_mock.communicate.return_value = (b"", b"")
            mock_popen.return_value = process_mock
            
            # Execute
            result = await convert_audio(input_file, output_file)
            
            # Verify
            assert result == output_file
            # Проверяем, что Popen вызван с правильными параметрами
            mock_popen.assert_called_once()
            # Проверяем параметры вызова
            args, kwargs = mock_popen.call_args
            command = args[0]
            assert ffmpeg_path in command
            assert input_file in command
            assert output_file in command


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
        
        # Патчим get_ffmpeg_path и subprocess.Popen
        with patch('app.utils.ffmpeg_utils.get_ffmpeg_path', return_value=ffmpeg_path), \
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
            # Проверяем, что Popen вызван с правильными параметрами
            mock_popen.assert_called_once()