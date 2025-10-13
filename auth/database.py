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
            # Проверяем, есть ли уже пользователи
            try:
                count = await conn.fetchval('SELECT COUNT(*) FROM auth.users')
                if count == 0:
                    # Создаем админа по умолчанию
                    admin_password = bcrypt.hashpw('admin'.encode('utf-8'), bcrypt.gensalt())
                    await conn.execute('''
                        INSERT INTO auth.users (username, email, password_hash, is_admin) 
                        VALUES ($1, $2, $3, $4)
                    ''', 'admin', 'admin@stools.local', admin_password.decode('utf-8'), True)
            except Exception as e:
                print(f"Error in init_tables: {e}")
                # Таблицы могут еще не существовать, это нормально

    async def create_user(self, username: str, email: str, password: str, is_admin: bool = False, is_active: bool = True) -> Dict:
        """Создание нового пользователя"""
        async with self.pool.acquire() as conn:
            password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
            
            user_id = await conn.fetchval('''
                INSERT INTO auth.users (username, email, password_hash, is_admin, is_active)
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
            row = await conn.fetchrow('''
                SELECT id, username, email, password_hash, is_active, is_admin, created_at
                FROM auth.users WHERE username = $1
            ''', username)
            
            if row:
                return dict(row)
            return None

    async def get_user_by_id(self, user_id: int) -> Optional[Dict]:
        """Получение пользователя по ID"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow('''
                SELECT id, username, email, password_hash, is_active, is_admin, created_at
                FROM auth.users WHERE id = $1
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

    async def get_user_by_token(self, token: str) -> Optional[Dict]:
        """Получение пользователя по токену (пока упрощенная версия)"""
        try:
            # Пока используем простую проверку - ищем пользователя admin
            # В реальной системе здесь должна быть проверка JWT токена
            if token == "admin_token" or token == "admin":
                return await self.get_user_by_username("admin")
            return None
        except Exception as e:
            print(f"Error getting user by token: {e}")
            return None

    async def get_all_users(self) -> List[Dict]:
        """Получение всех пользователей с их ролями"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch('''
                SELECT 
                    u.id, 
                    u.username, 
                    u.email, 
                    u.is_active, 
                    u.is_admin, 
                    u.created_at,
                    COALESCE(
                        json_agg(
                            json_build_object(
                                'id', r.id,
                                'name', r.name,
                                'description', r.description,
                                'sort_order', r.sort_order
                            ) ORDER BY r.sort_order, r.name
                        ) FILTER (WHERE r.id IS NOT NULL),
                        '[]'::json
                    ) as roles
                FROM auth.users u
                LEFT JOIN auth.user_roles ur ON u.id = ur.user_id
                LEFT JOIN auth.roles r ON ur.role_id = r.id
                GROUP BY u.id, u.username, u.email, u.is_active, u.is_admin, u.created_at
                ORDER BY u.created_at DESC
            ''')
            
            # Преобразуем результаты
            users = []
            for row in rows:
                user = dict(row)
                # roles уже JSON объект благодаря json_agg
                users.append(user)
            return users

    async def update_user(self, user_id: int, username: str, email: str, is_active: bool, is_admin: bool) -> bool:
        """Обновление пользователя"""
        async with self.pool.acquire() as conn:
            result = await conn.execute('''
                UPDATE auth.users 
                SET username = $2, email = $3, is_active = $4, is_admin = $5, updated_at = CURRENT_TIMESTAMP
                WHERE id = $1
            ''', user_id, username, email, is_active, is_admin)
            
            return result != 'UPDATE 0'

    async def update_user_password(self, user_id: int, password: str) -> bool:
        """Обновление пароля пользователя"""
        async with self.pool.acquire() as conn:
            password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
            result = await conn.execute('''
                UPDATE auth.users 
                SET password_hash = $2, updated_at = CURRENT_TIMESTAMP
                WHERE id = $1
            ''', user_id, password_hash.decode('utf-8'))
            
            return result != 'UPDATE 0'

    async def delete_user(self, user_id: int) -> bool:
        """Удаление пользователя"""
        async with self.pool.acquire() as conn:
            result = await conn.execute('DELETE FROM auth.users WHERE id = $1', user_id)
            return result != 'DELETE 0'

    async def check_username_exists(self, username: str, exclude_id: int = None) -> bool:
        """Проверка существования имени пользователя"""
        async with self.pool.acquire() as conn:
            if exclude_id:
                count = await conn.fetchval('''
                    SELECT COUNT(*) FROM auth.users WHERE username = $1 AND id != $2
                ''', username, exclude_id)
            else:
                count = await conn.fetchval('''
                    SELECT COUNT(*) FROM auth.users WHERE username = $1
                ''', username)
            
            return count > 0

    async def check_email_exists(self, email: str, exclude_id: int = None) -> bool:
        """Проверка существования email"""
        async with self.pool.acquire() as conn:
            if exclude_id:
                count = await conn.fetchval('''
                    SELECT COUNT(*) FROM auth.users WHERE email = $1 AND id != $2
                ''', email, exclude_id)
            else:
                count = await conn.fetchval('''
                    SELECT COUNT(*) FROM auth.users WHERE email = $1
                ''', email)
            
            return count > 0

    async def save_refresh_token(self, user_id: int, refresh_token: str) -> bool:
        """Сохранение refresh токена"""
        async with self.pool.acquire() as conn:
            try:
                # Сначала удаляем старые токены для этого пользователя
                await conn.execute('DELETE FROM auth.refresh_tokens WHERE user_id = $1', user_id)
                
                # Вставляем новый токен
                await conn.execute('''
                    INSERT INTO auth.refresh_tokens (user_id, token, expires_at)
                    VALUES ($1, $2, $3)
                ''', user_id, refresh_token, None)  # expires_at будет установлен в JWT
                return True
            except Exception as e:
                print(f"Error saving refresh token: {e}")
                return False

    async def verify_refresh_token(self, user_id: int, refresh_token: str) -> bool:
        """Проверка refresh токена"""
        async with self.pool.acquire() as conn:
            try:
                row = await conn.fetchrow('''
                    SELECT token FROM auth.refresh_tokens 
                    WHERE user_id = $1 AND token = $2
                ''', user_id, refresh_token)
                return row is not None
            except Exception as e:
                print(f"Error verifying refresh token: {e}")
                return False

    async def revoke_refresh_token(self, user_id: int, refresh_token: str) -> bool:
        """Отзыв refresh токена"""
        async with self.pool.acquire() as conn:
            try:
                result = await conn.execute('''
                    DELETE FROM auth.refresh_tokens 
                    WHERE user_id = $1 AND token = $2
                ''', user_id, refresh_token)
                return result != 'DELETE 0'
            except Exception as e:
                print(f"Error revoking refresh token: {e}")
                return False

    async def revoke_all_refresh_tokens(self, user_id: int) -> bool:
        """Отзыв всех refresh токенов пользователя"""
        async with self.pool.acquire() as conn:
            try:
                result = await conn.execute('''
                    DELETE FROM auth.refresh_tokens WHERE user_id = $1
                ''', user_id)
                return True
            except Exception as e:
                print(f"Error revoking all refresh tokens: {e}")
                return False

    # ===== МЕТОДЫ ДЛЯ РОЛЕВОЙ МОДЕЛИ RBAC =====

    async def get_user_roles(self, user_id: int) -> List[Dict]:
        """Получение ролей пользователя"""
        async with self.pool.acquire() as conn:
            try:
                roles = await conn.fetch('''
                    SELECT r.id, r.name, r.description, r.is_system, ur.assigned_at, ur.expires_at
                    FROM auth.user_roles ur
                    JOIN auth.roles r ON ur.role_id = r.id
                    WHERE ur.user_id = $1 AND (ur.expires_at IS NULL OR ur.expires_at > NOW())
                    ORDER BY r.name
                ''', user_id)
                return [dict(role) for role in roles]
            except Exception as e:
                print(f"Error getting user roles: {e}")
                return []

    async def get_user_permissions(self, user_id: int) -> List[Dict]:
        """Получение прав пользователя через роли"""
        async with self.pool.acquire() as conn:
            try:
                permissions = await conn.fetch('''
                    SELECT DISTINCT p.id, p.name, p.description, p.resource, p.action
                    FROM auth.user_roles ur
                    JOIN auth.role_permissions rp ON ur.role_id = rp.role_id
                    JOIN auth.permissions p ON rp.permission_id = p.id
                    WHERE ur.user_id = $1 AND (ur.expires_at IS NULL OR ur.expires_at > NOW())
                    ORDER BY p.resource, p.action
                ''', user_id)
                return [dict(permission) for permission in permissions]
            except Exception as e:
                print(f"Error getting user permissions: {e}")
                return []

    async def check_permission(self, user_id: int, resource: str, action: str) -> bool:
        """Проверка права пользователя"""
        async with self.pool.acquire() as conn:
            try:
                # Проверяем, есть ли у пользователя право
                has_permission = await conn.fetchval('''
                    SELECT COUNT(*) > 0
                    FROM auth.user_roles ur
                    JOIN auth.role_permissions rp ON ur.role_id = rp.role_id
                    JOIN auth.permissions p ON rp.permission_id = p.id
                    WHERE ur.user_id = $1 
                      AND p.resource = $2 
                      AND p.action = $3
                      AND (ur.expires_at IS NULL OR ur.expires_at > NOW())
                ''', user_id, resource, action)
                return has_permission
            except Exception as e:
                print(f"Error checking permission: {e}")
                return False

    async def get_all_roles(self) -> List[Dict]:
        """Получение всех ролей"""
        async with self.pool.acquire() as conn:
            try:
                roles = await conn.fetch('''
                    SELECT r.id, r.name, r.description, r.is_system, r.created_at, r.sort_order,
                           COUNT(ur.user_id) as user_count
                    FROM auth.roles r
                    LEFT JOIN auth.user_roles ur ON r.id = ur.role_id 
                        AND (ur.expires_at IS NULL OR ur.expires_at > NOW())
                    GROUP BY r.id, r.name, r.description, r.is_system, r.created_at, r.sort_order
                    ORDER BY r.sort_order, r.name
                ''')
                return [dict(role) for role in roles]
            except Exception as e:
                print(f"Error getting all roles: {e}")
                return []

    async def get_all_permissions(self) -> List[Dict]:
        """Получение всех прав"""
        async with self.pool.acquire() as conn:
            try:
                permissions = await conn.fetch('''
                    SELECT id, name, description, resource, action, created_at
                    FROM auth.permissions
                    ORDER BY resource, action
                ''')
                return [dict(permission) for permission in permissions]
            except Exception as e:
                print(f"Error getting all permissions: {e}")
                return []

    async def get_role_permissions(self, role_id: int) -> List[Dict]:
        """Получение прав роли"""
        async with self.pool.acquire() as conn:
            try:
                permissions = await conn.fetch('''
                    SELECT p.id, p.name, p.description, p.resource, p.action, p.created_at
                    FROM auth.permissions p
                    JOIN auth.role_permissions rp ON p.id = rp.permission_id
                    WHERE rp.role_id = $1
                    ORDER BY p.resource, p.action
                ''', role_id)
                return [dict(permission) for permission in permissions]
            except Exception as e:
                print(f"Error getting all permissions: {e}")
                return []

    async def get_user_roles(self, user_id: int) -> List[Dict]:
        """Получение ролей пользователя"""
        async with self.pool.acquire() as conn:
            try:
                roles = await conn.fetch('''
                    SELECT r.id, r.name, r.description, r.is_system, r.sort_order, ur.assigned_at
                    FROM auth.roles r
                    JOIN auth.user_roles ur ON r.id = ur.role_id
                    WHERE ur.user_id = $1
                    ORDER BY r.sort_order, r.name
                ''', user_id)
                return [dict(role) for role in roles]
            except Exception as e:
                print(f"Error getting user roles: {e}")
                return []

    async def assign_user_role(self, user_id: int, role_id: int, assigned_by: int) -> bool:
        """Назначение роли пользователю"""
        async with self.pool.acquire() as conn:
            try:
                await conn.execute('''
                    INSERT INTO auth.user_roles (user_id, role_id, assigned_by)
                    VALUES ($1, $2, $3)
                    ON CONFLICT (user_id, role_id) DO NOTHING
                ''', user_id, role_id, assigned_by)
                return True
            except Exception as e:
                print(f"Error assigning user role: {e}")
                return False

    async def remove_user_role(self, user_id: int, role_id: int) -> bool:
        """Удаление роли у пользователя"""
        async with self.pool.acquire() as conn:
            try:
                await conn.execute('''
                    DELETE FROM auth.user_roles
                    WHERE user_id = $1 AND role_id = $2
                ''', user_id, role_id)
                return True
            except Exception as e:
                print(f"Error removing user role: {e}")
                return False

    async def set_user_roles(self, user_id: int, role_ids: List[int], assigned_by: int) -> bool:
        """Установка ролей пользователя (заменяет все существующие)"""
        async with self.pool.acquire() as conn:
            try:
                # Удаляем все текущие роли
                await conn.execute('DELETE FROM auth.user_roles WHERE user_id = $1', user_id)
                
                # Добавляем новые роли
                if role_ids:
                    for role_id in role_ids:
                        await conn.execute('''
                            INSERT INTO auth.user_roles (user_id, role_id, assigned_by)
                            VALUES ($1, $2, $3)
                        ''', user_id, role_id, assigned_by)
                
                return True
            except Exception as e:
                print(f"Error setting user roles: {e}")
                return False

    async def create_role(self, name: str, description: str = None) -> Dict:
        """Создание новой роли"""
        async with self.pool.acquire() as conn:
            try:
                role_id = await conn.fetchval('''
                    INSERT INTO auth.roles (name, description)
                    VALUES ($1, $2)
                    RETURNING id
                ''', name, description)
                
                return {
                    'id': role_id,
                    'name': name,
                    'description': description,
                    'is_system': False
                }
            except Exception as e:
                print(f"Error creating role: {e}")
                raise

    async def assign_role_to_user(self, user_id: int, role_id: int, assigned_by: int = None) -> bool:
        """Назначение роли пользователю"""
        async with self.pool.acquire() as conn:
            try:
                await conn.execute('''
                    INSERT INTO auth.user_roles (user_id, role_id, assigned_by)
                    VALUES ($1, $2, $3)
                    ON CONFLICT (user_id, role_id) DO NOTHING
                ''', user_id, role_id, assigned_by)
                return True
            except Exception as e:
                print(f"Error assigning role to user: {e}")
                return False

    async def remove_role_from_user(self, user_id: int, role_id: int) -> bool:
        """Удаление роли у пользователя"""
        async with self.pool.acquire() as conn:
            try:
                await conn.execute('''
                    DELETE FROM auth.user_roles 
                    WHERE user_id = $1 AND role_id = $2
                ''', user_id, role_id)
                return True
            except Exception as e:
                print(f"Error removing role from user: {e}")
                return False

    async def get_role_by_id(self, role_id: int) -> Optional[Dict]:
        """Получение роли по ID"""
        async with self.pool.acquire() as conn:
            try:
                role = await conn.fetchrow('''
                    SELECT id, name, description, is_system, created_at
                    FROM auth.roles
                    WHERE id = $1
                ''', role_id)
                return dict(role) if role else None
            except Exception as e:
                print(f"Error getting role by id: {e}")
                return None

    async def delete_role(self, role_id: int) -> bool:
        """Удаление роли"""
        async with self.pool.acquire() as conn:
            try:
                # Удаляем связи с пользователями
                await conn.execute('DELETE FROM auth.user_roles WHERE role_id = $1', role_id)
                # Удаляем связи с правами
                await conn.execute('DELETE FROM auth.role_permissions WHERE role_id = $1', role_id)
                # Удаляем саму роль
                await conn.execute('DELETE FROM auth.roles WHERE id = $1', role_id)
                return True
            except Exception as e:
                print(f"Error deleting role: {e}")
                return False

    # ===== МЕТОДЫ ДЛЯ АУДИТА И ЛОГИРОВАНИЯ =====

    async def log_audit_event(self, user_id: int = None, username: str = None, action: str = None, 
                            resource: str = None, resource_id: str = None, details: dict = None,
                            ip_address: str = None, user_agent: str = None, session_id: str = None,
                            success: bool = True, error_message: str = None) -> bool:
        """Логирование события аудита"""
        async with self.pool.acquire() as conn:
            try:
                await conn.execute('''
                    INSERT INTO auth.audit_logs 
                    (user_id, username, action, resource, resource_id, details, 
                     ip_address, user_agent, session_id, success, error_message)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                ''', user_id, username, action, resource, resource_id, 
                    details, ip_address, user_agent, session_id, success, error_message)
                return True
            except Exception as e:
                print(f"Error logging audit event: {e}")
                return False

    async def log_login_attempt(self, username: str = None, ip_address: str = None, 
                              user_agent: str = None, success: bool = True, 
                              failure_reason: str = None) -> bool:
        """Логирование попытки входа"""
        async with self.pool.acquire() as conn:
            try:
                await conn.execute('''
                    INSERT INTO auth.login_attempts 
                    (username, ip_address, user_agent, success, failure_reason)
                    VALUES ($1, $2, $3, $4, $5)
                ''', username, ip_address, user_agent, success, failure_reason)
                return True
            except Exception as e:
                print(f"Error logging login attempt: {e}")
                return False

    async def create_user_session(self, user_id: int, session_id: str, 
                                ip_address: str = None, user_agent: str = None) -> bool:
        """Создание сессии пользователя"""
        async with self.pool.acquire() as conn:
            try:
                await conn.execute('''
                    INSERT INTO auth.user_sessions 
                    (user_id, session_id, ip_address, user_agent)
                    VALUES ($1, $2, $3, $4)
                ''', user_id, session_id, ip_address, user_agent)
                return True
            except Exception as e:
                print(f"Error creating user session: {e}")
                return False

    async def update_session_activity(self, session_id: str) -> bool:
        """Обновление времени последней активности сессии"""
        async with self.pool.acquire() as conn:
            try:
                await conn.execute('''
                    UPDATE auth.user_sessions 
                    SET last_activity = CURRENT_TIMESTAMP
                    WHERE session_id = $1 AND is_active = TRUE
                ''', session_id)
                return True
            except Exception as e:
                print(f"Error updating session activity: {e}")
                return False

    async def end_user_session(self, session_id: str) -> bool:
        """Завершение сессии пользователя"""
        async with self.pool.acquire() as conn:
            try:
                await conn.execute('''
                    UPDATE auth.user_sessions 
                    SET logout_at = CURRENT_TIMESTAMP, is_active = FALSE
                    WHERE session_id = $1
                ''', session_id)
                return True
            except Exception as e:
                print(f"Error ending user session: {e}")
                return False

    async def get_audit_logs(self, limit: int = 100, offset: int = 0, 
                           user_id: int = None, action: str = None, 
                           resource: str = None, start_date: str = None, 
                           end_date: str = None) -> List[Dict]:
        """Получение логов аудита с фильтрацией"""
        async with self.pool.acquire() as conn:
            try:
                # Строим динамический запрос
                conditions = []
                params = []
                param_count = 0

                if user_id:
                    param_count += 1
                    conditions.append(f"user_id = ${param_count}")
                    params.append(user_id)

                if action:
                    param_count += 1
                    conditions.append(f"action = ${param_count}")
                    params.append(action)

                if resource:
                    param_count += 1
                    conditions.append(f"resource = ${param_count}")
                    params.append(resource)

                if start_date:
                    param_count += 1
                    conditions.append(f"created_at >= ${param_count}")
                    params.append(start_date)

                if end_date:
                    param_count += 1
                    conditions.append(f"created_at <= ${param_count}")
                    params.append(end_date)

                where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""

                param_count += 1
                params.append(limit)
                param_count += 1
                params.append(offset)

                query = f'''
                    SELECT id, user_id, username, action, resource, resource_id, 
                           details, ip_address, user_agent, session_id, success, 
                           error_message, created_at
                    FROM auth.audit_logs
                    {where_clause}
                    ORDER BY created_at DESC
                    LIMIT ${param_count - 1} OFFSET ${param_count}
                '''

                logs = await conn.fetch(query, *params)
                return [dict(log) for log in logs]
            except Exception as e:
                print(f"Error getting audit logs: {e}")
                return []

    async def get_login_attempts(self, limit: int = 100, offset: int = 0, 
                               username: str = None, ip_address: str = None,
                               success: bool = None) -> List[Dict]:
        """Получение попыток входа с фильтрацией"""
        async with self.pool.acquire() as conn:
            try:
                conditions = []
                params = []
                param_count = 0

                if username:
                    param_count += 1
                    conditions.append(f"username = ${param_count}")
                    params.append(username)

                if ip_address:
                    param_count += 1
                    conditions.append(f"ip_address = ${param_count}")
                    params.append(ip_address)

                if success is not None:
                    param_count += 1
                    conditions.append(f"success = ${param_count}")
                    params.append(success)

                where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""

                param_count += 1
                params.append(limit)
                param_count += 1
                params.append(offset)

                query = f'''
                    SELECT id, username, ip_address, user_agent, success, 
                           failure_reason, created_at
                    FROM auth.login_attempts
                    {where_clause}
                    ORDER BY created_at DESC
                    LIMIT ${param_count - 1} OFFSET ${param_count}
                '''

                attempts = await conn.fetch(query, *params)
                return [dict(attempt) for attempt in attempts]
            except Exception as e:
                print(f"Error getting login attempts: {e}")
                return []

    async def get_active_sessions(self, limit: int = 100, offset: int = 0) -> List[Dict]:
        """Получение активных сессий"""
        async with self.pool.acquire() as conn:
            try:
                sessions = await conn.fetch('''
                    SELECT s.id, s.user_id, u.username, s.session_id, s.ip_address, 
                           s.user_agent, s.login_at, s.last_activity, s.is_active
                    FROM auth.user_sessions s
                    JOIN auth.users u ON s.user_id = u.id
                    WHERE s.is_active = TRUE
                    ORDER BY s.last_activity DESC
                    LIMIT $1 OFFSET $2
                ''', limit, offset)
                return [dict(session) for session in sessions]
            except Exception as e:
                print(f"Error getting active sessions: {e}")
                return []

    async def get_audit_stats(self) -> Dict:
        """Получение статистики аудита"""
        async with self.pool.acquire() as conn:
            try:
                # Общее количество событий
                total_events = await conn.fetchval('SELECT COUNT(*) FROM auth.audit_logs')
                
                # События за последние 24 часа
                events_24h = await conn.fetchval('''
                    SELECT COUNT(*) FROM auth.audit_logs 
                    WHERE created_at >= NOW() - INTERVAL '24 hours'
                ''')
                
                # Успешные/неуспешные события
                successful_events = await conn.fetchval('''
                    SELECT COUNT(*) FROM auth.audit_logs WHERE success = TRUE
                ''')
                
                failed_events = await conn.fetchval('''
                    SELECT COUNT(*) FROM auth.audit_logs WHERE success = FALSE
                ''')
                
                # Активные сессии
                active_sessions = await conn.fetchval('''
                    SELECT COUNT(*) FROM auth.user_sessions WHERE is_active = TRUE
                ''')
                
                # Попытки входа за последние 24 часа
                login_attempts_24h = await conn.fetchval('''
                    SELECT COUNT(*) FROM auth.login_attempts 
                    WHERE created_at >= NOW() - INTERVAL '24 hours'
                ''')
                
                return {
                    'total_events': total_events,
                    'events_24h': events_24h,
                    'successful_events': successful_events,
                    'failed_events': failed_events,
                    'active_sessions': active_sessions,
                    'login_attempts_24h': login_attempts_24h
                }
            except Exception as e:
                print(f"Error getting audit stats: {e}")
                return {}
