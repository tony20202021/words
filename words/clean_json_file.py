import json

def normalize_transcription(transcription):
    # Убирает повторы с учётом приведения к строке
    seen = set()
    lines = []
    for part in transcription.split('\n'):
        for p in part.split(','):
            p_clean = p.strip()
            if p_clean and p_clean not in seen:
                seen.add(p_clean)
                lines.append(p_clean)
    return '\n'.join(lines)

def merge_transcriptions(t1, t2):
    merged = (t1 + "\n" + t2).strip()
    return normalize_transcription(merged)

def merge_descriptions(desc1, desc2):
    raw_merged = []
    seen_lower = set()

    for d in desc1 + desc2:
        key = d.strip().lower()
        if key not in seen_lower:
            seen_lower.add(key)
            raw_merged.append(d.strip())

    # Удалим подстроки
    final = []
    for d in raw_merged:
        if not any((d != other and d in other) for other in raw_merged):
            final.append(d)
    return final

def clean_description(description_list, word):
    word_lower = word.strip().lower()
    return [desc for desc in description_list if desc.strip().lower() != word_lower]

def clean_json(input_path, output_path):
    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    result = {}
    seen_words = {}

    for key, entry in data.items():
        word_lower = entry["word"].strip().lower()

        # Очистка description от повтора самого слова
        entry["description"] = clean_description(entry["description"], entry["word"])

        # Пропуск если description стал пустым
        if not entry["description"]:
            continue

        if word_lower in seen_words:
            existing_key = seen_words[word_lower]
            existing_entry = result[existing_key]

            # Объединяем transcription
            existing_entry["transcription"] = merge_transcriptions(
                existing_entry.get("transcription", ""),
                entry.get("transcription", "")
            )

            # Объединяем description
            existing_entry["description"] = merge_descriptions(
                existing_entry.get("description", []),
                entry.get("description", [])
            )

            # Объединение all_transcriptions (просто добавим, без удаления дубликатов по сервису)
            existing_entry["all_transcriptions"].extend(entry.get("all_transcriptions", []))

        else:
            # Сохраняем запись
            seen_words[word_lower] = key
            result[key] = entry

    # Сохраняем очищенный JSON
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=4)

    print(f"Готово! Сохранено в {output_path}")

    
if __name__ == "__main__":
    # INPUT_FILE = "chinese_characters_0_10000.json"
    # OUTPUT_FILE_JSON = INPUT_FILE + ".cleaned.json"

    # INPUT_FILE = "../data/fr.json"
    # OUTPUT_FILE_JSON = INPUT_FILE + ".cleaned.json"

    # INPUT_FILE = "../data/eng.json"
    # OUTPUT_FILE_JSON = INPUT_FILE + ".cleaned.json"

    # INPUT_FILE = "../data/deutch.json"
    # OUTPUT_FILE_JSON = INPUT_FILE + ".cleaned.json"

    INPUT_FILE = "../data/spain.json"
    OUTPUT_FILE_JSON = INPUT_FILE + ".cleaned.json"

    clean_json(INPUT_FILE, OUTPUT_FILE_JSON)
