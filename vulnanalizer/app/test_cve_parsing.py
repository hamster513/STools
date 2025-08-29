#!/usr/bin/env python3
"""
Тестовый скрипт для проверки парсинга CVE-2021-4459
"""

import json
import gzip
import io
import aiohttp
import asyncio

# Импортируем функцию парсинга
import sys
sys.path.append('./vulnanalizer/app')
from services.cve_worker import parse_cve_json

async def test_cve_parsing():
    """Тестируем парсинг CVE-2021-4459"""
    
    # URL для загрузки CVE 2021
    url = "https://nvd.nist.gov/feeds/json/cve/2.0/nvdcve-2.0-2021.json.gz"
    
    print(f"Загружаем {url}...")
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status != 200:
                print(f"Ошибка загрузки: HTTP {resp.status}")
                return
            
            gz_content = await resp.read()
    
    print(f"Загружено {len(gz_content)} байт")
    
    # Разархивируем
    with gzip.GzipFile(fileobj=io.BytesIO(gz_content)) as gz:
        content = gz.read().decode('utf-8')
    
    print(f"Разархивировано {len(content)} символов")
    
    # Парсим JSON
    records = parse_cve_json(content)
    
    print(f"Найдено {len(records)} записей")
    
    # Ищем CVE-2021-4459
    target_cve = None
    for record in records:
        if record['cve_id'] == 'CVE-2021-4459':
            target_cve = record
            break
    
    if target_cve:
        print("\n=== CVE-2021-4459 найдена ===")
        print(f"CVE ID: {target_cve['cve_id']}")
        print(f"Description: {target_cve['description'][:100]}...")
        print(f"CVSS v3 Score: {target_cve['cvss_v3_base_score']}")
        print(f"CVSS v3 Severity: {target_cve['cvss_v3_base_severity']}")
        print(f"CVSS v3 Attack Vector: {target_cve['cvss_v3_attack_vector']}")
        print(f"CVSS v3 User Interaction: {target_cve['cvss_v3_user_interaction']}")
        print(f"CVSS v2 Score: {target_cve['cvss_v2_base_score']}")
        print(f"CVSS v2 Severity: {target_cve['cvss_v2_base_severity']}")
        print(f"CVSS v2 Access Vector: {target_cve['cvss_v2_access_vector']}")
        print(f"CVSS v2 Access Complexity: {target_cve['cvss_v2_access_complexity']}")
        print(f"CVSS v2 Authentication: {target_cve['cvss_v2_authentication']}")
    else:
        print("\nCVE-2021-4459 не найдена в данных")

if __name__ == "__main__":
    asyncio.run(test_cve_parsing())
