from fastapi import FastAPI, Request, HTTPException, UploadFile, File, Form
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
import os
import json
import uuid
import zipfile
import tarfile
import gzip
import bz2
import lzma
import re
from typing import Dict, List, Optional
from datetime import datetime
import asyncio
from pathlib import Path
import shutil
from database import Database
from models import LogFile, LogSettings, AnalysisPreset
import traceback
from concurrent.futures import ThreadPoolExecutor
import threading

# Импортируем новую систему распознавания форматов
from log_formats import detect_log_level, log_detector

def get_version():
    try:
        with open('VERSION', 'r') as f:
            return f.read().strip()
    except:
        return "0.5.00"

app = FastAPI(title="LogAnalizer", version=get_version())

# Увеличиваем лимиты для загрузки файлов
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключение статических файлов
app.mount("/static", StaticFiles(directory="static"), name="static")

# Настройка шаблонов с кэшированием
templates = Jinja2Templates(directory="templates")

# Кастомный роут для CSS файла с заголовками для предотвращения кэширования
@app.get("/static/css/main.css")
async def get_main_css():
    return FileResponse(
        "../../static/css/main.css",
        media_type="text/css",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0"
        }
    )

# Инициализация базы данных
db = Database()

# Создаем директорию для файлов
DATA_DIR = Path("/app/data")
DATA_DIR.mkdir(exist_ok=True)

# Кэш для часто используемых данных
_cache = {
    'settings': None,
    'presets': None,
    'custom_settings': None
}

# Global dictionary for tracking upload progress
upload_progress = {}

# Global thread pool executor for background tasks
thread_pool = ThreadPoolExecutor(max_workers=4)

# OPTIMIZATION: Add logging for debugging
def log_progress_update(upload_id: str, status: str, message: str, progress: int, details: str = None):
    """Logging progress updates"""
    progress_data = {
        'status': status,
        'message': message,
        'progress': progress,
        'details': details
    }
    upload_progress[upload_id] = progress_data
    print(f"📊 Progress updated for {upload_id}: {progress_data}")

    # OPTIMIZATION: Save to file for debugging
    try:
        with open(f"/app/data/progress_{upload_id}.json", "w") as f:
            json.dump(progress_data, f)
    except Exception as e:
        print(f"⚠️ Could not save progress to file: {e}")

def _detect_log_level(line: str, important_levels: List[str]) -> Optional[str]:
    """
    Универсальное определение уровня лога с использованием новой системы
    """
    return detect_log_level(line, important_levels, debug=True)

@app.on_event("startup")
async def startup():
    """Оптимизированная инициализация приложения"""
    try:
        # Ждем немного, чтобы PostgreSQL полностью запустился
        await asyncio.sleep(5)
        
        # Инициализируем базу данных
        await db.init_database()
        
        # Проверяем соединение с базой данных
        await db.test_connection()
        
        # Предварительно загружаем часто используемые данные
        await _preload_cache()
        
        print("LogAnalizer startup completed successfully")
    except Exception as e:
        print(f"Startup error: {e}")
        raise

async def _preload_cache():
    """Предварительная загрузка кэша"""
    try:
        # Загружаем настройки
        _cache['settings'] = await db.get_settings()
        
        # Загружаем пресеты
        _cache['presets'] = await db.get_presets()
        
        # Загружаем пользовательские настройки
        _cache['custom_settings'] = await db.get_custom_analysis_settings()
        
        print("Cache preloaded successfully")
    except Exception as e:
        print(f"Cache preload error: {e}")

@app.on_event("shutdown")
async def shutdown():
    """Корректное завершение работы"""
    try:
        await db.close()
        print("LogAnalizer shutdown completed")
    except Exception as e:
        print(f"Shutdown error: {e}")

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Главная страница с оптимизированной загрузкой"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/api/health")
async def health_check():
    """Проверка состояния системы"""
    try:
        await db.test_connection()
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "database": "disconnected", "error": str(e)}

@app.get("/api/version")
async def get_version():
    """Get application version"""
    try:
        with open('/app/VERSION', 'r') as f:
            version = f.read().strip()
        return {"version": version}
    except Exception as e:
        return {"version": "unknown"}

