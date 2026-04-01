import json
import tqdm
from pypinyin import lazy_pinyin, Style
import dragonmapper
import dragonmapper.transcriptions as dt
from dragonmapper.transcriptions import accented_syllable_to_numbered, numbered_syllable_to_accented


def generate_all_tones(transcription: str):
    """
    Generate all 5 tones for pinyin syllable
    Args:
        transcription: pinyin in any format ('jiu', 'jiu4', 'jiù')  
    Returns:
        list: [neutral0, tone1, tone2, tone3, tone4]
    """
    # Нормализуем к числовому формату
    numbered = dt.accented_syllable_to_numbered(transcription)
    base = numbered[:-1] if numbered[-1].isdigit() else numbered
    
    # Генерируем все тоны
    variants = {}
    variants[0] = base  # neutral tone
    for i in range(1, 4+1):
        if dt.is_pinyin(base + str(i)):
            variants[i] = dt.to_pinyin(base + str(i))
    
    return variants


if __name__ == "__main__":
    # INPUT_FILE = "/home/tony/repos/words/words/tones/data/words_Китайский_20250826_160132.json"
    # INPUT_FILE = "/home/tony/repos/words/words/tones/tones_2/data/words_Китайский_20251002_055605.json.new_radicals.json.tones.json.cross_references.json"
    INPUT_FILE = "/home/tony/repos/words/words/data/words_Китайский_20260331_151646.json"

    OUTPUT_FILE = INPUT_FILE + ".tones.json"

    LIMIT = 1_000

    HIDE_TONES = False

    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)

    data["words"] = data["words"][:LIMIT]

    # chars_dict = {}
    # for entry in tqdm.tqdm(data["words"][:LIMIT]):
    #     word_foreign = entry["word_foreign"]
    #     for char in set(word_foreign):
    #         if char not in chars_dict:
    #             chars_dict[char] = []
    #         chars_dict[char].append(entry)
            
    # print(f"chars_dict: {len(chars_dict)}")
    # print(chars_dict)

    tones_dict = {}
    for entry in tqdm.tqdm(data["words"][:LIMIT]):
        word_foreign = entry["word_foreign"]

        # if len(word_foreign) > 1:
        #     continue
        
        for char in set(word_foreign):
            transcriptions = lazy_pinyin(char, style=Style.TONE)
            if len(transcriptions) > 1:
                print(transcriptions)

            if transcriptions:
                for transcription in transcriptions:
                    if transcription not in tones_dict:
                        tones_dict[transcription] = []
                    tones_dict[transcription].append(entry)
            else:
                print(f"char {char} has no tones")
            
    print(f"tones_dict: {len(tones_dict)}")
    # print(tones_dict)

    for entry in tqdm.tqdm(data["words"][:LIMIT]):
        word_foreign = entry["word_foreign"]
        word_number = entry["word_number"]

        # print('-'*100)
        # print(f"[{word_number}] {word_foreign}")

        word_transcription_formatted = []
        all_tones_word_formatted = []

        for char in word_foreign:
            char_transcriptions = lazy_pinyin(char, style=Style.TONE)
            if len(char_transcriptions) > 1:
                word_transcription_formatted.append(f"({','.join(char_transcriptions)})")
            else:
                word_transcription_formatted.append(char_transcriptions[0])

            # print(char_transcriptions)

            for char_transcription in char_transcriptions:
                all_tones_char = generate_all_tones(char_transcription)
                # print(all_tones)

                all_tones_char_formatted = []
                for tone_index in sorted(all_tones_char.keys()):
                    tone = all_tones_char[tone_index]
                    # if tone == char_transcription:
                    #     all_tones_char_formatted.append(f"{tone_index}. <b>{tone}</b>: ***")
                    # el
                    if tone in tones_dict:
                        if len(tones_dict[tone]) > 1:
                            len_tones_str = "\n" + '<i>counts: ' + str(len(tones_dict[tone])) + '</i>'
                            all_words_str = []
                            word_foreign_star_all = set()
                            for t in tones_dict[tone]:
                                if HIDE_TONES and (t['word_number'] == word_number):
                                    all_words_str.append(f" - ***")
                                else:
                                    translation = ", ".join(t['translation'].split(',')[:3])
                                    if (not HIDE_TONES) or (len(t['word_foreign']) == 1):
                                        all_words_str.append(f" - [<i>{t['word_number']}</i>] <b>{t['word_foreign']}</b> [{t['transcription']}]: {translation}")
                                        word_foreign_star_all.add(t['word_foreign'])
                                    else:
                                        word_foreign_star_list = [t['word_foreign'][i] if (p == tone) else '*' for (i,p) in enumerate(t['transcription'].split(' ')) ]
                                        word_foreign_star_str = ''.join(word_foreign_star_list)
                                        word_foreign_not_star_str = ''.join([c for c in word_foreign_star_list if c != '*'])
                                        if word_foreign_not_star_str not in word_foreign_star_all:
                                            all_words_str.append(f" - [<i>{t['word_number']}</i>] <b>{word_foreign_star_str}</b>: ***")
                                            word_foreign_star_all.add(word_foreign_not_star_str)

                            all_words_str = "\n" + "\n".join(all_words_str)
                            all_tones_char_formatted.append(f"\n{tone_index}. <b>{tone}</b>{len_tones_str}: {all_words_str}")
                        elif HIDE_TONES and (tone == char_transcription):
                            all_tones_char_formatted.append(f"\n{tone_index}. <b>{tone}</b>: ***")
                        else:
                            len_tones_str = ''
                            t = tones_dict[tone][0]
                            translation = ", ".join(t['translation'].split(',')[:3])
                            all_words_str = f"[<i>{t['word_number']}</i>] <b>{t['word_foreign']}</b>: {translation}"
                            all_tones_char_formatted.append(f"\n{tone_index}. <b>{tone}</b>: {all_words_str}")
                    else:
                        all_tones_char_formatted.append(f"\n{tone_index}. <b>{tone}</b>: ---")

            all_tones_word_formatted.append("\n".join(all_tones_char_formatted))

        entry["tones"] = "\n ".join(all_tones_word_formatted)
        entry["transcription"] = " ".join(word_transcription_formatted)
        # print(entry["transcription"])
        # print(entry["tones"])

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

    print(f"Exported {len(data['words'])} words to {OUTPUT_FILE}")

