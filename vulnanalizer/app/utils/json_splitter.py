"""
Утилита для разбивки больших JSON файлов на части
"""
import json
import os
import ijson
from typing import List, Dict, Any
from pathlib import Path


class JSONSplitter:
    """Класс для разбивки больших JSON файлов на части"""
    
    def __init__(self, records_per_file: int = 10000):
        self.records_per_file = records_per_file
    
    def split_json_file(self, input_file: str, output_dir: str) -> List[str]:
        """
        Разбить JSON файл на части с потоковой обработкой
        
        Args:
            input_file: Путь к исходному JSON файлу
            output_dir: Директория для сохранения частей
            
        Returns:
            Список путей к созданным файлам
        """
        try:
            # Создаем выходную директорию
            Path(output_dir).mkdir(parents=True, exist_ok=True)
            
            # Получаем базовое имя файла без расширения
            base_name = Path(input_file).stem
            
            part_num = 1
            current_records = []
            created_files = []
            
            print(f"🔄 Начинаем разбивку файла {input_file}")
            print(f"📊 Записей в части: {self.records_per_file}")
            
            with open(input_file, 'rb') as f:
                parser = ijson.items(f, 'item')
                
                for item in parser:
                    current_records.append(item)
                    
                    # Если накопилось достаточно записей, сохраняем часть
                    if len(current_records) >= self.records_per_file:
                        output_file = os.path.join(output_dir, f"{base_name}_part_{part_num:03d}.json")
                        
                        with open(output_file, 'w', encoding='utf-8') as out_f:
                            json.dump(current_records, out_f, ensure_ascii=False, indent=2)
                        
                        print(f"✅ Создана часть {part_num}: {output_file} ({len(current_records)} записей)")
                        created_files.append(output_file)
                        
                        # Сбрасываем буфер и увеличиваем счетчик
                        current_records = []
                        part_num += 1
            
            # Сохраняем оставшиеся записи (если есть)
            if current_records:
                output_file = os.path.join(output_dir, f"{base_name}_part_{part_num:03d}.json")
                
                with open(output_file, 'w', encoding='utf-8') as out_f:
                    json.dump(current_records, out_f, ensure_ascii=False, indent=2)
                
                print(f"✅ Создана последняя часть {part_num}: {output_file} ({len(current_records)} записей)")
                created_files.append(output_file)
            
            print(f"🎉 Разбивка завершена! Создано {len(created_files)} частей")
            return created_files
            
        except Exception as e:
            print(f"❌ Ошибка разбивки файла: {e}")
            raise Exception(f"Ошибка разбивки JSON файла: {str(e)}")
    
    def get_file_info(self, file_path: str) -> Dict[str, Any]:
        """Получить информацию о файле"""
        try:
            file_size = os.path.getsize(file_path)
            
            # Быстро подсчитываем количество записей
            with open(file_path, 'rb') as f:
                parser = ijson.items(f, 'item')
                record_count = sum(1 for _ in parser)
            
            return {
                'file_path': file_path,
                'file_size_bytes': file_size,
                'file_size_mb': round(file_size / (1024 * 1024), 2),
                'record_count': record_count
            }
        except Exception as e:
            print(f"❌ Ошибка получения информации о файле: {e}")
            return {
                'file_path': file_path,
                'file_size_bytes': 0,
                'file_size_mb': 0,
                'record_count': 0
            }


def split_vm_data_file(input_file: str, output_dir: str = None, records_per_file: int = 10000) -> List[str]:
    """
    Удобная функция для разбивки VM данных
    
    Args:
        input_file: Путь к файлу VM данных
        output_dir: Директория для частей (по умолчанию рядом с исходным файлом)
        records_per_file: Количество записей в части
        
    Returns:
        Список путей к созданным частям
    """
    if output_dir is None:
        # Создаем директорию рядом с исходным файлом
        input_path = Path(input_file)
        output_dir = input_path.parent / f"{input_path.stem}_parts"
    
    splitter = JSONSplitter(records_per_file)
    return splitter.split_json_file(input_file, str(output_dir))


if __name__ == "__main__":
    # Пример использования
    import sys
    
    if len(sys.argv) < 2:
        print("Использование: python json_splitter.py <input_file> [output_dir] [records_per_file]")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else None
    records_per_file = int(sys.argv[3]) if len(sys.argv) > 3 else 10000
    
    try:
        created_files = split_vm_data_file(input_file, output_dir, records_per_file)
        print(f"\n📋 Созданные файлы:")
        for file_path in created_files:
            print(f"  - {file_path}")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        sys.exit(1)
