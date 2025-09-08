"""
Роуты для работы с CVE данными
"""
import traceback
import gzip
import io
import json
import aiohttp
import asyncio
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, HTTPException, File, UploadFile, Form, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from database import get_db

class CVEDownloadRequest(BaseModel):
    years: Optional[List[int]] = None

router = APIRouter(tags=["cve"])


def parse_cve_json(data):
    """Парсить JSON данные CVE (поддерживает форматы 1.1 и 2.0)"""
    records = []
    
    try:
        cve_data = json.loads(data)
        
        # Определяем формат CVE
        if 'CVE_Items' in cve_data:
            # Формат CVE 1.1
            cve_items = cve_data.get('CVE_Items', [])
            format_version = "1.1"
        elif 'vulnerabilities' in cve_data:
            # Формат CVE 2.0
            cve_items = cve_data.get('vulnerabilities', [])
            format_version = "2.0"
        else:
            raise Exception("Неизвестный формат CVE данных")
        
        print(f"📄 Обрабатываем CVE формат {format_version}, найдено {len(cve_items)} записей")
        
        for item in cve_items:
            try:
                if format_version == "1.1":
                    # Формат CVE 1.1
                    cve_info = item.get('cve', {})
                    cve_id = cve_info.get('CVE_data_meta', {}).get('ID')
                    
                    # Получаем описание
                    description = ""
                    description_data = cve_info.get('description', {}).get('description_data', [])
                    for desc in description_data:
                        if desc.get('lang') == 'en':
                            description = desc.get('value', '')
                            break
                else:
                    # Формат CVE 2.0
                    cve_info = item.get('cve', {})
                    cve_id = cve_info.get('id')
                    
                    # Получаем описание
                    description = ""
                    descriptions = cve_info.get('descriptions', [])
                    for desc in descriptions:
                        if desc.get('lang') == 'en':
                            description = desc.get('value', '')
                            break
                
                if not cve_id:
                    continue
                
                # Парсим CVSS данные
                cvss_v3_base_score = None
                cvss_v3_base_severity = None
                cvss_v2_base_score = None
                cvss_v2_base_severity = None
                exploitability_score = None
                impact_score = None
                
                if format_version == "1.1":
                    # Формат CVE 1.1
                    impact = item.get('impact', {})
                    
                    # CVSS v3.1
                    if 'baseMetricV3' in impact:
                        cvss_v3 = impact['baseMetricV3'].get('cvssV3', {})
                        cvss_v3_base_score = cvss_v3.get('baseScore')
                        cvss_v3_base_severity = cvss_v3.get('baseSeverity')
                        exploitability_score = impact['baseMetricV3'].get('exploitabilityScore')
                        impact_score = impact['baseMetricV3'].get('impactScore')
                    
                    # CVSS v3.0 (если v3.1 нет)
                    elif 'cvssV3' in impact:
                        cvss_v3 = impact['cvssV3']
                        cvss_v3_base_score = cvss_v3.get('baseScore')
                        cvss_v3_base_severity = cvss_v3.get('baseSeverity')
                        exploitability_score = impact.get('exploitabilityScore')
                        impact_score = impact.get('impactScore')
                    
                    # CVSS v2
                    if 'baseMetricV2' in impact:
                        cvss_v2 = impact['baseMetricV2'].get('cvssV2', {})
                        cvss_v2_base_score = cvss_v2.get('baseScore')
                        cvss_v2_base_severity = cvss_v2.get('baseSeverity')
                else:
                    # Формат CVE 2.0
                    metrics = cve_info.get('metrics', {})
                    
                    # CVSS v3.1
                    if 'cvssMetricV31' in metrics:
                        cvss_v31 = metrics['cvssMetricV31'][0] if metrics['cvssMetricV31'] else {}
                        cvss_data = cvss_v31.get('cvssData', {})
                        cvss_v3_base_score = cvss_data.get('baseScore')
                        cvss_v3_base_severity = cvss_data.get('baseSeverity')
                        exploitability_score = cvss_v31.get('exploitabilityScore')
                        impact_score = cvss_v31.get('impactScore')
                    
                    # CVSS v2
                    if 'cvssMetricV2' in metrics:
                        cvss_v2_metric = metrics['cvssMetricV2'][0] if metrics['cvssMetricV2'] else {}
                        cvss_v2_data = cvss_v2_metric.get('cvssData', {})
                        cvss_v2_base_score = cvss_v2_data.get('baseScore')
                        cvss_v2_base_severity = cvss_v2_data.get('baseSeverity')
                
                # Парсим даты
                published_date = None
                last_modified_date = None
                
                if format_version == "1.1":
                    if item.get('publishedDate'):
                        try:
                            # Убираем часовой пояс для совместимости с PostgreSQL
                            date_str = item['publishedDate'].replace('Z', '').replace('+00:00', '')
                            published_date = datetime.fromisoformat(date_str)
                        except:
                            pass
                    
                    if item.get('lastModifiedDate'):
                        try:
                            # Убираем часовой пояс для совместимости с PostgreSQL
                            date_str = item['lastModifiedDate'].replace('Z', '').replace('+00:00', '')
                            last_modified_date = datetime.fromisoformat(date_str)
                        except:
                            pass
                else:
                    # Формат CVE 2.0
                    if cve_info.get('published'):
                        try:
                            # Убираем часовой пояс для совместимости с PostgreSQL
                            date_str = cve_info['published'].replace('Z', '').replace('+00:00', '')
                            published_date = datetime.fromisoformat(date_str)
                        except:
                            pass
                    
                    if cve_info.get('lastModified'):
                        try:
                            # Убираем часовой пояс для совместимости с PostgreSQL
                            date_str = cve_info['lastModified'].replace('Z', '').replace('+00:00', '')
                            last_modified_date = datetime.fromisoformat(date_str)
                        except:
                            pass
                
                records.append({
                    'cve_id': cve_id,
                    'description': description,
                    'cvss_v3_base_score': cvss_v3_base_score,
                    'cvss_v3_base_severity': cvss_v3_base_severity,
                    'cvss_v2_base_score': cvss_v2_base_score,
                    'cvss_v2_base_severity': cvss_v2_base_severity,
                    'exploitability_score': exploitability_score,
                    'impact_score': impact_score,
                    'published_date': published_date,
                    'last_modified_date': last_modified_date
                })
                
            except Exception as e:
                print(f"⚠️ Ошибка обработки CVE записи: {e}")
                continue
        
        return records
        
    except Exception as e:
        print(f"❌ Ошибка парсинга JSON CVE: {e}")
        raise


