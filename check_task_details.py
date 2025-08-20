import asyncio
import asyncpg

async def check_task_details():
    conn = await asyncpg.connect('postgresql://stools_user:stools_pass@postgres/stools_db')
    
    # Устанавливаем схему vulnanalizer
    await conn.execute('SET search_path TO vulnanalizer;')
    
    # Проверяем детали последней задачи импорта
    task = await conn.fetchrow("""
        SELECT id, task_type, status, created_at, progress_percent, current_step, 
               error_message, parameters, description, processed_records, total_records
        FROM background_tasks 
        WHERE task_type = 'hosts_import'
        ORDER BY created_at DESC
        LIMIT 1
    """)
    
    if task:
        print(f'Последняя задача импорта (ID: {task["id"]}):')
        print(f'  Тип: {task["task_type"]}')
        print(f'  Статус: {task["status"]}')
        print(f'  Создана: {task["created_at"]}')
        print(f'  Прогресс: {task["progress_percent"]}%')
        print(f'  Текущий шаг: {task["current_step"]}')
        print(f'  Обработано записей: {task["processed_records"]}')
        print(f'  Всего записей: {task["total_records"]}')
        print(f'  Описание: {task["description"]}')
        if task["error_message"]:
            print(f'  Ошибка: {task["error_message"]}')
        if task["parameters"]:
            print(f'  Параметры: {task["parameters"]}')
    else:
        print('Задачи импорта не найдены')
    
    await conn.close()

if __name__ == "__main__":
    asyncio.run(check_task_details())
