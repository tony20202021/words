import json
    
if __name__ == "__main__":
    INPUT_FILE_JSON = "/home/tony/repos/words/words/chat_gpt_2/data/words_Китайский_20250826_160132.json.tones.json.merged.json"
    
    OUTPUT_FILE_JSON = INPUT_FILE_JSON + ".cross_references.json"

    with open(INPUT_FILE_JSON, 'r', encoding='utf-8') as f:
        data = json.load(f)

    print(f"Loaded {len(data)} words from {INPUT_FILE_JSON}")

    chars_ref = {}
    chars_counts = {}
    for entry in data["words"]:
        word_foreign = entry["word_foreign"]
        if len(word_foreign) == 1:
            if word_foreign not in chars_ref:
                chars_ref[word_foreign] = []
            chars_ref[word_foreign].append(entry)

        for char in word_foreign:
            if char not in chars_counts:
                chars_counts[char] = 0
            chars_counts[char] += 1

    print(f"created {len(chars_ref)} chars_ref and {len(chars_counts)} chars_counts")
    # print(chars_counts)

    for index, entry in enumerate(data["words"]):
        word_foreign = entry["word_foreign"]

        references_formatted = []
        for char in word_foreign:
            reference_text = f"<b>{char}</b>: "
            if char in chars_counts:
                reference_text += f"<i>counts: {chars_counts[char]}</i>"

            words_formatted = []
            if char in chars_ref:
                for ref in chars_ref[char]:
                    if ref["word_number"] != entry["word_number"]:
                        words_formatted.append(f"<i>[#{ref['word_number']}] </i>{ref['translation']}")

            if len(words_formatted) > 0:
                references_formatted.append(f"{reference_text} {', '.join(words_formatted)}")
            else:
                references_formatted.append(reference_text)
        
        if len(references_formatted) > 0:
            entry["references"] = "\n".join(references_formatted)

        # print(index)
        # print(entry["word_foreign"])
        # print(entry["references"])

    with open(OUTPUT_FILE_JSON, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

    print(f"Processed {len(data['words'])} words in {INPUT_FILE_JSON} and saved to {OUTPUT_FILE_JSON}")

