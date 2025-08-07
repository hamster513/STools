#!/usr/bin/env python3
"""
Тестовый скрипт для проверки работы фильтрации больших файлов
"""

import asyncio
import asyncpg
import json
import sys
from pathlib import Path

async def test_filtering():
    """Тестирует фильтрацию больших файлов"""
    try:
        # Подключаемся к базе данных
        conn = await asyncpg.connect(
            host='localhost',
            user='loganalizer',
            password='loganalizer',
            database='loganalizer'
        )
        
        # Получаем настройки
        settings_result = await conn.fetchval('''
            SELECT value FROM settings WHERE key = 'important_log_levels'
        ''')
        
        print(f"📋 Current log levels: {settings_result}")
        
        # Получаем информацию о файлах
        files = await conn.fetch('''
            SELECT id, original_name, file_size, file_path 
            FROM log_files 
            ORDER BY created_at DESC 
            LIMIT 5
        ''')
        
        print(f"📁 Found {len(files)} files:")
        for file in files:
            file_size_mb = file['file_size'] / (1024 * 1024)
            print(f"  - {file['original_name']}: {file_size_mb:.1f}MB")
        
        await conn.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_filtering()) 