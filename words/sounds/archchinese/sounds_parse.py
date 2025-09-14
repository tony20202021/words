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

    data = []
    
    # Находим все ссылки с onclick функциями fn_getTone
    tone_links = soup.find_all('a', onclick=True)
    
    for link in tone_links:
        onclick = link.get('onclick', '')
        # Извлекаем пиньинь из onclick функций типа fn_getTone('ba','b','a')
        if 'fn_getTone(' in onclick:
            # Используем регулярное выражение для извлечения первого параметра
            match = re.search(r"fn_getTone\('([^']+)'", onclick)
            if match:
                pinyin = match.group(1)
                data.append(pinyin)
    
    # Удаляем дубликаты и сортируем
    data = sorted(list(set(data)))
    
    print(f"Найдено {len(data)} уникальных слогов пиньинь:")
    print(data[:20], "..." if len(data) > 20 else "")

    for i, char in enumerate(data):
        print(f"{i+1}/{len(data)} {char}")
        for tone in [1, 2, 3, 4, 5]:
            url = url_template.format(char=char, tone=tone)

            # Send request
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'audio/mpeg',
                'Referer': 'https://archchinese.com/',
                'Origin': 'https://archchinese.com',
                'Connection': 'keep-alive',
                'Cache-Control': 'no-cache',
                'Pragma': 'no-cache',
                'Accept-Encoding': 'gzip, deflate, br',
                'Accept-Language': 'en-US,en;q=0.9',
            }
            
            try:
                response = requests.get(url, headers=headers, timeout=10)
                
                # Check if request was successful
                if response.status_code not in [200, 206]:
                    print(f"  Ошибка запроса {url}: status {response.status_code}")
                    continue
                
                # Проверяем, что получили аудио-файл (не HTML страницу с ошибкой)
                content_type = response.headers.get('content-type', '').lower()
                if 'audio' not in content_type and len(response.content) < 1000:
                    print(f"  Пропущен {char}{tone} - файл не найден")
                    continue

                output_file_name = os.path.join(output_dir, f"{char}{tone}.mp3")

                # Save response to file
                with open(output_file_name, 'wb') as f:
                    f.write(response.content)
                
                print(f"  Сохранен {char}{tone}.mp3 ({len(response.content)} bytes)")
                    
            except requests.exceptions.RequestException as e:
                print(f"  Ошибка сети для {char}{tone}: {e}")
                continue
        
            # Pause between requests to avoid overloading the server
            time.sleep(delay)
        
    print(f"Обработка завершена. Звуки сохранены в {output_dir}")

if __name__ == "__main__":
    url_template = "https://www.archchinese.com/swf/{char}{tone}.mp3"
    table_file_name = "/home/tony/repos/words/words/sounds/archchinese/data/Chinese Pinyin Table - 汉语拼音表.html"
    output_dir = "./sounds/archchinese/data/downloaded_sounds"
    
    download_sounds(output_dir=output_dir, table_file_name=table_file_name, url_template=url_template, delay=0.1)