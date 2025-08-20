import asyncio
import asyncpg

async def check_cve_structure():
    conn = await asyncpg.connect('postgresql://stools_user:stools_pass@postgres/stools_db')
    
    # Устанавливаем схему vulnanalizer
    await conn.execute('SET search_path TO vulnanalizer;')
    
    # Проверяем структуру таблицы cve
    columns = await conn.fetch("""
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_name = 'cve' 
        ORDER BY ordinal_position
    """)
    
    print('Структура таблицы cve:')
    for col in columns:
        print(f'  {col["column_name"]}: {col["data_type"]}')
    
    # Проверяем несколько записей из таблицы cve
    sample_cves = await conn.fetch("SELECT * FROM cve LIMIT 3")
    print(f'\nПримеры записей из таблицы cve:')
    for i, row in enumerate(sample_cves):
        print(f'  Запись {i+1}: {dict(row)}')
    
    await conn.close()

if __name__ == "__main__":
    asyncio.run(check_cve_structure())
