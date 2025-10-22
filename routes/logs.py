"""
Универсальные API роуты для управления логами всех компонентов
"""
from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import FileResponse
from pathlib import Path
import os
import json
from datetime import datetime
from typing import Dict, Any, Optional, List

router = APIRouter()

class UniversalLoggingService:
    """Универсальный сервис для логирования всех компонентов"""
    
    def __init__(self):
        self.logs_dir = Path('/app/data/logs')
        try:
            self.logs_dir.mkdir(parents=True, exist_ok=True)
        except PermissionError:
            # Если нет прав на создание директории, используем временную директорию
            import tempfile
            self.logs_dir = Path(tempfile.gettempdir()) / 'stools_logs'
            self.logs_dir.mkdir(parents=True, exist_ok=True)
    
    def get_log_files(self, task_type: str = None, component: str = None, limit: int = 50) -> List[Dict[str, Any]]:
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

# Глобальный экземпляр сервиса логирования
logging_service = UniversalLoggingService()


@router.get("/api/logs/test")
async def test_logs_endpoint():
    """Тестовый эндпоинт для проверки работы роутов логов"""
    return {
        "success": True,
        "message": "Универсальные роуты логов работают",
        "timestamp": "2024-01-15T10:00:00Z"
    }


@router.get("/api/logs/files")
async def get_log_files(task_type: str = None, component: str = None, limit: int = 50):
    """Получить список файлов логов"""
    try:
        log_files = logging_service.get_log_files(task_type, component, limit)
        
        formatted_files = []
        for file_info in log_files:
            formatted_files.append({
                "id": file_info["id"],
                "task_id": file_info["task_id"],
                "task_type": file_info["task_type"],
                "file_name": file_info["file_name"],
                "file_size": file_info["file_size"],
                "file_size_mb": file_info["file_size_mb"],
                "log_level": "INFO",
                "start_time": None,
                "end_time": None,
                "created_at": file_info["created_at"].isoformat() if file_info["created_at"] else None,
                "duration": None
            })
        
        return {
            "success": True,
            "files": formatted_files,
            "total_count": len(formatted_files)
        }
        
    except Exception as e:
        print(f"❌ Ошибка получения файлов логов: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка получения файлов логов: {str(e)}")


@router.get("/api/logs/files/{log_file_id}/download")
async def download_log_file(log_file_id: str):
    """Скачать файл лога"""
    try:
        log_files = logging_service.get_log_files()
        log_file = None
        
        for file_info in log_files:
            if file_info["id"] == log_file_id:
                log_file = file_info
                break
        
        if not log_file:
            raise HTTPException(status_code=404, detail="Файл лога не найден")
        
        file_path = Path(log_file["file_path"])
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="Файл лога не найден на диске")
        
        return FileResponse(
            path=str(file_path),
            filename=log_file["file_name"],
            media_type="text/plain"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Ошибка скачивания файла лога: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка скачивания файла лога: {str(e)}")


@router.delete("/api/logs/files/{log_file_id}")
async def delete_log_file(log_file_id: str):
    """Удалить файл лога"""
    try:
        success = logging_service.delete_log_file(log_file_id)
        
        if success:
            return {
                "success": True,
                "message": "Файл лога удален успешно"
            }
        else:
            raise HTTPException(status_code=404, detail="Файл лога не найден")
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Ошибка удаления файла лога: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка удаления файла лога: {str(e)}")


@router.post("/api/logs/cleanup")
async def cleanup_old_logs(request: Request):
    """Очистка старых логов"""
    try:
        data = await request.json()
        days = data.get("days", 30)
        
        deleted_count = logging_service.cleanup_old_logs(days)
        
        return {
            "success": True,
            "message": f"Удалено {deleted_count} старых файлов логов",
            "deleted_count": deleted_count
        }
        
    except Exception as e:
        print(f"❌ Ошибка очистки логов: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка очистки логов: {str(e)}")


@router.get("/api/logs/stats")
async def get_logs_stats():
    """Получить статистику логов"""
    try:
        all_files = logging_service.get_log_files()
        
        stats_by_type = {}
        total_size = 0
        total_files = len(all_files)
        
        for file_info in all_files:
            task_type = file_info["task_type"]
            file_size = file_info["file_size"] or 0
            
            if task_type not in stats_by_type:
                stats_by_type[task_type] = {
                    "count": 0,
                    "total_size": 0,
                    "total_size_mb": 0
                }
            
            stats_by_type[task_type]["count"] += 1
            stats_by_type[task_type]["total_size"] += file_size
            stats_by_type[task_type]["total_size_mb"] = round(
                stats_by_type[task_type]["total_size"] / (1024 * 1024), 2
            )
            
            total_size += file_size
        
        return {
            "success": True,
            "stats": {
                "total_files": total_files,
                "total_size": total_size,
                "total_size_mb": round(total_size / (1024 * 1024), 2),
                "by_task_type": stats_by_type
            }
        }
        
    except Exception as e:
        print(f"❌ Ошибка получения статистики логов: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка получения статистики логов: {str(e)}")
