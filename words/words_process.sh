# python ./words_parse.py
# python merge_json_descriptions.py ../data/results_qwen2.5-32b.json ../data/results_qwen2.5-32b_no_desc.json -o ./chinese_characters_0_10000_description.json
# python ./words_filter_errors.py
# python ./clean_json_file.py
python ./words_generate_doc.py