@app.get("/api/upload-progress/{upload_id}")
async def get_upload_progress(upload_id: str):
    """Get upload progress via SSE"""
    print(f"🔍 SSE request for upload_id: {upload_id}")

    async def event_generator():
        while True:
            if upload_id in upload_progress:
                progress_data = upload_progress[upload_id]
                print(f"📤 Sending SSE data: {progress_data}")
                yield f"data: {json.dumps(progress_data)}\n\n"

                # If upload is completed, stop the stream
                if progress_data.get('status') in ['completed', 'error']:
                    break
            else:
                # If upload_id not found, send an error message
                error_data = {
                    'status': 'not_found',
                    'message': 'Upload ID not found',
                    'progress': 0,
                    'details': f'Upload ID: {upload_id}'
                }
                yield f"data: {json.dumps(error_data)}\n\n"
                break

            await asyncio.sleep(1)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "text/event-stream",
        }
    )

@app.get("/api/upload-progress-json/{upload_id}")
async def get_upload_progress_json(upload_id: str):
    """Get upload progress in JSON format for fallback"""
    print(f"🔍 JSON request for upload_id: {upload_id}")

    if upload_id in upload_progress:
        progress_data = upload_progress[upload_id]
        print(f"📤 Sending JSON data: {progress_data}")
        return progress_data
    else:
        # If upload_id not found, return an error message
        error_data = {
            'status': 'not_found',
            'message': 'Upload ID not found',
            'progress': 0,
            'details': f'Upload ID: {upload_id}'
        }
        return error_data

@app.get("/api/settings")
async def get_settings():
    """Получение настроек с кэшированием"""
    try:
        # Если кэш пустой или None, загружаем из базы данных
        if _cache['settings'] is None:
            print("🔄 Loading settings from database (cache was None)")
            _cache['settings'] = await db.get_settings()
            print(f"📊 Settings loaded: {_cache['settings']}")
        return {"success": True, "data": _cache['settings']}
    except Exception as e:
        print(f"❌ Error loading settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/settings")
async def update_settings(request: Request):
    """Обновление настроек с инвалидацией кэша"""
    try:
        data = await request.json()
        await db.update_settings(data)
        # Инвалидируем кэш
        _cache['settings'] = None
        return {"success": True, "message": "Settings updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/logs/upload")
async def upload_logs(
    file: UploadFile = File(...),
    max_file_size: int = Form(100),  # MB
    extract_nested: bool = Form(True),
    max_depth: int = Form(5)
):
    """Upload and process log files - OPTIMIZED VERSION WITH BACKGROUND PROCESSING"""
    upload_id = str(uuid.uuid4())
    file_id = str(uuid.uuid4())

    print(f"🚀 Starting upload: {file.filename} (upload_id: {upload_id})")

    try:
        # Check file size
        if file.size > max_file_size * 1024 * 1024:
            raise HTTPException(status_code=400, detail=f"File too large. Max size: {max_file_size}MB")

        # Save file
        original_filename = file.filename
        file_extension = Path(original_filename).suffix.lower()
        file_path = DATA_DIR / f"{file_id}{file_extension}"

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        print(f"💾 File saved: {file_path}")

        # Initialize progress immediately
        log_progress_update(upload_id, 'starting', 'Начинаем обработку файла...', 0, f'Файл: {original_filename}')

        # OPTIMIZATION: Return upload_id immediately, processing in background
        result = {
            "success": True,
            "file_id": file_id,
            "upload_id": upload_id,
            "extracted_count": 0,  # Will be updated in background
            "message": f"File uploaded successfully, processing in background"
        }

        print(f"✅ Returning upload_id immediately: {upload_id}")

        # Run processing in thread pool
        def run_processing():
            try:
                print(f"🔄 Thread processing started for upload_id: {upload_id}")
                # Create new event loop for the thread
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                # Run the async function
                loop.run_until_complete(process_upload_in_background(
                    file_path, file_id, upload_id, original_filename,
                    file_extension, extract_nested, max_depth
                ))
                print(f"✅ Thread processing completed for upload_id: {upload_id}")
            except Exception as e:
                print(f"❌ Thread processing error: {e}")
                print(f"❌ Error details: {traceback.format_exc()}")
            finally:
                loop.close()
        
        print(f"🎯 Submitting background task to thread pool for upload_id: {upload_id}")
        thread_pool.submit(run_processing)
        print(f"🎯 Background task submitted to thread pool")
        
        # Небольшая задержка, чтобы убедиться, что upload_id зарегистрирован
        await asyncio.sleep(0.1)

        return result

    except Exception as e:
        print(f"❌ Upload error: {e}")
        log_progress_update(upload_id, 'error', 'Ошибка при загрузке файла', 0, str(e))
        raise HTTPException(status_code=500, detail=str(e))

