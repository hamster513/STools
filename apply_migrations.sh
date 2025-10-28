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
    "00-unified-database-init.sql"
    "04-add-refresh-tokens.sql"
    "05-add-rbac-tables.sql" 
    "06-insert-rbac-data.sql"
    "07-add-audit-tables.sql"
    "08-add-hosts-unique-index.sql"
    "09-update-role-descriptions.sql"
)

# Функция для применения миграции
apply_migration() {
    local migration_file=$1
    local migration_path="./init-db/$migration_file"
    
    echo "📋 Применяем миграцию: $migration_file"
    
    # Проверяем существует ли файл в хост-системе
    if [ ! -f "$migration_path" ]; then
        echo "⚠️  Файл $migration_file не найден, пропускаем"
        return 0
    fi
    
    # Применяем миграцию через postgres контейнер
    if docker-compose exec -T postgres psql -U stools_user -d stools_db -f "/docker-entrypoint-initdb.d/$migration_file"; then
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

# Проверяем что таблицы созданы через postgres
docker-compose exec -T postgres psql -U stools_user -d stools_db -c "
SELECT schemaname, tablename, tableowner
FROM pg_tables 
WHERE schemaname IN ('auth', 'vulnanalizer')
ORDER BY schemaname, tablename;
"

echo ""
echo "✅ Готово! Все миграции применены успешно."
echo ""
echo "🔧 Теперь можно:"
echo "   1. Запустить импорт VM"
echo "   2. Проверить что записи сохраняются в базу"
echo "   3. Убедиться что дубликаты обрабатываются корректно"