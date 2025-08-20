import asyncio
import asyncpg

async def check_risks():
    conn = await asyncpg.connect('postgresql://stools_user:stools_pass@postgres/stools_db')
    
    # Устанавливаем схему vulnanalizer
    await conn.execute('SET search_path TO vulnanalizer;')
    
    total = await conn.fetchval('SELECT COUNT(*) FROM hosts')
    with_risk = await conn.fetchval('SELECT COUNT(*) FROM hosts WHERE risk_score IS NOT NULL')
    
    print(f'Всего хостов: {total}')
    print(f'С рассчитанным риском: {with_risk}')
    print(f'Без риска: {total - with_risk}')
    
    await conn.close()

if __name__ == "__main__":
    asyncio.run(check_risks())
