"""
Роуты для работы с CVE данными
"""
import traceback
import gzip
import io
import json
import aiohttp
from datetime import datetime
from fastapi import APIRouter, HTTPException, File, UploadFile
from fastapi.responses import StreamingResponse

from database import get_db

router = APIRouter()


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
async def upload_cve(file: UploadFile = File(...)):
    """Загрузить CVE данные из файла"""
    try:
        content = await file.read()
        
        # Проверяем, является ли файл архивом
        if file.filename.endswith('.gz'):
            print("📦 Распаковываем gzip архив...")
            with gzip.GzipFile(fileobj=io.BytesIO(content)) as gz:
                content = gz.read()
        
        # Декодируем контент
        if isinstance(content, bytes):
            content = content.decode('utf-8')
        
        print(f"📄 Парсим JSON файл размером {len(content)} символов...")
        
        # Парсим JSON
        records = parse_cve_json(content)
        
        if not records:
            raise Exception("Не удалось извлечь CVE записи из файла")
        
        print(f"✅ Извлечено {len(records)} CVE записей")
        
        # Сохраняем в базу данных
        db = get_db()
        await db.insert_cve_records(records)
        
        return {
            "success": True,
            "count": len(records),
            "message": f"CVE данные успешно импортированы: {len(records)} записей"
        }
        
    except Exception as e:
        print(f'❌ CVE upload error: {traceback.format_exc()}')
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/cve/download")
async def download_cve():
    """Скачать CVE данные с внешнего источника"""
    try:
        print("🔄 Starting CVE download...")
        
        # Скачиваем данные за последние годы (с 2002)
        current_year = datetime.now().year
        
        # Создаем фоновую задачу
        db = get_db()
        task_id = await db.create_background_task(
            task_type='cve_download',
            parameters={'years': list(range(2002, current_year + 1))},
            description='Скачивание CVE данных с NVD'
        )
        total_records = 0
        
        for year in range(2002, current_year + 1):
            try:
                # Обновляем статус задачи
                await db.update_background_task(
                    task_id, 
                    current_step=f"Скачивание данных за {year} год...",
                    processed_items=year - 2002,
                    total_items=current_year - 2001
                )
                
                url = f"https://nvd.nist.gov/feeds/json/cve/2.0/nvdcve-2.0-{year}.json.gz"
                print(f"📥 Downloading from {url}")
                
                # Увеличиваем таймауты для больших файлов
                timeout = aiohttp.ClientTimeout(total=600, connect=60)
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.get(url) as resp:
                        if resp.status != 200:
                            print(f"⚠️ Failed to download {year}: {resp.status}")
                            continue
                        
                        print(f"📦 Reading compressed content for {year}...")
                        gz_content = await resp.read()
                        print(f"📊 Downloaded {len(gz_content)} bytes for {year}")
                
                print(f"🔓 Decompressing content for {year}...")
                with gzip.GzipFile(fileobj=io.BytesIO(gz_content)) as gz:
                    content = gz.read().decode('utf-8')
                
                print(f"📄 Decompressed {len(content)} characters for {year}")
                
                # Парсим JSON
                print(f"📄 Парсинг JSON файла за {year} год...")
                records = parse_cve_json(content)
                print(f"📊 Извлечено {len(records)} записей CVE из JSON")
                
                if records:
                    print(f"✅ Найдено {len(records)} записей CVE за {year} год")
                    print(f"📥 Начинаем загрузку в базу данных...")
                    await db.insert_cve_records(records)
                    total_records += len(records)
                    print(f"✅ Загружено {len(records)} записей CVE за {year} год")
                else:
                    print(f"⚠️ No CVE records found for {year}")
                
            except Exception as e:
                print(f"⚠️ Error processing year {year}: {e}")
                continue
        
        # Обновляем статус задачи
        await db.update_background_task(
            task_id, 
            status='completed',
            current_step='Загрузка завершена',
            total_records=total_records,
            updated_records=total_records
        )
        
        print("🎉 CVE download and processing completed successfully")
        return {"success": True, "count": total_records}
        
    except Exception as e:
        error_msg = f"CVE download error: {str(e)}"
        print(error_msg)
        print('Full traceback:', traceback.format_exc())
        
        # Обновляем статус задачи с ошибкой
        if 'task_id' in locals():
            await db.update_background_task(task_id, status='error', error_message=error_msg)
        
        raise HTTPException(status_code=500, detail=error_msg)


@router.get("/api/cve/status")
async def cve_status():
    """Получить статус CVE данных"""
    try:
        db = get_db()
        count = await db.count_cve_records()
        return {"success": True, "count": count}
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
        db = get_db()
        cancelled = await db.cancel_background_task('cve_download')
        
        if cancelled:
            return {"success": True, "message": "Загрузка CVE отменена"}
        else:
            return {"success": False, "message": "Активная загрузка CVE не найдена"}
            
    except Exception as e:
        print('CVE cancel error:', traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/cve/download-urls")
async def get_cve_download_urls():
    """Получить список URL для скачивания CVE данных"""
    current_year = datetime.now().year
    urls = []
    
    # Добавляем ссылки на CVE 2.0 для всех лет с 2002
    for year in range(2002, current_year + 1):
        urls.append({
            "year": f"{year} (CVE 2.0)",
            "url": f"https://nvd.nist.gov/feeds/json/cve/2.0/nvdcve-2.0-{year}.json.gz",
            "filename": f"nvdcve-2.0-{year}.json.gz"
        })
    
    return {
        "success": True,
        "urls": urls,
        "note": "Скачайте файлы по ссылкам выше для offline загрузки. CVE 2.0 - новый формат NVD (2002-2025)."
    }
