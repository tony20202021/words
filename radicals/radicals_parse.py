import os
import json
from PIL import Image, ImageDraw
from pdf2image import convert_from_path
from docx import Document
from docx.shared import Inches, Pt, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import parse_xml, OxmlElement

# Шаг 1: Преобразование PDF в изображения
def pdf_to_images(pdf_path, output_dir='output_images', dpi=300, fmt='png'):
    """
    Преобразует PDF-файл в отдельные изображения для каждой страницы.
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    print(f"Преобразование PDF в изображения с разрешением {dpi} DPI...")
    images = convert_from_path(pdf_path, dpi=dpi)
    
    saved_images = []
    
    for i, image in enumerate(images):
        page_num = i + 1
        output_file = os.path.join(output_dir, f"page_{page_num}.{fmt}")
        print(f"Сохранение страницы {page_num} в {output_file}...")
        
        image.save(output_file, fmt.upper())
        saved_images.append(output_file)
    
    print(f"Сохранено {len(saved_images)} изображений в директорию {output_dir}")
    return saved_images

# Шаг 2: Разрезание таблицы на ячейки с выделением регионов
def cut_table_into_cells_with_regions(image_path, output_dir, rows=11, cols=10, start_cell_num=1, page_number=1, 
                         margins=None, cell_padding=None, max_cell_num=None, regions=None):
    """
    Разрезает изображение таблицы на ячейки и выделяет регионы внутри каждой ячейки.
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    regions_dirs = {
        'character': os.path.join(output_dir, 'characters'),
        'pinyin': os.path.join(output_dir, 'pinyin'),
        'translation': os.path.join(output_dir, 'translation')
    }
    
    for region_dir in regions_dirs.values():
        if not os.path.exists(region_dir):
            os.makedirs(region_dir)
    
    image = Image.open(image_path)
    full_width, full_height = image.size
    
    if margins is None:
        margins = {'top': 0, 'right': 0, 'bottom': 0, 'left': 0}
    
    if cell_padding is None:
        cell_padding = {'top': 0, 'right': 5, 'bottom': 3, 'left': 0}
    
    if regions is None:
        regions = {
            'pinyin': {
                'top': 0.15,
                'left': 0.05,
                'bottom': 0.31,
                'right': 0.5
            },
            'character': {
                'top': 0.31,
                'left': 0.05,
                'bottom': 0.76,
                'right': 0.99
            },
            'translation': {
                'top': 0.76,
                'left': 0.05,
                'bottom': 0.99,
                'right': 0.99
            }
        }
    
    table_width = full_width - margins['left'] - margins['right']
    table_height = full_height - margins['top'] - margins['bottom']
    
    cell_width = table_width // cols
    cell_height = table_height // rows
    
    cells_info = {}
    cell_number = start_cell_num
    
    for row in range(rows):
        for col in range(cols):
            if max_cell_num is not None and cell_number > max_cell_num:
                print(f"Достигнут максимальный номер ячейки {max_cell_num}. Прекращаем обработку.")
                return cells_info
            
            left = margins['left'] + (col * cell_width)
            upper = margins['top'] + (row * cell_height)
            right = left + cell_width
            lower = upper + cell_height
            
            crop_left = left + cell_padding['left']
            crop_upper = upper + cell_padding['top']
            crop_right = right - cell_padding['right']
            crop_lower = lower - cell_padding['bottom']
            
            crop_left = max(0, crop_left)
            crop_upper = max(0, crop_upper)
            crop_right = min(full_width, crop_right)
            crop_lower = min(full_height, crop_lower)
            
            cell_image = image.crop((crop_left, crop_upper, crop_right, crop_lower))
            cell_width_actual = crop_right - crop_left
            cell_height_actual = crop_lower - crop_upper
            
            cell_filename = f"cell_{cell_number}.png"
            cell_path = os.path.join(output_dir, cell_filename)
            cell_image.save(cell_path)
            
            cell_with_regions = cell_image.copy()
            draw = ImageDraw.Draw(cell_with_regions)
            
            cell_regions = {}
            
            for region_name, region_coords in regions.items():
                region_left = int(region_coords['left'] * cell_width_actual)
                region_upper = int(region_coords['top'] * cell_height_actual)
                region_right = int(region_coords['right'] * cell_width_actual)
                region_lower = int(region_coords['bottom'] * cell_height_actual)
                
                region_left = max(0, region_left)
                region_upper = max(0, region_upper)
                region_right = min(cell_width_actual, region_right)
                region_lower = min(cell_height_actual, region_lower)
                
                region_image = cell_image.crop((region_left, region_upper, region_right, region_lower))
                
                region_filename = f"cell_{cell_number}_{region_name}.png"
                region_path = os.path.join(regions_dirs[region_name], region_filename)
                region_image.save(region_path)
                
                draw.rectangle(
                    [(region_left, region_upper), (region_right, region_lower)],
                    outline='red',
                    width=2
                )
                
                cell_regions[region_name] = {
                    "coordinates": {
                        "left": region_left,
                        "upper": region_upper,
                        "right": region_right,
                        "lower": region_lower
                    },
                    "image_path": region_path
                }
            
            cell_regions_filename = f"cell_{cell_number}_regions.png"
            cell_regions_path = os.path.join(output_dir, cell_regions_filename)
            cell_with_regions.save(cell_regions_path)
            
            cells_info[cell_number] = {
                "page": page_number,
                "row": row + 1,
                "column": col + 1,
                "coordinates": {
                    "left": crop_left,
                    "upper": crop_upper,
                    "right": crop_right,
                    "lower": crop_lower
                },
                "image_path": cell_path,
                "regions_image_path": cell_regions_path,
                "regions": cell_regions
            }
            
            cell_number += 1
    
    return cells_info

