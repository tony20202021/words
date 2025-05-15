# scripts/check_voice_recognition.py

import sys
import os
import asyncio
import argparse
import subprocess

# Добавляем путь к проекту
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

async def check_environment():
    print("\n===== Проверка окружения для распознавания речи =====\n")
    
    # Проверка imageio-ffmpeg
    print("1. Проверка imageio-ffmpeg:")
    try:
        import imageio_ffmpeg
        print(f"✅ imageio-ffmpeg установлен")
        
        ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()
        print(f"✅ Путь к FFmpeg: {ffmpeg_path}")
        
        # Проверка работоспособности
        result = subprocess.run(
            [ffmpeg_path, "-version"], 
            capture_output=True, 
            text=True
        )
        if result.returncode == 0:
            print(f"✅ FFmpeg версия: {result.stdout.splitlines()[0]}")
        else:
            print(f"❌ Ошибка запуска FFmpeg: {result.stderr}")
        
        # Проверка поддержки Opus
        result = subprocess.run(
            [ffmpeg_path, "-codecs"], 
            capture_output=True, 
            text=True
        )
        if "opus" in result.stdout.lower():
            print(f"✅ Поддержка кодека Opus: ДА")
        else:
            print(f"❌ Поддержка кодека Opus: НЕТ")
    except ImportError:
        print("❌ imageio-ffmpeg не установлен. Установите: pip install imageio-ffmpeg")
    
    # Проверка Whisper
    print("\n2. Проверка Whisper:")
    try:
        import whisper
        print(f"✅ Whisper установлен")
        
        # Проверка зависимостей
        try:
            import torch
            print(f"✅ PyTorch версия: {torch.__version__}")
            print(f"✅ CUDA доступен: {torch.cuda.is_available()}")
        except ImportError:
            print("❌ PyTorch не установлен")
    except ImportError:
        print("❌ Whisper не установлен. Установите: pip install openai-whisper")
    
    # Проверка наличия директории для временных файлов
    print("\n3. Проверка директории для временных файлов:")
    temp_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "temp")
    if os.path.exists(temp_dir):
        print(f"✅ Директория существует: {temp_dir}")
    else:
        print(f"❌ Директория не существует: {temp_dir}")
        try:
            os.makedirs(temp_dir)
            print(f"✅ Директория создана: {temp_dir}")
        except Exception as e:
            print(f"❌ Ошибка создания директории: {e}")
    
    print("\n===== Проверка завершена =====\n")

async def test_whisper(model_size="tiny"):
    print(f"\n===== Тестирование модели Whisper {model_size} =====\n")
    
    try:
        import whisper
        print("Загрузка модели Whisper (это может занять некоторое время)...")
        start_time = __import__("time").time()
        model = whisper.load_model(model_size)
        elapsed = __import__("time").time() - start_time
        print(f"✅ Модель загружена за {elapsed:.2f} секунд")
        
        print("\n===== Тестирование завершено =====\n")
    except Exception as e:
        print(f"❌ Ошибка при загрузке модели: {e}")

async def main():
    parser = argparse.ArgumentParser(description='Проверка распознавания речи')
    parser.add_argument('--check', action='store_true', help='Проверить окружение')
    parser.add_argument('--test-whisper', action='store_true', help='Тест загрузки модели Whisper')
    parser.add_argument('--model', type=str, default='tiny', 
                      choices=['tiny', 'base', 'small', 'medium', 'large'],
                      help='Размер модели Whisper')
    
    args = parser.parse_args()
    
    if args.check:
        await check_environment()
    
    if args.test_whisper:
        await test_whisper(args.model)
    
    if not args.check and not args.test_whisper:
        print("Укажите хотя бы один из параметров: --check или --test-whisper")
        parser.print_help()

if __name__ == "__main__":
    asyncio.run(main())
    