from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import os
import sys

# TODO: Добавить импорт auth модуля после исправления путей
# from auth.database import AuthDatabase

# Backup роуты перенесены в vulnanalizer/app/routes/backup.py

def get_version():
    try:
        with open('VERSION', 'r') as f:
            return f.read().strip()
    except:
        return "0.6.03"

app = FastAPI(title="STools Main Service", version=get_version())

# Логируем информацию о приложении (отладочно)
# print(f"🚀 FastAPI приложение создано: {app.title} v{app.version}")
# print(f"📁 Текущая директория: {os.getcwd()}")
# print(f"📁 Файлы в текущей директории: {os.listdir('.')}")

# Добавляем CORS middleware
app.mount("/static", StaticFiles(directory="static"), name="static")

# Настройка шаблонов
templates = Jinja2Templates(directory="templates")

# TODO: Инициализировать auth_db после исправления импорта
# auth_db = AuthDatabase()

# TODO: Добавить функции аутентификации после исправления импорта
async def get_current_user(request: Request) -> dict:
    """Получить текущего пользователя из сессии"""
    # Временно возвращаем admin для тестирования
    return {"username": "admin", "is_admin": True}

async def require_admin(request: Request) -> dict:
    """Требовать права администратора"""
    # Временно разрешаем доступ для тестирования
    user = await get_current_user(request)
    if not user.get('is_admin', False):
        raise HTTPException(status_code=403, detail="Требуются права администратора")
    return user

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
    # Проверяем права администратора
    await require_admin(request)
    return templates.TemplateResponse("users.html", {"request": request, "version": get_version()})

@app.get("/background-tasks/", response_class=HTMLResponse)
async def background_tasks_page(request: Request):
    """Страница управления очередями"""
    # Проверяем права администратора
    await require_admin(request)
    return templates.TemplateResponse("background-tasks.html", {"request": request, "version": get_version()})

@app.get("/settings/", response_class=HTMLResponse)
async def settings_page(request: Request):
    """Страница общих настроек системы"""
    # Проверяем права администратора
    await require_admin(request)
    return templates.TemplateResponse("settings.html", {"request": request, "version": get_version()})

# Backup роуты подключены в vulnanalizer/app/main.py

@app.get("/api/version")
async def get_api_version():
    """Получить версию API"""
    return {"version": get_version(), "api": "v1"}

# Тестовый роут для проверки
# Тестовый эндпоинт удален

@app.get("/simple-test")
async def simple_test():
    """Простой тестовый роут"""
    return {"message": "Простой тест работает!"}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "main"}

# Логируем зарегистрированные роуты (отладочно)
# print("�� Зарегистрированные роуты:")
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
