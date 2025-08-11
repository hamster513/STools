"""
Роуты для работы с пользователями
"""
import traceback
from fastapi import APIRouter, HTTPException, Depends, Form
from passlib.context import CryptContext

from models.user_models import UserCreate, UserUpdate, PasswordUpdate
from services.auth_service import create_access_token, get_current_user
from database import get_db

router = APIRouter()

# Настройки хеширования паролей
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Проверить пароль"""
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception as e:
        print(f"Ошибка при проверке пароля: {e}")
        return False


def get_password_hash(password: str) -> str:
    """Получить хеш пароля"""
    return pwd_context.hash(password)


@router.post("/api/users/register")
async def register_user(user: UserCreate):
    """Регистрация нового пользователя"""
    try:
        db = get_db()
        
        # Проверяем, существует ли пользователь
        existing_user = await db.get_user_by_username(user.username)
        if existing_user:
            raise HTTPException(status_code=400, detail="Пользователь с таким именем уже существует")
        
        # Создаем нового пользователя с хешированным паролем
        hashed_password = get_password_hash(user.password)
        user_id = await db.create_user(user.username, hashed_password, user.email, user.is_admin)
        
        return {
            "success": True,
            "user_id": user_id,
            "message": "Пользователь успешно зарегистрирован"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print('User registration error:', traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/users/login")
async def login_user(username: str = Form(...), password: str = Form(...)):
    """Вход пользователя"""
    try:
        db = get_db()
        
        # Получаем пользователя
        user = await db.get_user_by_username(username)
        if not user:
            raise HTTPException(status_code=401, detail="Неверное имя пользователя или пароль")
        
        if not user['is_active']:
            raise HTTPException(status_code=401, detail="Пользователь заблокирован")
        
        # Проверяем пароль
        if not verify_password(password, user['password']):
            raise HTTPException(status_code=401, detail="Неверное имя пользователя или пароль")
        
        # Создаем токен
        access_token = create_access_token(data={"sub": user['username']})
        
        return {
            "success": True,
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "id": user['id'],
                "username": user['username'],
                "email": user['email'],
                "is_admin": user['is_admin']
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print('User login error:', traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/users/me")
async def read_users_me(current_user: dict = Depends(get_current_user)):
    """Получить информацию о текущем пользователе"""
    try:
        db = get_db()
        user = await db.get_user_by_username(current_user['sub'])
        
        if not user:
            raise HTTPException(status_code=404, detail="Пользователь не найден")
        
        return {
            "success": True,
            "user": {
                "id": user['id'],
                "username": user['username'],
                "email": user['email'],
                "is_admin": user['is_admin'],
                "is_active": user['is_active']
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print('Get user me error:', traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/api/users/me", response_model=dict)
async def update_user_me(
    current_user: dict = Depends(get_current_user),
    user_update: UserUpdate = Form(...)
):
    """Обновить информацию о текущем пользователе"""
    try:
        db = get_db()
        user = await db.get_user_by_username(current_user['sub'])
        
        if not user:
            raise HTTPException(status_code=404, detail="Пользователь не найден")
        
        # Обновляем данные
        update_data = {
            'username': user_update.username,
            'email': user_update.email
        }
        
        await db.update_user(user['id'], user_update.username, user_update.email, user_update.is_active, user_update.is_admin)
        
        return {
            "success": True,
            "message": "Данные пользователя обновлены"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print('Update user me error:', traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/api/users/me/password", response_model=dict)
async def update_user_password_me(
    current_user: dict = Depends(get_current_user),
    password_update: PasswordUpdate = Form(...)
):
    """Обновить пароль текущего пользователя"""
    try:
        db = get_db()
        user = await db.get_user_by_username(current_user['sub'])
        
        if not user:
            raise HTTPException(status_code=404, detail="Пользователь не найден")
        
        # Обновляем пароль
        hashed_password = get_password_hash(password_update.password)
        await db.update_user_password(user['id'], hashed_password)
        
        return {
            "success": True,
            "message": "Пароль обновлен"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print('Update user password me error:', traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/users/all")
async def get_all_users(current_user: dict = Depends(get_current_user)):
    """Получить всех пользователей (только для админов)"""
    try:
        db = get_db()
        user = await db.get_user_by_username(current_user['sub'])
        
        if not user or not user['is_admin']:
            raise HTTPException(status_code=403, detail="Доступ запрещен")
        
        users = await db.get_all_users()
        
        return {
            "success": True,
            "users": users
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print('Get all users error:', traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/api/users/{user_id}/update")
async def update_user_by_id(
    user_id: int,
    user_update: UserUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Обновить пользователя по ID (только для админов)"""
    try:
        db = get_db()
        admin_user = await db.get_user_by_username(current_user['sub'])
        
        if not admin_user or not admin_user['is_admin']:
            raise HTTPException(status_code=403, detail="Доступ запрещен")
        
        # Обновляем данные
        update_data = {
            'username': user_update.username,
            'email': user_update.email,
            'is_active': user_update.is_active,
            'is_admin': user_update.is_admin
        }
        
        await db.update_user(user_id, user_update.username, user_update.email, user_update.is_active, user_update.is_admin)
        
        return {
            "success": True,
            "message": "Пользователь обновлен"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print('Update user by id error:', traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/api/users/{user_id}/password")
async def update_user_password_by_id(
    user_id: int,
    password_update: PasswordUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Обновить пароль пользователя по ID (только для админов)"""
    try:
        db = get_db()
        admin_user = await db.get_user_by_username(current_user['sub'])
        
        if not admin_user or not admin_user['is_admin']:
            raise HTTPException(status_code=403, detail="Доступ запрещен")
        
        # Обновляем пароль
        hashed_password = get_password_hash(password_update.password)
        await db.update_user_password(user_id, hashed_password)
        
        return {
            "success": True,
            "message": "Пароль пользователя обновлен"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print('Update user password by id error:', traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/api/users/{user_id}/delete")
async def delete_user_by_id(
    user_id: int,
    current_user: dict = Depends(get_current_user)
):
    """Удалить пользователя по ID (только для админов)"""
    try:
        db = get_db()
        admin_user = await db.get_user_by_username(current_user['sub'])
        
        if not admin_user or not admin_user['is_admin']:
            raise HTTPException(status_code=403, detail="Доступ запрещен")
        
        # Нельзя удалить самого себя
        if admin_user['id'] == user_id:
            raise HTTPException(status_code=400, detail="Нельзя удалить самого себя")
        
        await db.delete_user(user_id)
        
        return {
            "success": True,
            "message": "Пользователь удален"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print('Delete user by id error:', traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))
