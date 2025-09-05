"""
Роуты для работы с хостами
"""
import csv
import traceback
import asyncio
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException, File, UploadFile, Query
from fastapi.responses import StreamingResponse
from starlette.responses import FileResponse

from utils.file_utils import split_file_by_size, extract_compressed_file
from utils.validation_utils import is_valid_ip
from utils.progress_utils import update_import_progress, estimate_remaining_time, import_progress
from services.excel_service import create_excel_file
from database import get_db

router = APIRouter()


@router.post("/api/hosts/upload")
async def upload_hosts(file: UploadFile = File(...)):
    """Загрузить файл хостов и создать фоновую задачу для импорта"""
    try:
        print(f"🔄 Начинаем загрузку файла: {file.filename} ({file.size} байт)")
        
        # Проверяем, что файл был загружен
        if not file.filename:
            print("❌ DEBUG: Файл не выбран")
            raise HTTPException(status_code=422, detail="Файл не выбран")
        
        # Проверяем размер файла (максимум 1GB для стабильности)
        if file.size and file.size > 1024 * 1024 * 1024:  # 1GB
            raise HTTPException(status_code=400, detail="Файл слишком большой. Максимальный размер: 1GB.")
        
        # Проверяем, что файл не пустой
        if file.size == 0:
            print("❌ DEBUG: Файл пустой")
            raise HTTPException(status_code=422, detail="Файл пустой")
        
        # Проверяем тип файла (разрешаем CSV, TXT, ZIP, GZ, GZIP, TAR.GZ)
        allowed_extensions = ['.csv', '.txt', '.zip', '.gz', '.gzip', '.tar.gz']
        
        # Определяем расширение файла (учитываем составные расширения как .tar.gz)
        filename_lower = file.filename.lower()
        file_extension = ''
        if filename_lower.endswith('.tar.gz'):
            file_extension = '.tar.gz'
        elif '.' in filename_lower:
            file_extension = '.' + filename_lower.split('.')[-1]
        
        print(f"🔍 DEBUG: Расширение файла: '{file_extension}', разрешенные: {allowed_extensions}")
        if file_extension not in allowed_extensions:
            print(f"❌ DEBUG: Неподдерживаемый тип файла: '{file_extension}'")
            raise HTTPException(status_code=422, detail=f"Неподдерживаемый тип файла. Разрешены: {', '.join(allowed_extensions)}")
        
        # Загружаем файл
        content = await file.read()
        file_size_mb = len(content) / (1024 * 1024)
        print(f"📦 Файл загружен: {file_size_mb:.2f} МБ")
        
        # Сохраняем файл во временную директорию
        import os
        import tempfile
        from pathlib import Path
        
        # Создаем временную директорию для загрузок
        upload_dir = Path("/app/uploads")
        upload_dir.mkdir(exist_ok=True)
        print(f"📁 Директория для загрузок: {upload_dir}")
        
        # Генерируем уникальное имя файла
        import uuid
        file_id = str(uuid.uuid4())
        file_path = upload_dir / f"hosts_{file_id}_{file.filename}"
        
        # Сохраняем файл
        with open(file_path, "wb") as f:
            f.write(content)
        
        print(f"💾 Файл сохранен: {file_path}")
        
        # Создаем фоновую задачу для импорта
        print(f"🔧 Создаем фоновую задачу...")
        db = get_db()
        task_parameters = {
            "file_path": str(file_path),
            "filename": file.filename,
            "file_size_mb": file_size_mb
        }
        
        print(f"📋 Параметры задачи: {task_parameters}")
        
        task_id = await db.create_background_task(
            task_type="hosts_import",
            description=f"Импорт хостов из файла {file.filename}",
            parameters=task_parameters
        )
        
        print(f"✅ Создана фоновая задача {task_id} для импорта хостов")
        
        # Проверяем, что задача действительно создана
        conn = await db.get_connection()
        try:
            check_query = "SELECT id, task_type, status FROM vulnanalizer.background_tasks WHERE id = $1"
            task_check = await conn.fetchrow(check_query, task_id)
            if task_check:
                print(f"✅ Задача {task_id} подтверждена в БД: {dict(task_check)}")
            else:
                print(f"❌ Задача {task_id} не найдена в БД!")
        finally:
            await db.release_connection(conn)
        
        return {
            "success": True,
            "message": "Файл загружен. Импорт запущен в фоновом режиме.",
            "task_id": task_id,
            "file_size_mb": file_size_mb
        }
        
    except HTTPException:
        # Перебрасываем HTTP исключения как есть
        raise
    except Exception as e:
        error_msg = f"Ошибка при загрузке файла: {str(e)}"
        print(f"❌ {error_msg}")
        print(f"❌ Error details: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=error_msg)


@router.get("/api/hosts/status")
async def hosts_status():
    """Получить статус хостов"""
    try:
        db = get_db()
        count = await db.count_hosts_records()
        return {"success": True, "count": count}
    except Exception as e:
        print('Hosts status error:', traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/hosts/import-progress")
async def get_import_progress():
    """Получить текущий прогресс импорта хостов"""
    try:
        db = get_db()
        
        # Получаем последнюю активную задачу импорта хостов
        conn = await db.get_connection()
        
        query = """
            SELECT id, task_type, status, current_step, total_items, processed_items,
                   total_records, processed_records, updated_records, start_time, end_time, error_message, 
                   cancelled, parameters, description, created_at, updated_at
            FROM vulnanalizer.background_tasks 
            WHERE task_type = 'hosts_import' 
            AND status IN ('running', 'processing', 'initializing')
            ORDER BY created_at DESC
            LIMIT 1
        """
        
        task = await conn.fetchrow(query)
        
        if not task:
            # Если нет активных задач, возвращаем статус idle
            return {
                "status": "idle",
                "current_step": "Нет активных задач импорта",
                "progress": 0,
                "total_steps": 0,
                "current_step_progress": 0,
                "total_records": 0,
                "processed_records": 0,
                "error_message": None,
                "estimated_time": None,
                "total_parts": 0,
                "current_part": 0,
                "total_files_processed": 0,
                "current_file_records": 0,
                "overall_progress": 0
            }
        
        # Рассчитываем прогресс с учетом этапов
        progress_percent = 0
        current_step = task['current_step'] or 'Инициализация...'
        
        if task['status'] == 'completed':
            progress_percent = 100
        elif task['total_records'] and task['total_records'] > 0:
            # Используем processed_records для более точного расчета
            processed = task['processed_records'] or 0
            total = task['total_records']
            
            # Определяем этап на основе current_step
            if 'Этап 1/3' in current_step or 'Очистка' in current_step:
                progress_percent = min(5, (processed / total) * 5)
            elif 'Этап 2/3' in current_step or 'Сохранение' in current_step:
                base_progress = 5 + (processed / total) * 70  # 5-75%
                progress_percent = min(75, base_progress)
            elif 'Этап 3/3' in current_step or 'Расчет рисков' in current_step:
                # На этапе расчета рисков processed показывает количество CVE, а не записей
                # Используем фиксированный прогресс от 75% до 95%
                if 'Запуск параллельной обработки' in current_step:
                    progress_percent = 75
                elif 'Расчет рисков...' in current_step:
                    # Извлекаем прогресс из строки "Расчет рисков... (X/Y CVE)"
                    import re
                    match = re.search(r'\((\d+)/(\d+)\)', current_step)
                    if match:
                        current_cve = int(match.group(1))
                        total_cve = int(match.group(2))
                        if total_cve > 0:
                            cve_progress = (current_cve / total_cve) * 20  # 20% за расчет рисков
                            progress_percent = 75 + cve_progress
                        else:
                            progress_percent = 75
                    else:
                        progress_percent = 75
                elif 'Параллельная обработка завершена' in current_step:
                    progress_percent = 95
                else:
                    progress_percent = 75
            else:
                # Fallback на стандартный расчет
                progress_percent = min(100, (processed / total) * 100)
        elif task['total_items'] and task['total_items'] > 0:
            progress_percent = min(100, (task['processed_items'] / task['total_items']) * 100)
        
        # Рассчитываем оставшееся время
        estimated_time = None
        if (task['start_time'] and 
            task['processed_records'] and task['processed_records'] > 0 and 
            task['total_records'] and task['total_records'] > 0):
            estimated_time = estimate_remaining_time(
                task['start_time'],
                task['processed_records'],
                task['total_records']
            )
        
        # Парсим параметры для получения информации о файле
        import json
        parameters = {}
        if task['parameters']:
            try:
                parameters = json.loads(task['parameters'])
            except:
                parameters = {}
        
        filename = parameters.get('filename', 'Неизвестный файл')
        file_size_mb = parameters.get('file_size_mb', 0)
        
        # Формируем детальное описание текущего шага
        current_step = task['current_step'] or 'Инициализация...'
        if filename and filename != 'Неизвестный файл':
            current_step = f"Обработка файла {filename}: {current_step}"
        
        return {
            "status": task['status'],
            "current_step": current_step,
            "progress": progress_percent,
            "total_steps": task['total_items'] or 0,
            "current_step_progress": task['processed_items'] or 0,
            "total_records": task['total_records'] or 0,
            "processed_records": 0,  # Убираем отображение "Обработано записей"
            "error_message": task['error_message'],
            "estimated_time": estimated_time,
            "total_parts": task['total_items'] or 0,
            "current_part": task['processed_items'] or 0,
            "total_files_processed": task['processed_items'] or 0,
            "current_file_records": task['processed_records'] or 0,
            "overall_progress": progress_percent,
            "filename": filename,
            "file_size_mb": file_size_mb,
            "task_id": task['id']
        }
        
    except Exception as e:
        print(f"Error getting import progress: {e}")
        return {
            "status": "error",
            "current_step": "Ошибка получения прогресса",
            "progress": 0,
            "total_steps": 0,
            "current_step_progress": 0,
            "total_records": 0,
            "processed_records": 0,
            "error_message": str(e),
            "estimated_time": None,
            "total_parts": 0,
            "current_part": 0,
            "total_files_processed": 0,
            "current_file_records": 0,
            "overall_progress": 0
        }
    finally:
        await db.release_connection(conn)


@router.get("/api/hosts/import-limits")
async def get_import_limits():
    """Получить информацию о лимитах импорта"""
    return {
        "max_file_size_mb": 1024,  # 1GB
        "max_processing_time_minutes": 10,
        "recommended_file_size_mb": 100,
        "auto_split_size_mb": 100,
        "message": "Файлы больше 100 МБ автоматически разделяются на части по 100 МБ"
    }


@router.get("/api/hosts/search")
async def search_hosts(
    hostname: str = None,
    cve: str = None,
    ip_address: str = None,
    criticality: str = None,
    exploits_only: bool = False,
    epss_only: bool = False,
    sort_by: str = None,
    limit: int = 100,
    page: int = 1
):
    """Поиск хостов"""
    try:
        db = get_db()
        results, total_count = await db.search_hosts(
            hostname_pattern=hostname,
            cve=cve,
            ip_address=ip_address,
            criticality=criticality,
            exploits_only=exploits_only,
            epss_only=epss_only,
            sort_by=sort_by,
            limit=limit,
            page=page
        )
        return {
            "success": True, 
            "results": results,
            "total_count": total_count,
            "page": page,
            "limit": limit,
            "total_pages": (total_count + limit - 1) // limit
        }
    except Exception as e:
        print('Hosts search error:', traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))





@router.post("/api/hosts/update-data-background")
async def start_background_update():
    """Запустить фоновое обновление данных хостов"""
    try:
        db = get_db()
        
        # Проверяем, не запущена ли уже задача
        existing_task = await db.get_background_task_by_type('hosts_update')
        if existing_task and existing_task['status'] in ['processing', 'inserting']:
            return {"success": False, "message": "Обновление уже запущено"}
        
        # Создаем фоновую задачу для планировщика
        task_id = await db.create_background_task(
            task_type="hosts_update",
            parameters={
                "max_concurrent": 5,
                "update_type": "sequential"
            },
            description="Последовательное обновление данных хостов"
        )
        
        return {
            "success": True,
            "message": f"Задача обновления создана (ID: {task_id}). Обработка начнется автоматически.",
            "task_id": task_id
        }
        
    except Exception as e:
        print('Background update error:', traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/hosts/update-data-progress")
async def get_background_update_progress():
    """Получить прогресс фонового обновления данных"""
    try:
        db = get_db()
        task = await db.get_background_task_by_type('hosts_update')
        
        if not task:
            return {
                "status": "idle",
                "current_step": "Нет активных задач",
                "total_cves": 0,
                "processed_cves": 0,
                "total_hosts": 0,
                "updated_hosts": 0,
                "progress_percent": 0,
                "estimated_time_seconds": None,
                "start_time": None,
                "error_message": None
            }
        
        # Парсим информацию из сообщения для обратной совместимости
        total_cves = 0
        processed_cves = 0
        updated_hosts = 0
        
        if task.get('message'):
            import re
            # Формат: "Обработано 350 из 1,000 CVE (35.0%)"
            processed_match = re.search(r'Обработано ([\d,]+) из ([\d,]+) CVE', task['message'])
            if processed_match:
                processed_cves = int(processed_match.group(1).replace(',', ''))
                total_cves = int(processed_match.group(2).replace(',', ''))
            
            # Формат: "обновлено 33,320 записей хостов"
            hosts_match = re.search(r'обновлено ([\d,]+) записей хостов', task['message'])
            if hosts_match:
                updated_hosts = int(hosts_match.group(1).replace(',', ''))
        
        return {
            "status": task['status'],
            "current_step": task.get('current_step', 'Инициализация...'),
            "total_cves": task.get('total_items', 0),
            "processed_cves": task.get('processed_items', 0),
            "total_hosts": task.get('total_records', 0),
            "updated_hosts": task.get('updated_records', 0),
            "progress_percent": task.get('progress_percent', 0),
            "estimated_time_seconds": None,  # Убрали расчет времени
            "start_time": task.get('start_time').isoformat() if task.get('start_time') else task.get('created_at').isoformat() if task.get('created_at') else None,
            "error_message": task.get('error_message')
        }
    except Exception as e:
        print('Error getting background update progress:', e)
        return {
            "status": "error",
            "current_step": "Ошибка получения прогресса",
            "total_cves": 0,
            "processed_cves": 0,
            "total_hosts": 0,
            "updated_hosts": 0,
            "progress_percent": 0,
            "estimated_time_seconds": None,
            "start_time": None,
            "error_message": str(e)
        }


@router.post("/api/hosts/update-data-cancel")
async def cancel_background_update():
    """Отменить фоновое обновление данных"""
    try:
        db = get_db()
        
        # Отменяем задачу в базе данных
        cancelled = await db.cancel_background_task('hosts_update')
        
        if cancelled:
            return {"success": True, "message": "Обновление отменено"}
        else:
            return {"success": False, "message": "Нет активного процесса обновления"}
    except Exception as e:
        print('Error cancelling background update:', e)
        return {"success": False, "message": f"Ошибка отмены: {str(e)}"}


@router.post("/api/hosts/update-data-background-parallel")
async def start_background_update_parallel():
    """Запустить фоновое обновление данных хостов с параллельной обработкой"""
    try:
        db = get_db()
        
        # Проверяем, не запущена ли уже задача
        existing_task = await db.get_background_task_by_type('hosts_update')
        if existing_task and existing_task['status'] in ['processing', 'inserting', 'running', 'initializing']:
            return {"success": False, "message": "Обновление уже запущено"}
        
        # Создаем фоновую задачу для воркера
        task_id = await db.create_background_task(
            task_type="hosts_update",
            parameters={
                "max_concurrent": 10,
                "update_type": "parallel"
            },
            description="Параллельное обновление данных хостов"
        )
        
        print(f"✅ Фоновая задача обновления создана: {task_id}")
        
        return {
            "success": True,
            "task_id": task_id,
            "message": "Обновление данных хостов запущено в фоновом режиме"
        }
        
    except Exception as e:
        print('Background update error:', traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/hosts/calculate-missing-risks")
async def calculate_missing_risks():
    """Рассчитать риски для всех хостов, которые их не имеют"""
    try:
        db = get_db()
        
        # Проверяем, не запущена ли уже задача
        existing_task = await db.get_background_task_by_type('risk_calculation')
        if existing_task and existing_task['status'] in ['processing', 'running']:
            return {"success": False, "message": "Расчет рисков уже запущен"}
        
        # Создаем фоновую задачу для расчета рисков
        task_id = await db.create_background_task(
            task_type="risk_calculation",
            parameters={
                "calculation_type": "missing_risks"
            },
            description="Расчет рисков для хостов без EPSS и Risk данных"
        )
        
        print(f"✅ Фоновая задача расчета рисков создана: {task_id}")
        
        return {
            "success": True,
            "task_id": task_id,
            "message": "Расчет рисков для хостов без данных запущен в фоновом режиме"
        }
        
    except Exception as e:
        print('Risk calculation error:', traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/hosts/recalculate-all-risks")
async def recalculate_all_risks():
    """Пересчитать риски для ВСЕХ хостов по новой формуле"""
    try:
        db = get_db()
        
        # Проверяем, не запущена ли уже задача
        existing_task = await db.get_background_task_by_type('risk_recalculation')
        if existing_task and existing_task['status'] in ['processing', 'running']:
            return {"success": False, "message": "Пересчет рисков уже запущен"}
        
        # Создаем фоновую задачу для пересчета рисков
        task_id = await db.create_background_task(
            task_type="risk_recalculation",
            parameters={
                "calculation_type": "recalculate_all"
            },
            description="Пересчет рисков для всех хостов по новой формуле"
        )
        
        print(f"✅ Фоновая задача пересчета рисков создана: {task_id}")
        
        return {
            "success": True,
            "task_id": task_id,
            "message": "Пересчет рисков для всех хостов запущен в фоновом режиме"
        }
        
    except Exception as e:
        print('Risk recalculation error:', traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/hosts/update-data-optimized")
async def start_optimized_update():
    """Запустить оптимизированное обновление данных хостов (batch запросы)"""
    try:
        db = get_db()
        
        # Проверяем, не запущена ли уже задача
        existing_task = await db.get_background_task_by_type('hosts_update')
        if existing_task and existing_task['status'] in ['processing', 'inserting']:
            return {"success": False, "message": "Обновление уже запущено"}
        
        # Создаем фоновую задачу для воркера
        task_id = await db.create_background_task(
            task_type="hosts_update",
            parameters={
                "update_type": "optimized_batch"
            },
            description="Оптимизированное обновление данных хостов (batch запросы)"
        )
        
        print(f"✅ Фоновая задача оптимизированного обновления создана: {task_id}")
        
        return {
            "success": True,
            "task_id": task_id,
            "message": "Оптимизированное обновление данных хостов запущено в фоновом режиме"
        }
        
    except Exception as e:
        print('Optimized update error:', traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))
@router.get("/api/hosts/{host_id}/risk")
async def calculate_host_risk(host_id: int):
    """Рассчитать риск для конкретного хоста"""
    try:
        db = get_db()
        
        # Получаем данные хоста
        host_data = await db.get_host_by_id(host_id)
        if not host_data:
            raise HTTPException(status_code=404, detail="Хост не найден")
        
        # Получаем настройки
        try:
            with open("data/settings.json", "r", encoding="utf-8") as f:
                import json
                settings = json.load(f)
        except FileNotFoundError:
            settings = {
                "impact_resource_criticality": "Medium",
                "impact_confidential_data": "Отсутствуют",
                "impact_internet_access": "Недоступен"
            }
        
        # Рассчитываем риск
        from database.risk_calculation import calculate_risk_score
        risk_result = calculate_risk_score(
            epss=host_data.get('epss'),
            cvss=host_data.get('cvss'),
            criticality=host_data.get('criticality', 'Medium'),
            settings=settings,
            cve_data=cve_data,
            confidential_data=host_data.get('confidential_data', False),
            internet_access=host_data.get('internet_access', False)
        )
        
        return {
            "success": True,
            "host_id": host_id,
            "hostname": host_data.get('hostname'),
            "cve": host_data.get('cve'),
            "epss": host_data.get('epss'),
            "cvss": host_data.get('cvss'),
            "risk_calculation": risk_result
        }
    except HTTPException:
        raise
    except Exception as e:
        print('Host risk calculation error:', traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/hosts/export")
async def export_hosts(
    hostname: str = None,
    cve: str = None,
    ip_address: str = None,
    criticality: str = None,
    exploits_only: bool = False,
    epss_only: bool = False
):
    """Экспорт хостов в Excel"""
    try:
        db = get_db()
        
        # Получаем данные хостов
        hosts_data, _ = await db.search_hosts(
            hostname_pattern=hostname,
            cve=cve,
            ip_address=ip_address,
            criticality=criticality,
            exploits_only=exploits_only,
            epss_only=epss_only,
            limit=1000  # Большой лимит для экспорта
        )
        
        if not hosts_data:
            raise HTTPException(status_code=404, detail="Данные для экспорта не найдены")
        
        # Создаем Excel файл
        excel_file = create_excel_file(hosts_data)
        
        # Возвращаем файл для скачивания
        return StreamingResponse(
            excel_file,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=hosts_export.xlsx"}
        )
    except HTTPException:
        raise
    except Exception as e:
        print('Hosts export error:', traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/hosts/export-report")
async def export_hosts_report(
    format: str = "excel",
    filters: dict = None,
    include_charts: bool = True
):
    """Экспорт отчета по хостам"""
    try:
        db = get_db()
        
        # Применяем фильтры
        where_conditions = []
        params = []
        param_count = 0
        
        if filters:
            if filters.get('hostname'):
                param_count += 1
                where_conditions.append(f"hostname ILIKE ${param_count}")
                params.append(f"%{filters['hostname']}%")
            
            if filters.get('cve'):
                param_count += 1
                where_conditions.append(f"cve ILIKE ${param_count}")
                params.append(f"%{filters['cve']}%")
            
            if filters.get('criticality'):
                param_count += 1
                where_conditions.append(f"criticality = ${param_count}")
                params.append(filters['criticality'])
            
            if filters.get('min_risk'):
                param_count += 1
                where_conditions.append(f"risk_score >= ${param_count}")
                params.append(filters['min_risk'])
            
            if filters.get('has_exploits'):
                where_conditions.append("has_exploits = TRUE")
        
        where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"
        
        # Получаем данные
        query = f"""
            SELECT 
                hostname, ip_address, cve, cvss, cvss_source, criticality, 
                status, os_name, zone, epss_score, epss_percentile, 
                risk_score, exploits_count, has_exploits, last_exploit_date,
                epss_updated_at, exploits_updated_at, risk_updated_at
            FROM vulnanalizer.hosts 
            WHERE {where_clause}
            ORDER BY risk_score DESC NULLS LAST, hostname, cve
        """
        
        conn = await db.get_connection()
        rows = await conn.fetch(query, *params)
        
        if format.lower() == "excel":
            # Создаем Excel файл
            from services.excel_service import create_excel_report
            
            filename = f"vulnanalizer_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            file_path = await create_excel_report(rows, filename, include_charts)
            
            return FileResponse(
                file_path,
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                filename=filename
            )
        
        elif format.lower() == "csv":
            # Создаем CSV файл
            import csv
            import tempfile
            
            filename = f"vulnanalizer_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv')
            
            with temp_file:
                writer = csv.writer(temp_file)
                # Заголовки
                writer.writerow([
                    'Hostname', 'IP Address', 'CVE', 'CVSS', 'CVSS Source', 
                    'Criticality', 'Status', 'OS', 'Zone', 'EPSS Score', 
                    'EPSS Percentile', 'Risk Score', 'Exploits Count', 
                    'Has Exploits', 'Last Exploit Date'
                ])
                
                # Данные
                for row in rows:
                    writer.writerow([
                        row['hostname'], row['ip_address'], row['cve'], 
                        row['cvss'], row['cvss_source'], row['criticality'],
                        row['status'], row['os_name'], row['zone'], 
                        row['epss_score'], row['epss_percentile'], row['risk_score'],
                        row['exploits_count'], row['has_exploits'], row['last_exploit_date']
                    ])
            
            return FileResponse(
                temp_file.name,
                media_type="text/csv",
                filename=filename
            )
        
        elif format.lower() == "json":
            # Возвращаем JSON
            return {
                "success": True,
                "data": [dict(row) for row in rows],
                "total_count": len(rows),
                "exported_at": datetime.now().isoformat()
            }
        
        else:
            raise HTTPException(status_code=400, detail="Неподдерживаемый формат экспорта")
            
    except Exception as e:
        print(f"Error exporting report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/hosts/{host_id}/risk-calculation/{cve}")
async def get_host_risk_calculation(host_id: int, cve: str):
    """Получить детали расчета риска для конкретного хоста и CVE"""
    print(f"🔍 Risk calculation request: host_id={host_id}, cve={cve}")
    try:
        db = get_db()
        conn = await db.get_connection()
        
        try:
            # Получаем основную информацию о хосте и CVE
            query = """
                SELECT 
                    h.hostname, h.ip_address, h.criticality, h.risk_score,
                    h.cvss, h.cvss_source, h.epss_score, h.exploits_count,
                    h.epss_updated_at, h.exploits_updated_at, h.risk_updated_at,
                    c.description as cve_description
                FROM vulnanalizer.hosts h
                LEFT JOIN vulnanalizer.cve c ON h.cve = c.cve_id
                WHERE h.id = $1 AND h.cve = $2
            """
            
            print(f"🔍 Executing query: {query}")
            print(f"🔍 Parameters: host_id={host_id}, cve={cve}")
            row = await conn.fetchrow(query, host_id, cve)
            
            if not row:
                print(f"❌ No data found for host_id={host_id}, cve={cve}")
                raise HTTPException(status_code=404, detail="Хост или CVE не найдены")
            
            print(f"✅ Found data: {dict(row) if row else 'None'}")
            
            # Формируем данные о риске
            risk_data = {
                "hostname": row['hostname'],
                "ip_address": row['ip_address'],
                "criticality": row['criticality'],
                "risk_score": row['risk_score'],
                "cvss_score": row['cvss'],
                "cvss_severity": row['cvss_source'],
                "epss_score": row['epss_score'],
                "exploits_count": row['exploits_count'],
                "metasploit_rank": None,  # Убираем Metasploit, так как таблица не существует
                "cve_description": row['cve_description'],
                "epss_updated_at": row['epss_updated_at'],
                "exploits_updated_at": row['exploits_updated_at'],
                "risk_updated_at": row['risk_updated_at']
            }
            
            # Добавляем детали расчета из сервиса риска
            try:
                from services.risk_service import get_risk_calculation_details
                calculation_details = await get_risk_calculation_details(host_id, cve)
                if calculation_details:
                    risk_data.update(calculation_details)
                    print(f"✅ Added calculation details: {calculation_details}")
                else:
                    print(f"⚠️ No calculation details available")
            except Exception as e:
                print(f"⚠️ Error getting calculation details: {e}")
                # Если сервис недоступен, используем базовые данные
                pass
            
            return {
                "success": True,
                "risk_data": risk_data
            }
            
        finally:
            await db.release_connection(conn)
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error getting risk calculation: {e}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail="Ошибка получения данных о риске")


@router.get("/api/hosts/test-endpoint")
async def test_endpoint():
    """Тестовый endpoint для проверки работы роутера"""
    return {"success": True, "message": "Hosts router работает", "timestamp": datetime.now().isoformat()}

@router.get("/api/hosts/test-risk")
async def test_risk_endpoint():
    """Тестовый endpoint для проверки risk-calculation"""
    return {"success": True, "message": "Risk endpoint доступен", "timestamp": datetime.now().isoformat()}

@router.post("/api/hosts/clear")
async def clear_hosts():
    """Очистить все записи хостов"""
    try:
        db = get_db()
        await db.clear_hosts()
        return {"success": True, "message": "Все записи хостов удалены"}
    except Exception as e:
        print('Hosts clear error:', traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))



