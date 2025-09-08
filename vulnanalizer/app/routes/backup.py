"""
Роуты для управления бэкапами базы данных
"""
import os
import json
import tarfile
import tempfile
import shutil
from datetime import datetime
from typing import List, Dict, Optional
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from pydantic import BaseModel
from database import get_db

router = APIRouter()

# Настройки
BACKUP_DIR = os.getenv('BACKUP_DIR', './backups')
BACKUP_RETENTION_DAYS = int(os.getenv('BACKUP_RETENTION_DAYS', '30'))

# Создаем директорию для бэкапов
os.makedirs(BACKUP_DIR, exist_ok=True)

class BackupRequest(BaseModel):
    tables: List[str]
    include_schema: bool = True
    include_data: bool = True

class BackupInfo(BaseModel):
    id: str
    filename: str
    size: int
    created_at: datetime
    tables: List[str]
    status: str

class RestoreRequest(BaseModel):
    backup_id: str
    tables: Optional[List[str]] = None
    drop_existing: bool = False

@router.get("/api/backup/tables")
async def get_available_tables():
    """Получить список доступных таблиц для бэкапа"""
    try:
        # Получаем список таблиц из всех схем
        tables = []
        
        # Таблицы auth
        tables.extend([
            {"schema": "auth", "name": "users", "description": "Пользователи системы"},
            {"schema": "auth", "name": "sessions", "description": "Сессии пользователей"}
        ])
        
        # Таблицы vulnanalizer
        tables.extend([
            {"schema": "vulnanalizer", "name": "cve", "description": "Уязвимости CVE"},
            {"schema": "vulnanalizer", "name": "hosts", "description": "Хосты"},
            {"schema": "vulnanalizer", "name": "metasploit_modules", "description": "Модули Metasploit"},
            {"schema": "vulnanalizer", "name": "epss", "description": "Данные EPSS"},
            {"schema": "vulnanalizer", "name": "exploitdb", "description": "База ExploitDB"},
            {"schema": "vulnanalizer", "name": "background_tasks", "description": "Фоновые задачи"},
            {"schema": "vulnanalizer", "name": "settings", "description": "Настройки"}
        ])
        
        # Таблицы loganalizer
        tables.extend([
            {"schema": "loganalizer", "name": "log_entries", "description": "Записи логов"},
            {"schema": "loganalizer", "name": "log_files", "description": "Файлы логов"},
            {"schema": "loganalizer", "name": "analysis_settings", "description": "Настройки анализа"}
        ])
        
        return {"success": True, "tables": tables}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка получения списка таблиц: {str(e)}")

@router.post("/api/backup/create")
async def create_backup(request: BackupRequest):
    """Создать бэкап выбранных таблиц"""
    try:
        if not request.tables:
            raise HTTPException(status_code=400, detail="Не выбрано ни одной таблицы")
        
        # Создаем задачу в базе данных
        db = get_db()
        task_id = await db.create_background_task(
            task_type='backup_create',
            parameters={
                'tables': request.tables,
                'include_schema': request.include_schema,
                'include_data': request.include_data
            },
            description=f"Создание бэкапа таблиц: {', '.join(request.tables)}"
        )
        
        return {
            "success": True,
            "message": "Задача создания бэкапа поставлена в очередь",
            "task_id": task_id
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка создания задачи бэкапа: {str(e)}")

@router.get("/api/backup/list")
async def list_backups():
    """Получить список всех бэкапов"""
    try:
        backups = []
        
        for filename in os.listdir(BACKUP_DIR):
            if filename.endswith('.json'):
                backup_id = filename.replace('.json', '')
                metadata_file = os.path.join(BACKUP_DIR, filename)
                
                try:
                    with open(metadata_file, 'r') as f:
                        metadata = json.load(f)
                        backups.append(metadata)
                except:
                    continue
        
        # Сортируем по дате создания (новые сначала)
        backups.sort(key=lambda x: x['created_at'], reverse=True)
        
        return {"success": True, "backups": backups}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка получения списка бэкапов: {str(e)}")

@router.get("/api/backup/download/{backup_id}")
async def download_backup(backup_id: str):
    """Скачать бэкап по ID"""
    try:
        backup_file = os.path.join(BACKUP_DIR, f"{backup_id}.tar.gz")
        
        if not os.path.exists(backup_file):
            raise HTTPException(status_code=404, detail="Бэкап не найден")
        
        return FileResponse(
            backup_file,
            media_type='application/gzip',
            filename=f"{backup_id}.tar.gz"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка скачивания бэкапа: {str(e)}")

@router.delete("/api/backup/{backup_id}")
async def delete_backup(backup_id: str):
    """Удалить бэкап по ID"""
    try:
        # Удаляем файлы бэкапа
        backup_file = os.path.join(BACKUP_DIR, f"{backup_id}.tar.gz")
        metadata_file = os.path.join(BACKUP_DIR, f"{backup_id}.json")
        
        if os.path.exists(backup_file):
            os.remove(backup_file)
        
        if os.path.exists(metadata_file):
            os.remove(metadata_file)
        
        return {"success": True, "message": "Бэкап удален успешно"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка удаления бэкапа: {str(e)}")

@router.get("/api/backup/status/{task_id}")
async def get_backup_status(task_id: int):
    """Получить статус задачи создания бэкапа"""
    try:
        db = get_db()
        task = await db.get_background_task(task_id)
        
        if not task:
            raise HTTPException(status_code=404, detail="Задача не найдена")
        
        return {
            "success": True,
            "task": {
                "id": task['id'],
                "status": task['status'],
                "current_step": task.get('current_step', ''),
                "progress_percent": task.get('progress_percent', 0),
                "error_message": task.get('error_message'),
                "result_data": task.get('result_data'),
                "created_at": task['created_at'],
                "end_time": task.get('end_time')
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка получения статуса задачи: {str(e)}")

@router.get("/api/backup/cleanup")
async def cleanup_old_backups():
    """Очистить старые бэкапы"""
    try:
        deleted_count = 0
        
        for filename in os.listdir(BACKUP_DIR):
            if filename.endswith('.json'):
                backup_id = filename.replace('.json', '')
                metadata_file = os.path.join(BACKUP_DIR, filename)
                
                try:
                    with open(metadata_file, 'r') as f:
                        metadata = json.load(f)
                    
                    # Проверяем возраст бэкапа
                    created_at = datetime.fromisoformat(metadata['created_at'])
                    age_days = (datetime.now() - created_at).days
                    
                    if age_days > BACKUP_RETENTION_DAYS:
                        # Удаляем старый бэкап
                        backup_file = os.path.join(BACKUP_DIR, f"{backup_id}.tar.gz")
                        
                        if os.path.exists(backup_file):
                            os.remove(backup_file)
                        
                        os.remove(metadata_file)
                        deleted_count += 1
                        
                except:
                    continue
        
        return {
            "success": True,
            "message": f"Удалено {deleted_count} старых бэкапов",
            "deleted_count": deleted_count
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка очистки: {str(e)}")
