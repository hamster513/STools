import asyncpg
import bcrypt
from typing import Optional, List, Dict
import os

class AuthDatabase:
    def __init__(self):
        self.pool = None
        self.database_url = os.getenv('AUTH_DATABASE_URL', 'postgresql://stools_user:stools_pass@postgres:5432/stools_db')

    async def connect(self):
        """Подключение к базе данных"""
        if not self.pool:
            self.pool = await asyncpg.create_pool(self.database_url)
            await self.init_tables()

    async def close(self):
        """Закрытие соединения"""
        if self.pool:
            await self.pool.close()

    async def init_tables(self):
        """Инициализация таблиц"""
        async with self.pool.acquire() as conn:
            # Устанавливаем схему auth
            await conn.execute('SET search_path TO auth')
            
            # Проверяем, есть ли уже пользователи
            try:
                count = await conn.fetchval('SELECT COUNT(*) FROM users')
                if count == 0:
                    # Создаем админа по умолчанию
                    admin_password = bcrypt.hashpw('admin'.encode('utf-8'), bcrypt.gensalt())
                    await conn.execute('''
                        INSERT INTO users (username, email, password_hash, is_admin) 
                        VALUES ($1, $2, $3, $4)
                    ''', 'admin', 'admin@stools.local', admin_password.decode('utf-8'), True)
            except Exception as e:
                print(f"Error in init_tables: {e}")
                # Таблицы могут еще не существовать, это нормально

    async def create_user(self, username: str, email: str, password: str, is_admin: bool = False, is_active: bool = True) -> Dict:
        """Создание нового пользователя"""
        async with self.pool.acquire() as conn:
            await conn.execute('SET search_path TO auth')
            password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
            
            user_id = await conn.fetchval('''
                INSERT INTO users (username, email, password_hash, is_admin, is_active)
                VALUES ($1, $2, $3, $4, $5)
                RETURNING id
            ''', username, email, password_hash.decode('utf-8'), is_admin, is_active)
            
            return {
                'id': user_id,
                'username': username,
                'email': email,
                'is_admin': is_admin,
                'is_active': is_active
            }

    async def get_user_by_username(self, username: str) -> Optional[Dict]:
        """Получение пользователя по имени"""
        async with self.pool.acquire() as conn:
            await conn.execute('SET search_path TO auth')
            row = await conn.fetchrow('''
                SELECT id, username, email, password_hash, is_active, is_admin, created_at
                FROM users WHERE username = $1
            ''', username)
            
            if row:
                return dict(row)
            return None

    async def get_user_by_id(self, user_id: int) -> Optional[Dict]:
        """Получение пользователя по ID"""
        async with self.pool.acquire() as conn:
            await conn.execute('SET search_path TO auth')
            row = await conn.fetchrow('''
                SELECT id, username, email, password_hash, is_active, is_admin, created_at
                FROM users WHERE id = $1
            ''', user_id)
            
            if row:
                return dict(row)
            return None

    async def verify_password(self, username: str, password: str) -> Optional[Dict]:
        """Проверка пароля пользователя"""
        user = await self.get_user_by_username(username)
        if user and user['is_active']:
            if bcrypt.checkpw(password.encode('utf-8'), user['password_hash'].encode('utf-8')):
                return user
        return None

    async def get_all_users(self) -> List[Dict]:
        """Получение всех пользователей"""
        async with self.pool.acquire() as conn:
            await conn.execute('SET search_path TO auth')
            rows = await conn.fetch('''
                SELECT id, username, email, is_active, is_admin, created_at
                FROM users ORDER BY created_at DESC
            ''')
            return [dict(row) for row in rows]

    async def update_user(self, user_id: int, username: str, email: str, is_active: bool, is_admin: bool) -> bool:
        """Обновление пользователя"""
        async with self.pool.acquire() as conn:
            await conn.execute('SET search_path TO auth')
            result = await conn.execute('''
                UPDATE users 
                SET username = $2, email = $3, is_active = $4, is_admin = $5, updated_at = CURRENT_TIMESTAMP
                WHERE id = $1
            ''', user_id, username, email, is_active, is_admin)
            
            return result != 'UPDATE 0'

    async def update_user_password(self, user_id: int, password: str) -> bool:
        """Обновление пароля пользователя"""
        async with self.pool.acquire() as conn:
            await conn.execute('SET search_path TO auth')
            password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
            result = await conn.execute('''
                UPDATE users 
                SET password_hash = $2, updated_at = CURRENT_TIMESTAMP
                WHERE id = $1
            ''', user_id, password_hash.decode('utf-8'))
            
            return result != 'UPDATE 0'

    async def delete_user(self, user_id: int) -> bool:
        """Удаление пользователя"""
        async with self.pool.acquire() as conn:
            await conn.execute('SET search_path TO auth')
            result = await conn.execute('DELETE FROM users WHERE id = $1', user_id)
            return result != 'DELETE 0'

    async def check_username_exists(self, username: str, exclude_id: int = None) -> bool:
        """Проверка существования имени пользователя"""
        async with self.pool.acquire() as conn:
            await conn.execute('SET search_path TO auth')
            if exclude_id:
                count = await conn.fetchval('''
                    SELECT COUNT(*) FROM users WHERE username = $1 AND id != $2
                ''', username, exclude_id)
            else:
                count = await conn.fetchval('''
                    SELECT COUNT(*) FROM users WHERE username = $1
                ''', username)
            
            return count > 0

    async def check_email_exists(self, email: str, exclude_id: int = None) -> bool:
        """Проверка существования email"""
        async with self.pool.acquire() as conn:
            await conn.execute('SET search_path TO auth')
            if exclude_id:
                count = await conn.fetchval('''
                    SELECT COUNT(*) FROM users WHERE email = $1 AND id != $2
                ''', email, exclude_id)
            else:
                count = await conn.fetchval('''
                    SELECT COUNT(*) FROM users WHERE email = $1
                ''', email)
            
            return count > 0