@router.post("/api/cve/upload")
async def upload_cve(request: Request):
    """Загрузить CVE данные из файла"""
    try:
        # Читаем сырые данные
        body = await request.body()
        
        if len(body) == 0:
            raise HTTPException(status_code=422, detail="Тело запроса пустое")
        
        # Пытаемся найти файл в multipart данных
        content_type = request.headers.get('content-type', '')
        if 'multipart/form-data' in content_type:
            # Простой парсинг multipart
            boundary = content_type.split('boundary=')[1] if 'boundary=' in content_type else None
            if boundary:
                # Ищем файл в multipart данных
                parts = body.split(f'--{boundary}'.encode())
                
                for part in parts:
                    if b'Content-Disposition: form-data' in part and b'filename=' in part:
                        # Извлекаем имя файла
                        lines = part.split(b'\r\n')
                        filename = None
                        for line in lines:
                            if b'filename=' in line:
                                filename = line.decode('utf-8', errors='ignore').split('filename="')[1].split('"')[0]
                                break
                        
                        if filename:
                            # Извлекаем содержимое файла (после двойного \r\n)
                            content_start = part.find(b'\r\n\r\n')
                            if content_start != -1:
                                file_content = part[content_start + 4:]
                                # Убираем только последний \r\n если он есть, но не все
                                if file_content.endswith(b'\r\n'):
                                    file_content = file_content[:-2]
                                
                                # Обрабатываем файл
                                if filename.endswith('.gz'):
                                    try:
                                        with gzip.GzipFile(fileobj=io.BytesIO(file_content)) as gz:
                                            content = gz.read()
                                    except Exception as gz_error:
                                        raise HTTPException(status_code=422, detail=f"Ошибка распаковки gzip архива: {gz_error}")
                                else:
                                    content = file_content
                                
                                # Декодируем контент
                                if isinstance(content, bytes):
                                    try:
                                        content = content.decode('utf-8')
                                    except UnicodeDecodeError as decode_error:
                                        raise HTTPException(status_code=422, detail=f"Ошибка декодирования файла: {decode_error}")
                                
                                # Парсим JSON
                                try:
                                    records = parse_cve_json(content)
                                except Exception as parse_error:
                                    raise HTTPException(status_code=422, detail=f"Ошибка парсинга JSON: {parse_error}")
                                
                                if not records:
                                    raise HTTPException(status_code=422, detail="Не удалось извлечь CVE записи из файла")
                                
                                # Сохраняем в базу данных
                                try:
                                    db = get_db()
                                    await db.insert_cve_records(records)
                                except Exception as db_error:
                                    raise HTTPException(status_code=500, detail=f"Ошибка сохранения в базу данных: {db_error}")
                                
                                return {
                                    "success": True,
                                    "count": len(records),
                                    "message": f"CVE данные успешно импортированы: {len(records)} записей"
                                }
        else:
            raise HTTPException(status_code=422, detail=f"Ожидается multipart/form-data, получен: {content_type}")
        
        raise HTTPException(status_code=422, detail="Файл не найден в запросе")
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/cve/download")
async def download_cve(request: CVEDownloadRequest):
    """Скачать CVE данные с внешнего источника для выбранных лет"""
    try:
        from services.cve_worker import cve_worker
        
        years = request.years
        
        # Если годы не указаны, используем последние 5 лет
        if not years:
            current_year = datetime.now().year
            years = list(range(current_year - 4, current_year + 1))
        
        # Проверяем, не идет ли уже загрузка
        if cve_worker.is_downloading():
            raise HTTPException(status_code=400, detail="Загрузка уже выполняется")
        
        # Создаем фоновую задачу
        db = get_db()
        task_id = await db.create_background_task(
            task_type='cve_download',
            parameters={'years': years},
            description=f'Скачивание CVE данных с NVD для лет: {years}'
        )
        
        # Запускаем worker в фоновом режиме
        asyncio.create_task(cve_worker.start_download(years, task_id))
        
        return {
            "success": True, 
            "task_id": task_id,
            "message": f"Загрузка CVE запущена для {len(years)} лет",
            "years": years
        }
        
    except Exception as e:
        error_msg = f"CVE download error: {str(e)}"
        print(error_msg)
        print('Full traceback:', traceback.format_exc())
        raise HTTPException(status_code=500, detail=error_msg)


