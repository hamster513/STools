import asyncio
import asyncpg

async def check_epss():
    conn = await asyncpg.connect('postgresql://stools_user:stools_pass@postgres/stools_db')
    
    # Устанавливаем схему vulnanalizer
    await conn.execute('SET search_path TO vulnanalizer;')
    
    total_cves = await conn.fetchval('SELECT COUNT(*) FROM cve')
    total_epss = await conn.fetchval('SELECT COUNT(*) FROM epss')
    
    print(f'Всего CVE: {total_cves}')
    print(f'Всего EPSS записей: {total_epss}')
    
    # Проверим несколько CVE с EPSS
    epss_sample = await conn.fetch('SELECT cve, epss, percentile FROM epss LIMIT 5')
    print(f'\nПримеры EPSS данных:')
    for row in epss_sample:
        print(f'  {row["cve"]}: EPSS={row["epss"]}, Percentile={row["percentile"]}')
    
    await conn.close()

if __name__ == "__main__":
    asyncio.run(check_epss())
