"""
Роуты для работы с EPSS данными
"""
import traceback
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
        import csv
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
        await db.insert_epss_records(records)
        
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
    """Скачать EPSS данные"""
    try:
        db = get_db()
        epss_data = await db.get_all_epss_records()
        
        if not epss_data:
            raise HTTPException(status_code=404, detail="EPSS данные не найдены")
        
        # Создаем CSV
        import csv
        import io
        
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['cve', 'epss'])
        
        for record in epss_data:
            writer.writerow([record['cve'], record['epss']])
        
        output.seek(0)
        
        return StreamingResponse(
            io.BytesIO(output.getvalue().encode('utf-8')),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=epss_data.csv"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f'❌ EPSS download error: {traceback.format_exc()}')
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
