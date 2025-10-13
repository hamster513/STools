"""
Главный файл приложения VulnAnalizer
"""
from fastapi import FastAPI, Response, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
import os

# Импортируем роуты
from routes.system import router as system_router
from routes.hosts import router as hosts_router
from routes.epss import router as epss_router
from routes.exploitdb import router as exploitdb_router
from routes.cve import router as cve_router
from routes.vm import router as vm_router
from routes.metasploit import router as metasploit_router
from routes.backup import router as backup_router
from routes.archive import router as archive_router

def get_version():
    try:
        with open('/app/VERSION', 'r') as f:
            return f.read().strip()
    except:
        return "0.6.00"

# Создаем приложение
app = FastAPI(
    title="VulnAnalizer API",
    description="API для анализа уязвимостей",
    version=get_version()
)

# Настройки CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключаем статические файлы
app.mount("/static", StaticFiles(directory="static"), name="static")

# Настройка шаблонов
# Настройка шаблонов с поддержкой кроссплатформенности
template_dirs = ["templates"]
shared_templates_path = os.getenv('SHARED_TEMPLATES_PATH', None)
if shared_templates_path:
    template_dirs.append(shared_templates_path)

templates = Jinja2Templates(directory=template_dirs)

# Кастомный роут для CSS файла с заголовками для предотвращения кэширования
@app.get("/static/css/style.css")
async def get_style_css():
    return FileResponse(
        "static/css/style.css",
        media_type="text/css",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0"
        }
    )

# Кастомный роут для collapsible.css с заголовками для предотвращения кэширования
@app.get("/static/css/components/collapsible.css")
async def get_collapsible_css():
    return FileResponse(
        "static/css/components/collapsible.css",
        media_type="text/css",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0"
        }
    )

# Новый роут для CSS файлов через API
@app.get("/api/css/collapsible.css")
async def get_collapsible_css_api():
    return FileResponse(
        "static/css/components/collapsible.css",
        media_type="text/css",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0"
        }
    )

# Новый роут для CSS файлов через специальный путь
@app.get("/css-debug/collapsible.css")
@app.head("/css-debug/collapsible.css")
async def get_collapsible_css_debug():
    return FileResponse(
        "static/css/components/collapsible.css",
        media_type="text/css",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0"
        }
    )

# Главная страница
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Главная страница VulnAnalizer"""
    return templates.TemplateResponse("index.html", {"request": request, "version": get_version()})

# Подключаем роуты
app.include_router(system_router)
app.include_router(hosts_router)
app.include_router(epss_router)
app.include_router(exploitdb_router)
app.include_router(cve_router)
app.include_router(vm_router)
app.include_router(metasploit_router)
app.include_router(backup_router)
app.include_router(archive_router)

# События жизненного цикла
@app.on_event("startup")
async def startup():
    """Событие запуска приложения"""
    # Проверяем соединение с базой данных
    from database import get_db
    db = get_db()
    try:
        conn = await db.get_connection()
        await conn.execute("SELECT 1")
        await db.release_connection(conn)
        print("✅ База данных подключена")
        
        # Инициализируем планировщик фоновых задач
        from services.scheduler_service import scheduler_service
        await scheduler_service.start_scheduler()
        print("✅ Планировщик фоновых задач запущен")
        
    except Exception as e:
        print(f"❌ Ошибка подключения к базе данных: {e}")


@app.on_event("shutdown")
async def shutdown():
    """Событие остановки приложения"""
    # Останавливаем планировщик
    try:
        from services.scheduler_service import scheduler_service
        await scheduler_service.stop_scheduler()
        print("🔄 Планировщик остановлен")
    except Exception as e:
        print(f"⚠️ Ошибка остановки планировщика: {e}")
    
    print("🔄 Приложение остановлено")
