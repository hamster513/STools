"""
Роуты для работы с хостами
"""
import csv
import traceback
import asyncio
import os
import uuid
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException, File, UploadFile, Query
from fastapi.responses import StreamingResponse
from starlette.responses import FileResponse

from utils.file_utils import split_file_by_size, extract_compressed_file
from utils.validation_utils import is_valid_ip
from utils.progress_utils import update_import_progress, estimate_remaining_time, import_progress
from services.risk_service import calculate_risk_score
from services.excel_service import create_excel_file
from database import get_db

router = APIRouter()


@router.post("/api/hosts/upload")
async def upload_hosts(file: UploadFile = File(...)):
    """Загрузить файл и создать фоновую задачу для обработки"""
    try:
        print(f"🔄 Начинаем загрузку файла: {file.filename} ({file.size} байт)")
        
        # Проверяем размер файла (максимум 1GB для стабильности)
        if file.size and file.size > 1024 * 1024 * 1024:  # 1GB
            error_msg = "Файл слишком большой. Максимальный размер: 1GB."
            raise HTTPException(status_code=400, detail=error_msg)
        
        # Создаем уникальное имя файла
        import uuid
        file_id = str(uuid.uuid4())
        file_extension = os.path.splitext(file.filename)[1] if file.filename else '.csv'
        safe_filename = f"{file_id}{file_extension}"
        
        # Путь для сохранения файла в воркере
        worker_file_path = f"/app/uploads/{safe_filename}"
        
        # Сохраняем файл на диск
        upload_dir = "/app/uploads"
        os.makedirs(upload_dir, exist_ok=True)
        file_path = os.path.join(upload_dir, safe_filename)
        
        try:
            content = await file.read()
            with open(file_path, 'wb') as f:
                f.write(content)
            
            file_size_mb = len(content) / (1024 * 1024)
            print(f"📦 Файл сохранен на диск: {file_path} ({file_size_mb:.2f} МБ)")
        except Exception as save_error:
            error_msg = f"Ошибка при сохранении файла: {str(save_error)}"
            raise HTTPException(status_code=500, detail=error_msg)
        
        # Определяем, является ли файл архивом
        is_archive = file.filename.lower().endswith(('.zip', '.gz', '.gzip'))
        
        if is_archive:
            # Шаг 2: Распаковка архива
            update_import_progress('extracting', 'Распаковка архива...')
            try:
                decoded_content = extract_compressed_file(content, file.filename)
                decoded_size_mb = len(decoded_content.encode('utf-8')) / (1024 * 1024)
                print(f"🔓 Архив распакован: {decoded_size_mb:.2f} МБ")
            except Exception as extract_error:
                error_msg = f"Ошибка при распаковке архива: {str(extract_error)}"
                update_import_progress('error', error_msg, error_message=error_msg)
                raise HTTPException(status_code=400, detail=error_msg)
        else:
            # Если не архив, используем содержимое как есть
            decoded_content = content.decode('utf-8-sig')
            decoded_size_mb = len(decoded_content.encode('utf-8')) / (1024 * 1024)
            print(f"📄 Файл не является архивом: {decoded_size_mb:.2f} МБ")
        
        # Шаг 3: Проверяем размер распакованного файла и разделяем если нужно
        if decoded_size_mb > 100:
            update_import_progress('splitting', f'Файл большой ({decoded_size_mb:.1f} МБ), разделяем на части по 100 МБ...')
            try:
                parts = split_file_by_size(decoded_content, 100)
                total_parts = len(parts)
                print(f"✂️ Файл разделен на {total_parts} частей по 100 МБ")
                update_import_progress('splitting', f'Файл разделен на {total_parts} частей по 100 МБ', total_parts=total_parts)
            except Exception as split_error:
                error_msg = f"Ошибка при разделении файла: {str(split_error)}"
                update_import_progress('error', error_msg, error_message=error_msg)
                raise HTTPException(status_code=400, detail=error_msg)
        else:
            # Файл не нужно разделять
            parts = [decoded_content]
            total_parts = 1
            update_import_progress('processing', 'Файл готов к обработке', total_parts=total_parts)
        
        # Шаг 4: Обработка каждой части
        total_records = 0
        total_processed_lines = 0
        db = get_db()
        
        # Логируем память перед началом обработки
        try:
            from main import log_memory_usage
            log_memory_usage()
        except ImportError:
            print("💾 Memory logging not available")
        
        print(f"🚀 Начинаем обработку {len(parts)} частей файла")
        print(f"📊 Общий размер данных: {sum(len(part.encode('utf-8')) for part in parts) / (1024*1024):.2f} МБ")
        
        for part_index, part_content in enumerate(parts, 1):
            try:
                current_part = part_index
                part_start_time = datetime.now()
                
                # Проверяем общее время выполнения (максимум 30 минут на весь импорт)
                if part_index > 1:
                    total_elapsed = (datetime.now() - import_start_time).total_seconds()
                    if total_elapsed > 1800:  # 30 минут
                        error_msg = f"Превышено общее время импорта (30 минут). Обработано {part_index-1} из {total_parts} частей."
                        update_import_progress('error', error_msg, error_message=error_msg)
                        raise HTTPException(status_code=408, detail=error_msg)
                print(f"📋 Начинаем обработку части {current_part} из {total_parts}")
                print(f"📊 Размер части {current_part}: {len(part_content.encode('utf-8')) / (1024*1024):.2f} МБ")
                update_import_progress('processing', f'Обработка файла {current_part} из {total_parts}...', 
                                     current_part=current_part)
                
                print(f"📋 Обрабатываем файл {current_part} из {total_parts}")
                
                # Парсим текущую часть
                part_lines = part_content.splitlines()
                part_total_lines = len(part_lines)
                
                # Парсим CSV с разделителем ;
                reader = csv.DictReader(part_lines, delimiter=';')
                
                part_records = []
                part_processed_lines = 0
                batch_size = 1000
                start_time = datetime.now()
                
                for row in reader:
                    try:
                        # Проверяем время выполнения (максимум 10 минут на файл)
                        if (datetime.now() - start_time).total_seconds() > 600:  # 10 минут
                            error_msg = f"Превышено время обработки файла {current_part} (10 минут). Попробуйте файл меньшего размера."
                            update_import_progress('error', error_msg, error_message=error_msg)
                            raise HTTPException(status_code=408, detail=error_msg)
                        
                        # Парсим hostname и IP из поля @Host
                        host_info = row['@Host'].strip('"')
                        hostname = host_info.split(' (')[0] if ' (' in host_info else host_info
                        ip_address = host_info.split('(')[1].split(')')[0] if ' (' in host_info else ''
                        
                        # Проверяем валидность IP адреса
                        if ip_address and not is_valid_ip(ip_address):
                            print(f"⚠️ Пропускаем запись с невалидным IP: {ip_address}")
                            part_processed_lines += 1
                            continue
                        
                        # Получаем данные из полей
                        cve = row['Host.@Vulners.CVEs'].strip('"')
                        criticality = row['host.UF_Criticality'].strip('"')
                        zone = row['Host.UF_Zone'].strip('"')
                        os_name = row['Host.OsName'].strip('"')
                        status = 'Active'
                        
                        # Пропускаем записи с пустыми CVE
                        if not cve or cve == '' or cve == '""':
                            print(f"⚠️ Пропускаем запись с пустым CVE для хоста: {hostname} ({ip_address})")
                            part_processed_lines += 1
                            continue
                        
                        part_records.append({
                            'hostname': hostname,
                            'ip_address': ip_address,
                            'cve': cve,
                            'cvss': None,
                            'criticality': criticality,
                            'status': status,
                            'os_name': os_name,
                            'zone': zone
                        })
                        
                        part_processed_lines += 1
                        
                        # Обновляем прогресс каждые batch_size строк
                        if part_processed_lines % batch_size == 0:
                            update_import_progress('processing', 
                                                 f'Файл {current_part}/{total_parts}: {part_processed_lines:,}/{part_total_lines:,} строк', 
                                                 processed_records=part_processed_lines, total_records=part_total_lines,
                                                 current_file_records=len(part_records))
                            print(f"📊 Часть {current_part}: {part_processed_lines:,}/{part_total_lines:,} строк, {len(part_records):,} записей")
                        
                    except HTTPException:
                        raise
                    except Exception as row_error:
                        print(f"⚠️ Ошибка обработки строки {part_processed_lines} в файле {current_part}: {row_error}")
                        part_processed_lines += 1
                        continue
                
                print(f"✅ Файл {current_part} обработан: {len(part_records):,} записей")
                
                # Шаг 5: Вставка файла в базу данных
                print(f"💾 Готовимся к вставке {len(part_records):,} записей в базу данных")
                try:
                    log_memory_usage()
                except NameError:
                    print("💾 Memory logging not available")
                update_import_progress('inserting', f'Сохранение файла {current_part} из {total_parts}...', 
                                     current_file_records=len(part_records))
                
                try:
                    print(f"🔄 Начинаем вставку записей в базу данных...")
                    await db.insert_hosts_records_with_progress(part_records, update_import_progress)
                    print(f"✅ Вставка записей завершена успешно")
                    print(f"💾 Файл {current_part} сохранен в базу данных")
                    
                except Exception as db_error:
                    error_msg = f"Ошибка при сохранении файла {current_part}: {str(db_error)}"
                    update_import_progress('error', error_msg, error_message=error_msg)
                    raise HTTPException(status_code=500, detail=error_msg)
                
                # Обновляем общие счетчики
                total_records += len(part_records)
                total_processed_lines += part_processed_lines
                
                # Обновляем прогресс
                update_import_progress('processing', f'Файл {current_part} из {total_parts} завершен', 
                                     total_records=total_records, processed_records=total_processed_lines, total_files_processed=current_part)
                
                # Логируем память после обработки части
                try:
                    log_memory_usage()
                except NameError:
                    print("💾 Memory logging not available")
                
            except HTTPException:
                raise
            except Exception as part_error:
                error_msg = f"Ошибка при обработке файла {current_part}: {str(part_error)}"
                update_import_progress('error', error_msg, error_message=error_msg)
                raise HTTPException(status_code=500, detail=error_msg)
        
        # Завершение
        update_import_progress('completed', 'Импорт завершен', total_records=total_records, processed_records=total_processed_lines, 
                              total_files_processed=total_parts)
        print(f"🎉 Импорт успешно завершен: {total_records:,} записей из {total_processed_lines:,} строк в {total_parts} файлах")
        
        return {
            "success": True, 
            "count": total_records, 
            "total_processed": total_processed_lines,
            "total_parts": total_parts,
            "message": f"Файл автоматически разделен на {total_parts} файлов по 100 МБ и успешно импортирован"
        }
        
    except HTTPException:
        # Перебрасываем HTTP исключения как есть
        raise
    except Exception as e:
        error_msg = f"Неожиданная ошибка при импорте: {str(e)}"
        update_import_progress('error', error_msg, error_message=error_msg)
        print(f'❌ Hosts upload error: {traceback.format_exc()}')
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
    global import_progress
    
    # Рассчитываем оставшееся время
    estimated_time = None
    if (import_progress['start_time'] and 
        import_progress['processed_records'] > 0 and 
        import_progress['total_records'] > 0):
        estimated_time = estimate_remaining_time(
            import_progress['start_time'],
            import_progress['processed_records'],
            import_progress['total_records']
        )
    
    # Рассчитываем правильный процент прогресса
    overall_progress = 0
    if import_progress['total_records'] > 0:
        overall_progress = min(100, (import_progress['processed_records'] / import_progress['total_records']) * 100)
    
    # Формируем информацию о текущем файле
    current_file_info = ""
    if import_progress['current_part'] and import_progress['total_parts']:
        current_file_info = f"Файл {import_progress['current_part']} из {import_progress['total_parts']}"
    
    # Формируем детальное описание текущего шага
    detailed_step = import_progress['current_step']
    if current_file_info:
        detailed_step = f"{current_file_info}: {import_progress['current_step']}"
    
    return {
        "status": import_progress['status'],
        "current_step": detailed_step,
        "progress": overall_progress,
        "total_steps": import_progress['total_steps'],
        "current_step_progress": import_progress['current_step_progress'],
        "total_records": import_progress['total_records'],
        "processed_records": import_progress['processed_records'],
        "error_message": import_progress['error_message'],
        "estimated_time": estimated_time,
        "total_parts": import_progress['total_parts'],
        "current_part": import_progress['current_part'],
        "total_files_processed": import_progress['total_files_processed'],
        "current_file_records": import_progress['current_file_records'],
        "current_file_info": current_file_info,
        "overall_progress": overall_progress
    }


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
        results, total_count = await db.search_hosts(hostname, cve, ip_address, criticality, exploits_only, epss_only, sort_by, limit, page)
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
        existing_task = await db.get_background_task('hosts_update')
        if existing_task and existing_task['status'] in ['processing', 'initializing']:
            return {"success": False, "message": "Обновление уже запущено"}
        
        # Создаем новую задачу
        task_id = await db.create_background_task('hosts_update')
        
        def progress_callback(status, step, **kwargs):
            # Обновляем задачу в базе данных
            asyncio.create_task(db.update_background_task(task_id, 
                status=status, 
                current_step=step,
                total_items=kwargs.get('total_cves', 0),
                processed_items=kwargs.get('processed_cves', 0),
                total_records=kwargs.get('total_hosts', 0),
                updated_records=kwargs.get('updated_hosts', 0)
            ))
        
        # Запускаем фоновое обновление
        result = await db.update_hosts_epss_and_exploits_background(progress_callback)
        
        # Обновляем финальный статус в базе данных
        if result['success']:
            # Проверяем, не была ли задача отменена
            if 'отменено' in result.get('message', '').lower():
                await db.update_background_task(task_id, 
                    status='cancelled', 
                    current_step='Отменено пользователем',
                    total_items=result.get('processed_cves', 0),
                    processed_items=result.get('processed_cves', 0),
                    total_records=result.get('updated_count', 0),
                    updated_records=result.get('updated_count', 0)
                )
            else:
                await db.update_background_task(task_id, 
                    status='completed', 
                    current_step='Завершено',
                    total_items=result.get('processed_cves', 0),
                    processed_items=result.get('processed_cves', 0),
                    total_records=result.get('updated_count', 0),
                    updated_records=result.get('updated_count', 0)
                )
        else:
            await db.update_background_task(task_id, 
                status='error', 
                current_step='Ошибка',
                error_message=result.get('message', 'Неизвестная ошибка')
            )
        
        return result
        
    except Exception as e:
        print('Background update error:', traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/hosts/update-data-progress")
async def get_background_update_progress():
    """Получить прогресс фонового обновления данных"""
    try:
        db = get_db()
        task = await db.get_background_task('hosts_update')
        
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
        
        # Рассчитываем оставшееся время
        estimated_time = None
        if (task['start_time'] and 
            task['processed_items'] > 0 and 
            task['total_items'] > 0):
            
            elapsed = (datetime.now() - task['start_time']).total_seconds()
            if elapsed > 0:
                rate = task['processed_items'] / elapsed
                remaining_items = task['total_items'] - task['processed_items']
                estimated_time = remaining_items / rate if rate > 0 else None
        
        # Рассчитываем процент прогресса
        progress_percent = 0
        if task['total_items'] > 0:
            progress_percent = (task['processed_items'] / task['total_items']) * 100
        
        return {
            "status": task['status'],
            "current_step": task['current_step'] or "Инициализация...",
            "total_cves": task['total_items'],
            "processed_cves": task['processed_items'],
            "total_hosts": task['total_records'],
            "updated_hosts": task['updated_records'],
            "progress_percent": round(progress_percent, 1),
            "estimated_time_seconds": estimated_time,
            "start_time": task['start_time'].isoformat() if task['start_time'] else None,
            "error_message": task['error_message']
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
        existing_task = await db.get_background_task('hosts_update')
        if existing_task and existing_task['status'] in ['processing', 'initializing']:
            return {"success": False, "message": "Обновление уже запущено"}
        
        # Создаем новую задачу
        task_id = await db.create_background_task('hosts_update')
        
        def progress_callback(status, step, **kwargs):
            # Обновляем задачу в базе данных
            asyncio.create_task(db.update_background_task(task_id, 
                status=status, 
                current_step=step,
                total_items=kwargs.get('total_cves', 0),
                processed_items=kwargs.get('processed_cves', 0),
                total_records=kwargs.get('total_hosts', 0),
                updated_records=kwargs.get('updated_hosts', 0)
            ))
        
        # Запускаем параллельное фоновое обновление
        result = await db.update_hosts_complete(progress_callback)
        
        # Обновляем финальный статус в базе данных
        if result['success']:
            # Проверяем, не была ли задача отменена
            if 'отменено' in result.get('message', '').lower():
                await db.update_background_task(task_id, 
                    status='cancelled', 
                    current_step='Отменено пользователем',
                    total_items=result.get('processed_cves', 0),
                    processed_items=result.get('processed_cves', 0),
                    total_records=result.get('updated_count', 0),
                    updated_records=result.get('updated_count', 0)
                )
            else:
                await db.update_background_task(task_id, 
                    status='completed', 
                    current_step='Завершено',
                    total_items=result.get('processed_cves', 0),
                    processed_items=result.get('processed_cves', 0),
                    total_records=result.get('updated_count', 0),
                    updated_records=result.get('updated_count', 0)
                )
        else:
            await db.update_background_task(task_id, 
                status='error', 
                current_step='Ошибка',
                error_message=result.get('message', 'Неизвестная ошибка')
            )
        
        return result
        
    except Exception as e:
        print('Background update error:', traceback.format_exc())
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
        risk_result = calculate_risk_score(
            host_data.get('epss'),
            host_data.get('cvss'),
            settings
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
        hosts_data = await db.search_hosts(hostname, cve, ip_address, criticality, exploits_only, epss_only)
        
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


@router.post("/api/hosts/clean-empty-cve")
async def clean_empty_cve():
    """Очистить записи с пустыми CVE из базы данных"""
    try:
        db = get_db()
        conn = await db.get_connection()
        
        # Подсчитываем количество записей с пустыми CVE
        count_query = """
            SELECT COUNT(*) as cnt 
            FROM vulnanalizer.hosts 
            WHERE cve IS NULL OR cve = '' OR cve = '""'
        """
        count_result = await conn.fetchrow(count_query)
        empty_cve_count = count_result['cnt'] if count_result else 0
        
        if empty_cve_count == 0:
            return {
                "success": True,
                "message": "Записей с пустыми CVE не найдено",
                "deleted_count": 0
            }
        
        # Удаляем записи с пустыми CVE
        delete_query = """
            DELETE FROM vulnanalizer.hosts 
            WHERE cve IS NULL OR cve = '' OR cve = '""'
        """
        await conn.execute(delete_query)
        
        # Получаем общее количество записей после очистки
        total_query = "SELECT COUNT(*) as cnt FROM vulnanalizer.hosts"
        total_result = await conn.fetchrow(total_query)
        total_count = total_result['cnt'] if total_result else 0
        
        await db.release_connection(conn)
        
        return {
            "success": True,
            "message": f"Удалено {empty_cve_count} записей с пустыми CVE",
            "deleted_count": empty_cve_count,
            "remaining_count": total_count
        }
        
    except Exception as e:
        print(f"Error cleaning empty CVE records: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка при очистке записей с пустыми CVE: {str(e)}")


@router.get("/api/hosts/empty-cve-count")
async def get_empty_cve_count():
    """Получить количество записей с пустыми CVE"""
    try:
        db = get_db()
        conn = await db.get_connection()
        
        count_query = """
            SELECT COUNT(*) as cnt 
            FROM vulnanalizer.hosts 
            WHERE cve IS NULL OR cve = '' OR cve = '""'
        """
        count_result = await conn.fetchrow(count_query)
        empty_cve_count = count_result['cnt'] if count_result else 0
        
        # Получаем общее количество записей
        total_query = "SELECT COUNT(*) as cnt FROM vulnanalizer.hosts"
        total_result = await conn.fetchrow(total_query)
        total_count = total_result['cnt'] if total_result else 0
        
        await db.release_connection(conn)
        
        return {
            "success": True,
            "empty_cve_count": empty_cve_count,
            "total_count": total_count,
            "percentage": (empty_cve_count / total_count * 100) if total_count > 0 else 0
        }
        
    except Exception as e:
        print(f"Error getting empty CVE count: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка при получении статистики: {str(e)}")
