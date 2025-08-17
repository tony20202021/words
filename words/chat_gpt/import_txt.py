import json
    
if __name__ == "__main__":
    INPUT_FILE_JSON = "/home/tony/repos/words/words/chat_gpt/words_Китайский_20250805_194526.json"
    
    INPUT_FILE_TXT_2 = "/home/tony/repos/words/words/chat_gpt/words_Китайский_20250805_194526.json.txt.answer_3.txt"
    INPUT_FILE_TXT_3 = "/home/tony/repos/words/words/chat_gpt/answer.deepseek-r1.txt"
    INPUT_FILE_TXT_4 = "/home/tony/repos/words/words/chat_gpt/answer.qwen3-235b.txt"
    INPUT_FILE_TXT_5 = "/home/tony/repos/words/words/chat_gpt/answer.qwen3-coder-480b.txt"

    OUTPUT_FILE_JSON = INPUT_FILE_JSON + ".txt_imported.json"

    LIMIT_STR = 200

    with open(INPUT_FILE_JSON, 'r', encoding='utf-8') as f:
        data = json.load(f)

    data_2 = {}
    with open(INPUT_FILE_TXT_2, 'r', encoding='utf-8') as f:
        words_2 = f.read().splitlines()
        for entry in words_2:
            number, rest = entry.split(". ", 1) 
            number = int(number)

            if ": " in rest:
                word_foreign, translation_2 = rest.split(": ", 1)
            elif ":" in rest:
                word_foreign, translation_2 = rest.split(":", 1)
            else:
                print(f"Word [{number}] {rest}: wrong format in {INPUT_FILE_TXT_2}")
                continue

            data_2[number] = {
                "word_foreign": word_foreign,
                "translation_2": translation_2[:LIMIT_STR],
            }

    data_3 = {}
    with open(INPUT_FILE_TXT_3, 'r', encoding='utf-8') as f:
        words_3 = f.read().splitlines()
        for entry in words_3:
            number, translation_3 = entry.split(". ", 1)
            number = int(number)
            data_3[number] = {
                "translation_3": translation_3[:LIMIT_STR],
            }

    data_4 = {}
    with open(INPUT_FILE_TXT_4, 'r', encoding='utf-8') as f:
        words_4 = f.read().splitlines()
        for entry in words_4:
            number, translation_4 = entry.split(". ", 1)
            number = int(number)
            data_4[number] = {
                "translation_4": translation_4[:LIMIT_STR],
            }

    data_5 = {} 
    with open(INPUT_FILE_TXT_5, 'r', encoding='utf-8') as f:
        words_5 = f.read().splitlines()
        for entry in words_5:
            number, translation_5 = entry.split(". ", 1)
            number = int(number)
            data_5[number] = {
                "translation_5": translation_5[:LIMIT_STR],
            }

    print(f"Loaded {len(data)} words from {INPUT_FILE_JSON}")
    print(f"Loaded {len(data_2)} words from {INPUT_FILE_TXT_2}")
    print(f"Loaded {len(data_3)} words from {INPUT_FILE_TXT_3}")
    print(f"Loaded {len(data_4)} words from {INPUT_FILE_TXT_4}")
    print(f"Loaded {len(data_5)} words from {INPUT_FILE_TXT_5}")

    for index, entry in enumerate(data["words"]):
        word_number = entry["word_number"]
        word_foreign = entry["word_foreign"]
        transcription = entry["transcription"]
        
        entry["translation_1"] = entry["translation"]
        del entry["translation"]

        if word_number in data_2:
            entry["translation_2"] = data_2[word_number]["translation_2"]
        else:
            if word_number < len(data_2):
                print(f"Word [{word_number}] {word_foreign} not found in {INPUT_FILE_TXT_2}")
        
        if word_number in data_3:
            entry["translation_3"] = data_3[word_number]["translation_3"]
        else:
            if word_number < len(data_3):
                print(f"Word [{word_number}] {word_foreign} not found in {INPUT_FILE_TXT_3}")
        
        if word_number in data_4:
            entry["translation_4"] = data_4[word_number]["translation_4"]
        else:
            if word_number < len(data_4):
                print(f"Word [{word_number}] {word_foreign} not found in {INPUT_FILE_TXT_4}")
        
        if word_number in data_5:
            entry["translation_5"] = data_5[word_number]["translation_5"]
        else:
            if word_number < len(data_5):
                print(f"Word [{word_number}] {word_foreign} not found in {INPUT_FILE_TXT_5}")

    with open(OUTPUT_FILE_JSON, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

    print(f"Imported {len(data['words'])} words to {OUTPUT_FILE_JSON}")