def process_multiple_pages_with_regions(image_paths, output_dir="output_cells", rows_per_page=None, cols=10, 
                          margins_per_page=None, cell_padding=None, max_cell_num=None, total_cells=None,
                          regions=None):
    """
    Обрабатывает несколько страниц с таблицами, сохраняет ячейки и выделяет регионы.
    """
    if rows_per_page is None:
        rows_per_page = [11] * len(image_paths)
    
    if len(image_paths) != len(rows_per_page):
        print(f"ПРЕДУПРЕЖДЕНИЕ: Количество страниц ({len(image_paths)}) не соответствует списку с количеством строк ({len(rows_per_page)})")
        rows_per_page = rows_per_page + [rows_per_page[-1]] * (len(image_paths) - len(rows_per_page))
    
    if margins_per_page is None:
        margins_per_page = [
            {'top': 135, 'right': 39, 'bottom': 99, 'left': 71}
        ] * len(image_paths)
    
    if len(image_paths) != len(margins_per_page):
        print(f"ПРЕДУПРЕЖДЕНИЕ: Количество страниц ({len(image_paths)}) не соответствует списку с отступами ({len(margins_per_page)})")
        margins_per_page = margins_per_page + [margins_per_page[-1]] * (len(image_paths) - len(margins_per_page))
    
    if cell_padding is None:
        cell_padding = {'top': 0, 'right': 5, 'bottom': 3, 'left': 0}
    
    if total_cells is not None and max_cell_num is None:
        max_cell_num = total_cells
    
    if regions is None:
        regions = {
            'pinyin': {
                'top': 0.15,
                'left': 0.05,
                'bottom': 0.31,
                'right': 0.5
            },
            'character': {
                'top': 0.31,
                'left': 0.05,
                'bottom': 0.76,
                'right': 0.99
            },
            'translation': {
                'top': 0.76,
                'left': 0.05,
                'bottom': 0.99,
                'right': 0.99
            }
        }
    
    all_cells_info = {}
    next_cell_num = 1
    
    for i, image_path in enumerate(image_paths):
        page_num = i + 1
        rows = rows_per_page[i]
        margins = margins_per_page[i]
        
        print(f"Обработка страницы {page_num} с {rows} строками и {cols} столбцами...")
        print(f"Используемые отступы: верх={margins['top']}, право={margins['right']}, низ={margins['bottom']}, лево={margins['left']}")
        
        if max_cell_num is not None and next_cell_num > max_cell_num:
            print(f"Достигнут максимальный номер ячейки {max_cell_num}. Прекращаем обработку.")
            break
        
        cells_info = cut_table_into_cells_with_regions(
            image_path, 
            output_dir, 
            rows=rows, 
            cols=cols, 
            start_cell_num=next_cell_num,
            page_number=page_num,
            margins=margins,
            cell_padding=cell_padding,
            max_cell_num=max_cell_num,
            regions=regions
        )
        
        if not cells_info:
            break
        
        next_cell_num = max(cells_info.keys()) + 1
        
        all_cells_info.update(cells_info)
        
        print(f"Страница {page_num} обработана. Вырезано {len(cells_info)} ячеек с регионами.")
    
    json_path = os.path.join(output_dir, "cells_info.json")
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(all_cells_info, f, ensure_ascii=False, indent=4)
    
    print(f"Обработка завершена. Всего вырезано {len(all_cells_info)} ячеек с регионами.")
    print(f"Информация о ячейках сохранена в {json_path}")
    
    return all_cells_info, json_path
    
