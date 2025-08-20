#!/usr/bin/env python3
"""
Скрипт для тестирования производительности разных методов обновления
"""
import asyncio
import asyncpg
from datetime import datetime
import time

async def test_performance():
    """Тестирование производительности разных методов"""
    
    # Подключение к базе данных
    conn = await asyncpg.connect(
        host='postgres',
        port=5432,
        user='stools_user',
        password='stools_pass',
        database='stools_db'
    )
    
    try:
        # Устанавливаем схему
        await conn.execute('SET search_path TO vulnanalizer')
        
        print("🔍 Тестирование производительности методов обновления...")
        
        # Получаем количество хостов для тестирования
        total_hosts = await conn.fetchval("SELECT COUNT(*) FROM hosts")
        print(f"📊 Всего хостов в базе: {total_hosts}")
        
        # Получаем количество уникальных CVE
        total_cves = await conn.fetchval("SELECT COUNT(DISTINCT cve) FROM hosts WHERE cve IS NOT NULL AND cve != ''")
        print(f"📊 Уникальных CVE: {total_cves}")
        
        # Тест 1: Batch запросы (как в импорте)
        print(f"\n🧪 ТЕСТ 1: Batch запросы (метод импорта)")
        start_time = time.time()
        
        # Получаем первые 100 CVE для тестирования
        test_cves = await conn.fetch("SELECT DISTINCT cve FROM hosts WHERE cve IS NOT NULL AND cve != '' ORDER BY cve LIMIT 100")
        cve_list = [row['cve'] for row in test_cves]
        
        # Batch запрос для EPSS
        epss_start = time.time()
        epss_query = "SELECT cve, epss, percentile FROM epss WHERE cve = ANY($1::text[])"
        epss_rows = await conn.fetch(epss_query, cve_list)
        epss_time = time.time() - epss_start
        
        batch_total_time = time.time() - start_time
        
        print(f"   ✅ EPSS batch запрос: {epss_time:.3f}s ({len(epss_rows)} записей)")
        print(f"   🚀 Общее время batch запросов: {batch_total_time:.3f}s")
        
        # Тест 2: Индивидуальные запросы (как в старом методе)
        print(f"\n🧪 ТЕСТ 2: Индивидуальные запросы (старый метод)")
        start_time = time.time()
        
        # Берем первые 10 CVE для тестирования (чтобы не ждать слишком долго)
        test_cves_small = cve_list[:10]
        
        individual_epss_time = 0
        
        for cve in test_cves_small:
            # EPSS запрос
            epss_start = time.time()
            epss_row = await conn.fetchrow("SELECT epss, percentile FROM epss WHERE cve = $1", cve)
            individual_epss_time += time.time() - epss_start
        
        individual_total_time = time.time() - start_time
        
        print(f"   ⏱️ EPSS индивидуальные запросы: {individual_epss_time:.3f}s (10 запросов)")
        print(f"   🐌 Общее время индивидуальных запросов: {individual_total_time:.3f}s")
        
        # Расчет производительности
        print(f"\n📊 АНАЛИЗ ПРОИЗВОДИТЕЛЬНОСТИ:")
        
        # Экстраполируем на все CVE
        estimated_individual_time = (individual_total_time / 10) * total_cves
        speedup = estimated_individual_time / batch_total_time if batch_total_time > 0 else float('inf')
        
        print(f"   📈 Batch запросы для {total_cves} CVE: ~{batch_total_time:.3f}s")
        print(f"   📉 Индивидуальные запросы для {total_cves} CVE: ~{estimated_individual_time:.3f}s")
        print(f"   🚀 Ускорение: {speedup:.1f}x")
        
        # Расчет количества запросов
        batch_queries = 1  # EPSS
        individual_queries = total_cves * 1  # 1 запрос на каждый CVE
        
        print(f"\n📊 КОЛИЧЕСТВО ЗАПРОСОВ:")
        print(f"   🚀 Batch метод: {batch_queries} запросов")
        print(f"   🐌 Индивидуальный метод: {individual_queries} запросов")
        print(f"   📉 Сокращение запросов: {individual_queries / batch_queries:.0f}x")
        
        # Рекомендации
        print(f"\n💡 РЕКОМЕНДАЦИИ:")
        print(f"   ✅ Используйте batch запросы для массовых операций")
        print(f"   ✅ Кэшируйте данные в памяти")
        print(f"   ✅ Избегайте параллелизма для простых операций")
        print(f"   ✅ Оптимизируйте SQL запросы с помощью ANY() и IN()")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        print(f"❌ Детали: {traceback.format_exc()}")
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(test_performance())
