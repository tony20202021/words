import os
import json
from PIL import Image, ImageDraw


def cut_image_into_grid(image_path, output_dir, rows, cols, padding=0, format="png"):
    """
    Разрезает изображение на сетку ячеек указанного размера.
    
    Параметры:
    image_path (str): Путь к исходному изображению
    output_dir (str): Директория для сохранения результатов
    rows (int): Количество строк в сетке
    cols (int): Количество столбцов в сетке
    padding (int): Отступы между ячейками (пиксели)
    format (str): Формат сохранения изображений
    
    Возвращает:
    list: Список путей к сохраненным изображениям
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    # Открываем исходное изображение
    image = Image.open(image_path)
    width, height = image.size
    
    # Вычисляем размеры ячеек
    cell_width = width // cols
    cell_height = height // rows
    
    # Создаем список для хранения путей к сохраненным изображениям
    saved_images = []
    
    # Вырезаем и сохраняем каждую ячейку
    for row in range(rows):
        for col in range(cols):
            # Вычисляем координаты ячейки с учетом отступов
            left = col * cell_width + padding
            upper = row * cell_height + padding
            right = (col + 1) * cell_width - padding
            lower = (row + 1) * cell_height - padding
            
            # Обрезаем по границам изображения
            left = max(0, left)
            upper = max(0, upper)
            right = min(width, right)
            lower = min(height, lower)
            
            # Вырезаем ячейку
            cell = image.crop((left, upper, right, lower))
            
            # Создаем имя файла
            cell_filename = f"cell_r{row+1}_c{col+1}.{format}"
            cell_path = os.path.join(output_dir, cell_filename)
            
            # Сохраняем ячейку
            cell.save(cell_path)
            saved_images.append(cell_path)
    
    return saved_images


if __name__ == "__main__":
    image_path = "./21D58AFE-0451-4847-88BB-07B5EDB61E5C.jpeg"
    output_dir = "./output_cells"
    rows = 5
    cols = 9
    padding = 10
    format = "png"
    
    cut_image_into_grid(image_path, output_dir, rows, cols, padding, format)
