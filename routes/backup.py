"""
Роуты для управления бэкапами базы данных
"""
import os
import zipfile
import tarfile
import tempfile
import shutil
from datetime import datetime
from typing import List, Dict, Optional
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from pydantic import BaseModel
import subprocess
import asyncio

router = APIRouter()

# Настройки
BACKUP_DIR = os.getenv('BACKUP_DIR', './backups')
BACKUP_RETENTION_DAYS = int(os.getenv('BACKUP_RETENTION_DAYS', '30'))

def ensure_backup_dir():
    """Создает директорию для бэкапов если она не существует"""
    global BACKUP_DIR
    try:
        os.makedirs(BACKUP_DIR, exist_ok=True)
    except PermissionError:
        # Если нет прав на создание в текущей директории, используем /tmp
        BACKUP_DIR = '/tmp/backups'
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
        ensure_backup_dir()  # Убеждаемся что директория существует
        if not request.tables:
            raise HTTPException(status_code=400, detail="Не выбрано ни одной таблицы")
        
        # Создаем уникальный ID для бэкапа
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_id = f"backup_{timestamp}"
        
        # Создаем временную директорию
        with tempfile.TemporaryDirectory() as temp_dir:
            backup_file = os.path.join(temp_dir, f"{backup_id}.sql")
            
            # Формируем команду pg_dump
            cmd = [
                "docker", "exec", "stools_postgres", "pg_dump",
                "-U", "stools_user", "-d", "stools_db",
                "--clean", "--if-exists"
            ]
            
            # Добавляем таблицы
            for table in request.tables:
                if "." in table:
                    schema, table_name = table.split(".", 1)
                    cmd.extend(["-t", f"{schema}.{table_name}"])
                else:
                    cmd.extend(["-t", table])
            
            # Выполняем pg_dump
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=temp_dir
            )
            
            if result.returncode != 0:
                raise HTTPException(
                    status_code=500, 
                    detail=f"Ошибка создания дампа: {result.stderr}"
                )
            
            # Создаем архив
            archive_path = os.path.join(BACKUP_DIR, f"{backup_id}.tar.gz")
            with tarfile.open(archive_path, "w:gz") as tar:
                tar.add(backup_file, arcname=f"{backup_id}.sql")
            
            # Создаем метаданные бэкапа
            metadata = {
                "id": backup_id,
                "filename": f"{backup_id}.tar.gz",
                "size": os.path.getsize(archive_path),
                "created_at": datetime.now().isoformat(),
                "tables": request.tables,
                "status": "completed"
            }
            
            # Сохраняем метаданные
            metadata_file = os.path.join(BACKUP_DIR, f"{backup_id}.json")
            import json
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            return {
                "success": True,
                "backup_id": backup_id,
                "message": "Бэкап создан успешно",
                "download_url": f"/api/backup/download/{backup_id}"
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка создания бэкапа: {str(e)}")

@router.get("/api/backup/list")
async def list_backups():
    """Получить список всех бэкапов"""
    try:
        ensure_backup_dir()  # Убеждаемся что директория существует
        backups = []
        
        for filename in os.listdir(BACKUP_DIR):
            if filename.endswith('.json'):
                backup_id = filename.replace('.json', '')
                metadata_file = os.path.join(BACKUP_DIR, filename)
                
                try:
                    import json
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
        ensure_backup_dir()  # Убеждаемся что директория существует
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
        ensure_backup_dir()  # Убеждаемся что директория существует
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

@router.post("/api/backup/restore")
async def restore_backup(
    backup_file: UploadFile = File(...),
    tables: Optional[str] = Form(None),
    drop_existing: bool = Form(False)
):
    """Восстановить базу из бэкапа"""
    try:
        # Создаем временную директорию
        with tempfile.TemporaryDirectory() as temp_dir:
            # Сохраняем загруженный файл
            temp_archive = os.path.join(temp_dir, backup_file.filename)
            with open(temp_archive, "wb") as f:
                shutil.copyfileobj(backup_file.file, f)
            
            # Распаковываем архив
            if temp_archive.endswith('.tar.gz'):
                with tarfile.open(temp_archive, 'r:gz') as tar:
                    tar.extractall(temp_dir)
            elif temp_archive.endswith('.zip'):
                with zipfile.ZipFile(temp_archive, 'r') as zip_ref:
                    zip_ref.extractall(temp_dir)
            
            # Ищем SQL файл
            sql_file = None
            for file in os.listdir(temp_dir):
                if file.endswith('.sql'):
                    sql_file = os.path.join(temp_dir, file)
                    break
            
            if not sql_file:
                raise HTTPException(status_code=400, detail="SQL файл не найден в архиве")
            
            # Восстанавливаем базу
            cmd = [
                "docker", "exec", "-i", "stools_postgres", "psql",
                "-U", "stools_user", "-d", "stools_db"
            ]
            
            with open(sql_file, 'r') as f:
                result = subprocess.run(
                    cmd,
                    input=f.read(),
                    capture_output=True,
                    text=True
                )
            
            if result.returncode != 0:
                raise HTTPException(
                    status_code=500,
                    detail=f"Ошибка восстановления: {result.stderr}"
                )
            
            return {
                "success": True,
                "message": "База данных восстановлена успешно"
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка восстановления: {str(e)}")

@router.get("/api/backup/cleanup")
async def cleanup_old_backups():
    """Очистить старые бэкапы"""
    try:
        ensure_backup_dir()  # Убеждаемся что директория существует
        deleted_count = 0
        
        for filename in os.listdir(BACKUP_DIR):
            if filename.endswith('.json'):
                backup_id = filename.replace('.json', '')
                metadata_file = os.path.join(BACKUP_DIR, filename)
                
                try:
                    import json
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
