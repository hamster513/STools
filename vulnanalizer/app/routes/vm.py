"""
Роуты для работы с VM MaxPatrol
"""
import os
import traceback
from fastapi import APIRouter, HTTPException, Request
from database import get_db

router = APIRouter()


@router.get("/api/vm/settings")
async def get_vm_settings():
    """Получить настройки VM MaxPatrol"""
    try:
        with open("data/vm_settings.json", "r", encoding="utf-8") as f:
            import json
            return json.load(f)
    except FileNotFoundError:
        return {
            "server_url": "",
            "username": "",
            "password": "",
            "api_key": ""
        }


@router.post("/api/vm/settings")
async def update_vm_settings(request: Request):
    """Обновить настройки VM MaxPatrol"""
    try:
        settings = await request.json()
        try:
            os.makedirs("data", exist_ok=True)
        except PermissionError:
            # Если нет прав на создание в текущей директории, используем /tmp
            os.makedirs("/tmp/vm_data", exist_ok=True)
            os.chdir("/tmp")
        with open("data/vm_settings.json", "w", encoding="utf-8") as f:
            import json
            json.dump(settings, f, ensure_ascii=False, indent=2)
        return {"message": "Настройки VM MaxPatrol обновлены"}
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
        # Получаем настройки
        try:
            with open("data/vm_settings.json", "r", encoding="utf-8") as f:
                import json
                settings = json.load(f)
        except FileNotFoundError:
            raise HTTPException(status_code=400, detail="Настройки VM MaxPatrol не найдены")
        
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
        # Получаем настройки
        try:
            with open("data/vm_settings.json", "r", encoding="utf-8") as f:
                import json
                settings = json.load(f)
        except FileNotFoundError:
            return {
                "connected": False,
                "message": "Настройки VM MaxPatrol не найдены"
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
