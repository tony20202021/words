import pandas as pd
import requests
from bs4 import BeautifulSoup
import json
import urllib.parse
import time
import re
import os
import tqdm

def parse_chinese_radicals(start_index, end_index, input_file="chinese_characters_0_10000.json", url_template="https://hanzicraft.com/character/{word}", delay=1):
    """
    Function parses information about Chinese radicals from bkrs.info website
    
    Args:
        start_index (int): Starting index (from 0)
        end_index (int): Ending index
        json_file (str): Path to JSON file with characters
        delay (int): Pause between requests in seconds
        max_descriptions (int): Maximum number of description lines to collect
        
    Returns:
        dict: Dictionary with information about characters
    """
    # Check index validity
    if start_index < 0 or end_index < start_index:
        raise ValueError("Invalid indices")
    
    # Check if file exists
    if not os.path.exists(input_file):
        raise FileNotFoundError(f"File {input_file} not found")
    
    print(f"Reading file: {input_file}")
    
    # Reading data from file
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    print(f"words: {len(data['words'])}")

    output_file = f"{input_file}.radicals.{start_index}_{end_index}.json"

    # Process each character
    for i, entry in tqdm.tqdm(enumerate(data["words"])):
        try:
            word_foreign = entry["word_foreign"]
            # print(f"Processing character {i+1}: {char}")

            # Check type and convert if necessary
            if not isinstance(word_foreign, str):
                print(f"Character {i} is not a string. Converting.")
                word_foreign = str(word_foreign)
            
            radicals_all = []
            for char in word_foreign:
                # Encode character for URL
                encoded_char = urllib.parse.quote(char)
                url = url_template.format(word=encoded_char)
                
                # print(f"Request for character {i}: {char} -> URL: {url}")
                
                # Send request
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                }
                response = requests.get(url, headers=headers)
                
                # Check if request was successful
                if response.status_code != 200:
                    print(f"Error requesting {url}: status {response.status_code}")
                    continue
                
                # print(f"Successful response for character {i}: {char}")
                
                # Parse HTML
                soup = BeautifulSoup(response.text, 'html.parser')
                # print(soup)

                # Находим все блоки с заголовками декомпозиции
                decomp_titles = soup.find_all('div', class_='decomptitle')
                
                radicals = None
                for title in decomp_titles:
                    if title.get_text(strip=True) == 'Radical :':
                        # Находим следующий блок с содержимым
                        decomp_box = title.find_next_sibling('div', class_='decompbox')
                        if decomp_box:
                            # return format_radical_block(char, decomp_box)
                            # print(decomp_box)
                            text = decomp_box.get_text()
                            _, radicals = text.split('=>')
                            radicals = radicals.strip()
                            # print(radicals)
                            break
                if not radicals:
                    print(f"Radicals not found for {char}")
                    continue

                radicals_all.append(radicals)
                # print(f"Found radicals: [{i+1}/{len(data['words'])}] {char} -> {radicals}")

            entry["radicals"] = ";".join(radicals_all)
            
            # Save current results to JSON file after each character
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            
            
            print(i, word_foreign, entry["radicals"])
            
            # Pause between requests to avoid overloading the server
            time.sleep(delay)
            
        except Exception as e:
            print(f"Error processing character {i}: {str(e)}")
            import traceback
            print(traceback.format_exc())
    
    # Final statistics output (file is already saved after each character)
    print(f"Final data saving completed to file {output_file}")

if __name__ == "__main__":
    file_name = "./chat_gpt/words_Китайский_20250805_194526.json"
    url_template = "https://hanzicraft.com/character/{word}"
    
    parse_chinese_radicals(start_index=0, end_index=10_000, input_file=file_name, url_template=url_template, delay=0.1)
   
