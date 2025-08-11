"""
Системные роуты (health, version, settings, system status)
"""
import os
import psutil
from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def read_root():
    """Главная страница"""
    with open("templates/index.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())


@router.get("/login", response_class=HTMLResponse)
async def login_page():
    """Страница входа"""
    with open("templates/login.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())


@router.get("/api/settings")
async def get_settings():
    """Получить настройки приложения"""
    try:
        with open("data/settings.json", "r", encoding="utf-8") as f:
            import json
            return json.load(f)
    except FileNotFoundError:
        # Возвращаем настройки по умолчанию
        return {
            "impact_resource_criticality": "Medium",
            "impact_confidential_data": "Отсутствуют",
            "impact_internet_access": "Недоступен"
        }


@router.post("/api/settings")
async def update_settings(settings: dict):
    """Обновить настройки приложения"""
    try:
        os.makedirs("data", exist_ok=True)
        with open("data/settings.json", "w", encoding="utf-8") as f:
            import json
            json.dump(settings, f, ensure_ascii=False, indent=2)
        return {"message": "Настройки обновлены"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка сохранения настроек: {str(e)}")


@router.get("/api/health")
async def health_check():
    """Проверка здоровья приложения"""
    try:
        # Проверяем подключение к базе данных
        from database import get_db
        db = get_db()
        await db.test_connection()
        
        return {
            "status": "healthy",
            "database": "connected",
            "timestamp": "2024-01-01T00:00:00Z"
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Service unhealthy: {str(e)}")


@router.get("/api/version")
async def get_version():
    """Получить версию приложения"""
    try:
        with open("VERSION", "r") as f:
            version = f.read().strip()
        return {"version": version}
    except FileNotFoundError:
        return {"version": "unknown"}


@router.get("/api/system/status")
async def get_system_status():
    """Получить статус системы и использование ресурсов"""
    try:
        # Получаем информацию о памяти
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Получаем информацию о процессе
        process = psutil.Process(os.getpid())
        
        return {
            "memory": {
                "total_mb": memory.total // (1024 * 1024),
                "available_mb": memory.available // (1024 * 1024),
                "used_mb": memory.used // (1024 * 1024),
                "percent": memory.percent
            },
            "disk": {
                "total_gb": disk.total // (1024 * 1024 * 1024),
                "free_gb": disk.free // (1024 * 1024 * 1024),
                "used_gb": disk.used // (1024 * 1024 * 1024),
                "percent": (disk.used / disk.total) * 100
            },
            "process": {
                "memory_mb": process.memory_info().rss // (1024 * 1024),
                "cpu_percent": process.cpu_percent(),
                "threads": process.num_threads()
            }
        }
    except Exception as e:
        return {"error": str(e)}