async def process_upload_in_background(
    file_path: Path, file_id: str, upload_id: str,
    original_filename: str, file_extension: str,
    extract_nested: bool, max_depth: int
):
    """Background processing of the uploaded file"""
    # Create new database connection for this thread
    thread_db = Database()
    
    try:
        print(f"🔄 Starting background processing for upload_id: {upload_id}")
        print(f"📁 File path: {file_path}")
        print(f"🆔 File ID: {file_id}")
        print(f"📄 Original filename: {original_filename}")
        print(f"🔧 Extract nested: {extract_nested}")
        print(f"📏 Max depth: {max_depth}")

        # Initialize database connection
        await thread_db.init_database()

        # STAGE 1: ARCHIVE EXTRACTION
        log_progress_update(upload_id, 'extracting', 'Распаковка архива...', 10, f'Файл: {original_filename}')

        extracted_files = []
        if file_path.suffix.lower() in ['.zip', '.tar', '.gz', '.bz2', '.xz']:
            # Add timeout for large archives
            try:
                extracted_files = await asyncio.wait_for(
                    extract_archive(file_path, file_id, extract_nested, max_depth, 0, file_id),
                    timeout=300  # 5 minutes timeout
                )
                print(f"📦 Extracted {len(extracted_files)} files")
            except asyncio.TimeoutError:
                log_progress_update(upload_id, 'error', 'Таймаут при распаковке архива', 0, 'Обработка заняла слишком много времени')
                return
        else:
            # Regular file
            extracted_files = [{
                'id': file_id,
                'original_name': original_filename,
                'file_path': str(file_path),
                'file_type': file_extension,
                'file_size': file_path.stat().st_size,
                'upload_date': datetime.now(),
                'parent_file_id': None
            }]

        # STAGE 2: SAVING TO DATABASE
        log_progress_update(upload_id, 'saving_to_db', 'Сохранение в базу данных...', 50, f'Файлов для сохранения: {len(extracted_files)}')

        if len(extracted_files) > 1:
            # Batch insert for archives
            await thread_db.insert_log_files_batch(extracted_files)
        else:
            # Single insert
            await thread_db.insert_log_file(extracted_files[0])

        log_progress_update(upload_id, 'saving_completed', 'Сохранение в базу данных завершено', 70, f'Сохранено файлов: {len(extracted_files)}')

        # STAGE 3: FILE FILTERING
        log_progress_update(upload_id, 'filtering', 'Начинаем фильтрацию файлов...', 80, f'Файлов для фильтрации: {len(extracted_files)}')

        # OPTIMIZATION: Batch file filtering
        batch_size = 5  # Filter 5 files simultaneously
        total_batches = (len(extracted_files) + batch_size - 1) // batch_size

        for batch_idx in range(total_batches):
            start_idx = batch_idx * batch_size
            end_idx = min(start_idx + batch_size, len(extracted_files))
            batch = extracted_files[start_idx:end_idx]

            # Update progress for the batch
            progress = 80 + (batch_idx + 1) * 15 / total_batches
            
            # Показываем информацию о первом файле в пакете
            if batch:
                first_file = batch[0]
                file_size_mb = first_file.get('file_size', 0) / (1024 * 1024)
                log_progress_update(
                    upload_id,
                    'filtering',
                    f'Фильтрация пакета {batch_idx + 1} из {total_batches}...',
                    min(progress, 95),
                    f'Файлы {start_idx + 1}-{end_idx} из {len(extracted_files)} | Текущий: {first_file["original_name"]} ({file_size_mb:.1f} MB)'
                )
            else:
                log_progress_update(
                    upload_id,
                    'filtering',
                    f'Фильтрация пакета {batch_idx + 1} из {total_batches}...',
                    min(progress, 95),
                    f'Файлы {start_idx + 1}-{end_idx} из {len(extracted_files)}'
                )
            print(f"📊 Progress updated (filtering batch {batch_idx + 1}): {upload_progress[upload_id]}")

            # OPTIMIZATION: Parallel filtering of the batch with individual file progress
            async def filter_file_parallel(file_info):
                try:
                    # Показываем информацию о текущем файле
                    file_size_mb = file_info.get('file_size', 0) / (1024 * 1024)
                    log_progress_update(
                        upload_id,
                        'filtering_file',
                        f'Фильтрация файла: {file_info["original_name"]}',
                        progress,
                        f'Размер: {file_size_mb:.1f} MB | Пакет {batch_idx + 1} из {total_batches}'
                    )
                    
                    print(f"🔍 Starting to filter file: {file_info['original_name']}")
                    result = await filter_log_file(Path(file_info['file_path']), file_info['id'], thread_db)
                    print(f"✅ Successfully filtered file: {file_info['original_name']}")
                    return result
                except Exception as e:
                    print(f"❌ Error filtering file {file_info['original_name']}: {e}")
                    print(f"❌ Error details: {traceback.format_exc()}")
                    raise

            # Perform parallel filtering of the batch
            print(f"🔄 Starting parallel filtering of batch {batch_idx + 1} with {len(batch)} files")
            await asyncio.gather(*[filter_file_parallel(file_info) for file_info in batch])
            print(f"✅ Filtered batch {batch_idx + 1}: {[f['original_name'] for f in batch]}")

        # Filtering completion
        log_progress_update(upload_id, 'filtering_completed', 'Фильтрация файлов завершена', 95, f'Отфильтровано файлов: {len(extracted_files)}')

        # Delete original archive file
        if file_path.exists() and file_path.suffix.lower() in ['.zip', '.tar', '.gz', '.bz2', '.xz']:
            file_path.unlink()
            print(f"🗑️ Original archive deleted")

        # Complete progress
        log_progress_update(upload_id, 'completed', 'Загрузка завершена успешно!', 100, f'Обработано файлов: {len(extracted_files)}')

    except Exception as e:
        print(f"❌ Background processing error: {e}")
        print(f"❌ Error details: {traceback.format_exc()}")
        log_progress_update(upload_id, 'error', 'Ошибка при обработке файла', 0, str(e))
    finally:
        # Close database connection
        if thread_db.pool:
            await thread_db.close()

