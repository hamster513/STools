#!/bin/bash

# Скрипт для резервного копирования базы данных STools
# Использование: ./backup_database.sh [имя_бэкапа]

set -e

# Настройки
BACKUP_DIR="./backups"
DB_NAME="stools_db"
DB_USER="stools_user"
DB_HOST="localhost"
DB_PORT="5432"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

# Создаем директорию для бэкапов если её нет
mkdir -p "$BACKUP_DIR"

# Имя файла бэкапа
if [ -n "$1" ]; then
    BACKUP_NAME="$1"
else
    BACKUP_NAME="stools_backup_${TIMESTAMP}"
fi

BACKUP_FILE="${BACKUP_DIR}/${BACKUP_NAME}.sql"

echo "🔄 Начинаем резервное копирование базы данных..."
echo "📁 Файл: $BACKUP_FILE"

# Проверяем, что PostgreSQL контейнер запущен
if ! docker ps | grep -q stools_postgres; then
    echo "❌ Контейнер PostgreSQL не запущен!"
    echo "Запустите: docker-compose up -d postgres"
    exit 1
fi

# Создаем бэкап
echo "💾 Создаем резервную копию..."
docker exec stools_postgres pg_dump -U $DB_USER -d $DB_NAME --clean --if-exists --create > "$BACKUP_FILE"

if [ $? -eq 0 ]; then
    echo "✅ Резервная копия создана успешно!"
    echo "📊 Размер файла: $(du -h "$BACKUP_FILE" | cut -f1)"
    echo "📍 Путь: $BACKUP_FILE"
    
    # Создаем сжатую версию
    gzip -f "$BACKUP_FILE"
    echo "🗜️  Создан сжатый файл: ${BACKUP_FILE}.gz"
    echo "📊 Размер сжатого файла: $(du -h "${BACKUP_FILE}.gz" | cut -f1)"
else
    echo "❌ Ошибка при создании резервной копии!"
    exit 1
fi

echo "🎉 Резервное копирование завершено!"
