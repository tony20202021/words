import json
    
if __name__ == "__main__":
    INPUT_FILE = "/home/tony/repos/words/words/chat_gpt_2/data/words_Китайский_20250826_160132.json.tones.json"
    LIMIT = 100

    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)

    for index in range(0, len(data["words"]), LIMIT):
        index_begin = index
        index_end = index + LIMIT
        OUTPUT_FILE = INPUT_FILE + f".{index_begin+1:04d}_{index_end:04d}.txt"
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            for entry in data["words"][index_begin:index_end]:
                word_number = entry["word_number"]
                word_foreign = entry["word_foreign"]
                transcription = entry["transcription"]
                translation = entry["translation"]

                f.write(f"{word_number}. {word_foreign} [{transcription}]: {translation}\n")

    print(f"Exported {len(data['words'])} words to {OUTPUT_FILE}")