async def extract_archive(file_path: Path, file_id: str, extract_nested: bool, max_depth: int, current_depth: int = 0, parent_id: str = None) -> List[Dict]:
    """Рекурсивная распаковка архивов"""
    extracted_files = []
    
    try:
        # Определяем тип архива
        if file_path.suffix.lower() in ['.zip', '.tar', '.gz', '.bz2', '.xz']:
            # Это архив, распаковываем
            if current_depth >= max_depth:
                return extracted_files
            
            # Промежуточные архивы не сохраняем в БД, только конечные файлы
            
            extract_dir = DATA_DIR / f"{file_id}_extracted"
            extract_dir.mkdir(exist_ok=True)
            
            if file_path.suffix.lower() == '.zip':
                with zipfile.ZipFile(file_path, 'r') as zip_ref:
                    zip_ref.extractall(extract_dir)
            elif file_path.suffix.lower() == '.tar':
                with tarfile.open(file_path, 'r:*') as tar_ref:
                    tar_ref.extractall(extract_dir)
            elif file_path.suffix.lower() == '.gz':
                with gzip.open(file_path, 'rb') as gz_ref:
                    with open(extract_dir / file_path.stem, 'wb') as f:
                        shutil.copyfileobj(gz_ref, f)
            elif file_path.suffix.lower() == '.bz2':
                with bz2.open(file_path, 'rb') as bz2_ref:
                    with open(extract_dir / file_path.stem, 'wb') as f:
                        shutil.copyfileobj(bz2_ref, f)
            elif file_path.suffix.lower() == '.xz':
                with lzma.open(file_path, 'rb') as xz_ref:
                    with open(extract_dir / file_path.stem, 'wb') as f:
                        shutil.copyfileobj(xz_ref, f)
            
            # Обрабатываем распакованные файлы
            for extracted_file in extract_dir.rglob('*'):
                if extracted_file.is_file():
                    # Пропускаем служебные файлы macOS
                    if extracted_file.name.startswith('._') or extracted_file.name.startswith('.DS_Store'):
                        continue
                    if extract_nested and extracted_file.suffix.lower() in ['.zip', '.tar', '.gz', '.bz2', '.xz']:
                        # Рекурсивно распаковываем вложенные архивы
                        nested_file_id = str(uuid.uuid4())
                        nested_files = await extract_archive(
                            extracted_file, 
                            nested_file_id, 
                            extract_nested, 
                            max_depth, 
                            current_depth + 1,
                            parent_id  # Передаем корневой parent_id
                        )
                        extracted_files.extend(nested_files)
                    else:
                        # Обычный файл
                        extracted_files.append({
                            'id': str(uuid.uuid4()),
                            'original_name': extracted_file.name,
                            'file_path': str(extracted_file),
                            'file_type': extracted_file.suffix.lower(),
                            'file_size': extracted_file.stat().st_size,
                            'upload_date': datetime.now(),
                            'parent_file_id': None  # Не ссылаемся на корневой архив
                        })
        else:
            # Обычный текстовый файл - не добавляем в extracted_files, 
            # так как он будет обработан в основной функции upload_logs
            pass
    
    except Exception as e:
        print(f"Error extracting archive {file_path}: {e}")
    
    return extracted_files

