"""
Упрощенный сервис логирования фоновых задач (только файлы)
"""
import os
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List


class SimpleTaskLoggingService:
    """Упрощенный сервис для логирования фоновых задач"""
    
    def __init__(self):
        self.logs_dir = Path('/app/data/logs')
        self.logs_dir.mkdir(parents=True, exist_ok=True)
    
    async def is_detailed_logging_enabled(self, task_type: str) -> bool:
        """Проверить, включено ли подробное логирование для типа задачи"""
        return True
    
    async def create_task_logger(self, task_id: int, task_type: str) -> 'SimpleTaskLogger':
        """Создать логгер для конкретной задачи"""
        return SimpleTaskLogger(task_id, task_type, self.logs_dir)
    
    def get_log_files(self, task_type: str = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Получить список файлов логов"""
        try:
            log_files = []
            
            for log_file in self.logs_dir.glob('*.log'):
                if not log_file.is_file():
                    continue
                
                filename = log_file.name
                if not filename.endswith('.log'):
                    continue
                
                name_without_ext = filename[:-4]
                parts = name_without_ext.split('_')
                
                if len(parts) < 4:
                    continue
                
                # Парсинг: task_type_taskid_YYYYMMDD_HHMMSS
                if len(parts) >= 4:
                    file_date = parts[-2]
                    file_time = parts[-1]
                    file_task_id = parts[-3]
                    file_task_type = '_'.join(parts[:-3])
                else:
                    continue
                
                if task_type and file_task_type != task_type:
                    continue
                
                stat = log_file.stat()
                
                log_files.append({
                    'id': filename,
                    'task_id': int(file_task_id),
                    'task_type': file_task_type,
                    'file_name': filename,
                    'file_path': str(log_file),
                    'file_size': stat.st_size,
                    'file_size_mb': round(stat.st_size / (1024 * 1024), 2),
                    'created_at': datetime.fromtimestamp(stat.st_ctime),
                    'modified_at': datetime.fromtimestamp(stat.st_mtime)
                })
            
            log_files.sort(key=lambda x: x['created_at'], reverse=True)
            return log_files[:limit]
            
        except Exception as e:
            print(f"❌ Ошибка получения файлов логов: {e}")
            return []
    
    def delete_log_file(self, log_file_id: str) -> bool:
        """Удалить файл лога"""
        try:
            file_path = self.logs_dir / log_file_id
            if file_path.exists():
                file_path.unlink()
                return True
            return False
        except Exception as e:
            print(f"❌ Ошибка удаления файла лога: {e}")
            return False
    
    def cleanup_old_logs(self, days: int = 30):
        """Очистка старых логов"""
        try:
            from datetime import timedelta
            cutoff_date = datetime.now() - timedelta(days=days)
            deleted_count = 0
            
            for log_file in self.logs_dir.glob('*.log'):
                if log_file.is_file():
                    file_time = datetime.fromtimestamp(log_file.stat().st_ctime)
                    if file_time < cutoff_date:
                        log_file.unlink()
                        deleted_count += 1
            
            print(f"✅ Очищено {deleted_count} старых файлов логов")
            return deleted_count
        except Exception as e:
            print(f"❌ Ошибка очистки старых логов: {e}")
            return 0


class SimpleTaskLogger:
    """Упрощенный логгер для конкретной задачи"""
    
    def __init__(self, task_id: int, task_type: str, logs_dir: Path):
        self.task_id = task_id
        self.task_type = task_type
        self.logs_dir = logs_dir
        self.log_file_path = None
        self.log_file = None
        self.start_time = datetime.now()
        self._setup_file_logging()
    
    def _setup_file_logging(self):
        """Настройка файлового логирования"""
        try:
            timestamp = self.start_time.strftime('%Y%m%d_%H%M%S')
            filename = f"{self.task_type}_{self.task_id}_{timestamp}.log"
            self.log_file_path = self.logs_dir / filename
            
            self.log_file = open(self.log_file_path, 'w', encoding='utf-8')
            
            self.log_file.write(f"=== Лог задачи {self.task_type} (ID: {self.task_id}) ===\n")
            self.log_file.write(f"Начало: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            self.log_file.write("=" * 60 + "\n\n")
            self.log_file.flush()
        except Exception as e:
            print(f"❌ Ошибка настройки файлового логирования: {e}")
            self.log_file = None
    
    async def log(self, level: str, message: str, details: Dict[str, Any] = None):
        """Записать лог"""
        try:
            timestamp = datetime.now()
            
            if self.log_file:
                self._log_to_file(level, message, details, timestamp)
            
            print(f"[{timestamp.strftime('%H:%M:%S')}] {level}: {message}")
        except Exception as e:
            print(f"❌ Ошибка записи лога: {e}")
    
    def _log_to_file(self, level: str, message: str, details: Dict[str, Any], timestamp: datetime):
        """Записать лог в файл"""
        try:
            if not self.log_file:
                return
            
            log_entry = f"[{timestamp.strftime('%Y-%m-%d %H:%M:%S')}] {level}: {message}\n"
            
            if details:
                log_entry += f"  Детали: {json.dumps(details, ensure_ascii=False, indent=2)}\n"
            
            log_entry += "\n"
            
            self.log_file.write(log_entry)
            self.log_file.flush()
        except Exception as e:
            print(f"❌ Ошибка записи лога в файл: {e}")
    
    async def info(self, message: str, details: Dict[str, Any] = None):
        await self.log('INFO', message, details)
    
    async def warning(self, message: str, details: Dict[str, Any] = None):
        await self.log('WARNING', message, details)
    
    async def error(self, message: str, details: Dict[str, Any] = None):
        await self.log('ERROR', message, details)
    
    async def debug(self, message: str, details: Dict[str, Any] = None):
        await self.log('DEBUG', message, details)
    
    async def close(self):
        """Закрыть логгер"""
        try:
            end_time = datetime.now()
            
            if self.log_file:
                self.log_file.write(f"\n{'=' * 60}\n")
                self.log_file.write(f"Завершение: {end_time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                self.log_file.write(f"Длительность: {end_time - self.start_time}\n")
                self.log_file.close()
        except Exception as e:
            print(f"❌ Ошибка закрытия логгера: {e}")


# Глобальный экземпляр упрощенного сервиса логирования
simple_logging_service = SimpleTaskLoggingService()
