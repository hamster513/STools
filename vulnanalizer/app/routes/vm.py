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
        
        # Проверяем, не запущена ли уже задача импорта
        existing_task = await db.get_background_task_by_type('vm_import')
        if existing_task and existing_task['status'] in ['processing', 'running', 'initializing', 'idle']:
            return {"success": False, "message": "Импорт VM данных уже запущен"}
        
        # Создаем фоновую задачу для импорта
        task_id = await db.create_background_task(
            task_type="vm_import",
            parameters={
                "import_type": "vm_maxpatrol"
            },
            description="Импорт данных из VM MaxPatrol"
        )
        
        print(f"✅ Фоновая задача импорта VM создана: {task_id}")
        
        return {
            "success": True,
            "task_id": task_id,
            "message": "Импорт данных из VM MaxPatrol запущен в фоновом режиме"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print('VM import error:', traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/vm/manual-import")
async def manual_import_vm_hosts(request: Request):
    """Ручной импорт хостов из сохраненного файла VM с фильтрами"""
    try:
        # Проверяем, не запущена ли уже задача импорта
        db = get_db()
        existing_task = await db.get_background_task_by_type('vm_manual_import')
        if existing_task and existing_task['status'] in ['processing', 'running', 'initializing', 'idle']:
            return {"success": False, "message": "Ручной импорт VM данных уже запущен"}
        
        # Получаем данные из JSON запроса
        try:
            body = await request.json()
            criticality_filter = body.get('criticality_filter', '')
            os_filter = body.get('os_filter', '')
            zone_filter = body.get('zone_filter', '')
        except:
            criticality_filter = ''
            os_filter = ''
            zone_filter = ''
        
        # Логируем фильтры
        if criticality_filter:
            print(f"🔍 Фильтр критичности для ручного импорта: {criticality_filter}")
        if os_filter:
            print(f"🔍 Фильтр ОС для ручного импорта: {os_filter}")
        if zone_filter:
            print(f"🔍 Фильтр зоны для ручного импорта: {zone_filter}")
        
        # Создаем фоновую задачу для ручного импорта с фильтрами
        task_parameters = {
            "import_type": "vm_manual_import",
            "criticality_filter": criticality_filter,
            "os_filter": os_filter,
            "zone_filter": zone_filter
        }
        
        task_id = await db.create_background_task(
            task_type="vm_manual_import",
            parameters=task_parameters,
            description="Ручной импорт данных из файла VM MaxPatrol"
        )
        
        print(f"✅ Фоновая задача ручного импорта VM создана: {task_id}")
        
        return {
            "success": True,
            "task_id": task_id,
            "message": "Ручной импорт данных из файла VM запущен в фоновом режиме"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print('VM manual import error:', traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/vm/file-status")
async def get_vm_file_status():
    """Получить статус файла VM в папке vm_imports"""
    try:
        import os
        from pathlib import Path
        from datetime import datetime
        
        vm_data_dir = "/app/data/vm_imports"
        
        # Проверяем существование директории
        if not os.path.exists(vm_data_dir):
            return {
                "success": True,
                "file_exists": False,
                "message": "Директория vm_imports не найдена"
            }
        
        # Ищем файлы VM данных
        vm_files = []
        for filename in os.listdir(vm_data_dir):
            if filename.startswith("vm_data_") and filename.endswith(".json"):
                file_path = os.path.join(vm_data_dir, filename)
                stat = os.stat(file_path)
                vm_files.append({
                    "filename": filename,
                    "file_path": file_path,
                    "file_size": stat.st_size,
                    "file_size_mb": stat.st_size / (1024 * 1024),
                    "created_at": datetime.fromtimestamp(stat.st_ctime).strftime("%Y-%m-%d %H:%M:%S")
                })
        
        if vm_files:
            # Берем самый новый файл
            latest_file = max(vm_files, key=lambda x: x["created_at"])
            return {
                "success": True,
                "file_exists": True,
                "filename": latest_file["filename"],
                "file_size": latest_file["file_size"],
                "file_size_mb": latest_file["file_size_mb"],
                "created_at": latest_file["created_at"]
            }
        else:
            return {
                "success": True,
                "file_exists": False,
                "message": "Файлы VM данных не найдены"
            }
            
    except Exception as e:
        return {
            "success": False,
            "file_exists": False,
            "message": f"Ошибка проверки файла: {str(e)}"
        }


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
