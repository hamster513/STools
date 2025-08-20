from fastapi import FastAPI, HTTPException, Depends, Request, Response, Form
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import jwt
import os
from datetime import datetime, timedelta
from typing import Optional
import json

from database import AuthDatabase

def get_version():
    try:
        with open('VERSION', 'r') as f:
            return f.read().strip()
    except:
        return "0.5.00"

app = FastAPI(title="STools Auth Service", version=get_version())

# Настройки JWT
SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'your-secret-key-change-in-production')
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Инициализация базы данных
auth_db = AuthDatabase()

# Безопасность
security = HTTPBearer()

# Статические файлы и шаблоны
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Кастомный роут для CSS файла с заголовками для предотвращения кэширования
@app.get("/static/css/main.css")
async def get_main_css():
    return FileResponse(
        "../static/css/main.css",
        media_type="text/css",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0"
        }
    )

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Создание JWT токена"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str) -> Optional[dict]:
    """Проверка JWT токена"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.PyJWTError:
        return None

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """Получение текущего пользователя из токена"""
    token = credentials.credentials
    payload = verify_token(token)
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    username = payload.get("sub")
    if username is None:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    user = await auth_db.get_user_by_username(username)
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    
    return user

@app.on_event("startup")
async def startup():
    """Инициализация при запуске"""
    await auth_db.connect()

@app.on_event("shutdown")
async def shutdown():
    """Очистка при выключении"""
    await auth_db.close()

@app.get("/", response_class=HTMLResponse)
async def login_page(request: Request):
    """Страница входа"""
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/users", response_class=HTMLResponse)
async def users_page(request: Request):
    """Страница управления пользователями"""
    return templates.TemplateResponse("users.html", {"request": request})

from pydantic import BaseModel
from typing import Optional

class UserCreate(BaseModel):
    username: str
    email: Optional[str] = None
    password: str
    is_admin: bool = False
    is_active: bool = True

class UserUpdate(BaseModel):
    username: str
    email: Optional[str] = None
    is_active: bool
    is_admin: bool

class PasswordUpdate(BaseModel):
    password: str

@app.post("/api/login")
async def login(username: str = Form(...), password: str = Form(...)):
    """Вход пользователя"""
    user = await auth_db.verify_password(username, password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Создаем токен
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user['username']}, expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user['id'],
            "username": user['username'],
            "email": user['email'],
            "is_admin": user['is_admin']
        }
    }

@app.get("/api/users")
async def get_users(current_user: dict = Depends(get_current_user)):
    """Получение списка пользователей (только для админов)"""
    if not current_user['is_admin']:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    users = await auth_db.get_all_users()
    return {"users": users}

@app.get("/api/users/{user_id}")
async def get_user(user_id: int, current_user: dict = Depends(get_current_user)):
    """Получение пользователя по ID (только для админов)"""
    if not current_user['is_admin']:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    user = await auth_db.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return user

@app.post("/api/users")
async def create_user(
    user_data: UserCreate,
    current_user: dict = Depends(get_current_user)
):
    """Создание нового пользователя (только для админов)"""
    if not current_user['is_admin']:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Проверяем уникальность
    if await auth_db.check_username_exists(user_data.username):
        raise HTTPException(status_code=400, detail="Username already exists")
    
    if user_data.email and await auth_db.check_email_exists(user_data.email):
        raise HTTPException(status_code=400, detail="Email already exists")
    
    user = await auth_db.create_user(user_data.username, user_data.email, user_data.password, user_data.is_admin, user_data.is_active)
    return {"message": "User created successfully", "user": user}

@app.put("/api/users/{user_id}")
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Обновление пользователя (только для админов)"""
    if not current_user['is_admin']:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Проверяем уникальность
    if await auth_db.check_username_exists(user_data.username, user_id):
        raise HTTPException(status_code=400, detail="Username already exists")
    
    if user_data.email and await auth_db.check_email_exists(user_data.email, user_id):
        raise HTTPException(status_code=400, detail="Email already exists")
    
    success = await auth_db.update_user(user_id, user_data.username, user_data.email, user_data.is_active, user_data.is_admin)
    if not success:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {"message": "User updated successfully"}

@app.put("/api/users/{user_id}/password")
async def update_user_password(
    user_id: int,
    password_data: PasswordUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Обновление пароля пользователя (только для админов)"""
    if not current_user['is_admin']:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    success = await auth_db.update_user_password(user_id, password_data.password)
    if not success:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {"message": "Password updated successfully"}

@app.delete("/api/users/{user_id}")
async def delete_user(
    user_id: int,
    current_user: dict = Depends(get_current_user)
):
    """Удаление пользователя (только для админов)"""
    if not current_user['is_admin']:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Нельзя удалить самого себя
    if user_id == current_user['id']:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")
    
    success = await auth_db.delete_user(user_id)
    if not success:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {"message": "User deleted successfully"}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Проверяем подключение к базе данных
        await auth_db.connect()
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}

@app.get("/api/version")
async def get_version():
    """Get application version"""
    try:
        with open('/app/VERSION', 'r') as f:
            version = f.read().strip()
        return {"version": version}
    except Exception as e:
        return {"version": "unknown"}

@app.get("/api/me")
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    """Получение информации о текущем пользователе"""
    return {
        "id": current_user['id'],
        "username": current_user['username'],
        "email": current_user['email'],
        "is_admin": current_user['is_admin']
    }

@app.post("/api/verify")
async def verify_token_endpoint(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Проверка токена"""
    payload = verify_token(credentials.credentials)
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    return {"valid": True, "username": payload.get("sub")}
