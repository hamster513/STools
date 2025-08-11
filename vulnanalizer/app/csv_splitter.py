#!/usr/bin/env python3
"""
Утилита для разделения больших CSV файлов на части
"""

import csv
import os
import sys
import argparse
from pathlib import Path

def split_csv_file(input_file, output_dir, lines_per_file=1000000, delimiter=';'):
    """
    Разделить CSV файл на части
    
    Args:
        input_file (str): Путь к входному CSV файлу
        output_dir (str): Директория для сохранения частей
        lines_per_file (int): Количество строк в каждом файле
        delimiter (str): Разделитель CSV
    """
    
    # Создаем выходную директорию
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Получаем имя файла без расширения
    input_path = Path(input_file)
    base_name = input_path.stem
    
    # Читаем заголовки из первого файла
    with open(input_file, 'r', encoding='utf-8-sig') as f:
        reader = csv.reader(f, delimiter=delimiter)
        headers = next(reader)  # Читаем заголовки
    
    # Счетчики
    total_lines = 0
    file_number = 1
    current_lines = 0
    current_file = None
    current_writer = None
    
    print(f"📁 Начинаем разделение файла: {input_file}")
    print(f"📊 Размер части: {lines_per_file:,} строк")
    print(f"📋 Заголовки: {', '.join(headers)}")
    
    # Читаем и разделяем файл
    with open(input_file, 'r', encoding='utf-8-sig') as f:
        reader = csv.reader(f, delimiter=delimiter)
        next(reader)  # Пропускаем заголовки (уже прочитали)
        
        for row in reader:
            # Если нужно создать новый файл
            if current_lines == 0:
                if current_file:
                    current_file.close()
                
                output_file = output_path / f"{base_name}_part_{file_number:03d}.csv"
                current_file = open(output_file, 'w', newline='', encoding='utf-8-sig')
                current_writer = csv.writer(current_file, delimiter=delimiter)
                current_writer.writerow(headers)  # Записываем заголовки
                
                print(f"📄 Создаем файл: {output_file.name}")
            
            # Записываем строку
            current_writer.writerow(row)
            current_lines += 1
            total_lines += 1
            
            # Если достигли лимита строк, переходим к следующему файлу
            if current_lines >= lines_per_file:
                print(f"✅ Файл {output_file.name} завершен: {current_lines:,} строк")
                current_lines = 0
                file_number += 1
    
    # Закрываем последний файл
    if current_file:
        current_file.close()
        print(f"✅ Файл {output_file.name} завершен: {current_lines:,} строк")
    
    print(f"\n🎉 Разделение завершено!")
    print(f"📊 Всего обработано строк: {total_lines:,}")
    print(f"📁 Создано файлов: {file_number - 1}")
    print(f"📂 Выходная директория: {output_dir}")
    
    return file_number - 1

def main():
    parser = argparse.ArgumentParser(description='Разделить большой CSV файл на части')
    parser.add_argument('input_file', help='Путь к входному CSV файлу')
    parser.add_argument('output_dir', help='Директория для сохранения частей')
    parser.add_argument('--lines', '-l', type=int, default=1000000, 
                       help='Количество строк в каждом файле (по умолчанию: 1,000,000)')
    parser.add_argument('--delimiter', '-d', default=';', 
                       help='Разделитель CSV (по умолчанию: ;)')
    
    args = parser.parse_args()
    
    # Проверяем существование входного файла
    if not os.path.exists(args.input_file):
        print(f"❌ Ошибка: Файл {args.input_file} не найден")
        sys.exit(1)
    
    try:
        num_files = split_csv_file(args.input_file, args.output_dir, args.lines, args.delimiter)
        print(f"\n💡 Рекомендации:")
        print(f"   - Загружайте файлы по одному")
        print(f"   - Проверяйте прогресс импорта")
        print(f"   - При ошибках попробуйте уменьшить размер части")
        
    except Exception as e:
        print(f"❌ Ошибка при разделении файла: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
