# python ./words_parse.py
# python merge_json_descriptions.py ../data/results_qwen2.5-32b.json ../data/results_qwen2.5-32b_no_desc.json -o ./chinese_characters_0_10000_description.json
# python ./words_filter_errors.py
# python ./clean_json_file.py
# python ./words_generate_doc.py

# python ./radicals_parse.py
# python ./chat_gpt/export_txt.py
# python ./chat_gpt/import_txt.py
# python ./chat_gpt/cross_references.py
# python ./chat_gpt/merge_all.py

# python ./sounds/sounds_parse.py
# python ./radicals_names/radicals_names.py
python ./tones/tones_all.py
