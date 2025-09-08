"""
Роуты для работы с VM MaxPatrol
"""
import traceback
from fastapi import APIRouter, HTTPException, Request
from database import get_db

router = APIRouter()


@router.get("/api/vm/settings")
async def get_vm_settings():
    """Получить настройки VM MaxPatrol"""
    try:
        db = get_db()
        settings = await db.get_vm_settings()
        return settings
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка получения настроек: {str(e)}")


@router.post("/api/vm/settings")
async def update_vm_settings(request: Request):
    """Обновить настройки VM MaxPatrol"""
    try:
        settings = await request.json()
        db = get_db()
        await db.update_vm_settings(settings)
        return {"success": True, "message": "Настройки VM MaxPatrol обновлены"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка сохранения настроек: {str(e)}")


@router.post("/api/vm/test-connection")
async def test_vm_connection(request: Request):
    """Тестировать подключение к VM MaxPatrol"""
    try:
        settings = await request.json()
        
        # Здесь должна быть логика тестирования подключения к VM MaxPatrol
        # Пока возвращаем заглушку
        return {
            "success": True,
            "message": "Подключение к VM MaxPatrol успешно"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка подключения: {str(e)}")


@router.post("/api/vm/import")
async def import_vm_hosts():
    """Импортировать хосты из VM MaxPatrol"""
    try:
        # Получаем настройки из базы данных
        db = get_db()
        settings = await db.get_vm_settings()
        
        if not settings.get('vm_host') or not settings.get('vm_username'):
            raise HTTPException(status_code=400, detail="Настройки VM MaxPatrol не настроены")
        
        # Здесь должна быть логика импорта хостов из VM MaxPatrol
        # Пока возвращаем заглушку
        return {
            "success": True,
            "message": "Импорт хостов из VM MaxPatrol завершен",
            "count": 0
        }
    except HTTPException:
        raise
    except Exception as e:
        print('VM import error:', traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/vm/status")
async def get_vm_status():
    """Получить статус подключения к VM MaxPatrol"""
    try:
        # Получаем настройки из базы данных
        db = get_db()
        settings = await db.get_vm_settings()
        
        if not settings.get('vm_host') or not settings.get('vm_username'):
            return {
                "connected": False,
                "message": "Настройки VM MaxPatrol не настроены"
            }
        
        # Здесь должна быть логика проверки статуса подключения
        # Пока возвращаем заглушку
        return {
            "connected": True,
            "message": "Подключение к VM MaxPatrol активно"
        }
    except Exception as e:
        return {
            "connected": False,
            "message": f"Ошибка подключения: {str(e)}"
        }
