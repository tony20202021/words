import pandas as pd
import requests
from bs4 import BeautifulSoup
import json
import urllib.parse
import time
import re
import os
import tqdm

def download_sounds(output_dir, table_file_name, url_template, delay=1):
    
    os.makedirs(output_dir, exist_ok=True)

    with open(table_file_name, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    soup = BeautifulSoup(html_content, 'html.parser')
    # print(soup)

    data = []
    # Find <div class="pinyin-chart-table">
    pinyin_chart_table = soup.find('div', class_='pinyin-chart-table')
    for row in pinyin_chart_table.find_all('tr'):
        if row.get('class') == ['tr-header']:
            continue
        for cell in row.find_all('td'):
            if cell.get_text() == '':
                continue
            data.append(cell.get_text())
    
    print(data)

    for i, char in enumerate(data):
        print(f"{i+1}/{len(data)} {char}")
        for tone in [1, 2, 3, 4]:
            url = url_template.format(char=char, tone=tone)
            # print(f"{i+1}/{len(data)} {url}")

            # Send request
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'audio/mpeg',
                'Referer': 'https://yoyochinese.com/',
                'Origin': 'https://yoyochinese.com',
                # 'Range': 'bytes=0-',
                'Connection': 'keep-alive',
                'Cache-Control': 'no-cache',
                'Pragma': 'no-cache',
                'Accept-Encoding': 'gzip, deflate, br',
                'Accept-Language': 'en-US,en;q=0.9',
            }
            response = requests.get(url, headers=headers)
            
            # Check if request was successful
            if response.status_code not in [200, 206]:
                print(f"Error requesting {url}: status {response.status_code}")
                continue
            
            # print("\t", f"Successful response for character {url}")

            output_file_name = os.path.join(output_dir, f"{char}{tone}.mp3")

            # Save response to file
            with open(output_file_name, 'wb') as f:
                f.write(response.content)
        
            # Pause between requests to avoid overloading the server
            time.sleep(delay)
        
    print(f"{len(data)} sounds saved to {output_dir}")

if __name__ == "__main__":
    # file_name = "./chat_gpt/words_Китайский_20250805_194526.json"
    url_template = "https://cdn.yoyochinese.com/audio/pychart/{char}{tone}.mp3"
    table_file_name = "/home/tony/repos/words/words/sounds/Interactive Pinyin Chart _ Yoyo Chinese.html"
    output_dir = "./sounds/downloaded_sounds"
    
    download_sounds(output_dir=output_dir, table_file_name=table_file_name, url_template=url_template, delay=0.1)
   
