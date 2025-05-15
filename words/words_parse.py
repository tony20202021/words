import pandas as pd
import requests
from bs4 import BeautifulSoup
import json
import urllib.parse
import time
import re
import os

def parse_chinese_character(start_index, end_index, excel_file="Frequencies of top 50000 Chinese words.xls", delay=1, max_descriptions=5):
    """
    Function parses information about Chinese characters from bkrs.info website
    
    Args:
        start_index (int): Starting index (from 0)
        end_index (int): Ending index
        excel_file (str): Path to Excel file with characters
        delay (int): Pause between requests in seconds
        max_descriptions (int): Maximum number of description lines to collect
        
    Returns:
        dict: Dictionary with information about characters
    """
    # Check index validity
    if start_index < 0 or end_index < start_index:
        raise ValueError("Invalid indices")
    
    # Check if file exists
    if not os.path.exists(excel_file):
        raise FileNotFoundError(f"File {excel_file} not found")
    
    print(f"Reading file: {excel_file}")
    
    # Reading data from Excel file
    try:
        # For .xls files use engine='xlrd'
        if excel_file.endswith('.xls'):
            df = pd.read_excel(excel_file, sheet_name=0, engine='xlrd')
        # For .xlsx files use engine='openpyxl'
        elif excel_file.endswith('.xlsx'):
            df = pd.read_excel(excel_file, sheet_name=0, engine='openpyxl')
        else:
            raise ValueError(f"Unsupported file format: {excel_file}")
        
        # Print first 5 rows of DataFrame for debugging
        print("First 5 rows of DataFrame:")
        print(df.head())
        
        # Print column data types
        print("Column data types:")
        print(df.dtypes)
        
        # Take characters from 'word' column (index 1)
        characters = df.iloc[start_index:end_index+1, 1].tolist()
        # Take numbers from 'No' column (index 0)
        numbers = df.iloc[start_index:end_index+1, 0].tolist()
        
        # Print list of characters and their types
        print("Retrieved characters:")
        for i, (num, char) in enumerate(zip(numbers, characters)):
            print(f"{i}: №{num} - {char} (type: {type(char)})")
    except Exception as e:
        raise Exception(f"Error reading Excel file: {str(e)}")
    
    # Dictionary to store results
    results = {}
    
    # Process each character
    for i, (num, char) in enumerate(zip(numbers, characters)):
        try:
            # Check type and convert if necessary
            if not isinstance(char, str):
                print(f"Character {i} is not a string. Converting.")
                char = str(char)
            
            # Encode character for URL
            encoded_char = urllib.parse.quote(char)
            url = f"https://bkrs.info/slovo.php?ch={encoded_char}"
            
            print(f"Request for character {i}: {char} -> URL: {url}")
            
            # Send request
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.get(url, headers=headers)
            
            # Check if request was successful
            if response.status_code != 200:
                print(f"Error requesting {url}: status {response.status_code}")
                continue
            
            print(f"Successful response for character {i}: {char}")
            
            # Parse HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract data
            character_data = {
                "character": char,
                "transcription": "",
                "description": [],
                "frequency": ""
            }
            
            # Search for transcription (class 'py')
            transcription_section = soup.find('div', {'class': 'py'})
            if transcription_section:
                # Clean text from extra spaces and line breaks
                # Use .text instead of .get_text() for simpler text retrieval
                transcription = transcription_section.text.strip()
                # Remove everything after img tag if it exists
                if 'audioplay' in str(transcription_section):
                    transcription = transcription.split('\n')[0].strip()
                character_data["transcription"] = transcription
                print(f"Found transcription: {transcription}")
                
                # Split transcription by commas for subsequent verification
                transcription_variants = re.split('[,;. ]+', transcription)
                transcription_variants = [t.strip() for t in transcription_variants if t.strip()]
                print(f"Transcription variants: {transcription_variants}")
            else:
                print("Transcription not found")
                transcription_variants = []
            
            # FIX 1: Search for description (class 'ru') - improved algorithm
            description_section = soup.find('div', {'class': 'ru'})
            if description_section:
                # First method: find all divs inside ru
                all_divs = description_section.find_all('div')
                description_texts = []
                visited_texts = set()  # To track already added texts
                
                # Variables to track numbering hierarchy
                current_roman = ""
                current_number = ""
                current_letter = ""
                
                for div in all_divs:
                    text = div.text.strip()
                    
                    # Skip empty strings
                    if not text.strip():
                        continue
                    
                    # Remove from description all words matching any transcription variant
                    for variant in transcription_variants:
                        text = text.replace(variant, '')

                    # Prevent adding duplicates
                    if text in visited_texts:
                        continue
                    visited_texts.add(text)
                    
                    # Process Roman numerals
                    # Update current Roman numeral
                    # Do not save the line starting with a Roman numeral
                    roman_match = re.match(r'^([IVX]+)(\s*)(.*?)$', text)
                    if roman_match:
                        current_roman = roman_match.group(1)
                        
                        # Reset lower level numbering
                        current_number = ""
                        current_letter = ""
                        
                        continue
                    
                    # Process numerical numbering (1), 2), etc.)
                    number_match = re.match(r'^(\d+\))(.*?)$', text)
                    if number_match:
                        current_number = number_match.group(1)
                        remaining_text = number_match.group(2).strip()
                        
                        if not remaining_text.strip():
                            continue

                        # Replace parenthesis with dot in hierarchical numbering
                        current_number_formatted = current_number.replace(')', '.')
                        
                        # If there is a current Roman numeral, add it to the number
                        prefix = f"{current_roman}." if current_roman else ""
                        
                        # Add space after numbering
                        text = f"{prefix}{current_number_formatted} {remaining_text}"
                        
                        # Reset letter numbering
                        current_letter = ""
                        
                    # Process letter numbering (а), б), etc.)
                    letter_match = re.match(r'^([а-я]\))(.*?)$', text)
                    if letter_match:
                        current_letter = letter_match.group(1)
                        remaining_text = letter_match.group(2).strip()
                        
                        if not remaining_text.strip():
                            continue

                        # Replace parenthesis with dot in hierarchical numbering
                        current_letter_formatted = current_letter.replace(')', '.')
                        
                        # Build full hierarchical numbering
                        prefix = ""
                        if current_roman:
                            prefix += f"{current_roman}."
                        if current_number:
                            # Use formatted number (with dot instead of parenthesis)
                            number_formatted = current_number.replace(')', '.')
                            prefix += f"{number_formatted}"
                        
                        # Add space after numbering
                        text = f"{prefix}{current_letter_formatted} {remaining_text}"
                                            
                    # Skip lines containing Chinese examples
                    if re.search(r'[\u4e00-\u9fff]', text):
                        # Check if div has class "ex" (example)
                        if 'ex' in div.get('class', []) or div.find(class_='ex'):
                            continue
                    
                    text = text.replace(character_data["character"], '*')
                                    
                    # Skip empty lines and lines with only spaces
                    if not text:
                        continue
                    
                    # If description starts with "гл. A" - skip the line
                    if text.startswith("гл."):
                        continue
                    
                    # Add the valid description line (after all filters)
                    description_texts.append(text)
                    
                    # Take only first max_descriptions valid lines
                    if len(description_texts) >= max_descriptions:
                        break
                
                # FIX 1: If description is empty, try to find it another way
                if not description_texts:
                    print("First method didn't find descriptions. Trying alternative method...")
                    
                    # Take description directly from div.ru
                    ru_text = description_section.get_text(strip=True, separator=' ')
                    
                    # If there is text, but no description in standard format
                    if ru_text:
                        # Try to find Russian text after transcription (if known)
                        if character_data["transcription"]:
                            # Search in full HTML after div.py closing
                            full_html = str(soup)
                            
                            # Find text after div.py
                            py_pos = full_html.find('</div>', full_html.find('class="py"'))
                            if py_pos > 0:
                                # Find div.ru after div.py closing
                                ru_pos = full_html.find('<div class="ru">', py_pos)
                                if ru_pos > 0:
                                    # Find text between div.ru opening and closing
                                    ru_close_pos = full_html.find('</div>', ru_pos)
                                    if ru_close_pos > 0:
                                        ru_content = full_html[ru_pos:ru_close_pos]
                                        
                                        # Create new BeautifulSoup object for this fragment
                                        ru_soup = BeautifulSoup(ru_content, 'html.parser')
                                        pure_text = ru_soup.get_text(strip=True)
                                        
                                        # Remove transcription from text and add it to description
                                        for variant in transcription_variants:
                                            pure_text = pure_text.replace(variant, '').strip()
                                        
                                        if pure_text:
                                            description_texts.append(pure_text)
                                            print(f"Found description with alternative method: {pure_text}")
                
                character_data["description"] = description_texts
                print(f"Found description: {character_data['description']}")
            else:
                print("Description not found")
            
            # Search for frequency
            # Find element with id="frequency"
            frequency_section = soup.find('span', {'id': 'frequency'})
            if frequency_section:
                # Get text from element and next sibling
                frequency_text = frequency_section.text.strip()
                next_text = frequency_section.next_sibling
                if next_text:
                    next_text_str = str(next_text).strip()
                    # Extract number from text, removing # symbol
                    match = re.search(r'#(\d+)', next_text_str)
                    if match:
                        # Convert to number (int)
                        frequency_value = int(match.group(1))
                        character_data["frequency"] = frequency_value
                        print(f"Found frequency: {frequency_value}")
                
                # If frequency not found via next_sibling, try other methods
                if not character_data["frequency"]:
                    full_text = str(frequency_section) + (str(next_text) if next_text else "")
                    match = re.search(r'частотность:\s*#?(\d+)', full_text)
                    if match:
                        frequency_value = int(match.group(1))
                        character_data["frequency"] = frequency_value
                        print(f"Found frequency through regex: {frequency_value}")
            else:
                print("Frequency not found")
            
            # Add data to results dictionary
            # Use character number as key
            results[str(num)] = character_data
            print(f"Data for character {i} (№{num}) successfully added")
            
            # Save current results to JSON file after each character
            output_file = f"chinese_characters_{start_index}_{end_index}.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=4)
            print(f"Progressive saving: data added to file {output_file}")
            
            # Pause between requests to avoid overloading the server
            time.sleep(delay)
            
        except Exception as e:
            print(f"Error processing character {i}: {str(e)}")
            import traceback
            print(traceback.format_exc())
    
    # Final statistics output (file is already saved after each character)
    output_file = f"chinese_characters_{start_index}_{end_index}.json"
    print(f"Final data saving completed to file {output_file}")
    print(f"Number of processed characters: {len(results)}")
    
    return results