@router.get("/api/cve/status")
async def cve_status():
    """Получить статус CVE данных"""
    try:
        from services.cve_worker import cve_worker
        
        db = get_db()
        
        # Получаем количество CVE записей
        try:
            count = await db.count_cve_records()
        except Exception as count_error:
            print(f'CVE count error: {count_error}')
            count = 0
        
        # Получаем статус текущей загрузки
        try:
            is_downloading = cve_worker.is_downloading()
            current_task_id = cve_worker.get_current_task_id()
        except Exception as worker_error:
            print(f'CVE worker error: {worker_error}')
            is_downloading = False
            current_task_id = None
        
        # Если идет загрузка, получаем детали задачи
        task_details = None
        if current_task_id:
            try:
                task_details = await db.get_background_task(current_task_id)
            except Exception as task_error:
                print(f'CVE task details error: {task_error}')
                task_details = None
        
        return {
            "success": True, 
            "count": count,
            "is_downloading": is_downloading,
            "current_task_id": current_task_id,
            "task_details": task_details
        }
    except Exception as e:
        print('CVE status error:', traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/cve/clear")
async def clear_cve():
    """Очистить все CVE данные"""
    try:
        db = get_db()
        await db.clear_cve()
        return {"success": True, "message": "Все CVE данные удалены"}
    except Exception as e:
        print('CVE clear error:', traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/cve/download-recent")
async def download_cve_recent():
    """Скачать последние CVE данные (recent)"""
    try:
        print("🔄 Starting CVE recent download...")
        
        url = "https://nvd.nist.gov/feeds/json/cve/2.0/nvdcve-2.0-recent.json.gz"
        print(f"📥 Downloading from {url}")
        
        # Создаем фоновую задачу
        db = get_db()
        task_id = await db.create_background_task(
            task_type='cve_download_recent',
            parameters={'url': url},
            description='Скачивание последних CVE данных с NVD'
        )
        
        # Увеличиваем таймауты для больших файлов
        timeout = aiohttp.ClientTimeout(total=600, connect=60)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    error_msg = f"Failed to download recent CVE: {resp.status}"
                    await db.update_background_task(task_id, status='error', error_message=error_msg)
                    raise HTTPException(status_code=500, detail=error_msg)
                
                print(f"📦 Reading compressed content...")
                gz_content = await resp.read()
                print(f"📊 Downloaded {len(gz_content)} bytes")
        
        print(f"🔓 Decompressing content...")
        with gzip.GzipFile(fileobj=io.BytesIO(gz_content)) as gz:
            content = gz.read().decode('utf-8')
        
        print(f"📄 Decompressed {len(content)} characters")
        
        # Парсим JSON
        print(f"📄 Парсинг JSON файла...")
        records = parse_cve_json(content)
        print(f"📊 Извлечено {len(records)} записей CVE из JSON")
        
        if records:
            print(f"✅ Найдено {len(records)} записей CVE")
            print(f"📥 Начинаем загрузку в базу данных...")
            await db.insert_cve_records(records)
            print(f"✅ Загружено {len(records)} записей CVE")
        else:
            print(f"⚠️ No CVE records found")
        
        # Обновляем статус задачи
        await db.update_background_task(
            task_id, 
            status='completed',
            current_step='Загрузка завершена',
            total_records=len(records) if records else 0,
            updated_records=len(records) if records else 0
        )
        
        print("🎉 CVE recent download and processing completed successfully")
        return {"success": True, "count": len(records) if records else 0}
        
    except Exception as e:
        error_msg = f"CVE recent download error: {str(e)}"
        print(error_msg)
        print('Full traceback:', traceback.format_exc())
        
        # Обновляем статус задачи с ошибкой
        if 'task_id' in locals():
            await db.update_background_task(task_id, status='error', error_message=error_msg)
        
        raise HTTPException(status_code=500, detail=error_msg)


@router.post("/api/cve/download-modified")
async def download_cve_modified():
    """Скачать измененные CVE данные (modified)"""
    try:
        print("🔄 Starting CVE modified download...")
        
        url = "https://nvd.nist.gov/feeds/json/cve/2.0/nvdcve-2.0-modified.json.gz"
        print(f"📥 Downloading from {url}")
        
        # Создаем фоновую задачу
        db = get_db()
        task_id = await db.create_background_task(
            task_type='cve_download_modified',
            parameters={'url': url},
            description='Скачивание измененных CVE данных с NVD'
        )
        
        # Увеличиваем таймауты для больших файлов
        timeout = aiohttp.ClientTimeout(total=600, connect=60)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    error_msg = f"Failed to download modified CVE: {resp.status}"
                    await db.update_background_task(task_id, status='error', error_message=error_msg)
                    raise HTTPException(status_code=500, detail=error_msg)
                
                print(f"📦 Reading compressed content...")
                gz_content = await resp.read()
                print(f"📊 Downloaded {len(gz_content)} bytes")
        
        print(f"🔓 Decompressing content...")
        with gzip.GzipFile(fileobj=io.BytesIO(gz_content)) as gz:
            content = gz.read().decode('utf-8')
        
        print(f"📄 Decompressed {len(content)} characters")
        
        # Парсим JSON
        print(f"📄 Парсинг JSON файла...")
        records = parse_cve_json(content)
        print(f"📊 Извлечено {len(records)} записей CVE из JSON")
        
        if records:
            print(f"✅ Найдено {len(records)} записей CVE")
            print(f"📥 Начинаем загрузку в базу данных...")
            await db.insert_cve_records(records)
            print(f"✅ Загружено {len(records)} записей CVE")
        else:
            print(f"⚠️ No CVE records found")
        
        # Обновляем статус задачи
        await db.update_background_task(
            task_id, 
            status='completed',
            current_step='Загрузка завершена',
            total_records=len(records) if records else 0,
            updated_records=len(records) if records else 0
        )
        
        print("🎉 CVE modified download and processing completed successfully")
        return {"success": True, "count": len(records) if records else 0}
        
    except Exception as e:
        error_msg = f"CVE modified download error: {str(e)}"
        print(error_msg)
        print('Full traceback:', traceback.format_exc())
        
        # Обновляем статус задачи с ошибкой
        if 'task_id' in locals():
            await db.update_background_task(task_id, status='error', error_message=error_msg)
        
        raise HTTPException(status_code=500, detail=error_msg)


@router.post("/api/cve/cancel")
async def cancel_cve_download():
    """Отменить текущую загрузку CVE"""
    try:
        from services.cve_worker import cve_worker
        
        if cve_worker.is_downloading():
            cancelled = await cve_worker.cancel_download()
            if cancelled:
                return {"success": True, "message": "Загрузка CVE отменена"}
            else:
                return {"success": False, "message": "Не удалось отменить загрузку"}
        else:
            return {"success": False, "message": "Активная загрузка CVE не найдена"}
            
    except Exception as e:
        print('CVE cancel error:', traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/cve/download-urls")
async def get_cve_download_urls():
    """Получить URL для скачивания CVE данных"""
    try:
        current_year = datetime.now().year
        urls = []
        
        # URL для всех лет с 2002 (когда начались CVE) до текущего года + 1
        for year in range(2002, current_year + 2):
            urls.append({
                "year": year,
                "url": f"https://nvd.nist.gov/feeds/json/cve/2.0/nvdcve-2.0-{year}.json.gz",
                "filename": f"nvdcve-2.0-{year}.json.gz"
            })
        
        # Добавляем также ссылки на recent и modified файлы
        urls.extend([
            {
                "year": "recent",
                "url": "https://nvd.nist.gov/feeds/json/cve/2.0/nvdcve-2.0-recent.json.gz",
                "filename": "nvdcve-2.0-recent.json.gz"
            },
            {
                "year": "modified", 
                "url": "https://nvd.nist.gov/feeds/json/cve/2.0/nvdcve-2.0-modified.json.gz",
                "filename": "nvdcve-2.0-modified.json.gz"
            }
        ])
        
        return {"success": True, "urls": urls}
    except Exception as e:
        print(f"❌ Ошибка получения URL для скачивания CVE: {e}")
        return {"success": False, "error": str(e)}


@router.get("/api/cve/preview")
async def get_cve_preview():
    """Получить первые 20 записей CVE для предварительного просмотра"""
    try:
        db = get_db()
        
        # Получаем первые 20 записей из базы данных
        query = """
            SELECT cve_id, description, cvss_v3_base_score, cvss_v3_base_severity,
                   cvss_v3_attack_vector, cvss_v3_privileges_required, cvss_v3_user_interaction,
                   cvss_v3_confidentiality_impact, cvss_v3_integrity_impact, cvss_v3_availability_impact,
                   cvss_v2_base_score, cvss_v2_base_severity, cvss_v2_access_vector,
                   cvss_v2_access_complexity, cvss_v2_authentication, cvss_v2_confidentiality_impact,
                   cvss_v2_integrity_impact, cvss_v2_availability_impact, published_date, last_modified_date,
                   created_at
            FROM vulnanalizer.cve 
            ORDER BY created_at DESC 
            LIMIT 20
        """
        
        conn = await db.get_connection()
        try:
            results = await conn.fetch(query)
        finally:
            await db.release_connection(conn)
        
        # Конвертируем результаты в список словарей
        records = []
        for row in results:
            records.append({
                "cve_id": row['cve_id'],
                "description": row['description'],
                "cvss_v3_score": row['cvss_v3_base_score'],
                "cvss_v3_severity": row['cvss_v3_base_severity'],
                "cvss_v3_attack_vector": row['cvss_v3_attack_vector'],
                "cvss_v3_privileges_required": row['cvss_v3_privileges_required'],
                "cvss_v3_user_interaction": row['cvss_v3_user_interaction'],
                "cvss_v3_confidentiality_impact": row['cvss_v3_confidentiality_impact'],
                "cvss_v3_integrity_impact": row['cvss_v3_integrity_impact'],
                "cvss_v3_availability_impact": row['cvss_v3_availability_impact'],
                "cvss_v2_score": row['cvss_v2_base_score'],
                "cvss_v2_severity": row['cvss_v2_base_severity'],
                "cvss_v2_access_vector": row['cvss_v2_access_vector'],
                "cvss_v2_access_complexity": row['cvss_v2_access_complexity'],
                "cvss_v2_authentication": row['cvss_v2_authentication'],
                "cvss_v2_confidentiality_impact": row['cvss_v2_confidentiality_impact'],
                "cvss_v2_integrity_impact": row['cvss_v2_integrity_impact'],
                "cvss_v2_availability_impact": row['cvss_v2_availability_impact'],
                "published_date": row['published_date'].isoformat() if row['published_date'] else None,
                "last_modified_date": row['last_modified_date'].isoformat() if row['last_modified_date'] else None,
                "created_at": row['created_at'].isoformat() if row['created_at'] else None
            })
        
        return {
            "success": True,
            "records": records,
            "count": len(records)
        }
    except Exception as e:
        print(f"Error getting CVE preview: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/cve/{cve_id}/description")
async def get_cve_description(cve_id: str):
    """Получить описание CVE по ID"""
    try:
        db = get_db()
        
        # Получаем данные CVE через репозиторий
        cve_data = await db.get_cve_by_id(cve_id)
        
        if not cve_data:
            return {"success": False, "error": "CVE не найден"}
        
        return {
            "success": True,
            "cve": {
                "id": cve_data['cve_id'],
                "description": cve_data['description'],
                "cvss_v3_score": cve_data['cvss_v3_base_score'],
                "cvss_v3_severity": cve_data['cvss_v3_base_severity'],
                "cvss_v3_attack_vector": cve_data['cvss_v3_attack_vector'],
                "cvss_v3_privileges_required": cve_data['cvss_v3_privileges_required'],
                "cvss_v3_user_interaction": cve_data['cvss_v3_user_interaction'],
                "cvss_v3_confidentiality_impact": cve_data['cvss_v3_confidentiality_impact'],
                "cvss_v3_integrity_impact": cve_data['cvss_v3_integrity_impact'],
                "cvss_v3_availability_impact": cve_data['cvss_v3_availability_impact'],
                "cvss_v2_score": cve_data['cvss_v2_base_score'],
                "cvss_v2_severity": cve_data['cvss_v2_base_severity'],
                "cvss_v2_access_vector": cve_data['cvss_v2_access_vector'],
                "cvss_v2_access_complexity": cve_data['cvss_v2_access_complexity'],
                "cvss_v2_authentication": cve_data['cvss_v2_authentication'],
                "cvss_v2_confidentiality_impact": cve_data['cvss_v2_confidentiality_impact'],
                "cvss_v2_integrity_impact": cve_data['cvss_v2_integrity_impact'],
                "cvss_v2_availability_impact": cve_data['cvss_v2_availability_impact'],
                "exploitability_score": cve_data['exploitability_score'],
                "impact_score": cve_data['impact_score'],
                "published_date": cve_data['published_date'],
                "last_modified_date": cve_data['last_modified_date']
            }
        }
    except Exception as e:
        print(f"❌ Ошибка получения описания CVE {cve_id}: {e}")
        return {"success": False, "error": str(e)}


@router.get("/api/cve/test")
async def test_cve():
    """
    Тестовый endpoint для проверки работы CVE роутера
    """
    return {"success": True, "message": "CVE router is working"}

@router.get("/api/cve/search/{cve_id}")
async def search_cve(cve_id: str):
    """
    Поиск информации о CVE с расчетом риска
    """
    try:
        db = get_db()
        
        # Получаем данные CVE
        cve_data = await db.cve.get_cve_by_id(cve_id)
        if not cve_data:
            return {
                "success": False,
                "error": f"CVE {cve_id} не найден в базе данных"
            }
        
        # Получаем данные EPSS
        epss_data = await db.epss.get_epss_by_cve(cve_id)
        
        # Получаем данные ExploitDB
        exploitdb_data = await db.exploitdb.get_exploitdb_by_cve(cve_id)
        
        # Получаем данные Metasploit
        metasploit_data = await db.metasploit.get_metasploit_by_cve(cve_id)
        
        # Получаем настройки системы для расчета риска
        from database.settings_repository import SettingsRepository
        settings_repo = SettingsRepository()
        settings = await settings_repo.get_settings()
        
        # Подготавливаем данные CVE для расчета риска (как в risk_service.py)
        cve_calculation_data = {
            'cve_id': cve_id,
            'cvss_v3_attack_vector': cve_data.get('cvss_v3_attack_vector'),
            'cvss_v3_privileges_required': cve_data.get('cvss_v3_privileges_required'),
            'cvss_v3_user_interaction': cve_data.get('cvss_v3_user_interaction'),
            'cvss_v2_access_vector': cve_data.get('cvss_v2_access_vector'),
            'cvss_v2_access_complexity': cve_data.get('cvss_v2_access_complexity'),
            'cvss_v2_authentication': cve_data.get('cvss_v2_authentication')
        }
        
        # Получаем тип эксплойта из ExploitDB (как в risk_service.py)
        if exploitdb_data and isinstance(exploitdb_data, list) and len(exploitdb_data) > 0:
            cve_calculation_data['exploitdb_type'] = exploitdb_data[0].get('type', '').lower()
        else:
            cve_calculation_data['exploitdb_type'] = None
        
        # Получаем ранг Metasploit (как в risk_service.py)
        if metasploit_data:
            cve_calculation_data['msf_rank'] = metasploit_data.get('rank')
        else:
            cve_calculation_data['msf_rank'] = None
        
        # Используем единую функцию расчета риска
        from database.risk_calculation import calculate_risk_score
        
        epss_score = epss_data.get('epss', 0.0) if epss_data else 0.0
        cvss_score = cve_data.get('cvss_v3_base_score') or cve_data.get('cvss_v2_base_score', 0.0)
        
        risk_result = calculate_risk_score(
            epss=float(epss_score),
            cvss=float(cvss_score) if cvss_score else None,
            criticality='Medium',  # По умолчанию для CVE search
            settings=settings,
            cve_data=cve_calculation_data,
            confidential_data=False,  # По умолчанию для CVE search
            internet_access=True  # По умолчанию для CVE search
        )
        
        # Формируем данные риска
        risk_data = {
            "score": risk_result.get('risk_score', 0),
            "risk_score": risk_result.get('risk_score', 0),  # Добавляем для совместимости с JavaScript
            "level": "HIGH" if risk_result.get('risk_score', 0) > 70 else "MEDIUM" if risk_result.get('risk_score', 0) > 30 else "LOW",
            "factors": [],
            "epss": epss_score,
            "cvss_factor": (float(cvss_score) / 10) if cvss_score else 0.0,
            "impact": risk_result.get('impact', 1.0),
            "cve_param": risk_result.get('cve_param', 1.0),
            "exdb_param": risk_result.get('exdb_param', 1.0),
            "msf_param": risk_result.get('msf_param', 1.0)
        }
        
        # Преобразуем Metasploit данные в массив для совместимости с JavaScript
        metasploit_array = []
        if metasploit_data:
            # Добавляем поле rank как строку для совместимости с JavaScript
            metasploit_item = dict(metasploit_data)
            metasploit_item['rank'] = metasploit_data.get('rank_text', 'unknown')
            metasploit_array = [metasploit_item]
        
        return {
            "success": True,
            "cve": {
                "cve_id": cve_data['cve_id'],
                "description": cve_data['description'],
                "status": "PUBLISHED",  # Заглушка
                "published_date": cve_data['published_date'],
                "last_modified_date": cve_data['last_modified_date'],
                "cvss_v3_score": cve_data['cvss_v3_base_score'],
                "cvss_v3_severity": cve_data['cvss_v3_base_severity'],
                "cvss_v2_score": cve_data['cvss_v2_base_score'],
                "cvss_v2_severity": cve_data['cvss_v2_base_severity']
            },
            "epss": epss_data,
            "exploitdb": exploitdb_data,
            "metasploit": metasploit_array,
            "risk": risk_data
        }
        
    except Exception as e:
        print(f"Error searching CVE {cve_id}: {e}")
        return {
            "success": False,
            "error": str(e)
        }
