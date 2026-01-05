import os
import shutil

import json
import tqdm

import dragonmapper.transcriptions as dt
from pypinyin import lazy_pinyin, Style

from pydub import AudioSegment

from gtts import gTTS

def mp3_combine(chars_sounds_all: list, new_name: str, pause_duration_ms=100):
    # # Создаем паузу (тишину)
    # pause = AudioSegment.silent(duration=pause_duration_ms)
    
    # Загружаем MP3 файлы
    segments_all = []
    for file in chars_sounds_all:
        # if len(segments_all) > 0:
        #     segments_all.append(pause)
        segments_all.append(AudioSegment.from_mp3(file))

    # Склеиваем: первый файл + пауза + второй файл
    combined = sum(segments_all)
    
    # Сохраняем результат
    combined.export(new_name, format="mp3")


def combine_sounds(word_foreign: str, sounds_path: str, output_dir: str):
    
    result = None

    chars_sounds_all = []
    chars_transcriptions_all = []
    all_found = True

    for char in word_foreign:
        char_transcription = lazy_pinyin(char, style=Style.TONE3)[0]
        if char_transcription[-1] not in ['1', '2', '3', '4']:
            char_transcription = char_transcription + '5'
            
        chars_transcriptions_all.append(char_transcription)

        sound_file_name = os.path.join(sounds_path, f"{char_transcription}.mp3")
        if os.path.exists(sound_file_name):
            chars_sounds_all.append(sound_file_name)
            # print(sound_file_name)
        else:
            print(f"Sound file not found: {sound_file_name}")
            all_found = False
            break

    new_name = output_dir + f"/{'_'.join(chars_transcriptions_all)}.mp3"

    if all_found:
        if len(chars_sounds_all) == 1:
            shutil.copy(chars_sounds_all[0], new_name)
        else:
            mp3_combine(chars_sounds_all, new_name)
                                
        result = new_name
    
    return result


def generate_audio(text, output_file):
    """Генерирует MP3 из китайского текста"""
    tts = gTTS(text=text, lang='zh-CN', slow=False)  # или 'zh-TW' для традиционного
    tts.save(output_file)
    return output_file


def generate_sounds(word_foreign: str, output_dir: str):
    result = None

    chars_toned_all = []
    for char in word_foreign:
        char_transcription = lazy_pinyin(char, style=Style.TONE3)[0]
        if char_transcription[-1] not in ['1', '2', '3', '4']:
            char_transcription = char_transcription + '5'
        chars_toned_all.append(char_transcription)

    new_name = os.path.join(output_dir, f"{'_'.join(chars_toned_all)}.mp3")
    result = generate_audio(word_foreign, new_name)
                        
    return result


def generate_all_sounds(word_foreign: str, sounds_dict: dict, output_dir: str):
    
    sounds_all = {}
    
    for sound_name in sorted(sounds_dict.keys()):
        sound_config = sounds_dict[sound_name]
        
        output_path = os.path.join(output_dir, sound_name)
        os.makedirs(output_path, exist_ok=True)

        if sound_config['use_path']:
            word_sound_path = combine_sounds(word_foreign, sound_config['path'], output_path)
        else:
            word_sound_path = generate_sounds(word_foreign, output_path)
        
        sounds_all[sound_name] = word_sound_path

    return sounds_all
    

if __name__ == "__main__":

    WORK_DIR = ""
    INPUT_DIR = os.path.join(WORK_DIR, "data")
    INPUT_FILE = "words_Китайский_20251002_055605.json.new_radicals.json.tones.json.cross_references.json.tones.json"
    INPUT_PATH = os.path.join(INPUT_DIR, INPUT_FILE)

    OUTPUT_DIR = os.path.join(WORK_DIR, "sounds")
    OUTPUT_PATH = os.path.join(OUTPUT_DIR, INPUT_FILE + ".sounds.json")

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    LIMIT = 1_000

    sounds_dict = {
        'sound_1': {
            'use_path': True,
            'path': '/home/tony/repos/words/words/sounds/archchinese/data/downloaded_sounds',
        },
        'sound_2': {
            'use_path': True,
            'path': '/home/tony/repos/words/words/sounds/Yoyo_Chinese/data/downloaded_sounds',
        },
        'sound_3': {
            'use_path': False,
            'path': None,
        },
    }

    with open(INPUT_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)

    data["words"] = data["words"][:LIMIT]

    count_empty = 0

    for entry in tqdm.tqdm(data["words"][:LIMIT]):
        word_foreign = entry["word_foreign"]
        word_number = entry["word_number"]

        all_sounds = generate_all_sounds(word_foreign, sounds_dict, OUTPUT_DIR)

        if len(all_sounds) == 0:
            count_empty += 1

        entry["sounds"] = {k: all_sounds[k] for k in sorted(all_sounds.keys()) if all_sounds[k] is not None}

    print(f"count_empty: {count_empty}")

    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

    print(f"Exported {len(data['words'])} words to {OUTPUT_PATH}")

