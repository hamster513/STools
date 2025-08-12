"""
Главный файл приложения VulnAnalizer
"""
from fastapi import FastAPI, Response
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

# Импортируем роуты
from routes.system import router as system_router
from routes.hosts import router as hosts_router
from routes.epss import router as epss_router
from routes.exploitdb import router as exploitdb_router
from routes.cve import router as cve_router
from routes.vm import router as vm_router
from routes.users import router as users_router

# Создаем приложение
app = FastAPI(
    title="VulnAnalizer API",
    description="API для анализа уязвимостей",
    version="0.3.0002"
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

# Кастомный роут для CSS файла с заголовками для предотвращения кэширования
@app.get("/static/css/style.css")
async def get_css():
    """Возвращает CSS файл с заголовками для предотвращения кэширования"""
    return FileResponse(
        "static/css/style.css",
        media_type="text/css",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0"
        }
    )

# Подключаем роуты
app.include_router(system_router)
app.include_router(hosts_router)
app.include_router(epss_router)
app.include_router(exploitdb_router)
app.include_router(cve_router)
app.include_router(vm_router)
app.include_router(users_router)

# События жизненного цикла
@app.on_event("startup")
async def startup():
    """Событие запуска приложения"""
    # Проверяем соединение с базой данных
    from database import get_db
    db = get_db()
    try:
        db.execute("SELECT 1")
        print("✅ База данных подключена")
    except Exception as e:
        print(f"❌ Ошибка подключения к базе данных: {e}")


@app.on_event("shutdown")
async def shutdown():
    """Событие остановки приложения"""
    # Закрытие соединений происходит автоматически
    print("🔄 Приложение остановлено")
