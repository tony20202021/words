import json
    
if __name__ == "__main__":
    INPUT_FILE_MONGO = "/home/tony/repos/words/words/chat_gpt/words_Китайский_20250805_194526.json"
    INPUT_FILE_REFERENCES = "/home/tony/repos/words/words/chat_gpt/words_Китайский_20250805_194526.json.cross_references.json"
    INPUT_FILE_RADICALS = "/home/tony/repos/words/words/chat_gpt/words_Китайский_20250805_194526.json.radicals.0_10000.json"
    INPUT_FILE_NEW_TRANSLATION = "/home/tony/repos/words/words/chat_gpt/all.qwen3-235b.txt"
    
    OUTPUT_FILE_JSON = INPUT_FILE_MONGO + ".merged.json"

    LIMIT_STR = 200

    with open(INPUT_FILE_MONGO, 'r', encoding='utf-8') as f:
        data_mongo = json.load(f)

    with open(INPUT_FILE_REFERENCES, 'r', encoding='utf-8') as f:
        data_references = json.load(f)

    with open(INPUT_FILE_RADICALS, 'r', encoding='utf-8') as f:
        data_radicals = json.load(f)

    data_new_translation = {}
    with open(INPUT_FILE_NEW_TRANSLATION, 'r', encoding='utf-8') as f:
        words_new_translation = f.read().splitlines()
        for entry in words_new_translation:
            number, rest = entry.split(". ", 1) 
            number = int(number)

            if ": " in rest:
                word_foreign, new_translation = rest.split(": ", 1)
            elif ":" in rest:
                word_foreign, new_translation = rest.split(":", 1)
            else:
                print(f"Word [{number}] {rest}: wrong format in {INPUT_FILE_NEW_TRANSLATION}")
                continue

            data_new_translation[number] = {
                "word_foreign": word_foreign,
                "new_translation": new_translation[:LIMIT_STR],
            }

    print(f"Loaded {len(data_mongo['words'])} words from {INPUT_FILE_MONGO}")
    print(f"Loaded {len(data_references['words'])} words from {INPUT_FILE_REFERENCES}")
    print(f"Loaded {len(data_radicals['words'])} words from {INPUT_FILE_RADICALS}")
    print(f"Loaded {len(data_new_translation)} words from {INPUT_FILE_NEW_TRANSLATION}")

    for index, (entry_mongo, entry_references, entry_radicals) in enumerate(zip(data_mongo["words"], data_references["words"], data_radicals["words"])):
        if (entry_mongo["word_number"] != entry_references["word_number"] or entry_mongo["word_number"] != entry_radicals["word_number"]):
            print(f"Word [{entry_mongo['word_number']}] {entry_mongo['word_foreign']} not found in {INPUT_FILE_REFERENCES} or {INPUT_FILE_RADICALS}")
            break

        if (entry_mongo["word_foreign"] != entry_references["word_foreign"] or entry_mongo["word_foreign"] != entry_radicals["word_foreign"]):
            print(f"Word [{entry_mongo['word_foreign']}] {entry_mongo['word_foreign']} not found in {INPUT_FILE_REFERENCES} or {INPUT_FILE_RADICALS}")
            break

        word_number = entry_mongo["word_number"]
        word_foreign = entry_mongo["word_foreign"]
        transcription = entry_mongo["transcription"]
        references = entry_references["references"]
        radicals = entry_radicals["radicals"]
        
        entry_mongo["references"] = references
        entry_mongo["radicals"] = radicals

        if word_number in data_new_translation:
            new_translation = data_new_translation[word_number]["new_translation"]
            entry_mongo["translation"] = new_translation
        else:
            if word_number < len(data_new_translation):
                print(f"Word [{word_number}] {word_foreign} not found in {INPUT_FILE_NEW_TRANSLATION}")


    with open(OUTPUT_FILE_JSON, 'w', encoding='utf-8') as f:
        json.dump(data_mongo, f, ensure_ascii=False, indent=4)

    print(f"Merged {len(data_mongo['words'])} words to {OUTPUT_FILE_JSON}")

