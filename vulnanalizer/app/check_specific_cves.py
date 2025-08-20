import asyncio
import asyncpg

async def check_specific_cves():
    conn = await asyncpg.connect('postgresql://stools_user:stools_pass@postgres/stools_db')
    
    # Устанавливаем схему vulnanalizer
    await conn.execute('SET search_path TO vulnanalizer;')
    
    # Проверяем конкретные CVE из скриншота
    test_cves = ['CVE-2016-5195', 'CVE-2016-7039', 'CVE-2016-8666']
    
    for cve in test_cves:
        print(f'\n=== Проверка {cve} ===')
        
        # Проверяем EPSS данные
        epss_row = await conn.fetchrow("SELECT epss, percentile FROM epss WHERE cve = $1", cve)
        if epss_row:
            print(f'  EPSS: {epss_row["epss"]}, Percentile: {epss_row["percentile"]}')
        else:
            print(f'  EPSS: НЕТ ДАННЫХ')
        
        # Проверяем CVSS данные
        cve_row = await conn.fetchrow("SELECT cvss_v3_base_score, cvss_v2_base_score FROM cve WHERE cve_id = $1", cve)
        if cve_row:
            print(f'  CVSS v3: {cve_row["cvss_v3_base_score"]}, CVSS v2: {cve_row["cvss_v2_base_score"]}')
        else:
            print(f'  CVSS: НЕТ ДАННЫХ')
        
        # Проверяем хосты с этим CVE
        hosts = await conn.fetch("SELECT id, risk_score, epss_score, cvss FROM hosts WHERE cve = $1 LIMIT 3", cve)
        print(f'  Хостов с этим CVE: {len(hosts)}')
        for host in hosts:
            print(f'    Хост {host["id"]}: risk_score={host["risk_score"]}, epss_score={host["epss_score"]}, cvss={host["cvss"]}')
    
    await conn.close()

if __name__ == "__main__":
    asyncio.run(check_specific_cves())
