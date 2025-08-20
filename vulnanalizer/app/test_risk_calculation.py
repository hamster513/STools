#!/usr/bin/env python3
"""
Скрипт для тестирования расчета рисков
"""
import asyncio
import asyncpg
from datetime import datetime

async def test_risk_calculation():
    """Тестирование расчета рисков"""
    
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
        
        print("🔍 Проверяем текущее состояние хостов...")
        
        # Проверяем общее количество хостов
        total_hosts = await conn.fetchval("SELECT COUNT(*) FROM hosts")
        print(f"📊 Всего хостов: {total_hosts}")
        
        # Проверяем хосты с EPSS данными
        hosts_with_epss = await conn.fetchval("SELECT COUNT(*) FROM hosts WHERE epss_score IS NOT NULL")
        print(f"📊 Хостов с EPSS данными: {hosts_with_epss}")
        
        # Проверяем хосты с рассчитанными рисками
        hosts_with_risk = await conn.fetchval("SELECT COUNT(*) FROM hosts WHERE risk_score IS NOT NULL")
        print(f"📊 Хостов с рассчитанными рисками: {hosts_with_risk}")
        
        # Проверяем хосты без EPSS данных
        hosts_without_epss = await conn.fetchval("SELECT COUNT(*) FROM hosts WHERE epss_score IS NULL")
        print(f"📊 Хостов без EPSS данных: {hosts_without_epss}")
        
        # Проверяем хосты без рассчитанных рисков
        hosts_without_risk = await conn.fetchval("SELECT COUNT(*) FROM hosts WHERE risk_score IS NULL")
        print(f"📊 Хостов без рассчитанных рисков: {hosts_without_risk}")
        
        # Находим CVE хостов без EPSS данных, но с доступными EPSS данными
        cve_query = """
            SELECT DISTINCT h.cve 
            FROM hosts h 
            LEFT JOIN epss e ON h.cve = e.cve 
            WHERE h.cve IS NOT NULL AND h.cve != '' 
            AND (h.epss_score IS NULL OR h.risk_score IS NULL)
            AND e.cve IS NOT NULL
            ORDER BY h.cve
            LIMIT 10
        """
        cve_rows = await conn.fetch(cve_query)
        
        print(f"🔍 Найдено {len(cve_rows)} CVE для расчета рисков (первые 10):")
        for row in cve_rows:
            print(f"  - {row['cve']}")
        
        if cve_rows:
            # Берем первый CVE для тестирования
            test_cve = cve_rows[0]['cve']
            print(f"\n🧪 Тестируем расчет рисков для CVE: {test_cve}")
            
            # Получаем EPSS данные
            epss_query = "SELECT epss, percentile FROM epss WHERE cve = $1"
            epss_row = await conn.fetchrow(epss_query, test_cve)
            
            if epss_row:
                print(f"✅ EPSS данные найдены: {epss_row['epss']}")
                
                # Получаем хосты для этого CVE
                hosts_query = "SELECT id, hostname, cvss, criticality FROM hosts WHERE cve = $1 LIMIT 5"
                hosts_rows = await conn.fetch(hosts_query, test_cve)
                
                print(f"✅ Найдено {len(hosts_rows)} хостов для тестирования:")
                
                # Получаем настройки
                settings_query = "SELECT key, value FROM settings"
                settings_rows = await conn.fetch(settings_query)
                settings = {row['key']: row['value'] for row in settings_rows}
                
                print(f"⚙️ Настройки: {settings}")
                
                # Рассчитываем риск для каждого хоста
                for host_row in hosts_rows:
                    print(f"\n🏠 Хост: {host_row['hostname']} (ID: {host_row['id']})")
                    print(f"   CVE: {test_cve}")
                    print(f"   CVSS: {host_row['cvss']}")
                    print(f"   Criticality: {host_row['criticality']}")
                    
                    # Рассчитываем риск
                    epss_score = float(epss_row['epss'])
                    criticality = host_row['criticality'] or 'Medium'
                    
                    # Веса для критичности ресурса
                    resource_weights = {
                        'Critical': 0.33,
                        'High': 0.25,
                        'Medium': 0.15,
                        'Low': 0.1,
                        'None': 0.05
                    }
                    
                    # Веса для конфиденциальных данных
                    data_weights = {
                        'Есть': 0.33,
                        'Отсутствуют': 0.1
                    }
                    
                    # Веса для доступа к интернету
                    internet_weights = {
                        'Доступен': 0.33,
                        'Недоступен': 0.1
                    }
                    
                    # Получаем значения из настроек
                    confidential_data = settings.get('impact_confidential_data', 'Отсутствуют')
                    internet_access = settings.get('impact_internet_access', 'Недоступен')
                    
                    # Рассчитываем Impact
                    impact = (
                        resource_weights.get(criticality, 0.15) +
                        data_weights.get(confidential_data, 0.1) +
                        internet_weights.get(internet_access, 0.1)
                    )
                    
                    # Рассчитываем риск
                    raw_risk = epss_score * impact
                    risk_score = min(1, raw_risk) * 100
                    
                    print(f"   EPSS: {epss_score}")
                    print(f"   Impact: {impact}")
                    print(f"   Raw Risk: {raw_risk}")
                    print(f"   Risk Score: {risk_score}")
                    
                    # Обновляем хост
                    update_query = """
                        UPDATE hosts SET
                            epss_score = $1,
                            epss_percentile = $2,
                            risk_score = $3,
                            risk_raw = $4,
                            epss_updated_at = $5,
                            risk_updated_at = $6
                        WHERE id = $7
                    """
                    
                    await conn.execute(update_query,
                        epss_score,
                        float(epss_row['percentile']) if epss_row['percentile'] else None,
                        risk_score,
                        raw_risk,
                        datetime.now(),
                        datetime.now(),
                        host_row['id']
                    )
                    
                    print(f"   ✅ Хост обновлен")
        
        print(f"\n✅ Тестирование завершено")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        print(f"❌ Детали: {traceback.format_exc()}")
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(test_risk_calculation())
