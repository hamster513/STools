from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import JSONResponse
import json
import logging
import asyncio
import traceback
from typing import Optional
from services.metasploit_service import MetasploitService
from database import get_db

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/metasploit", tags=["metasploit"])

# Инициализация сервиса
metasploit_service = MetasploitService()

@router.get("/status")
async def get_metasploit_status():
    """Получение статуса базы Metasploit"""
    try:
        from services.metasploit_worker import metasploit_worker
        
        db = get_db()
        
        # Получаем количество Metasploit записей
        try:
            count = await db.count_metasploit_modules()
        except Exception as count_error:
            logger.error(f'Metasploit count error: {count_error}')
            count = 0
        
        # Получаем статус текущей загрузки
        try:
            is_downloading = metasploit_worker.is_downloading()
            current_task_id = metasploit_worker.get_current_task_id()
        except Exception as worker_error:
            logger.error(f'Metasploit worker error: {worker_error}')
            is_downloading = False
            current_task_id = None
        
        # Если идет загрузка, получаем детали задачи
        task_details = None
        if current_task_id:
            try:
                task_details = await db.get_background_task(current_task_id)
                # Конвертируем datetime объекты в строки для JSON сериализации
                if task_details:
                    if 'created_at' in task_details and task_details['created_at']:
                        task_details['created_at'] = task_details['created_at'].isoformat()
                    if 'updated_at' in task_details and task_details['updated_at']:
                        task_details['updated_at'] = task_details['updated_at'].isoformat()
            except Exception as task_error:
                logger.error(f'Metasploit task details error: {task_error}')
                task_details = None
        
        return JSONResponse(content={
            "success": True, 
            "count": count,
            "is_downloading": is_downloading,
            "current_task_id": current_task_id,
            "task_details": task_details
        })
    except Exception as e:
        logger.error('Metasploit status error:', traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/download")
async def download_metasploit():
    """Загрузка данных Metasploit с GitHub"""
    try:
        from services.metasploit_worker import metasploit_worker
        
        # Проверяем, не идет ли уже загрузка
        if metasploit_worker.is_downloading():
            raise HTTPException(status_code=400, detail="Загрузка уже выполняется")
        
        # Создаем фоновую задачу
        db = get_db()
        task_id = await db.create_background_task(
            task_type='metasploit_download',
            parameters={},
            description='Скачивание данных Metasploit с GitHub'
        )
        
        # Запускаем worker в фоновом режиме
        asyncio.create_task(metasploit_worker.start_download(task_id))
        
        return JSONResponse(content={
            "success": True, 
            "task_id": task_id,
            "message": "Загрузка Metasploit запущена"
        })
        
    except Exception as e:
        error_msg = f"Metasploit download error: {str(e)}"
        logger.error(error_msg)
        logger.error('Full traceback:', traceback.format_exc())
        raise HTTPException(status_code=500, detail=error_msg)

@router.post("/upload")
async def upload_metasploit_file(file: UploadFile = File(...)):
    """Загрузка файла Metasploit"""
    try:
        if not file.filename.endswith('.json'):
            raise HTTPException(status_code=400, detail="Only JSON files are supported")
        
        # Читаем содержимое файла
        content = await file.read()
        data = json.loads(content.decode('utf-8'))
        
        # Обрабатываем и сохраняем данные
        count = await metasploit_service.process_and_save_metasploit_data(data)
        
        return JSONResponse(content={
            'success': True,
            'count': count,
            'message': f'Successfully uploaded {count} metasploit modules'
        })
        
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON file")
    except Exception as e:
        logger.error(f"Error uploading metasploit file: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/cancel")
async def cancel_metasploit_download():
    """Отмена текущей загрузки Metasploit"""
    try:
        from services.metasploit_worker import metasploit_worker
        
        success = await metasploit_worker.cancel_download()
        
        if success:
            return JSONResponse(content={
                'success': True,
                'message': 'Загрузка Metasploit отменена'
            })
        else:
            return JSONResponse(content={
                'success': False,
                'message': 'Нет активной загрузки для отмены'
            })
    except Exception as e:
        logger.error(f"Error cancelling metasploit download: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/preview")
async def get_metasploit_preview():
    """Получить первые 20 записей Metasploit для предварительного просмотра"""
    try:
        db = get_db()
        
        # Получаем первые 20 записей из базы данных
        query = """
            SELECT module_name, name, rank, rank_text, disclosure_date, 
                   type, description, "references", created_at, updated_at
            FROM vulnanalizer.metasploit_modules 
            ORDER BY created_at DESC 
            LIMIT 20
        """
        
        conn = await db.get_connection()
        try:
            results = await conn.fetch(query)
        finally:
            await db.release_connection(conn)
        
        # Конвертируем результаты в список словарей
        modules = []
        for row in results:
            modules.append({
                "module_name": row['module_name'],
                "name": row['name'],
                "rank": row['rank'],
                "rank_text": row['rank_text'],
                "disclosure_date": row['disclosure_date'].isoformat() if row['disclosure_date'] else None,
                "type": row['type'],
                "description": row['description'],
                "references": row['references'],
                "created_at": row['created_at'].isoformat() if row['created_at'] else None,
                "updated_at": row['updated_at'].isoformat() if row['updated_at'] else None
            })
        
        return JSONResponse(content={
            "success": True,
            "modules": modules,
            "count": len(modules)
        })
    except Exception as e:
        logger.error(f"Error getting metasploit preview: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/clear")
async def clear_metasploit_data():
    """Очистка всех данных Metasploit"""
    try:
        success = await metasploit_service.clear_metasploit_data()
        if success:
            return JSONResponse(content={
                'success': True,
                'message': 'Metasploit data cleared successfully'
            })
        else:
            raise HTTPException(status_code=500, detail="Failed to clear metasploit data")
    except Exception as e:
        logger.error(f"Error clearing metasploit data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


