"""
Базовый класс для работы с базой данных
"""
import asyncio
import asyncpg
from typing import Dict, Optional, Any
import os


class DatabaseBase:
    """Базовый класс для работы с базой данных"""
    
    _global_pool = None  # Глобальный пул для всех экземпляров
    
    def __init__(self):
        self.database_url = os.getenv('DATABASE_URL', 'postgresql://stools_user:stools_pass@postgres:5432/stools_db')

    async def get_pool(self):
        """Получить пул соединений"""
        if DatabaseBase._global_pool is None:
            try:
                DatabaseBase._global_pool = await asyncpg.create_pool(
                    self.database_url,
                    min_size=1,
                    max_size=10,  # Уменьшили с 20 до 10
                    command_timeout=60
                )
            except Exception as e:
                print(f"Failed to create database pool: {e}")
                raise
        return DatabaseBase._global_pool

    async def get_connection(self):
        """Получить соединение с базой данных"""
        pool = await self.get_pool()
        conn = await pool.acquire()
        # Устанавливаем схему vulnanalizer
        await conn.execute('SET search_path TO vulnanalizer')
        return conn

    async def release_connection(self, conn):
        """Освободить соединение"""
        if conn:
            pool = await self.get_pool()
            await pool.release(conn)

    async def test_connection(self):
        """Тестирование соединения с базой данных"""
        try:
            conn = await self.get_connection()
            result = await conn.fetchval("SELECT 1")
            await self.release_connection(conn)
            return result == 1
        except Exception as e:
            print(f"Database connection test failed: {e}")
            return False

    async def get_settings(self) -> Dict[str, str]:
        """Получить настройки из базы данных"""
        conn = await self.get_connection()
        try:
            # Устанавливаем схему vulnanalizer
            await conn.execute('SET search_path TO vulnanalizer')
            
            rows = await conn.fetch("SELECT key, value FROM settings")
            settings = {row['key']: row['value'] for row in rows}
            
            # Добавляем значения по умолчанию, если они не установлены
            default_settings = {
                'impact_availability': '5.0',
                'impact_confidentiality': '5.0',
                'impact_integrity': '5.0',
                'impact_resource_criticality': 'Medium',
                'max_concurrent_requests': '3'
            }
            
            for key, default_value in default_settings.items():
                if key not in settings:
                    settings[key] = default_value
            
            return settings
        except Exception as e:
            print(f"Error getting settings: {e}")
            return {}
        finally:
            await self.release_connection(conn)

    async def update_settings(self, settings: Dict[str, str]):
        """Обновить настройки в базе данных"""
        conn = await self.get_connection()
        try:
            # Устанавливаем схему vulnanalizer
            await conn.execute('SET search_path TO vulnanalizer')
            
            for key, value in settings.items():
                await conn.execute("""
                    INSERT INTO settings (key, value) 
                    VALUES ($1, $2) 
                    ON CONFLICT (key) 
                    DO UPDATE SET value = $2, updated_at = CURRENT_TIMESTAMP
                """, key, value)
        except Exception as e:
            print(f"Error updating settings: {e}")
            raise
        finally:
            await self.release_connection(conn)
