# scripts/test_opus_support.py

import sys
import os
import asyncio
import argparse
import subprocess

# Добавляем путь к проекту
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

async def check_imageio_ffmpeg():
    print("\n===== Проверка imageio-ffmpeg =====\n")
    
    try:
        import imageio_ffmpeg
        print(f"✅ imageio-ffmpeg установлен")
        
        # Получение пути к FFmpeg
        ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()
        print(f"✅ Путь к FFmpeg: {ffmpeg_path}")
        
        # Проверка работоспособности
        try:
            result = subprocess.run(
                [ffmpeg_path, "-version"], 
                capture_output=True, 
                text=True
            )
            if result.returncode == 0:
                print(f"✅ FFmpeg версия: {result.stdout.splitlines()[0]}")
            else:
                print(f"❌ Ошибка запуска FFmpeg: {result.stderr}")
                return False
        except Exception as e:
            print(f"❌ Ошибка при тесте FFmpeg: {e}")
            return False
        
        # Проверка поддержки OGG
        try:
            result = subprocess.run(
                [ffmpeg_path, "-formats"], 
                capture_output=True, 
                text=True
            )
            if "ogg" in result.stdout.lower():
                print(f"✅ Поддержка формата OGG: ДА")
            else:
                print(f"❌ Поддержка формата OGG: НЕТ")
                return False
        except Exception as e:
            print(f"❌ Ошибка при проверке поддержки OGG: {e}")
            return False
        
        # Проверка поддержки Opus
        try:
            result = subprocess.run(
                [ffmpeg_path, "-codecs"], 
                capture_output=True, 
                text=True
            )
            if "opus" in result.stdout.lower():
                print(f"✅ Поддержка кодека Opus: ДА")
            else:
                print(f"❌ Поддержка кодека Opus: НЕТ")
                return False
        except Exception as e:
            print(f"❌ Ошибка при проверке поддержки Opus: {e}")
            return False
        
        print("\n✅ imageio-ffmpeg полностью поддерживает OGG/Opus!")
        return True
        
    except ImportError:
        print("❌ imageio-ffmpeg не установлен. Установите: pip install imageio-ffmpeg")
        return False
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False

async def test_ogg_conversion(ogg_file):
    if not os.path.exists(ogg_file):
        print(f"❌ Файл {ogg_file} не найден")
        return False
    
    try:
        import imageio_ffmpeg
        ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()
        
        # Создаем выходной WAV файл
        wav_file = os.path.splitext(ogg_file)[0] + "_test.wav"
        
        # Запускаем конвертацию
        cmd = [
            ffmpeg_path,
            "-y",
            "-i", ogg_file,
            "-ar", "16000",
            "-ac", "1",
            "-c:a", "pcm_s16le",
            wav_file
        ]
        
        print(f"Выполняем команду: {' '.join(cmd)}")
        
        process = subprocess.Popen(
            cmd, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE
        )
        stdout, stderr = process.communicate()
        
        if process.returncode != 0:
            print(f"❌ Ошибка конвертации: {stderr.decode()}")
            return False
        
        if os.path.exists(wav_file) and os.path.getsize(wav_file) > 0:
            print(f"✅ Успешная конвертация: {ogg_file} -> {wav_file}")
            
            # Получаем информацию о созданном WAV файле
            info_cmd = [ffmpeg_path, "-i", wav_file]
            process = subprocess.Popen(
                info_cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE
            )
            _, stderr = process.communicate()
            
            print(f"Информация о созданном WAV файле:")
            print(stderr.decode())
            
            return True
        else:
            print(f"❌ Выходной файл не создан или пуст: {wav_file}")
            return False
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False

async def main():
    parser = argparse.ArgumentParser(description='Проверка поддержки OGG/Opus в imageio-ffmpeg')
    parser.add_argument('--check', action='store_true', help='Проверить поддержку OGG/Opus')
    parser.add_argument('--test', type=str, help='Тест конвертации OGG файла в WAV')
    
    args = parser.parse_args()
    
    if args.check:
        await check_imageio_ffmpeg()
    
    if args.test:
        await test_ogg_conversion(args.test)
    
    if not args.check and not args.test:
        print("Укажите хотя бы один из параметров: --check или --test=/path/to/file.ogg")
        parser.print_help()

if __name__ == "__main__":
    asyncio.run(main())
    