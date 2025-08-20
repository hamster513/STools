import asyncio
import asyncpg

async def check_tasks():
    conn = await asyncpg.connect('postgresql://stools_user:stools_pass@postgres/stools_db')
    
    # Устанавливаем схему vulnanalizer
    await conn.execute('SET search_path TO vulnanalizer;')
    
    # Проверяем структуру таблицы
    columns = await conn.fetch("""
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_name = 'background_tasks' 
        ORDER BY ordinal_position
    """)
    
    print('Структура таблицы background_tasks:')
    for col in columns:
        print(f'  {col["column_name"]}: {col["data_type"]}')
    
    # Проверяем активные задачи
    active_tasks = await conn.fetch("""
        SELECT id, task_type, status, created_at, progress_percent, current_step, error_message
        FROM background_tasks 
        WHERE status IN ('pending', 'running')
        ORDER BY created_at DESC
        LIMIT 10
    """)
    
    print(f'\nАктивных задач: {len(active_tasks)}')
    
    for task in active_tasks:
        print(f'\nЗадача {task["id"]}:')
        print(f'  Тип: {task["task_type"]}')
        print(f'  Статус: {task["status"]}')
        print(f'  Создана: {task["created_at"]}')
        print(f'  Прогресс: {task["progress_percent"]}%')
        print(f'  Текущий шаг: {task["current_step"]}')
        if task["error_message"]:
            print(f'  Ошибка: {task["error_message"]}')
    
    # Проверяем последние завершенные задачи
    recent_tasks = await conn.fetch("""
        SELECT id, task_type, status, created_at, progress_percent, current_step, error_message
        FROM background_tasks 
        WHERE status = 'completed'
        ORDER BY created_at DESC
        LIMIT 5
    """)
    
    print(f'\nПоследние завершенные задачи: {len(recent_tasks)}')
    
    for task in recent_tasks:
        print(f'\nЗадача {task["id"]}:')
        print(f'  Тип: {task["task_type"]}')
        print(f'  Статус: {task["status"]}')
        print(f'  Создана: {task["created_at"]}')
        print(f'  Прогресс: {task["progress_percent"]}%')
    
    await conn.close()

if __name__ == "__main__":
    asyncio.run(check_tasks())
