import json
    
if __name__ == "__main__":
    INPUT_FILE = "/home/tony/repos/words/words/chat_gpt/words_Китайский_20250805_194526.json"
    LIMIT = 10_000

    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)

    for index in range(0, len(data["words"]), LIMIT):
        index_begin = index
        index_end = index + LIMIT
        OUTPUT_FILE = INPUT_FILE + f".{index_begin+1:04d}_{index_end:04d}.txt"
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            for entry in data["words"][index_begin:index_end]:
                word_lower = entry["word_foreign"].strip().lower()
                word_number = entry["word_number"]
                f.write(f"{word_number}. {word_lower}\n")

    print(f"Exported {len(data['words'])} words to {OUTPUT_FILE}")

