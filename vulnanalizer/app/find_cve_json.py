#!/usr/bin/env python3
"""
Скрипт для поиска CVE-2021-4459 в исходном JSON
"""

import json
import gzip
import io
import aiohttp
import asyncio

async def find_cve_json():
    """Ищем CVE-2021-4459 в исходном JSON"""
    
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
    cve_data = json.loads(content)
    vulnerabilities = cve_data.get('vulnerabilities', [])
    
    print(f"Найдено {len(vulnerabilities)} записей")
    
    # Ищем CVE-2021-4459
    target_cve = None
    for item in vulnerabilities:
        cve_info = item.get('cve', {})
        cve_id = cve_info.get('id')
        if cve_id == 'CVE-2021-4459':
            target_cve = item
            break
    
    if target_cve:
        print("\n=== CVE-2021-4459 найдена в JSON ===")
        print("Полная структура:")
        print(json.dumps(target_cve, indent=2))
    else:
        print("\nCVE-2021-4459 не найдена в данных")

if __name__ == "__main__":
    asyncio.run(find_cve_json())
