#!/bin/bash

# Скрипт для отмены всех задач импорта VM через базу данных

echo "🔍 Проверяем существующие базы данных..."

# Показать все базы данных
PGPASSWORD=stools_pass docker-compose exec -T postgres psql -U stools_user -d postgres -c "\l"

echo ""
echo "🔍 Проверяем текущие задачи VM импорта..."

# Показать текущие задачи VM
PGPASSWORD=stools_pass docker-compose exec -T postgres psql -U stools_user -d stools_db -c "
SELECT id, task_type, status, created_at, updated_at 
FROM vulnanalizer.background_tasks 
WHERE task_type = 'vm_import'
ORDER BY created_at DESC;
"

echo ""
echo "❓ Хотите отменить все задачи VM импорта? (y/n)"
read -r response

if [[ "$response" =~ ^[Yy]$ ]]; then
    echo "🔄 Отменяем все задачи VM импорта..."
    
    # Отменить все активные задачи VM (установить статус 'cancelled')
    PGPASSWORD=stools_pass docker-compose exec -T postgres psql -U stools_user -d stools_db -c "
    UPDATE vulnanalizer.background_tasks 
    SET status = 'cancelled', 
        end_time = CURRENT_TIMESTAMP,
        updated_at = CURRENT_TIMESTAMP
    WHERE task_type = 'vm_import' 
    AND status IN ('idle', 'running', 'initializing', 'processing');
    "
    
    echo "✅ Задачи VM импорта отменены (проверьте количество обновленных записей выше)"
    
    echo ""
    echo "📊 Проверяем результат..."
    
    # Показать обновленные задачи
    PGPASSWORD=stools_pass docker-compose exec -T postgres psql -U stools_user -d stools_db -c "
    SELECT id, task_type, status, created_at, updated_at 
    FROM vulnanalizer.background_tasks 
    WHERE task_type = 'vm_import'
    ORDER BY created_at DESC;
    "
    
else
    echo "❌ Операция отменена"
fi

echo ""
echo "🎯 Готово!"