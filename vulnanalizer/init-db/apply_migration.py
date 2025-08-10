#!/usr/bin/env python3
"""
Скрипт для применения миграции базы данных VulnAnalizer
"""

import asyncio
import asyncpg
import os
import sys

async def apply_migration():
    """Применяет миграцию к базе данных"""
    
    # Получаем параметры подключения из переменных окружения
    database_url = os.getenv('VULNANALIZER_DATABASE_URL', 'postgresql://vulnanalizer_user:vulnanalizer_pass@vulnanalizer_postgres:5432/vulnanalizer_db')
    
    try:
        # Подключаемся к базе данных
        print("Подключение к базе данных...")
        conn = await asyncpg.connect(database_url)
        
        # Читаем файл миграции
        print("Чтение файла миграции...")
        with open('migration.sql', 'r', encoding='utf-8') as f:
            migration_sql = f.read()
        
        # Применяем миграцию
        print("Применение миграции...")
        await conn.execute(migration_sql)
        
        print("✅ Миграция успешно применена!")
        
        # Проверяем структуру таблицы
        print("\nПроверка структуры таблицы hosts:")
        columns = await conn.fetch("""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns 
            WHERE table_name = 'hosts' 
            ORDER BY ordinal_position
        """)
        
        for col in columns:
            print(f"  - {col['column_name']}: {col['data_type']} {'(NULL)' if col['is_nullable'] == 'YES' else '(NOT NULL)'}")
        
        await conn.close()
        
    except Exception as e:
        print(f"❌ Ошибка при применении миграции: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(apply_migration())
