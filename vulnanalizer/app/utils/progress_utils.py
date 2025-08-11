"""
Утилиты для отслеживания прогресса
"""
from datetime import datetime
from typing import Optional


def update_import_progress(status, current_step, total_steps=None, current_step_progress=None, 
                          total_records=None, processed_records=None, error_message=None,
                          total_parts=None, current_part=None, total_files_processed=None, current_file_records=None):
    """Обновить прогресс импорта"""
    global import_progress
    import_progress.update({
        'status': status,
        'current_step': current_step,
        'error_message': error_message
    })
    
    if total_steps is not None:
        import_progress['total_steps'] = total_steps
    if current_step_progress is not None:
        import_progress['current_step_progress'] = current_step_progress
    if total_records is not None:
        import_progress['total_records'] = total_records
    if processed_records is not None:
        import_progress['processed_records'] = processed_records
    if total_parts is not None:
        import_progress['total_parts'] = total_parts
    if current_part is not None:
        import_progress['current_part'] = current_part
    if total_files_processed is not None:
        import_progress['total_files_processed'] = total_files_processed
    if current_file_records is not None:
        import_progress['current_file_records'] = current_file_records
    
    if import_progress['start_time'] is None and status != 'idle':
        import_progress['start_time'] = datetime.now()
    
    # Рассчитываем правильный процент прогресса
    overall_progress = 0
    if import_progress['total_records'] > 0:
        overall_progress = min(100, (import_progress['processed_records'] / import_progress['total_records']) * 100)
    
    # Формируем информацию о текущем файле
    current_file_info = ""
    if import_progress['current_part'] and import_progress['total_parts']:
        current_file_info = f"Файл {import_progress['current_part']} из {import_progress['total_parts']}"
    
    # Формируем детальное описание текущего шага
    detailed_step = current_step
    if current_file_info:
        detailed_step = f"{current_file_info}: {current_step}"
    
    print(f"📊 Import Progress: {status} - {detailed_step} - {overall_progress:.1f}%")


def estimate_remaining_time(start_time, processed_records, total_records):
    """Оценить оставшееся время"""
    if processed_records == 0:
        return None
    
    elapsed_time = (datetime.now() - start_time).total_seconds()
    records_per_second = processed_records / elapsed_time
    remaining_records = total_records - processed_records
    
    if records_per_second > 0:
        remaining_seconds = remaining_records / records_per_second
        return remaining_seconds
    
    return None


# Глобальная переменная для отслеживания прогресса импорта
import_progress = {
    'status': 'idle',  # idle, uploading, extracting, splitting, processing, inserting, completed, error
    'current_step': '',
    'progress': 0,
    'total_steps': 0,
    'current_step_progress': 0,
    'total_records': 0,
    'processed_records': 0,
    'error_message': None,
    'start_time': None,
    'total_parts': 0,
    'current_part': 0,
    'total_files_processed': 0,
    'current_file_records': 0
}
