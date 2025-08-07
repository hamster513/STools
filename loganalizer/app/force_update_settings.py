#!/usr/bin/env python3
"""
Скрипт для принудительного обновления настроек в базе данных
"""

import asyncio
import asyncpg
import json
import sys

async def force_update_settings():
    """Принудительно обновляет настройки в базе данных"""
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
        
        # Принудительно обновляем настройки
        await conn.execute('''
            UPDATE settings 
            SET value = $1::jsonb
            WHERE key = 'important_log_levels'
        ''', json.dumps(new_levels))
        
        # Проверяем результат
        result = await conn.fetchval('''
            SELECT value FROM settings WHERE key = 'important_log_levels'
        ''')
        
        print(f'✅ Settings force updated successfully!')
        print(f'📋 New levels: {result}')
        
        await conn.close()
        
    except Exception as e:
        print(f'❌ Error updating settings: {e}')
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(force_update_settings()) 