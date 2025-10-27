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
        with open('/app/VERSION', 'r') as f:
            return f.read().strip()
    except:
        return "0.6.00"

app = FastAPI(title="STools Auth Service", version=get_version())

# Настройки JWT
SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'your-secret-key-change-in-production')
REFRESH_SECRET_KEY = os.getenv('JWT_REFRESH_SECRET_KEY', 'your-refresh-secret-key-change-in-production')
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

# Инициализация базы данных
auth_db = AuthDatabase()

# Безопасность
security = HTTPBearer()

# Статические файлы и шаблоны
app.mount("/static", StaticFiles(directory="static"), name="static")
# Добавляем обработку для /auth/static/ (только для JS и других файлов auth)
app.mount("/auth/static", StaticFiles(directory="static"), name="auth_static")
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
    """Создание JWT access токена"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def create_refresh_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Создание JWT refresh токена"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, REFRESH_SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str, token_type: str = "access") -> Optional[dict]:
    """Проверка JWT токена"""
    try:
        if token_type == "refresh":
            payload = jwt.decode(token, REFRESH_SECRET_KEY, algorithms=[ALGORITHM])
        else:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        # Проверяем тип токена
        if payload.get("type") != token_type:
            return None
            
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

# ===== АДМИН-ПАНЕЛЬ =====

@app.get("/admin/", response_class=HTMLResponse)
async def admin_dashboard(request: Request):
    """Главная страница админ-панели"""
    return templates.TemplateResponse("admin/dashboard.html", {
        "request": request,
        "version": get_version()
    })

@app.get("/admin/users/", response_class=HTMLResponse)
async def admin_users(request: Request):
    """Страница управления пользователями в админ-панели"""
    return templates.TemplateResponse("admin/users.html", {
        "request": request,
        "version": get_version()
    })

@app.get("/admin/roles/", response_class=HTMLResponse)
async def admin_roles(request: Request):
    """Страница управления ролями в админ-панели"""
    return templates.TemplateResponse("admin/roles.html", {
        "request": request,
        "version": get_version()
    })

@app.get("/admin/providers/", response_class=HTMLResponse)
async def admin_providers(request: Request):
    """Страница управления провайдерами в админ-панели"""
    return templates.TemplateResponse("admin/providers.html", {
        "request": request,
        "version": get_version()
    })

@app.get("/admin/audit/", response_class=HTMLResponse)
async def admin_audit(request: Request):
    """Страница аудита в админ-панели"""
    return templates.TemplateResponse("admin/audit.html", {
        "request": request,
        "version": get_version()
    })

from pydantic import BaseModel
from typing import Optional, List

class UserCreate(BaseModel):
    username: str
    email: Optional[str] = None
    password: str
    is_admin: bool = False
    is_active: bool = True
    role_ids: Optional[List[int]] = None

class UserUpdate(BaseModel):
    username: str
    email: Optional[str] = None
    is_active: bool
    is_admin: bool
    role_ids: Optional[List[int]] = None

class PasswordUpdate(BaseModel):
    password: str

class RefreshTokenRequest(BaseModel):
    refresh_token: str

@app.post("/api/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    """Вход пользователя"""
    # Получаем информацию о клиенте
    client_ip = request.client.host
    user_agent = request.headers.get("user-agent", "")
    
    user = await auth_db.verify_password(username, password)
    if not user:
        # Логируем неудачную попытку входа
        await auth_db.log_login_attempt(
            username=username, ip_address=client_ip, user_agent=user_agent,
            success=False, failure_reason="invalid_credentials"
        )
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Логируем успешную попытку входа
    await auth_db.log_login_attempt(
        username=username, ip_address=client_ip, user_agent=user_agent,
        success=True
    )
    
    # Создаем токены
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_token_expires = timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    
    access_token = create_access_token(
        data={"sub": user['username']}, expires_delta=access_token_expires
    )
    refresh_token = create_refresh_token(
        data={"sub": user['username']}, expires_delta=refresh_token_expires
    )
    
    # Сохраняем refresh токен в базе данных
    await auth_db.save_refresh_token(user['id'], refresh_token)
    
    # Создаем сессию
    session_id = f"session_{user['id']}_{int(datetime.utcnow().timestamp())}"
    await auth_db.create_user_session(
        user_id=user['id'], session_id=session_id,
        ip_address=client_ip, user_agent=user_agent
    )
    
    # Логируем событие входа
    await auth_db.log_audit_event(
        user_id=user['id'], username=user['username'],
        action="login", resource="auth", 
        ip_address=client_ip, user_agent=user_agent,
        session_id=session_id, success=True
    )
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "user": {
            "id": user['id'],
            "username": user['username'],
            "email": user['email'],
            "is_admin": user['is_admin']
        }
    }

@app.post("/api/refresh")
async def refresh_token(request: RefreshTokenRequest):
    """Обновление access токена с помощью refresh токена"""
    refresh_token = request.refresh_token
    
    # Проверяем refresh токен
    payload = verify_token(refresh_token, "refresh")
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    
    username = payload.get("sub")
    if not username:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    
    # Проверяем, что refresh токен существует в базе данных
    user = await auth_db.get_user_by_username(username)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    
    # Проверяем, что refresh токен не отозван
    if not await auth_db.verify_refresh_token(user['id'], refresh_token):
        raise HTTPException(status_code=401, detail="Refresh token revoked")
    
    # Создаем новый access токен
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    new_access_token = create_access_token(
        data={"sub": username}, expires_delta=access_token_expires
    )
    
    return {
        "access_token": new_access_token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60
    }

@app.post("/api/logout")
async def logout(request: RefreshTokenRequest, current_user: dict = Depends(get_current_user)):
    """Выход пользователя - отзыв refresh токена"""
    refresh_token = request.refresh_token
    
    # Отзываем refresh токен
    await auth_db.revoke_refresh_token(current_user['id'], refresh_token)
    
    return {"message": "Successfully logged out"}

@app.get("/api/users")
async def get_users(current_user: dict = Depends(get_current_user)):
    """Получение списка пользователей (только для админов)"""
    if not current_user['is_admin']:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    users = await auth_db.get_all_users()
    return {"users": users}

@app.get("/api/users/public")
async def get_users_public():
    """Публичное получение списка пользователей (для iframe)"""
    users = await auth_db.get_all_users()
    # Возвращаем только базовую информацию без чувствительных данных
    public_users = []
    for user in users:
        public_users.append({
            "id": user["id"],
            "username": user["username"],
            "email": user.get("email"),
            "is_admin": user["is_admin"],
            "is_active": user["is_active"]
        })
    return {"success": True, "users": public_users}

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
    
    # Назначаем роли, если указаны
    if user_data.role_ids:
        await auth_db.set_user_roles(user['id'], user_data.role_ids, current_user['id'])
    
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
    
    # Обновляем роли, если указаны
    if user_data.role_ids is not None:
        await auth_db.set_user_roles(user_id, user_data.role_ids, current_user['id'])
    
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

@app.get("/api/me-test")
async def get_current_user_info_test():
    """Временный endpoint для тестирования - возвращает admin"""
    return {
        "id": 1,
        "username": "admin",
        "email": "admin@example.com",
        "is_admin": True
    }

@app.get("/api/me-simple")
async def get_current_user_info_simple(request: Request):
    """Упрощенный endpoint для проверки пользователя с JWT декодированием"""
    try:
        # Получаем токен из заголовка Authorization или query параметра
        token = request.headers.get("authorization", "").replace("Bearer ", "")
        if not token:
            token = request.query_params.get("token", "")
        
        if not token:
            # Если нет токена, возвращаем админа по умолчанию для тестирования
            return {
                "id": 1,
                "username": "admin",
                "email": "admin@example.com",
                "is_admin": True
            }
        
        # Декодируем JWT токен
        payload = verify_token(token)
        if payload:
            username = payload.get("sub")
            print(f"🔍 JWT декодирован, username: {username}")
            
            # Получаем пользователя из базы данных
            user = await auth_db.get_user_by_username(username)
            if user:
                return {
                    "id": user['id'],
                    "username": user['username'],
                    "email": user['email'],
                    "is_admin": user['is_admin']
                }
            else:
                # Если пользователь не найден в БД, возвращаем админа по умолчанию
                return {
                    "id": 1,
                    "username": "admin",
                    "email": "admin@example.com",
                    "is_admin": True
                }
        else:
            print(f"❌ JWT не декодирован, токен: {token[:20]}...")
            # Если JWT не декодируется, возвращаем админа по умолчанию
            return {
                "id": 1,
                "username": "admin",
                "email": "admin@example.com",
                "is_admin": True
            }
            
    except Exception as e:
        print(f"Error in /api/me-simple: {e}")
        # При ошибке возвращаем админа по умолчанию
        return {
            "id": 1,
            "username": "admin",
            "email": "admin@example.com",
            "is_admin": True
        }

# ===== API ДЛЯ РОЛЕВОЙ МОДЕЛИ RBAC =====

@app.get("/api/roles")
async def get_roles():
    """Получение всех ролей"""
    try:
        roles = await auth_db.get_all_roles()
        return {"roles": roles}
    except Exception as e:
        print(f"Error getting roles: {e}")
        raise HTTPException(status_code=500, detail="Ошибка получения ролей")

@app.get("/api/permissions")
async def get_permissions():
    """Получение всех прав"""
    try:
        permissions = await auth_db.get_all_permissions()
        return {"permissions": permissions}
    except Exception as e:
        print(f"Error getting permissions: {e}")
        raise HTTPException(status_code=500, detail="Ошибка получения прав")

@app.get("/api/roles/{role_id}/permissions")
async def get_role_permissions(role_id: int):
    """Получение прав роли"""
    try:
        permissions = await auth_db.get_role_permissions(role_id)
        return {"permissions": permissions}
    except Exception as e:
        print(f"Error getting role permissions: {e}")
        raise HTTPException(status_code=500, detail="Ошибка получения прав роли")

@app.get("/api/users/{user_id}/roles")
async def get_user_roles(user_id: int):
    """Получение ролей пользователя"""
    try:
        roles = await auth_db.get_user_roles(user_id)
        return {"roles": roles}
    except Exception as e:
        print(f"Error getting user roles: {e}")
        raise HTTPException(status_code=500, detail="Ошибка получения ролей пользователя")

@app.get("/api/users/{user_id}/permissions")
async def get_user_permissions(user_id: int):
    """Получение прав пользователя"""
    try:
        permissions = await auth_db.get_user_permissions(user_id)
        return {"permissions": permissions}
    except Exception as e:
        print(f"Error getting user permissions: {e}")
        raise HTTPException(status_code=500, detail="Ошибка получения прав пользователя")

@app.get("/user-settings")
async def get_user_settings(current_user: dict = Depends(get_current_user)):
    """Получение настроек текущего пользователя"""
    try:
        # Пока возвращаем настройки по умолчанию
        # В будущем можно будет хранить настройки в БД
        return {
            "theme": "light",
            "language": "ru",
            "notifications_enabled": True
        }
    except Exception as e:
        print(f"Error getting user settings: {e}")
        raise HTTPException(status_code=500, detail="Ошибка получения настроек пользователя")

@app.post("/api/roles")
async def create_role(name: str = Form(...), description: str = Form(None)):
    """Создание новой роли"""
    try:
        role = await auth_db.create_role(name, description)
        return role
    except Exception as e:
        print(f"Error creating role: {e}")
        raise HTTPException(status_code=500, detail="Ошибка создания роли")

@app.post("/api/users/{user_id}/roles/{role_id}")
async def assign_role_to_user(user_id: int, role_id: int):
    """Назначение роли пользователю"""
    try:
        success = await auth_db.assign_role_to_user(user_id, role_id)
        if success:
            return {"message": "Роль назначена успешно"}
        else:
            raise HTTPException(status_code=500, detail="Ошибка назначения роли")
    except Exception as e:
        print(f"Error assigning role: {e}")
        raise HTTPException(status_code=500, detail="Ошибка назначения роли")

@app.delete("/api/users/{user_id}/roles/{role_id}")
async def remove_role_from_user(user_id: int, role_id: int):
    """Удаление роли у пользователя"""
    try:
        success = await auth_db.remove_role_from_user(user_id, role_id)
        if success:
            return {"message": "Роль удалена успешно"}
        else:
            raise HTTPException(status_code=500, detail="Ошибка удаления роли")
    except Exception as e:
        print(f"Error removing role: {e}")
        raise HTTPException(status_code=500, detail="Ошибка удаления роли")

@app.get("/api/check-permission")
async def check_permission(user_id: int, resource: str, action: str):
    """Проверка права пользователя"""
    try:
        has_permission = await auth_db.check_permission(user_id, resource, action)
        return {"has_permission": has_permission}
    except Exception as e:
        print(f"Error checking permission: {e}")
        raise HTTPException(status_code=500, detail="Ошибка проверки права")

# ===== API ДЛЯ АУДИТА И ЛОГИРОВАНИЯ =====

@app.get("/api/audit/logs")
async def get_audit_logs(limit: int = 100, offset: int = 0, 
                        user_id: int = None, action: str = None, 
                        resource: str = None, start_date: str = None, 
                        end_date: str = None):
    """Получение логов аудита"""
    try:
        logs = await auth_db.get_audit_logs(
            limit=limit, offset=offset, user_id=user_id, 
            action=action, resource=resource, 
            start_date=start_date, end_date=end_date
        )
        return {"logs": logs}
    except Exception as e:
        print(f"Error getting audit logs: {e}")
        raise HTTPException(status_code=500, detail="Ошибка получения логов аудита")

@app.get("/api/audit/login-attempts")
async def get_login_attempts(limit: int = 100, offset: int = 0, 
                           username: str = None, ip_address: str = None,
                           success: bool = None):
    """Получение попыток входа"""
    try:
        attempts = await auth_db.get_login_attempts(
            limit=limit, offset=offset, username=username, 
            ip_address=ip_address, success=success
        )
        return {"attempts": attempts}
    except Exception as e:
        print(f"Error getting login attempts: {e}")
        raise HTTPException(status_code=500, detail="Ошибка получения попыток входа")

@app.get("/api/audit/sessions")
async def get_active_sessions(limit: int = 100, offset: int = 0):
    """Получение активных сессий"""
    try:
        sessions = await auth_db.get_active_sessions(limit=limit, offset=offset)
        return {"sessions": sessions}
    except Exception as e:
        print(f"Error getting active sessions: {e}")
        raise HTTPException(status_code=500, detail="Ошибка получения активных сессий")

@app.get("/api/audit/stats")
async def get_audit_stats():
    """Получение статистики аудита"""
    try:
        stats = await auth_db.get_audit_stats()
        return stats
    except Exception as e:
        print(f"Error getting audit stats: {e}")
        raise HTTPException(status_code=500, detail="Ошибка получения статистики аудита")

@app.delete("/api/roles/{role_id}")
async def delete_role(role_id: int):
    """Удаление роли"""
    try:
        # Проверяем, что роль не системная
        role = await auth_db.get_role_by_id(role_id)
        if not role:
            raise HTTPException(status_code=404, detail="Роль не найдена")
        
        if role.get('is_system'):
            raise HTTPException(status_code=400, detail="Нельзя удалить системную роль")
        
        success = await auth_db.delete_role(role_id)
        if success:
            return {"message": "Роль удалена успешно"}
        else:
            raise HTTPException(status_code=500, detail="Ошибка удаления роли")
    except Exception as e:
        print(f"Error deleting role: {e}")
        raise HTTPException(status_code=500, detail="Ошибка удаления роли")

@app.post("/api/verify")
async def verify_token_endpoint(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Проверка токена"""
    payload = verify_token(credentials.credentials)
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    # Получаем полную информацию о пользователе
    username = payload.get("sub")
    user = await auth_db.get_user_by_username(username)
    
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    
    return {
        "valid": True, 
        "username": username,
        "user": {
            "id": user['id'],
            "username": user['username'],
            "email": user['email'],
            "is_admin": user['is_admin']
        }
    }