# Главная функция для запуска всего процесса
def process_chinese_radicals_table(pdf_path, total_cells=214, full_image_scale=0.4, 
                                 character_image_scale=0.6, region_image_scale=0.8,
                                 use_modified_table=True):
    """
    Полный процесс обработки таблицы иероглифических ключей:
    1. Преобразование PDF в изображения
    2. Разрезание таблицы на ячейки с выделением регионов
    3. Создание документа Word с таблицей
    
    Параметры:
    pdf_path (str): Путь к PDF-файлу с таблицей
    total_cells (int): Общее количество ячеек для обработки
    full_image_scale (float): Коэффициент масштабирования полных изображений ячеек
    character_image_scale (float): Коэффициент масштабирования изображений иероглифов
    region_image_scale (float): Коэффициент масштабирования других изображений регионов
    use_modified_table (bool): Использовать модифицированную структуру таблицы с объединенными ячейками
    """
    print(f"Начало обработки таблицы иероглифических ключей: {pdf_path}")
    print(f"Всего будет обработано {total_cells} ячеек")
    print(f"Коэффициенты масштабирования изображений:")
    print(f" - Полные ячейки: {full_image_scale * 100}%")
    print(f" - Иероглифы: {character_image_scale * 100}%")
    print(f" - Пиньинь и перевод: {region_image_scale * 100}%")
    
    # Шаг 1: Преобразование PDF в изображения
    images = pdf_to_images(pdf_path, 'output_images')
    
    # Шаг 2: Разрезание таблицы на ячейки с выделением регионов
    regions = {
        'pinyin': {
            'top': 0.15,
            'left': 0.05,
            'bottom': 0.31,
            'right': 0.5
        },
        'character': {
            'top': 0.31,
            'left': 0.05,
            'bottom': 0.76,
            'right': 0.99
        },
        'translation': {
            'top': 0.76,
            'left': 0.05,
            'bottom': 0.99,
            'right': 0.99
        }
    }
    
    margins_per_page = [
        {'top': 135, 'right': 39, 'bottom': 99, 'left': 71},
        {'top': 135, 'right': 39, 'bottom': 99, 'left': 71}
    ]
    
    cell_padding = {'top': 0, 'right': 5, 'bottom': 3, 'left': 0}
    
    _, json_path = process_multiple_pages_with_regions(
        images, 
        rows_per_page=[11, 11], 
        cols=10,
        margins_per_page=margins_per_page,
        cell_padding=cell_padding,
        total_cells=total_cells,
        regions=regions
    )
    
    
    print("Полный процесс обработки завершен!")

# Дополнительные функции для более гибкой работы с изображениями
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
    # Путь к PDF-файлу с таблицей иероглифических ключей
    pdf_path = "./ключи.pdf"
    
    # Запуск полного процесса обработки с модифицированной структурой таблицы
    process_chinese_radicals_table(
        pdf_path, 
        total_cells=214, 
        full_image_scale=0.4,       # Полные изображения ячеек уменьшены до 40%
        character_image_scale=0.6,  # Изображения иероглифов уменьшены до 60%
        region_image_scale=0.8,     # Изображения пиньиня и перевода уменьшены до 80%
        use_modified_table=False     # Использовать модифицированную структуру таблицы
    )
