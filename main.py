from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import os

# Импортируем роуты (временно отключено)
# from routes.backup import router as backup_router

def get_version():
    try:
        with open('VERSION', 'r') as f:
            return f.read().strip()
    except:
        return "0.6.03"

app = FastAPI(title="STools", version=get_version())

# Логируем информацию о приложении (отладочно)
# print(f"🚀 FastAPI приложение создано: {app.title} v{app.version}")
# print(f"📁 Текущая директория: {os.getcwd()}")
# print(f"📁 Файлы в текущей директории: {os.listdir('.')}")

# Добавляем CORS middleware
app.mount("/static", StaticFiles(directory="static"), name="static")

# Настройка шаблонов
templates = Jinja2Templates(directory="templates")

# Добавляем CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Главная страница - перенаправляем на vulnanalizer"""
    return templates.TemplateResponse("base.html", {"request": request, "version": get_version()})

@app.get("/users/", response_class=HTMLResponse)
async def users_page(request: Request):
    """Страница управления пользователями"""
    return templates.TemplateResponse("users.html", {"request": request, "version": get_version()})

@app.get("/background-tasks/", response_class=HTMLResponse)
async def background_tasks_page(request: Request):
    """Страница управления очередями"""
    return templates.TemplateResponse("background-tasks.html", {"request": request, "version": get_version()})

@app.get("/settings/", response_class=HTMLResponse)
async def settings_page(request: Request):
    """Страница общих настроек системы"""
    return templates.TemplateResponse("settings.html", {"request": request, "version": get_version()})

# Подключаем роуты (временно отключено)
# try:
#     app.include_router(backup_router)
#     print("✅ Backup router подключен успешно")
# except Exception as e:
#     print(f"❌ Ошибка подключения backup router: {e}")

# Простые роуты для бэкапа (временно)
@app.get("/api/backup/tables")
async def get_backup_tables():
    """Получить список доступных таблиц для бэкапа"""
    tables = [
        {"schema": "auth", "name": "users", "description": "Пользователи системы"},
        {"schema": "auth", "name": "sessions", "description": "Сессии пользователей"},
        {"schema": "vulnanalizer", "name": "cve", "description": "Уязвимости CVE"},
        {"schema": "vulnanalizer", "name": "hosts", "description": "Хосты"},
                    {"schema": "vulnanalizer", "name": "metasploit_modules", "description": "Модули Metasploit"},
        {"schema": "vulnanalizer", "name": "epss", "description": "Данные EPSS"},
        {"schema": "vulnanalizer", "name": "exploitdb", "description": "База ExploitDB"},
        {"schema": "vulnanalizer", "name": "background_tasks", "description": "Фоновые задачи"},
        {"schema": "vulnanalizer", "name": "settings", "description": "Настройки"},
        {"schema": "loganalizer", "name": "log_entries", "description": "Записи логов"},
        {"schema": "loganalizer", "name": "log_files", "description": "Файлы логов"},
        {"schema": "loganalizer", "name": "analysis_settings", "description": "Настройки анализа"}
    ]
    return {"success": True, "tables": tables}

@app.get("/api/backup/list")
async def list_backups():
    """Получить список бэкапов"""
    return {"success": True, "backups": []}

@app.post("/api/backup/create")
async def create_backup(request: dict):
    """Создать бэкап выбранных таблиц"""
    try:
        if not request.get('tables'):
            raise HTTPException(status_code=400, detail="Не выбрано ни одной таблицы")
        
        # Здесь должна быть логика создания бэкапа
        # Пока возвращаем заглушку
        return {
            "success": True, 
            "message": "Бэкап создан успешно",
            "backup_id": f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка создания бэкапа: {str(e)}")

@app.get("/api/version")
async def get_api_version():
    """Получить версию API"""
    return {"version": get_version(), "api": "v1"}

# Тестовый роут для проверки
@app.get("/test-backup")
async def test_backup():
    """Тестовый роут для проверки"""
    return {"message": "Backup API работает!", "status": "ok"}

@app.get("/simple-test")
async def simple_test():
    """Простой тестовый роут"""
    return {"message": "Простой тест работает!"}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "main"}

# Логируем зарегистрированные роуты (отладочно)
# print("📋 Зарегистрированные роуты:")
# for route in app.routes:
#     try:
#         if hasattr(route, 'path') and hasattr(route, 'methods'):
#             print(f"  - {route.methods} {route.path}")
#         elif hasattr(route, 'path'):
#             print(f"  - {route.path}")
#     except Exception as e:
#         print(f"  - Ошибка при обработке роута: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