async def filter_log_file(file_path: Path, file_id: str, db_instance: Database = None, skip_size_check: bool = False) -> Optional[Dict]:
    """Фильтрация лог файла согласно настройкам"""
    print(f"🔍 Starting filter_log_file for: {file_path}")
    try:
        # Используем переданное соединение или глобальное
        db_conn = db_instance if db_instance else db
        
        # Получаем настройки фильтрации
        settings = await db_conn.get_settings()
        custom_settings = await db_conn.get_custom_analysis_settings()
        
        # Проверяем размер файла для фильтрации (только для автоматической фильтрации)
        if not skip_size_check:
            file_size_mb = file_path.stat().st_size / (1024 * 1024)
            max_filtering_size = settings.get('max_filtering_file_size_mb', 50)
            
            if file_size_mb > max_filtering_size:
                print(f"⚠️ File {file_path} is too large for automatic filtering ({file_size_mb:.1f}MB > {max_filtering_size}MB)")
                return None
        else:
            file_size_mb = file_path.stat().st_size / (1024 * 1024)
            print(f"🔍 Manual filtering: File size is {file_size_mb:.1f}MB (size check skipped)")
        
        # Собираем все активные паттерны
        patterns = []
        
        # Добавляем важные уровни логов
        important_levels = settings.get('important_log_levels', [])
        
        # Добавляем пользовательские настройки
        for setting in custom_settings:
            if setting.get('enabled', True):
                patterns.append(setting['pattern'])
        
        if not important_levels and not patterns:
            return None
        
        # Создаем отфильтрованный файл
        filtered_file_path = DATA_DIR / f"{file_id}_filtered"
        filtered_lines = []
        
        # Читаем и фильтруем файл
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                line = line.strip()
                if line:
                    # Проверяем уровни логов с улучшенной фильтрацией
                    if important_levels:
                        detected_level = _detect_log_level(line, important_levels)
                        if detected_level:
                            filtered_lines.append(line)
                            continue
                    
                    # Проверяем пользовательские паттерны
                    for pattern in patterns:
                        if re.search(pattern, line):
                            filtered_lines.append(line)
                            break
        
        # Сохраняем отфильтрованный файл
        if filtered_lines:
            with open(filtered_file_path, 'w', encoding='utf-8') as f:
                for line in filtered_lines:
                    f.write(line + '\n')
            
            # Сохраняем информацию в базу
            filtered_file_data = {
                'id': str(uuid.uuid4()),
                'original_file_id': file_id,
                'filtered_file_path': str(filtered_file_path),
                'filter_settings': {
                    'important_levels': important_levels,
                    'custom_patterns': [s['name'] for s in custom_settings if s.get('enabled', True)]
                },
                'lines_count': len(filtered_lines)
            }
            
            print(f"💾 Saving filtered file data to database: {filtered_file_data}")
            try:
                await db_conn.insert_filtered_file(filtered_file_data)
                print(f"✅ Successfully filtered file {file_path}: {len(filtered_lines)} lines")
                return filtered_file_data
            except Exception as e:
                print(f"❌ Error saving filtered file data: {e}")
                print(f"❌ Error details: {traceback.format_exc()}")
                return None
        
        print(f"⚠️ No matching lines found in file {file_path}")
        return None
        
    except Exception as e:
        print(f"❌ Error filtering file {file_path}: {e}")
        print(f"❌ Error details: {traceback.format_exc()}")
        return None

