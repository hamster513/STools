import asyncio
import asyncpg

async def check_tables_structure():
    conn = await asyncpg.connect('postgresql://stools_user:stools_pass@postgres/stools_db')
    
    # Устанавливаем схему vulnanalizer
    await conn.execute('SET search_path TO vulnanalizer;')
    
    # Проверяем структуру таблицы epss
    epss_columns = await conn.fetch("""
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_name = 'epss' 
        ORDER BY ordinal_position
    """)
    
    print('Структура таблицы epss:')
    for col in epss_columns:
        print(f'  {col["column_name"]}: {col["data_type"]}')
    
    # Проверяем структуру таблицы exploitdb
    exploitdb_columns = await conn.fetch("""
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_name = 'exploitdb' 
        ORDER BY ordinal_position
    """)
    
    print(f'\nСтруктура таблицы exploitdb:')
    for col in exploitdb_columns:
        print(f'  {col["column_name"]}: {col["data_type"]}')
    
    # Проверяем несколько записей из таблицы epss
    sample_epss = await conn.fetch("SELECT * FROM epss LIMIT 2")
    print(f'\nПримеры записей из таблицы epss:')
    for i, row in enumerate(sample_epss):
        print(f'  Запись {i+1}: {dict(row)}')
    
    await conn.close()

if __name__ == "__main__":
    asyncio.run(check_tables_structure())
