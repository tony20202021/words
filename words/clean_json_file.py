import json

def normalize_field(value):
    """Преобразует значение в множество строк, убирает дубликаты и лишние пробелы"""
    if isinstance(value, list):
        return set(map(str.strip, value))
    elif isinstance(value, str):
        return set(map(str.strip, value.split(',')))
    return set()

def merge_values(original, new):
    """Объединяет значения transcription и description"""
    orig_set = normalize_field(original)
    new_set = normalize_field(new)
    merged = orig_set.union(new_set)
    return "\n".join(sorted(merged)) if isinstance(original, str) else sorted(merged)

def clean_duplicates(input_path, output_path):
    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    result = {}
    seen_words = {}

    for key, entry in data.items():
        word_lower = entry['word'].lower()

        if word_lower in seen_words:
            existing_key = seen_words[word_lower]
            existing_entry = result[existing_key]

            same_transcription = normalize_field(entry['transcription']) == normalize_field(existing_entry['transcription'])
            same_description = normalize_field(entry['description']) == normalize_field(existing_entry['description'])

            if same_transcription and same_description:
                continue  # дубликат, ничего делать не нужно
            else:
                # объединяем поля
                existing_entry['transcription'] = merge_values(existing_entry['transcription'], entry['transcription'])
                existing_entry['description'] = merge_values(existing_entry['description'], entry['description'])
        else:
            result[key] = entry
            seen_words[word_lower] = key

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=4)

    print(f"Готово! Очищенные данные сохранены в {output_path}")

if __name__ == "__main__":
    # INPUT_FILE = "chinese_characters_0_10000.json"
    # OUTPUT_FILE_JSON = INPUT_FILE + ".cleaned.json"

    INPUT_FILE = "../data/fr.json"
    OUTPUT_FILE_JSON = INPUT_FILE + ".cleaned.json"

    # INPUT_FILE = "../word_tranription/data/eng.json"
    # OUTPUT_FILE_JSON = INPUT_FILE + ".cleaned.json"

    # INPUT_FILE = "../data/deutch.json"
    # OUTPUT_FILE_JSON = INPUT_FILE + ".cleaned.json"

    # INPUT_FILE = "../data/spain.json"
    # OUTPUT_FILE_JSON = INPUT_FILE + ".cleaned.json"

    clean_duplicates(INPUT_FILE, OUTPUT_FILE_JSON)
