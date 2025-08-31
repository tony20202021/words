import json
    
if __name__ == "__main__":
    INPUT_FILE_MONGO = "/home/tony/repos/words/words/chat_gpt_2/data/words_Китайский_20250826_160132.json.tones.json"
    INPUT_FILE_NEW_TRANSLATION = "/home/tony/repos/words/words/chat_gpt_2/data/result.txt"
    
    OUTPUT_FILE_JSON = INPUT_FILE_MONGO + ".merged.json"

    LIMIT_STR = 200

    with open(INPUT_FILE_MONGO, 'r', encoding='utf-8') as f:
        data_mongo = json.load(f)

    data_new_translation = {}
    with open(INPUT_FILE_NEW_TRANSLATION, 'r', encoding='utf-8') as f:
        words_new_translation = f.read().splitlines()
        for entry in words_new_translation:
            if entry == "":
                continue

            if ". " in entry:
                number, rest = entry.split(". ", 1) 
                number = int(number)
            else:
                print(f"Word [{entry}]: wrong format in {INPUT_FILE_NEW_TRANSLATION}")
                continue

            if ": " in rest:
                word_foreign, new_translation = rest.split(": ", 1)
            elif ":" in rest:
                word_foreign, new_translation = rest.split(":", 1)
            else:
                print(f"Word [{number}] {rest}: wrong format in {INPUT_FILE_NEW_TRANSLATION}")
                continue

            if " [" in word_foreign:
                word_foreign, _ = word_foreign.split(" [", 1)

            data_new_translation[number] = {
                "word_foreign": word_foreign,
                "new_translation": new_translation.strip(" ")[:LIMIT_STR],
            }

    print(f"Loaded {len(data_mongo['words'])} words from {INPUT_FILE_MONGO}")
    print(f"Loaded {len(data_new_translation)} words from {INPUT_FILE_NEW_TRANSLATION}")

    for index, entry_mongo in enumerate(data_mongo["words"]):
        word_number = entry_mongo["word_number"]
        word_foreign = entry_mongo["word_foreign"]
        
        if word_number in data_new_translation:
            if word_foreign != data_new_translation[word_number]["word_foreign"]:
                print(f"Word [{word_number}] {word_foreign} != {data_new_translation[word_number]['word_foreign']} in {INPUT_FILE_NEW_TRANSLATION}")
            new_translation = data_new_translation[word_number]["new_translation"]
            entry_mongo["translation"] = new_translation
        else:
            if word_number < len(data_new_translation):
                print(f"Word [{word_number}] {word_foreign} not found in {INPUT_FILE_NEW_TRANSLATION}")


    with open(OUTPUT_FILE_JSON, 'w', encoding='utf-8') as f:
        json.dump(data_mongo, f, ensure_ascii=False, indent=4)

    print(f"Merged {len(data_new_translation)} new translations and {len(data_mongo['words'])} words to {OUTPUT_FILE_JSON}")

