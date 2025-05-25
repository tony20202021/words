import json

def split_json_file(input_path, output_prefix, chunk_size):
    # Считаем исходный файл
    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    keys = list(data.keys())
    total = len(keys)
    
    # Разбиваем на чанки
    for i in range(0, total, chunk_size):
        chunk_keys = keys[i:i+chunk_size]
        chunk_data = {k: data[k] for k in chunk_keys}
        
        output_path = f"{output_prefix}_{i//chunk_size + 1}.json"
        with open(output_path, 'w', encoding='utf-8') as out_f:
            json.dump(chunk_data, out_f, ensure_ascii=False, indent=4)
        
        print(f"Сохранён файл {output_path} с {len(chunk_keys)} записями")

if __name__ == "__main__":
    # Пример использования
    input_file = "input.json"
    output_file_prefix = "output_chunk"
    chunk_size = 100  # можно менять
    
    split_json_file(input_file, output_file_prefix, chunk_size)
