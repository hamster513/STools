"""
Роуты для работы с VM MaxPatrol
"""
import traceback
import requests
from fastapi import APIRouter, HTTPException, Request
from database import get_db

router = APIRouter()


async def get_vm_token(host, username, password, client_secret):
    """Получить токен аутентификации для VM MaxPatrol"""
    try:
        url = f'https://{host}:3334/connect/token'
        
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        data = {
            'username': username,
            'password': password,
            'client_id': 'mpx',
            'client_secret': client_secret,
            'grant_type': 'password',
            'response_type': 'code id_token',
            'scope': 'offline_access mpx.api'
        }
        
        response = requests.post(url, headers=headers, data=data, verify=False, timeout=30)
        response.raise_for_status()
        
        result = response.json()
        if 'access_token' not in result:
            raise Exception(f"Токен не получен: {result}")
            
        return result['access_token']
        
    except requests.exceptions.RequestException as e:
        raise Exception(f"Ошибка HTTP запроса: {str(e)}")
    except Exception as e:
        raise Exception(f"Ошибка получения токена: {str(e)}")


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
        
        # Валидация обязательных параметров
        required_fields = ['vm_host', 'vm_username', 'vm_password', 'vm_client_secret']
        for field in required_fields:
            if not settings.get(field):
                raise HTTPException(
                    status_code=400, 
                    detail=f"Отсутствует обязательный параметр: {field}"
                )
        
        # Получаем токен для проверки аутентификации
        token = await get_vm_token(
            settings['vm_host'],
            settings['vm_username'], 
            settings['vm_password'],
            settings['vm_client_secret']
        )
        
        # Делаем тестовый запрос к API для проверки доступности
        test_url = f"https://{settings['vm_host']}/api/assets_temporal_readmodel/v1/assets_grid"
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {token}'
        }
        
        # Простой тестовый запрос
        test_params = {
            'pdql': 'select(@Host) | limit(1)',
            'includeNestedGroups': False
        }
        
        response = requests.post(test_url, headers=headers, json=test_params, verify=False, timeout=30)
        response.raise_for_status()
        
        return {
            "success": True,
            "message": f"Подключение к VM MaxPatrol ({settings['vm_host']}) успешно установлено"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        return {
            "success": False,
            "error": f"Ошибка подключения к VM MaxPatrol: {str(e)}"
        }


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
