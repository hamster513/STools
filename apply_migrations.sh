#!/bin/bash

# Скрипт для применения всех миграций базы данных
# Использование: ./apply_migrations.sh

set -e

echo "🚀 Начинаем применение миграций базы данных..."

# Проверяем что docker-compose запущен
if ! docker-compose ps | grep -q "Up"; then
    echo "❌ Docker-compose не запущен. Запустите: docker-compose up -d"
    exit 1
fi

# Список миграций для применения
MIGRATIONS=(
    "04-add-refresh-tokens.sql"
    "05-add-rbac-tables.sql" 
    "06-insert-rbac-data.sql"
    "07-add-audit-tables.sql"
    "08-add-hosts-unique-index.sql"
)

# Функция для применения миграции
apply_migration() {
    local migration_file=$1
    local migration_path="/app/init-db/$migration_file"
    
    echo "📋 Применяем миграцию: $migration_file"
    
    # Проверяем существует ли файл
    if ! docker-compose exec -T vulnanalizer_web test -f "$migration_path"; then
        echo "⚠️  Файл $migration_file не найден, пропускаем"
        return 0
    fi
    
    # Применяем миграцию через Python (psql не доступен в vulnanalizer_web)
    if docker-compose exec -T vulnanalizer_web python3 -c "
import asyncio
import sys
sys.path.append('/app')
from database.hosts_repository import HostsRepository

async def apply_migration():
    db = HostsRepository()
    conn = await db.get_connection()
    try:
        with open('$migration_path', 'r') as f:
            sql = f.read()
        await conn.execute(sql)
        print('✅ Миграция $migration_file применена успешно')
    except Exception as e:
        print(f'❌ Ошибка: {e}')
        sys.exit(1)
    finally:
        await db.release_connection(conn)

asyncio.run(apply_migration())
"; then
        echo "✅ Миграция $migration_file применена успешно"
    else
        echo "❌ Ошибка применения миграции $migration_file"
        return 1
    fi
}

# Применяем все миграции
for migration in "${MIGRATIONS[@]}"; do
    apply_migration "$migration"
done

echo ""
echo "🎯 Все миграции применены!"
echo ""
echo "📊 Проверяем статус базы данных..."

# Проверяем что таблицы созданы через Python
docker-compose exec -T vulnanalizer_web python3 -c "
import asyncio
import sys
sys.path.append('/app')
from database.hosts_repository import HostsRepository

async def check_tables():
    db = HostsRepository()
    conn = await db.get_connection()
    try:
        tables = await conn.fetch('''
            SELECT schemaname, tablename, tableowner
            FROM pg_tables 
            WHERE schemaname IN ('auth', 'vulnanalizer', 'loganalizer')
            ORDER BY schemaname, tablename
        ''')
        print(f'📋 Найдено таблиц: {len(tables)}')
        for table in tables:
            print(f'  {table[\"schemaname\"]}.{table[\"tablename\"]}')
    finally:
        await db.release_connection(conn)

asyncio.run(check_tables())
"

echo ""
echo "✅ Готово! Все миграции применены успешно."
echo ""
echo "🔧 Теперь можно:"
echo "   1. Запустить импорт VM"
echo "   2. Проверить что записи сохраняются в базу"
echo "   3. Убедиться что дубликаты обрабатываются корректно"