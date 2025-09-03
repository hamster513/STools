#!/usr/bin/env python3
"""
Скрипт для обновления уровней логов в базе данных
"""

import asyncio
import asyncpg
import json
import sys
import os

# Добавляем путь к модулям приложения
sys.path.append('/app')

async def update_log_levels():
    """Обновляет уровни логов в базе данных"""
    try:
        # Подключаемся к базе данных
        conn = await asyncpg.connect(
            host='localhost',
            user='loganalizer',
            password='loganalizer',
            database='loganalizer'
        )
        
        # Новые уровни логов
        new_levels = ['ERROR', 'WARN', 'CRITICAL', 'FATAL', 'ALERT', 'EMERGENCY', 'INFO', 'DEBUG']
        
        # Обновляем настройки
        await conn.execute('''
            UPDATE loganalizer.settings 
            SET value = $1::jsonb
            WHERE key = 'important_log_levels'
        ''', json.dumps(new_levels))
        
        # Проверяем результат
        result = await conn.fetchval('''
            SELECT value FROM loganalizer.settings WHERE key = 'important_log_levels'
        ''')
        
        print(f'✅ Log levels updated successfully!')
        print(f'📋 New levels: {result}')
        
        await conn.close()
        
    except Exception as e:
        print(f'❌ Error updating log levels: {e}')
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(update_log_levels()) 