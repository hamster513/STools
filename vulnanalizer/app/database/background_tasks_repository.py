"""
Repository for background tasks operations
"""
import asyncpg
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
from .base import DatabaseBase


class BackgroundTasksRepository(DatabaseBase):
    """Repository for background tasks operations"""
    
    async def create_task(self, task_type: str, description: str, parameters: Dict[str, Any] = None) -> int:
        """Создать новую фоновую задачу"""
        conn = await self.get_connection()
        try:
            query = """
                INSERT INTO vulnanalizer.background_tasks (task_type, status, current_step, description, parameters)
                VALUES ($1, 'idle', 'Инициализация...', $2, $3)
                RETURNING id
            """
            task_id = await conn.fetchval(query, task_type, description, json.dumps(parameters) if parameters else None)
            return task_id
        finally:
            await self.release_connection(conn)
    
    async def get_task(self, task_id: int) -> Optional[Dict[str, Any]]:
        """Получить задачу по ID"""
        conn = await self.get_connection()
        try:
            query = """
                SELECT id, task_type, status, current_step, total_items, processed_items,
                       total_records, processed_records, updated_records, progress_percent, start_time, end_time, 
                       error_message, cancelled, parameters, description, created_at, updated_at
                FROM vulnanalizer.background_tasks 
                WHERE id = $1
            """
            row = await conn.fetchrow(query, task_id)
            if row:
                return dict(row)
            return None
        finally:
            await self.release_connection(conn)
    
    async def get_idle_tasks(self) -> List[Dict[str, Any]]:
        """Получить задачи в статусе 'idle'"""
        conn = await self.get_connection()
        try:
            query = """
                SELECT id, task_type, status, current_step, total_items, processed_items,
                       total_records, processed_records, updated_records, progress_percent, start_time, end_time, 
                       error_message, cancelled, parameters, description, created_at, updated_at
                FROM vulnanalizer.background_tasks 
                WHERE status = 'idle'
                ORDER BY created_at ASC
            """
            rows = await conn.fetch(query)
            return [dict(row) for row in rows]
        finally:
            await self.release_connection(conn)
    
    async def update_task(self, task_id: int, **kwargs) -> bool:
        """Обновить задачу"""
        conn = await self.get_connection()
        try:
            # Строим динамический запрос
            fields = []
            values = []
            param_count = 1
            
            for key, value in kwargs.items():
                if key in ['total_items', 'processed_items', 'total_records', 'processed_records', 'updated_records', 'progress_percent']:
                    fields.append(f"{key} = ${param_count}")
                    values.append(value)
                    param_count += 1
                elif key == 'parameters' and value is not None:
                    fields.append(f"{key} = ${param_count}")
                    values.append(json.dumps(value))
                    param_count += 1
                elif key in ['status', 'current_step', 'error_message', 'description']:
                    fields.append(f"{key} = ${param_count}")
                    values.append(value)
                    param_count += 1
                elif key in ['start_time', 'end_time']:
                    fields.append(f"{key} = ${param_count}")
                    values.append(value)
                    param_count += 1
                elif key == 'cancelled':
                    fields.append(f"{key} = ${param_count}")
                    values.append(value)
                    param_count += 1
            
            if not fields:
                return False
            
            fields.append("updated_at = CURRENT_TIMESTAMP")
            values.append(task_id)
            
            query = f"UPDATE vulnanalizer.background_tasks SET {', '.join(fields)} WHERE id = ${param_count}"
            await conn.execute(query, *values)
            return True
        finally:
            await self.release_connection(conn)
    
    async def get_recent_tasks(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Получить последние задачи"""
        conn = await self.get_connection()
        try:
            query = """
                SELECT id, task_type, status, current_step, total_items, processed_items,
                       total_records, processed_records, updated_records, start_time, end_time, 
                       error_message, cancelled, parameters, description, created_at, updated_at
                FROM vulnanalizer.background_tasks 
                ORDER BY created_at DESC
                LIMIT $1
            """
            rows = await conn.fetch(query, limit)
            return [dict(row) for row in rows]
        finally:
            await self.release_connection(conn)
    
    async def get_active_tasks(self) -> List[Dict[str, Any]]:
        """Получить активные задачи"""
        conn = await self.get_connection()
        try:
            query = """
                SELECT id, task_type, status, current_step, total_items, processed_items,
                       total_records, processed_records, updated_records, start_time, end_time, 
                       error_message, cancelled, parameters, description, created_at, updated_at
                FROM vulnanalizer.background_tasks 
                WHERE status IN ('processing', 'running', 'initializing')
                ORDER BY created_at DESC
            """
            rows = await conn.fetch(query)
            return [dict(row) for row in rows]
        finally:
            await self.release_connection(conn)
    
    async def get_completed_tasks(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Получить завершенные задачи"""
        conn = await self.get_connection()
        try:
            query = """
                SELECT id, task_type, status, current_step, total_items, processed_items,
                       total_records, processed_records, updated_records, progress_percent, start_time, end_time, 
                       error_message, cancelled, parameters, description, created_at, updated_at
                FROM vulnanalizer.background_tasks 
                WHERE status = 'completed'
                ORDER BY created_at DESC
                LIMIT $1
            """
            rows = await conn.fetch(query, limit)
            return [dict(row) for row in rows]
        finally:
            await self.release_connection(conn)
    
    async def cancel_task(self, task_id: int) -> bool:
        """Отменить задачу"""
        conn = await self.get_connection()
        try:
            query = """
                UPDATE vulnanalizer.background_tasks 
                SET status = 'cancelled', cancelled = true, end_time = CURRENT_TIMESTAMP,
                    current_step = 'Задача отменена', updated_at = CURRENT_TIMESTAMP
                WHERE id = $1 AND status IN ('idle', 'processing', 'running', 'initializing')
            """
            result = await conn.execute(query, task_id)
            return result.split()[-1] != '0'  # Проверяем, что была обновлена хотя бы одна строка
        finally:
            await self.release_connection(conn)
    
    async def cleanup_old_tasks(self, days: int = 30) -> int:
        """Очистить старые задачи"""
        conn = await self.get_connection()
        try:
            query = """
                DELETE FROM vulnanalizer.background_tasks 
                WHERE created_at < CURRENT_TIMESTAMP - INTERVAL '$1 days'
                AND status IN ('completed', 'cancelled', 'error')
            """
            result = await conn.execute(query, days)
            return int(result.split()[-1]) if result.split()[-1].isdigit() else 0
        finally:
            await self.release_connection(conn)
    
    async def get_background_task_by_type(self, task_type: str) -> Optional[Dict[str, Any]]:
        """Получить последнюю фоновую задачу определенного типа"""
        conn = await self.get_connection()
        try:
            query = """
                SELECT id, task_type, status, current_step, total_items, processed_items,
                       total_records, processed_records, updated_records, progress_percent, start_time, end_time, 
                       error_message, cancelled, parameters, description, created_at, updated_at
                FROM vulnanalizer.background_tasks 
                WHERE task_type = $1
                ORDER BY created_at DESC
                LIMIT 1
            """
            row = await conn.fetchrow(query, task_type)
            if row:
                return dict(row)
            return None
        finally:
            await self.release_connection(conn)
    
    async def cancel_background_task(self, task_type: str) -> bool:
        """Отменить фоновую задачу по типу"""
        conn = await self.get_connection()
        try:
            query = """
                UPDATE vulnanalizer.background_tasks 
                SET status = 'cancelled', current_step = 'Отменено пользователем', 
                    cancelled = TRUE, end_time = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
                WHERE task_type = $1 AND status IN ('running', 'processing')
            """
            result = await conn.execute(query, task_type)
            return result != 'UPDATE 0'
        finally:
            await self.release_connection(conn)
    
    async def get_background_tasks_by_status(self, status: str) -> List[Dict[str, Any]]:
        """Получить задачи по статусу"""
        conn = await self.get_connection()
        try:
            query = """
                SELECT id, task_type, status, current_step, total_items, processed_items,
                       total_records, processed_records, updated_records, progress_percent, start_time, end_time, 
                       error_message, cancelled, parameters, description, created_at, updated_at
                FROM vulnanalizer.background_tasks 
                WHERE status = $1
                ORDER BY created_at ASC
            """
            rows = await conn.fetch(query, status)
            return [dict(row) for row in rows]
        finally:
            await self.release_connection(conn)
