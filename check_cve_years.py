import asyncio
import asyncpg

async def check_cve_years():
    conn = await asyncpg.connect('postgresql://stools_user:stools_pass@postgres/stools_db')
    
    # Устанавливаем схему vulnanalizer
    await conn.execute('SET search_path TO vulnanalizer;')
    
    # Проверяем годы CVE в таблице cve
    years_query = """
        SELECT 
            EXTRACT(YEAR FROM published_date) as year,
            COUNT(*) as count
        FROM cve 
        WHERE published_date IS NOT NULL
        GROUP BY EXTRACT(YEAR FROM published_date)
        ORDER BY year DESC
        LIMIT 10
    """
    years = await conn.fetch(years_query)
    
    print('Годы CVE в таблице cve:')
    for row in years:
        print(f'  {int(row["year"])}: {row["count"]} CVE')
    
    # Проверяем годы CVE в таблице epss
    epss_years_query = """
        SELECT 
            SUBSTRING(cve FROM 5 FOR 4)::integer as year,
            COUNT(*) as count
        FROM epss 
        WHERE cve ~ '^CVE-\d{4}-\d+$'
        GROUP BY SUBSTRING(cve FROM 5 FOR 4)::integer
        ORDER BY year DESC
        LIMIT 10
    """
    epss_years = await conn.fetch(epss_years_query)
    
    print(f'\nГоды CVE в таблице epss:')
    for row in epss_years:
        print(f'  {int(row["year"])}: {row["count"]} CVE')
    
    await conn.close()

if __name__ == "__main__":
    asyncio.run(check_cve_years())
