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
        ensure_backup_dir()  # Убеждаемся что директория существует
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
        ensure_backup_dir()  # Убеждаемся что директория существует
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
                import zipfile
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
            
            # Восстанавливаем базу через прямое подключение
            db = get_db()
            conn = await db.get_connection()
            
            try:
                # Читаем SQL файл
                with open(sql_file, 'r') as f:
                    sql_content = f.read()
                
                # Разбиваем SQL на отдельные команды
                sql_commands = [cmd.strip() for cmd in sql_content.split(';') if cmd.strip() and not cmd.strip().startswith('--')]
                
                # Выполняем каждую команду отдельно
                for command in sql_commands:
                    if command:
                        try:
                            await conn.execute(command)
                        except Exception as e:
                            # Логируем ошибку, но продолжаем выполнение
                            print(f"Ошибка выполнения SQL команды: {command[:100]}... - {e}")
                            continue
                
            finally:
                await db.release_connection(conn)
            
            return {
                "success": True,
                "message": "База данных восстановлена успешно",
                "filename": backup_file.filename
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка восстановления: {str(e)}")

@router.post("/api/backup/restore-by-id")
async def restore_backup_by_id(request: RestoreRequest):
    """Восстановить базу из бэкапа по ID"""
    try:
        ensure_backup_dir()
        
        # Проверяем существование бэкапа
        backup_file = os.path.join(BACKUP_DIR, f"{request.backup_id}.tar.gz")
        if not os.path.exists(backup_file):
            raise HTTPException(status_code=404, detail="Бэкап не найден")
        
        # Создаем временную директорию
        with tempfile.TemporaryDirectory() as temp_dir:
            # Распаковываем архив
            with tarfile.open(backup_file, 'r:gz') as tar:
                tar.extractall(temp_dir)
            
            # Ищем SQL файл
            sql_files = [f for f in os.listdir(temp_dir) if f.endswith('.sql')]
            if not sql_files:
                raise HTTPException(status_code=400, detail="SQL файл не найден в архиве")
            
            sql_file = os.path.join(temp_dir, sql_files[0])
            
            # Читаем SQL файл
            with open(sql_file, 'r', encoding='utf-8') as f:
                sql_content = f.read()
            
            # Получаем подключение к базе данных
            from database import get_db
            db = get_db()
            conn = await db.get_connection()
            
            try:
                # Безопасное выполнение SQL через asyncpg
                # Разбиваем на отдельные команды, но правильно
                import re
                
                # Умная разбивка SQL - учитываем строки в кавычках
                def split_sql_safely(sql_text):
                    commands = []
                    current_command = ""
                    in_string = False
                    escape_next = False
                    
                    for char in sql_text:
                        if escape_next:
                            current_command += char
                            escape_next = False
                        elif char == '\\':
                            current_command += char
                            escape_next = True
                        elif char == "'" and not in_string:
                            in_string = True
                            current_command += char
                        elif char == "'" and in_string:
                            in_string = False
                            current_command += char
                        elif char == ';' and not in_string:
                            if current_command.strip():
                                commands.append(current_command.strip())
                            current_command = ""
                        else:
                            current_command += char
                    
                    # Добавляем последнюю команду если есть
                    if current_command.strip():
                        commands.append(current_command.strip())
                    
                    return commands
                
                # Разбиваем SQL на команды безопасно
                sql_commands = split_sql_safely(sql_content)
                
                # Выполняем каждую команду отдельно
                failed_commands = 0
                total_commands = 0
                error_samples = []
                
                for command in sql_commands:
                    if command and not command.startswith('--'):
                        total_commands += 1
                        try:
                            await conn.execute(command)
                        except Exception as e:
                            failed_commands += 1
                            
                            # Сохраняем первые 5 ошибок для анализа
                            if len(error_samples) < 5:
                                error_samples.append({
                                    'command_num': total_commands,
                                    'error': str(e),
                                    'command_preview': command[:200] + "..." if len(command) > 200 else command
                                })
                            
                            # Логируем только первые 10 ошибок, чтобы не засорять логи
                            if failed_commands <= 10:
                                print(f"❌ Ошибка выполнения SQL команды #{total_commands}: {e}")
                                if "INSERT INTO vulnanalizer.metasploit_modules" in command:
                                    print(f"   Проблемная команда: {command[:200]}...")
                            continue
                
                print(f"📊 Статистика выполнения: {total_commands - failed_commands}/{total_commands} команд выполнено успешно")
                if failed_commands > 0:
                    print(f"⚠️  Провалено команд: {failed_commands}")
                    print("🔍 Образцы ошибок:")
                    for i, error in enumerate(error_samples, 1):
                        print(f"   {i}. Команда #{error['command_num']}: {error['error']}")
                        print(f"      {error['command_preview']}")
                        print()
                
            finally:
                await db.release_connection(conn)
            
            return {
                "success": True,
                "message": "База данных восстановлена успешно",
                "backup_id": request.backup_id
            }
            
    except Exception as e:
        print(f"❌ Ошибка восстановления: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Ошибка восстановления: {str(e)}")
