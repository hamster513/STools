"""
Роуты для работы с EPSS данными
"""
import traceback
import gzip
import io
import csv
import aiohttp
from datetime import datetime
from fastapi import APIRouter, HTTPException, File, UploadFile
from fastapi.responses import StreamingResponse

from database import get_db

router = APIRouter()


@router.post("/api/epss/upload")
async def upload_epss(file: UploadFile = File(...)):
    """Загрузить EPSS данные"""
    try:
        content = await file.read()
        decoded_content = content.decode('utf-8-sig')
        
        # Парсим CSV
        lines = decoded_content.splitlines()
        reader = csv.DictReader(lines, delimiter=',')
        
        records = []
        for row in reader:
            try:
                cve = row.get('cve', '').strip()
                epss = row.get('epss', '').strip()
                
                if cve and epss:
                    try:
                        epss_value = float(epss)
                        records.append({
                            'cve': cve,
                            'epss': epss_value
                        })
                    except ValueError:
                        print(f"⚠️ Пропускаем запись с невалидным EPSS: {cve} = {epss}")
                        continue
                        
            except Exception as row_error:
                print(f"⚠️ Ошибка обработки строки EPSS: {row_error}")
                continue
        
        # Сохраняем в базу данных
        db = get_db()
        await db.epss.insert_records(records)
        
        return {
            "success": True,
            "count": len(records),
            "message": f"EPSS данные успешно импортированы: {len(records)} записей"
        }
        
    except Exception as e:
        print(f'❌ EPSS upload error: {traceback.format_exc()}')
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/epss/download")
async def download_epss():
    """Скачать EPSS данные с внешнего источника (фоновый режим)"""
    try:
        print("🔄 Starting EPSS download in background...")
        
        # Создаем фоновую задачу
        db = get_db()
        task_id = await db.create_background_task(
            task_type='epss_download',
            parameters={
                'url': 'https://epss.empiricalsecurity.com/epss_scores-current.csv.gz',
                'description': 'Загрузка EPSS данных с внешнего источника'
            },
            description='Загрузка EPSS данных с внешнего источника'
        )
        
        print(f"✅ EPSS download task created with ID: {task_id}")
        return {
            "success": True, 
            "message": "Задача загрузки EPSS поставлена в очередь",
            "task_id": task_id
        }
        
    except Exception as e:
        error_msg = f"EPSS download task creation error: {str(e)}"
        print(error_msg)
        print('Full traceback:', traceback.format_exc())
        raise HTTPException(status_code=500, detail=error_msg)


@router.get("/api/epss/search")
async def search_epss(
    cve: str = None,
    limit: int = 100,
    page: int = 1
):
    """Поиск EPSS данных"""
    try:
        db = get_db()
        results, total_count = await db.search_epss(
            cve_pattern=cve,
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
        print('EPSS search error:', traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/epss/status")
async def epss_status():
    """Получить статус EPSS данных"""
    try:
        db = get_db()
        count = await db.count_epss_records()
        return {"success": True, "count": count}
    except Exception as e:
        print('EPSS status error:', traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/epss/preview")
async def get_epss_preview():
    """Получить первые 20 записей EPSS для предварительного просмотра"""
    try:
        db = get_db()
        
        # Получаем первые 20 записей из базы данных
        query = """
            SELECT cve, epss, percentile, updated_at
            FROM vulnanalizer.epss 
            ORDER BY updated_at DESC 
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
                "cve": row['cve'],
                "epss": float(row['epss']),
                "percentile": float(row['percentile']),
                "updated_at": row['updated_at'].isoformat() if row['updated_at'] else None
            })
        
        return {
            "success": True,
            "records": records,
            "count": len(records)
        }
    except Exception as e:
        print(f"Error getting EPSS preview: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/epss/clear")
async def clear_epss():
    """Очистить все EPSS данные"""
    try:
        db = get_db()
        await db.clear_epss()
        return {"success": True, "message": "Все EPSS данные удалены"}
    except Exception as e:
        print('EPSS clear error:', traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))
