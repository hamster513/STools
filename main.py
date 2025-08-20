from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
import os

def get_version():
    try:
        with open('VERSION', 'r') as f:
            return f.read().strip()
    except:
        return "0.5.00"

app = FastAPI(title="STools", version=get_version())

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
    return templates.TemplateResponse("base.html", {"request": request})

@app.get("/users/", response_class=HTMLResponse)
async def users_page(request: Request):
    """Страница управления пользователями"""
    return templates.TemplateResponse("users.html", {"request": request})

@app.get("/background-tasks/", response_class=HTMLResponse)
async def background_tasks_page(request: Request):
    """Страница управления очередями"""
    return templates.TemplateResponse("background-tasks.html", {"request": request})

@app.get("/settings/", response_class=HTMLResponse)
async def settings_page(request: Request):
    """Страница общих настроек системы"""
    return templates.TemplateResponse("settings.html", {"request": request, "version": get_version()})

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "main"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
