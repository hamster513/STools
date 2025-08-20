#!/usr/bin/env python3
"""
Скрипт для массового расчета рисков для всех хостов без EPSS данных
"""
import asyncio
import asyncpg
from datetime import datetime

async def calculate_all_risks():
    """Массовый расчет рисков для всех хостов без EPSS данных"""
    
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
        
        print("🔍 Начинаем массовый расчет рисков...")
        
        # Находим все CVE хостов без EPSS данных, но с доступными EPSS данными
        cve_query = """
            SELECT DISTINCT h.cve 
            FROM hosts h 
            LEFT JOIN epss e ON h.cve = e.cve 
            WHERE h.cve IS NOT NULL AND h.cve != '' 
            AND (h.epss_score IS NULL OR h.risk_score IS NULL)
            AND e.cve IS NOT NULL
            ORDER BY h.cve
        """
        cve_rows = await conn.fetch(cve_query)
        
        if not cve_rows:
            print("✅ Нет хостов для расчета рисков")
            return
        
        total_cves = len(cve_rows)
        print(f"🔍 Найдено {total_cves} CVE для расчета рисков")
        
        # Получаем все EPSS данные одним запросом для оптимизации
        cve_list = [cve_row['cve'] for cve_row in cve_rows]
        epss_query = "SELECT cve, epss, percentile FROM epss WHERE cve = ANY($1)"
        epss_rows = await conn.fetch(epss_query, cve_list)
        epss_data = {row['cve']: row for row in epss_rows}
        
        print(f"✅ Загружено EPSS данных: {len(epss_data)} из {len(cve_list)} CVE")
        
        # Получаем настройки
        settings_query = "SELECT key, value FROM settings"
        settings_rows = await conn.fetch(settings_query)
        settings = {row['key']: row['value'] for row in settings_rows}
        
        print(f"⚙️ Настройки загружены: {settings}")
        
        # Счетчики
        processed_cves = 0
        updated_hosts = 0
        error_cves = 0
        
        # Обрабатываем каждый CVE
        for i, cve_row in enumerate(cve_rows):
            cve = cve_row['cve']
            
            try:
                # Логируем прогресс каждые 100 CVE
                if i % 100 == 0:
                    print(f"🔄 Обработано {i+1}/{total_cves} CVE (обновлено хостов: {updated_hosts}, ошибок: {error_cves})")
                
                # Получаем EPSS данные из кэша
                epss_row = epss_data.get(cve)
                
                if not epss_row or epss_row['epss'] is None:
                    print(f"⚠️ Нет EPSS данных для {cve}")
                    continue
                
                # Получаем хосты для этого CVE
                hosts_query = "SELECT id, cvss, criticality FROM hosts WHERE cve = $1"
                hosts_rows = await conn.fetch(hosts_query, cve)
                
                if not hosts_rows:
                    continue
                
                # Рассчитываем риск для каждого хоста
                for host_row in hosts_rows:
                    try:
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
                        
                        updated_hosts += 1
                        
                    except Exception as host_error:
                        print(f"⚠️ Ошибка обновления хоста {host_row['id']} для {cve}: {host_error}")
                        continue
                
                processed_cves += 1
                
            except Exception as e:
                error_cves += 1
                print(f"❌ Ошибка обработки CVE {cve}: {e}")
                continue
        
        print(f"\n✅ Массовый расчет рисков завершен:")
        print(f"   📊 Обработано CVE: {processed_cves}/{total_cves}")
        print(f"   🏠 Обновлено хостов: {updated_hosts}")
        print(f"   ❌ Ошибок: {error_cves}")
        
        # Проверяем результат
        final_hosts_with_epss = await conn.fetchval("SELECT COUNT(*) FROM hosts WHERE epss_score IS NOT NULL")
        final_hosts_with_risk = await conn.fetchval("SELECT COUNT(*) FROM hosts WHERE risk_score IS NOT NULL")
        
        print(f"\n📊 Финальная статистика:")
        print(f"   🏠 Хостов с EPSS данными: {final_hosts_with_epss}")
        print(f"   🏠 Хостов с рассчитанными рисками: {final_hosts_with_risk}")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        print(f"❌ Детали: {traceback.format_exc()}")
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(calculate_all_risks())
