"""
Утилиты для работы с файлами
"""
import csv
import gzip
import io
import zipfile
from typing import List


def split_csv_automatically(content: str, max_lines: int = 1000000, delimiter: str = ';') -> List[str]:
    """
    Автоматически разделить CSV контент на части
    
    Args:
        content (str): Содержимое CSV файла
        max_lines (int): Максимальное количество строк в части
        delimiter (str): Разделитель CSV
    
    Returns:
        list: Список частей CSV (каждая часть - строка с содержимым)
    """
    lines = content.splitlines()
    total_lines = len(lines)
    
    if total_lines <= max_lines:
        return [content]  # Файл не нужно разделять
    
    # Читаем заголовки
    headers = lines[0]
    data_lines = lines[1:]
    
    parts = []
    for i in range(0, len(data_lines), max_lines):
        part_lines = data_lines[i:i + max_lines]
        part_content = headers + '\n' + '\n'.join(part_lines)
        parts.append(part_content)
    
    return parts


def split_file_by_size(content: str, max_size_mb: int = 100) -> List[str]:
    """Разделить файл на части по размеру в мегабайтах"""
    max_size_bytes = max_size_mb * 1024 * 1024
    parts = []
    
    if len(content) <= max_size_bytes:
        return [content]
    
    # Находим заголовки (первая строка)
    lines = content.splitlines()
    if not lines:
        return [content]
    
    header = lines[0]
    data_lines = lines[1:]
    
    current_part = [header]
    current_size = len(header.encode('utf-8'))
    
    for line in data_lines:
        line_size = len(line.encode('utf-8'))
        
        if current_size + line_size > max_size_bytes and current_part:
            # Завершаем текущую часть
            parts.append('\n'.join(current_part))
            current_part = [header]  # Начинаем новую часть с заголовка
            current_size = len(header.encode('utf-8'))
        
        current_part.append(line)
        current_size += line_size
    
    # Добавляем последнюю часть
    if current_part:
        parts.append('\n'.join(current_part))
    
    return parts


def extract_compressed_file(file_content: bytes, filename: str) -> str:
    """Извлечь содержимое из сжатого файла"""
    try:
        # Определяем тип архива по расширению
        file_ext = filename.lower()
        
        if file_ext.endswith('.zip'):
            # Обработка ZIP файла
            with zipfile.ZipFile(io.BytesIO(file_content), 'r') as zip_file:
                # Ищем CSV файл в архиве
                csv_files = [f for f in zip_file.namelist() if f.lower().endswith('.csv')]
                if not csv_files:
                    raise Exception("CSV файл не найден в ZIP архиве")
                
                # Берем первый CSV файл
                csv_filename = csv_files[0]
                with zip_file.open(csv_filename) as csv_file:
                    content = csv_file.read()
                    return content.decode('utf-8-sig')
        
        elif file_ext.endswith('.gz') or file_ext.endswith('.gzip'):
            # Обработка GZIP файла
            with gzip.GzipFile(fileobj=io.BytesIO(file_content)) as gz_file:
                content = gz_file.read()
                return content.decode('utf-8-sig')
        
        else:
            # Обычный CSV файл
            return file_content.decode('utf-8-sig')
    
    except Exception as e:
        raise Exception(f"Ошибка при извлечении файла: {str(e)}")