@app.get("/api/logs/files")
async def get_log_files():
    """Получение списка загруженных файлов"""
    try:
        files = await db.get_log_files()
        return {"success": True, "data": files}
    except Exception as e:
        print(f"❌ Error in get_log_files: {e}")
        print(f"❌ Error details: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/logs/files/{file_id}/preview")
async def preview_log_file(file_id: str, lines: int = 100):
    """Предварительный просмотр файла"""
    try:
        file_info = await db.get_log_file(file_id)
        if not file_info:
            raise HTTPException(status_code=404, detail="File not found")
        
        file_path = Path(file_info['file_path'])
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="File not found on disk")
        
        # Читаем первые N строк
        preview_lines = []
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            for i, line in enumerate(f):
                if i >= lines:
                    break
                preview_lines.append(line.rstrip())
        
        return {
            "success": True,
            "file_id": file_id,
            "original_name": file_info['original_name'],
            "preview": preview_lines,
            "total_lines": len(preview_lines)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/logs/files/{file_id}/filtered")
async def preview_filtered_file(file_id: str, lines: int = 100):
    """Предварительный просмотр отфильтрованного файла"""
    try:
        print(f"🔍 Requesting filtered file for file_id: {file_id}")
        
        filtered_file_info = await db.get_filtered_file(file_id)
        print(f"📊 Filtered file info: {filtered_file_info}")
        
        if not filtered_file_info:
            print(f"❌ No filtered file found for file_id: {file_id}")
            # Возвращаем пустой результат вместо ошибки
            return {
                "success": True,
                "file_id": file_id,
                "filtered_file_id": None,
                "preview": [],
                "total_lines": 0,
                "filter_settings": {},
                "message": "No matching lines found in file"
            }
        
        file_path = Path(filtered_file_info['filtered_file_path'])
        print(f"📁 Checking file path: {file_path}")
        
        if not file_path.exists():
            print(f"❌ Filtered file not found on disk: {file_path}")
            raise HTTPException(status_code=404, detail="Filtered file not found on disk")
        
        # Читаем первые N строк
        preview_lines = []
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            for i, line in enumerate(f):
                if i >= lines:
                    break
                preview_lines.append(line.rstrip())
        
        print(f"✅ Successfully read {len(preview_lines)} lines from filtered file")
        
        return {
            "success": True,
            "file_id": file_id,
            "filtered_file_id": filtered_file_info['id'],
            "preview": preview_lines,
            "total_lines": filtered_file_info['lines_count'],
            "filter_settings": filtered_file_info['filter_settings']
        }
        
    except Exception as e:
        print(f"❌ Error in preview_filtered_file: {e}")
        print(f"❌ Error details: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/logs/files/{file_id}")
async def delete_log_file(file_id: str):
    """Удаление файла"""
    try:
        file_info = await db.get_log_file(file_id)
        if not file_info:
            raise HTTPException(status_code=404, detail="File not found")
        
        # Удаляем отфильтрованный файл если есть
        filtered_file_info = await db.get_filtered_file(file_id)
        if filtered_file_info:
            filtered_file_path = Path(filtered_file_info['filtered_file_path'])
            if filtered_file_path.exists():
                filtered_file_path.unlink()
            await db.delete_filtered_file(file_id)
        
        # Удаляем файл с диска
        file_path = Path(file_info['file_path'])
        if file_path.exists():
            file_path.unlink()
        
        # Удаляем запись из базы данных
        await db.delete_log_file(file_id)
        
        return {"success": True, "message": "File deleted successfully"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/logs/files/clear")
async def clear_all_log_files():
    """Очистка всех файлов"""
    try:
        files = await db.get_log_files()
        
        # Удаляем все файлы с диска
        for file_info in files:
            file_path = Path(file_info['file_path'])
            if file_path.exists():
                file_path.unlink()
        
        # Очищаем базу данных
        await db.clear_log_files()
        
        return {"success": True, "message": "All files cleared successfully"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/logs/analyze")
async def analyze_logs(request: Request):
    """Анализ выделенных файлов"""
    try:
        data = await request.json()
        file_ids = data.get('file_ids', [])
        system_name = data.get('system_name', 'Unknown System')
        preset_id = data.get('preset_id')
        
        if not file_ids:
            raise HTTPException(status_code=400, detail="No files selected for analysis")
        
        # Получаем настройки для фильтрации
        settings = await db.get_settings()
        important_levels = settings.get('important_log_levels', ['ERROR', 'WARN', 'CRITICAL', 'FATAL', 'ALERT', 'EMERGENCY', 'INFO', 'DEBUG'])
        
        # Анализируем каждый файл
        analysis_results = []
        for file_id in file_ids:
            file_info = await db.get_log_file(file_id)
            if not file_info:
                continue
            
            file_path = Path(file_info['file_path'])
            if not file_path.exists():
                continue
            
            # Читаем и фильтруем важные строки
            important_lines = []
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                for line_num, line in enumerate(f, 1):
                    # Улучшенная фильтрация с учетом контекста уровня лога
                    detected_level = self._detect_log_level(line, important_levels)
                    if detected_level:
                        important_lines.append({
                            'line_number': line_num,
                            'content': line.rstrip(),
                            'level': detected_level
                        })
            
            analysis_results.append({
                'file_id': file_id,
                'original_name': file_info['original_name'],
                'important_lines': important_lines,
                'total_lines': len(important_lines)
            })
        
        return {
            "success": True,
            "system_name": system_name,
            "preset_id": preset_id,
            "results": analysis_results
        }
        
    except Exception as e:
        print('Log analysis error:', traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/presets")
async def get_presets():
    """Получение пресетов с кэшированием"""
    try:
        if _cache['presets'] is None:
            _cache['presets'] = await db.get_presets()
        return {"success": True, "data": _cache['presets']}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/presets")
async def create_preset(request: Request):
    """Создание нового пресета с инвалидацией кэша"""
    try:
        data = await request.json()
        preset_id = await db.create_preset(data)
        # Инвалидируем кэш
        _cache['presets'] = None
        return {"success": True, "preset_id": preset_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/custom-analysis-settings")
async def get_custom_analysis_settings():
    """Получение пользовательских настроек с кэшированием"""
    try:
        if _cache['custom_settings'] is None:
            _cache['custom_settings'] = await db.get_custom_analysis_settings()
        return {"success": True, "data": _cache['custom_settings']}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/custom-analysis-settings")
async def create_custom_analysis_setting(request: Request):
    """Создание новой пользовательской настройки анализа"""
    try:
        data = await request.json()
        setting_id = await db.create_custom_analysis_setting(data)
        # Инвалидируем кэш пользовательских настроек
        _cache['custom_settings'] = None
        return {"success": True, "setting_id": setting_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/custom-analysis-settings/{setting_id}")
async def update_custom_analysis_setting(setting_id: str, request: Request):
    """Обновление пользовательской настройки анализа"""
    try:
        data = await request.json()
        await db.update_custom_analysis_setting(setting_id, data)
        # Инвалидируем кэш пользовательских настроек
        _cache['custom_settings'] = None
        return {"success": True, "message": "Setting updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/custom-analysis-settings/{setting_id}")
async def delete_custom_analysis_setting(setting_id: str):
    """Удаление пользовательской настройки анализа"""
    try:
        await db.delete_custom_analysis_setting(setting_id)
        # Инвалидируем кэш пользовательских настроек
        _cache['custom_settings'] = None
        return {"success": True, "message": "Setting deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/log-formats")
async def get_supported_log_formats():
    """Получение списка поддерживаемых форматов логов"""
    try:
        formats = log_detector.get_supported_formats()
        return {"success": True, "data": formats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/logs/files/{file_id}/filter")
async def filter_existing_file(file_id: str):
    """Принудительная фильтрация существующего файла"""
    try:
        file_info = await db.get_log_file(file_id)
        if not file_info:
            raise HTTPException(status_code=404, detail="File not found")
        
        file_path = Path(file_info['file_path'])
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="File not found on disk")
        
        # Фильтруем файл (пропускаем проверку размера для ручной фильтрации)
        filtered_result = await filter_log_file(file_path, file_id, db, skip_size_check=True)
        
        if filtered_result:
            return {
                "success": True,
                "message": f"File filtered successfully. Found {filtered_result['lines_count']} matching lines",
                "filtered_file_id": filtered_result['id']
            }
        else:
            return {
                "success": True,
                "message": "No matching lines found in file",
                "filtered_file_id": None
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 