def reprocess_errors_file(error_file, delay=3):
    """
    Function for reprocessing characters from error file
    
    Args:
        error_file (str): Path to JSON file with error records
        delay (int): Pause between requests in seconds
        
    Returns:
        dict: Dictionary with corrected character information
    """
    print(f"Reprocessing errors from file: {error_file}")
    
    # Check if file exists
    if not os.path.exists(error_file):
        print(f"Error: File {error_file} not found")
        return {}
    
    try:
        # Read data from JSON error file
        with open(error_file, 'r', encoding='utf-8') as f:
            error_data = json.load(f)
        
        print(f"Read {len(error_data)} error records")
        
        # Dictionary to store reprocessing results
        results = {}
        
        # Process each character from error file
        for key, entry in error_data.items():
            try:
                char = entry["character"]
                print(f"Reprocessing character №{key}: {char}")
                
                # Encode character for URL
                encoded_char = urllib.parse.quote(char)
                url = f"https://bkrs.info/slovo.php?ch={encoded_char}"
                
                print(f"Request for character №{key}: {char} -> URL: {url}")
                
                # Send request
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                }
                response = requests.get(url, headers=headers)
                
                # Check if request was successful
                if response.status_code != 200:
                    print(f"Error requesting {url}: status {response.status_code}")
                    continue
                
                print(f"Successful response for character №{key}: {char}")
                
                # Parse HTML
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Extract data
                character_data = {
                    "character": char,
                    "transcription": entry.get("transcription", ""),
                    "description": [],
                    "frequency": entry.get("frequency", "")
                }
                
                # Search for transcription (class 'py'), if missing
                if not character_data["transcription"]:
                    transcription_section = soup.find('div', {'class': 'py'})
                    if transcription_section:
                        transcription = transcription_section.text.strip()
                        if 'audioplay' in str(transcription_section):
                            transcription = transcription.split('\n')[0].strip()
                        character_data["transcription"] = transcription
                        print(f"Found transcription: {transcription}")
                
                # Split transcription by commas for subsequent verification
                transcription_variants = [t.strip() for t in character_data["transcription"].split(',')]
                
                # Search for description (class 'ru'), if empty
                if not entry.get("description"):
                    # First try standard method of finding div.ru
                    description_section = soup.find('div', {'class': 'ru'})
                    if description_section:
                        # First try to get text directly, without parsing numbering
                        direct_text = description_section.get_text(strip=True)
                        
                        # Remove transcription from text
                        for variant in transcription_variants:
                            direct_text = direct_text.replace(variant, '').strip()
                        
                        if direct_text:
                            character_data["description"] = [direct_text]
                            print(f"Found direct description: {direct_text}")
                        else:
                            # If direct method failed, search for all text information
                            # From all HTML after div with class py (transcription)
                            full_html = str(soup)
                            py_section = soup.find('div', {'class': 'py'})
                            
                            if py_section:
                                # Find position after div.py closing
                                start_pos = full_html.find('</div>', full_html.find(str(py_section)))
                                
                                if start_pos > 0:
                                    # Find text until next significant div
                                    next_div_pos = full_html.find('<div', start_pos + 6)
                                    
                                    if next_div_pos > 0:
                                        text_between = full_html[start_pos:next_div_pos]
                                        
                                        # Create new BeautifulSoup object for this fragment
                                        text_soup = BeautifulSoup(text_between, 'html.parser')
                                        extracted_text = text_soup.get_text(strip=True)
                                        
                                        if extracted_text:
                                            character_data["description"] = [extracted_text]
                                            print(f"Found indirect description: {extracted_text}")
                
                # Search for frequency, if missing
                if not character_data["frequency"]:
                    # Try to find frequency if it's directly in the number
                    try:
                        frequency_value = int(key)
                        character_data["frequency"] = frequency_value
                        print(f"Frequency set from record number: {frequency_value}")
                    except ValueError:
                        # If number is not an integer, search for frequency on page
                        frequency_section = soup.find('span', {'id': 'frequency'})
                        if frequency_section:
                            next_text = frequency_section.next_sibling
                            if next_text:
                                next_text_str = str(next_text).strip()
                                match = re.search(r'#(\d+)', next_text_str)
                                if match:
                                    frequency_value = int(match.group(1))
                                    character_data["frequency"] = frequency_value
                                    print(f"Found frequency: {frequency_value}")
                
                # Add data to results dictionary
                results[key] = character_data
                print(f"Data for character №{key} successfully updated")
                
                # Save current results to JSON file after each character
                output_file = f"{os.path.splitext(error_file)[0]}.new.json"
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(results, f, ensure_ascii=False, indent=4)
                print(f"Progressive saving: data added to file {output_file}")
                
                # Pause between requests
                time.sleep(delay)
                
            except Exception as e:
                print(f"Error reprocessing character №{key}: {str(e)}")
                import traceback
                print(traceback.format_exc())
        
        # Final statistics output
        output_file = f"{os.path.splitext(error_file)[0]}.new.json"
        print(f"Final data saving completed to file {output_file}")
        print(f"Number of processed characters: {len(results)}")
        
        return results
        
    except Exception as e:
        print(f"Error processing error file: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return {}

# Usage example
if __name__ == "__main__":
    # Parse first 10 characters (indexes 0 to 9)
    # parse_chinese_character(0, 30, delay=1)
    
    # To run with other parameters:
    parse_chinese_character(start_index=0, end_index=1_000, delay=1)
    
    # Reprocess errors from file
    # error_file = "chinese_characters_0_1000.errors.json"
    # reprocess_errors_file(error_file, delay=3)