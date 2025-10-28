"""
Repository for hosts operations
"""
import asyncpg
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
from .base import DatabaseBase
from .hosts_update_service import HostsUpdateService


class HostsRepository(DatabaseBase):
    """Repository for hosts operations"""
    
    async def insert_hosts_records_with_duplicate_check(self, records: list, progress_callback=None):
        """Вставить записи хостов с проверкой дублей и расчетом риска"""
        conn = None
        try:
            conn = await asyncpg.connect(self.database_url)
            await conn.execute("SELECT 1")
            
            # Подсчитываем только записи с CVE
            valid_records = [rec for rec in records if rec.get('cve', '').strip()]
            total_records = len(valid_records)
            skipped_records = len(records) - total_records
            
            print(f"📊 Начинаем импорт {total_records} записей с проверкой дублей")
            print(f"📊 Пропущено {skipped_records} записей без CVE")
            
            # Этап 1: Подготовка к импорту (5%)
            if progress_callback:
                await progress_callback('preparing', 'Подготовка к импорту с проверкой дублей...', 5)
            
            # Этап 2: Вставка записей с проверкой дублей (70%)
            batch_size = 100
            inserted_count = 0
            duplicate_count = 0
            
            # Запрос для проверки дублей и вставки
            insert_query = """
                INSERT INTO vulnanalizer.hosts (hostname, ip_address, cve, cvss, criticality, status, os_name, zone)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                ON CONFLICT (hostname, ip_address, cve) DO NOTHING
                RETURNING id
            """
            
            # Запрос для подсчета дублей
            check_duplicate_query = """
                SELECT COUNT(*) FROM vulnanalizer.hosts 
                WHERE hostname = $1 AND ip_address = $2 AND cve = $3
            """
            
            for i in range(0, total_records, batch_size):
                batch_records = valid_records[i:i + batch_size]
                try:
                    await conn.execute("SELECT 1")
                except Exception as e:
                    # Connection lost, reconnecting
                    await conn.close()
                    conn = await asyncpg.connect(self.database_url)
                
                # Обрабатываем каждую запись
                for rec in batch_records:
                    try:
                        async with conn.transaction():
                            # Проверяем, есть ли дубль
                            duplicate_result = await conn.fetchval(check_duplicate_query, 
                                rec['hostname'], rec['ip_address'], rec['cve'])
                            
                            if duplicate_result > 0:
                                duplicate_count += 1
                                print(f"⚠️ Дубль найден: {rec['hostname']} - {rec['cve']}")
                            else:
                                # Вставляем запись
                                result = await conn.fetchval(insert_query, 
                                    rec['hostname'], rec['ip_address'], rec['cve'],
                                    rec['cvss'], rec['criticality'], rec['status'],
                                    rec.get('os_name', ''), rec.get('zone', ''))
                                
                                if result:
                                    inserted_count += 1
                                
                                if inserted_count % 10 == 0:
                                    progress_percent = 5 + (inserted_count / total_records) * 70
                                    if progress_callback:
                                        await progress_callback('inserting', 
                                            f'Сохранение записей... ({inserted_count}/{total_records})', 
                                            progress_percent, processed_records=inserted_count)
                                    
                    except Exception as e:
                        print(f"⚠️ Ошибка обработки записи {rec['hostname']}: {e}")
                        continue
                
                # Обновляем прогресс после каждой партии
                progress_percent = 5 + (inserted_count / total_records) * 70
                if progress_callback:
                    await progress_callback('inserting', 
                        f'Сохранение записей... ({inserted_count}/{total_records})', 
                        progress_percent, processed_records=inserted_count)
            
            print(f"✅ Импорт завершен: {inserted_count} записей сохранено, {duplicate_count} дублей пропущено")
            
            # Этап 3: Расчет рисков (25%)
            if inserted_count > 0:
                if progress_callback:
                    await progress_callback('calculating_risk', 'Расчет рисков для новых записей...', 75)
                
                # Получаем настройки для расчета рисков
                settings = await self.db.get_settings()
                
                # Получаем CVE для расчета рисков
                cve_rows = await conn.fetch("""
                    SELECT DISTINCT cve FROM vulnanalizer.hosts 
                    WHERE cve IS NOT NULL AND cve != ''
                """)
                
                if cve_rows:
                    print(f"🔄 Начинаем расчет рисков для {len(cve_rows)} CVE...")
                    
                    try:
                        # Используем улучшенный расчет рисков с анализом эксплойтов
                        await self._calculate_risks_with_exploits_during_import(cve_rows, conn, settings, progress_callback)
                        print("✅ Расчет рисков завершен успешно")
                    except Exception as risk_error:
                        print(f"❌ Ошибка в расчете рисков: {risk_error}")
                        import traceback
                        print(f"❌ Детали ошибки: {traceback.format_exc()}")
                else:
                    print("⚠️ Нет CVE для расчета рисков")
            
            # Завершение
            if progress_callback:
                await progress_callback('completed', 'Импорт и расчет рисков завершены', 100, 
                                      processed_records=inserted_count)
            
            return inserted_count
            
        except Exception as e:
            if progress_callback:
                await progress_callback('error', f'Ошибка импорта: {str(e)}', 0)
            raise
        finally:
            if conn:
                await conn.close()

    async def get_hosts_count(self) -> int:
        """Получить количество хостов"""
        conn = await self.get_connection()
        try:
            count = await conn.fetchval("SELECT COUNT(*) FROM vulnanalizer.hosts")
            return count
        finally:
            await self.release_connection(conn)
    
    async def get_hosts(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """Получить список хостов"""
        conn = await self.get_connection()
        try:
            query = """
                SELECT h.id, h.hostname, h.ip_address, h.cve, h.cvss, h.criticality, h.status, 
                       h.os_name, h.zone, h.epss_score, h.risk_score, h.created_at, h.updated_at,
                       h.metasploit_rank as msf_rank
                FROM vulnanalizer.hosts h
                ORDER BY h.created_at DESC 
                LIMIT $1 OFFSET $2
            """
            rows = await conn.fetch(query, limit, offset)
            results = []
            for row in rows:
                results.append({
                    'id': row['id'],
                    'hostname': row['hostname'],
                    'ip_address': row['ip_address'],
                    'cve': row['cve'],
                    'cvss': float(row['cvss']) if row['cvss'] else None,
                    'criticality': row['criticality'],
                    'status': row['status'],
                    'os_name': row['os_name'],
                    'zone': row['zone'],
                    'epss_score': float(row['epss_score']) if row['epss_score'] else None,
                    'risk_score': float(row['risk_score']) if row['risk_score'] else None,
                    'created_at': row['created_at'].isoformat() if row['created_at'] else None,
                    'updated_at': row['updated_at'].isoformat() if row['updated_at'] else None,
                    'msf_rank': row['msf_rank']
                })
            return results
        finally:
            await self.release_connection(conn)
    
    async def get_hosts_by_cve(self, cve: str) -> List[Dict[str, Any]]:
        """Получить хосты по CVE"""
        conn = await self.get_connection()
        try:
            query = """
                SELECT h.id, h.hostname, h.ip_address, h.cve, h.cvss, h.criticality, h.status, 
                       h.os_name, h.zone, h.epss_score, h.risk_score, h.created_at, h.updated_at,
                       h.metasploit_rank as msf_rank
                FROM vulnanalizer.hosts h
                WHERE h.cve = $1
                ORDER BY h.hostname
            """
            rows = await conn.fetch(query, cve)
            results = []
            for row in rows:
                results.append({
                    'id': row['id'],
                    'hostname': row['hostname'],
                    'ip_address': row['ip_address'],
                    'cve': row['cve'],
                    'cvss': float(row['cvss']) if row['cvss'] else None,
                    'criticality': row['criticality'],
                    'status': row['status'],
                    'os_name': row['os_name'],
                    'zone': row['zone'],
                    'epss_score': float(row['epss_score']) if row['epss_score'] else None,
                    'risk_score': float(row['risk_score']) if row['risk_score'] else None,
                    'created_at': row['created_at'].isoformat() if row['created_at'] else None,
                    'updated_at': row['updated_at'].isoformat() if row['updated_at'] else None,
                    'msf_rank': row['msf_rank']
                })
            return results
        finally:
            await self.release_connection(conn)
    
    async def delete_all_hosts(self) -> int:
        """Удалить все хосты"""
        conn = await self.get_connection()
        try:
            count = await conn.fetchval("SELECT COUNT(*) FROM vulnanalizer.hosts")
            await conn.execute("DELETE FROM vulnanalizer.hosts")
            return count
        finally:
            await self.release_connection(conn)
    
    async def insert_hosts_records_with_progress(self, records: list, progress_callback=None):
        """Вставить записи хостов с детальным отображением прогресса и расчетом риска"""
        conn = None
        try:
            conn = await asyncpg.connect(self.database_url)
            await conn.execute("SELECT 1")
            
            # Подсчитываем только записи с CVE
            valid_records = [rec for rec in records if rec.get('cve', '').strip()]
            total_records = len(valid_records)
            skipped_records = len(records) - total_records
            
            # Начинаем импорт записей
            
            # Этап 1: Подготовка к импорту (5%)
            if progress_callback:
                await progress_callback('preparing', 'Подготовка к импорту...', 5)
            
            # Подготовка к импорту записей
            
            # Этап 2: Вставка записей (70%)
            batch_size = 100
            inserted_count = 0
            
            query = """
                INSERT INTO vulnanalizer.hosts (hostname, ip_address, cve, cvss, criticality, status, os_name, zone)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            """
            
            for i in range(0, total_records, batch_size):
                batch_records = valid_records[i:i + batch_size]
                try:
                    await conn.execute("SELECT 1")
                except Exception as e:
                    # Connection lost, reconnecting
                    await conn.close()
                    conn = await asyncpg.connect(self.database_url)
                
                # Обрабатываем каждую запись в отдельной транзакции
                for rec in batch_records:
                    try:
                        async with conn.transaction():
                            await conn.execute(query, 
                                rec['hostname'], rec['ip_address'], rec['cve'],
                                rec['cvss'], rec['criticality'], rec['status'],
                                rec.get('os_name', ''), rec.get('zone', ''))
                            inserted_count += 1
                            
                            if inserted_count % 10 == 0:
                                progress_percent = 5 + (inserted_count / total_records) * 70
                                if progress_callback:
                                    await progress_callback('inserting', 
                                        f'Сохранение в базу данных... ({inserted_count:,}/{total_records:,})', 
                                        progress_percent, 
                                        current_step_progress=inserted_count, 
                                        processed_records=inserted_count)
                            
                    except Exception as e:
                        # Error inserting record, skipping
                        continue
                
                progress_percent = 5 + (inserted_count / total_records) * 70
                if progress_callback:
                    await progress_callback('inserting', 
                        f'Сохранение в базу данных... ({inserted_count:,}/{total_records:,})', 
                        progress_percent, 
                        current_step_progress=inserted_count, 
                        processed_records=inserted_count)
                
                print(f"💾 Обработано записей: {inserted_count:,}/{total_records:,} ({progress_percent:.1f}%)")
            
            # Этап 3: Анализ эксплойтов и расчет рисков (25%)
            if progress_callback:
                await progress_callback('calculating_risk', 'Анализ эксплойтов и расчет рисков...', 75)
            
            print("🔍 Начинаем анализ эксплойтов и расчет рисков для загруженных хостов...")
            
            try:
                settings_query = "SELECT key, value FROM vulnanalizer.settings"
                settings_rows = await conn.fetch(settings_query)
                settings = {row['key']: row['value'] for row in settings_rows}
                print(f"📋 Загружено настроек: {len(settings)}")
            except Exception as e:
                print(f"⚠️ Ошибка загрузки настроек: {e}")
                settings = {}
            
            cve_query = """
                SELECT DISTINCT cve FROM vulnanalizer.hosts 
                WHERE cve IS NOT NULL AND cve != '' 
                ORDER BY cve
            """
            cve_rows = await conn.fetch(cve_query)
            
            if cve_rows:
                print(f"📊 Найдено {len(cve_rows)} уникальных CVE для анализа")
                
                print(f"🔄 Начинаем анализ эксплойтов и расчет рисков для {len(cve_rows)} CVE...")
                
                try:
                    # Используем улучшенный расчет рисков с анализом эксплойтов
                    await self._calculate_risks_with_exploits_during_import(cve_rows, conn, settings, progress_callback)
                    print("✅ Анализ эксплойтов и расчет рисков завершен успешно")
                except Exception as risk_error:
                    print(f"❌ Ошибка в анализе эксплойтов и расчете рисков: {risk_error}")
                    import traceback
                    print(f"❌ Детали ошибки: {traceback.format_exc()}")
            else:
                print("⚠️ Нет CVE для анализа")
            
            # Завершение
            if progress_callback:
                await progress_callback('completed', 'Импорт и расчет рисков завершены', 100, 
                                      current_step_progress=inserted_count, 
                                      processed_records=inserted_count)
            
            # Расчет рисков завершен
            
            return inserted_count
            
        except Exception as e:
            if progress_callback:
                await progress_callback('error', f'Ошибка импорта: {str(e)}', 0)
            raise
        finally:
            if conn:
                await conn.close()

    async def _calculate_risks_with_exploits_during_import(self, cve_rows, conn, settings, progress_callback):
        """Улучшенный расчет рисков во время импорта с анализом эксплойтов"""
        print(f"🔍 Начинаем анализ эксплойтов и расчет рисков для {len(cve_rows)} CVE")
        
        total_cves = len(cve_rows)
        processed_cves = 0
        error_cves = 0
        updated_hosts = 0
        
        # Кэшируем настройки для оптимизации
        cached_settings = settings or {}
        
        # Список для batch обновлений хостов
        hosts_to_update = []
        
        # Инициализируем переменные кэша
        exploitdb_types_data = {}
        metasploit_data = {}
        
        # Получаем все EPSS данные одним запросом для оптимизации
        cve_list = [cve_row['cve'] for cve_row in cve_rows]
        epss_query = "SELECT cve, epss, percentile FROM vulnanalizer.epss WHERE cve = ANY($1::text[])"
        epss_rows = await conn.fetch(epss_query, cve_list)
        epss_data = {row['cve']: row for row in epss_rows}
        
        # Получаем все CVSS данные одним запросом
        cve_query = "SELECT cve_id as cve, cvss_v3_base_score, cvss_v2_base_score, cvss_v3_attack_vector, cvss_v3_privileges_required, cvss_v3_user_interaction, cvss_v2_access_vector, cvss_v2_access_complexity, cvss_v2_authentication FROM vulnanalizer.cve WHERE cve_id = ANY($1::text[])"
        cve_rows_data = await conn.fetch(cve_query, cve_list)
        cve_data = {row['cve']: row for row in cve_rows_data}
        
        # Получаем все ExploitDB данные одним запросом (исправленная логика)
        # Создаем временную таблицу для разбора всех CVE из поля codes
        exploitdb_query = """
            WITH cve_exploits AS (
                SELECT 
                    unnest(string_to_array(codes, ';')) as cve_id,
                    exploit_id
                FROM vulnanalizer.exploitdb 
                WHERE codes IS NOT NULL AND codes LIKE '%CVE-%'
            )
            SELECT cve_id, COUNT(*) as exploit_count
            FROM cve_exploits 
            WHERE cve_id LIKE 'CVE-%'
            GROUP BY cve_id
        """
        try:
            # Добавляем таймаут для запроса
            import asyncio
            exploitdb_rows = await asyncio.wait_for(conn.fetch(exploitdb_query), timeout=30.0)
            exploitdb_data = {row['cve_id']: row['exploit_count'] for row in exploitdb_rows}
            print(f"✅ Загружено ExploitDB данных: {len(exploitdb_data)} CVE с эксплойтами")
            
            # Загружаем типы эксплойтов ExploitDB
            exploitdb_types_query = """
                WITH cve_exploits AS (
                    SELECT 
                        unnest(string_to_array(codes, ';')) as cve_id,
                        type
                    FROM vulnanalizer.exploitdb 
                    WHERE codes IS NOT NULL AND codes LIKE '%CVE-%'
                )
                SELECT cve_id, type
                FROM cve_exploits 
                WHERE cve_id LIKE 'CVE-%'
            """
            exploitdb_types_rows = await asyncio.wait_for(conn.fetch(exploitdb_types_query), timeout=30.0)
            exploitdb_types_data = {row['cve_id']: row['type'] for row in exploitdb_types_rows}
            print(f"✅ Загружено типов ExploitDB: {len(exploitdb_types_data)} CVE")
            
            # Загружаем данные Metasploit
            metasploit_query = """
                WITH cve_metasploit AS (
                    SELECT 
                        unnest(string_to_array("references", ';')) as cve_id,
                        rank
                    FROM vulnanalizer.metasploit_modules 
                    WHERE "references" IS NOT NULL AND "references" LIKE '%CVE-%'
                )
                SELECT cve_id, rank
                FROM cve_metasploit 
                WHERE cve_id LIKE 'CVE-%'
            """
            metasploit_rows = await asyncio.wait_for(conn.fetch(metasploit_query), timeout=30.0)
            metasploit_data = {row['cve_id']: row['rank'] for row in metasploit_rows}
            print(f"✅ Загружено Metasploit данных: {len(metasploit_data)} CVE")
            
            # Отладочная информация
        except asyncio.TimeoutError:
            print("⚠️ Таймаут при загрузке ExploitDB данных, пропускаем анализ эксплойтов")
            exploitdb_data = {}
            exploitdb_types_data = {}
            metasploit_data = {}
        except Exception as e:
            print(f"⚠️ Ошибка загрузки ExploitDB данных: {e}")
            exploitdb_data = {}
            exploitdb_types_data = {}
            metasploit_data = {}
        
        print(f"✅ Загружено EPSS данных: {len(epss_data)} из {len(cve_list)} CVE")
        print(f"✅ Загружено CVSS данных: {len(cve_data)} из {len(cve_list)} CVE")
        print(f"✅ Загружено ExploitDB данных: {len(exploitdb_data)} CVE с эксплойтами")
        
        for i, cve_row in enumerate(cve_rows):
            cve = cve_row['cve']
            
            try:
                # Обновляем прогресс каждые 50 CVE
                if progress_callback and i % 50 == 0:
                    progress_percent = 75 + (i / total_cves) * 20  # 75-95%
                    await progress_callback('calculating_risk', 
                        f'Расчет рисков... ({i+1}/{total_cves} CVE, обновлено хостов: {updated_hosts})', 
                        progress_percent, 
                        current_step_progress=i+1, 
                        processed_cves=i+1,
                        updated_hosts=updated_hosts)
                
                # Получаем данные из кэша
                epss_row = epss_data.get(cve)
                cve_data_row = cve_data.get(cve)
                exploit_count = exploitdb_data.get(cve, 0)
                has_exploits = exploit_count > 0
                
                
                # Получаем хосты для этого CVE
                hosts_query = "SELECT id, cvss, criticality, confidential_data, internet_access FROM vulnanalizer.hosts WHERE cve = $1"
                hosts_rows = await conn.fetch(hosts_query, cve)
                
                if not hosts_rows:
                    print(f"⚠️ Нет хостов для CVE {cve}")
                    continue
                
                # Проверяем наличие EPSS данных
                has_epss_data = epss_row and epss_row['epss'] is not None
                
                if not has_epss_data:
                    print(f"⚠️ Нет EPSS данных для {cve}")
                
                # Рассчитываем риск для каждого хоста
                for host_row in hosts_rows:
                    try:
                        criticality = host_row['criticality'] or 'Medium'
                        
                        # Если нет EPSS данных, устанавливаем риск как n/a
                        if not has_epss_data:
                            epss_score = None
                            epss_percentile = None
                            risk_score = None
                            raw_risk = None
                        else:
                            # Используем оригинальную формулу расчета риска
                            epss_score = float(epss_row['epss'])
                            epss_percentile = float(epss_row['percentile']) if epss_row['percentile'] else None
                        
                        # Определяем CVSS score (приоритет: CVE v3 > CVE v2 > хост)
                        cvss_score = None
                        cvss_source = None
                        
                        if cve_data_row and cve_data_row['cvss_v3_base_score'] is not None:
                            cvss_score = float(cve_data_row['cvss_v3_base_score'])
                            cvss_source = 'CVSS v3'
                        elif cve_data_row and cve_data_row['cvss_v2_base_score'] is not None:
                            cvss_score = float(cve_data_row['cvss_v2_base_score'])
                            cvss_source = 'CVSS v2'
                        elif host_row['cvss'] is not None:
                            cvss_score = float(host_row['cvss'])
                            cvss_source = 'Host'
                        
                        # Рассчитываем риск только если есть EPSS данные
                        if has_epss_data:
                            # Используем единую функцию расчета риска
                            from database.risk_calculation import calculate_risk_score
                            
                            # Подготавливаем данные CVE для расчета
                            cve_calculation_data = {}
                            if cve_data_row:
                                cve_calculation_data.update({
                                    'cvss_v3_attack_vector': cve_data_row.get('cvss_v3_attack_vector'),
                                    'cvss_v3_privileges_required': cve_data_row.get('cvss_v3_privileges_required'),
                                    'cvss_v3_user_interaction': cve_data_row.get('cvss_v3_user_interaction'),
                                    'cvss_v2_access_vector': cve_data_row.get('cvss_v2_access_vector'),
                                    'cvss_v2_access_complexity': cve_data_row.get('cvss_v2_access_complexity'),
                                    'cvss_v2_authentication': cve_data_row.get('cvss_v2_authentication')
                                })
                            
                            # Получаем данные ExploitDB и Metasploit для CVE из кэша
                            if exploit_count > 0:
                                # Получаем тип эксплойта из кэша
                                if cve in exploitdb_types_data:
                                    cve_calculation_data['exploitdb_type'] = exploitdb_types_data[cve]
                            
                            # Получаем ранг Metasploit для CVE из кэша
                            if cve in metasploit_data:
                                cve_calculation_data['msf_rank'] = metasploit_data[cve]
                            else:
                                cve_calculation_data['msf_rank'] = None
                            
                            # Рассчитываем риск с единой функцией
                            risk_result = calculate_risk_score(
                                epss=epss_score,
                                cvss=cvss_score,
                                criticality=criticality,
                                settings=cached_settings,
                                cve_data=cve_calculation_data,
                                confidential_data=host_row.get('confidential_data', False),
                                internet_access=host_row.get('internet_access', False)
                            )
                            
                            risk_score = risk_result['risk_score']
                            raw_risk = risk_result['raw_risk']
                        else:
                            # Если нет EPSS данных, устанавливаем значения по умолчанию
                            cve_calculation_data = {}
                        
                        # Добавляем хост в список для batch обновления
                        hosts_to_update.append({
                            'id': host_row['id'],
                            'cvss_score': cvss_score,
                            'cvss_source': cvss_source,
                            'epss_score': epss_score,
                            'epss_percentile': epss_percentile,
                            'exploit_count': exploit_count,
                            'has_exploits': has_exploits,
                            'risk_score': risk_score,
                            'raw_risk': raw_risk,
                            'msf_rank': cve_calculation_data.get('msf_rank') if has_epss_data else None
                        })
                        
                        updated_hosts += 1
                        
                    except Exception as host_error:
                        print(f"⚠️ Ошибка обновления хоста {host_row['id']} для {cve}: {host_error}")
                        continue
                
                processed_cves += 1
                
                # Логируем прогресс каждые 100 CVE
                if i % 100 == 0:
                    print(f"✅ Обработано {i+1}/{total_cves} CVE (ошибок: {error_cves}, обновлено хостов: {updated_hosts})")
                
            except Exception as e:
                error_cves += 1
                print(f"❌ Ошибка обработки CVE {cve}: {e}")
                continue
        
        # Выполняем batch обновление хостов
        if hosts_to_update:
            await self._batch_update_hosts(conn, hosts_to_update)
        
        print(f"✅ Расчет рисков завершен: обработано {processed_cves} CVE, ошибок {error_cves}, обновлено хостов {updated_hosts}")
        
        if progress_callback:
            await progress_callback('calculating_risk', 
                f'Расчет рисков завершен ({processed_cves}/{total_cves} CVE, обновлено хостов: {updated_hosts})', 
                95, 
                current_step_progress=total_cves, 
                processed_records=processed_cves)
    
    async def _batch_update_hosts(self, conn, hosts_to_update):
        """Batch обновление хостов для оптимизации производительности"""
        if not hosts_to_update:
            return
        
        # Группируем хосты по 1000 для batch обновления
        batch_size = 1000
        for i in range(0, len(hosts_to_update), batch_size):
            batch = hosts_to_update[i:i + batch_size]
            
            # Создаем временную таблицу для batch обновления
            temp_table_query = """
                CREATE TEMP TABLE temp_host_updates (
                    id INTEGER,
                    cvss DECIMAL,
                    cvss_source TEXT,
                    epss_score DECIMAL,
                    epss_percentile DECIMAL,
                    exploits_count INTEGER,
                    has_exploits BOOLEAN,
                    risk_score INTEGER,
                    risk_raw DECIMAL,
                    metasploit_rank INTEGER
                )
            """
            await conn.execute(temp_table_query)
            
            # Вставляем данные в временную таблицу
            insert_query = """
                INSERT INTO temp_host_updates (id, cvss, cvss_source, epss_score, epss_percentile, 
                                             exploits_count, has_exploits, risk_score, risk_raw, metasploit_rank)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            """
            
            for host in batch:
                # Преобразуем msf_rank в INTEGER, если это возможно
                msf_rank = host['msf_rank']
                if msf_rank is not None:
                    try:
                        msf_rank = int(msf_rank) if isinstance(msf_rank, str) else msf_rank
                    except (ValueError, TypeError):
                        msf_rank = None
                
                await conn.execute(insert_query,
                    host['id'],
                    host['cvss_score'],
                    host['cvss_source'],
                    host['epss_score'],
                    host['epss_percentile'],
                    host['exploit_count'],
                    host['has_exploits'],
                    host['risk_score'],
                    host['raw_risk'],
                    msf_rank
                )
            
            # Выполняем batch обновление
            update_query = """
                UPDATE vulnanalizer.hosts SET
                    cvss = t.cvss,
                    cvss_source = t.cvss_source,
                    epss_score = t.epss_score,
                    epss_percentile = t.epss_percentile,
                    exploits_count = t.exploits_count,
                    has_exploits = t.has_exploits,
                    risk_score = t.risk_score,
                    risk_raw = t.risk_raw,
                    epss_updated_at = NOW(),
                    exploits_updated_at = NOW(),
                    risk_updated_at = NOW(),
                    metasploit_rank = t.metasploit_rank
                FROM temp_host_updates t
                WHERE hosts.id = t.id
            """
            await conn.execute(update_query)
            
            # Удаляем временную таблицу
            await conn.execute("DROP TABLE temp_host_updates")
    
    async def get_hosts_stats(self) -> Dict[str, Any]:
        """Получить статистику хостов"""
        conn = await self.get_connection()
        try:
            stats = {}
            
            # Общее количество
            stats['total'] = await conn.fetchval("SELECT COUNT(*) FROM vulnanalizer.hosts")
            
            # По статусам
            status_query = "SELECT status, COUNT(*) as count FROM vulnanalizer.hosts GROUP BY status"
            status_rows = await conn.fetch(status_query)
            stats['by_status'] = {row['status']: row['count'] for row in status_rows}
            
            # По критичности
            criticality_query = "SELECT criticality, COUNT(*) as count FROM vulnanalizer.hosts GROUP BY criticality"
            criticality_rows = await conn.fetch(criticality_query)
            stats['by_criticality'] = {row['criticality']: row['count'] for row in criticality_rows}
            
            # По зонам
            zone_query = "SELECT zone, COUNT(*) as count FROM vulnanalizer.hosts WHERE zone IS NOT NULL AND zone != '' GROUP BY zone"
            zone_rows = await conn.fetch(zone_query)
            stats['by_zone'] = {row['zone']: row['count'] for row in zone_rows}
            
            return stats
        finally:
            await self.release_connection(conn)

    async def count_hosts_records(self):
        """Подсчитать количество записей хостов (для обратной совместимости)"""
        return await self.get_hosts_count()

    async def search_hosts(self, hostname_pattern: str = None, cve: str = None, ip_address: str = None, criticality: str = None, exploits_only: bool = False, epss_only: bool = False, sort_by: str = None, limit: int = 100, page: int = 1):
        """Поиск хостов по различным критериям с расширенными данными"""
        conn = await self.get_connection()
        try:
            conditions = []
            params = []
            param_count = 0
            
            if hostname_pattern:
                param_count += 1
                # Поддержка маски * для hostname
                pattern = hostname_pattern.replace('*', '%')
                if '%' not in pattern:
                    pattern = f"%{pattern}%"
                conditions.append(f"hostname ILIKE ${param_count}")
                params.append(pattern)
            
            if cve:
                param_count += 1
                # Поддержка поиска по части CVE ID
                cve_pattern = cve.upper()
                if not cve_pattern.startswith('CVE-'):
                    # Если введен только номер, добавляем CVE- префикс
                    if cve_pattern.isdigit():
                        cve_pattern = f"CVE-%{cve_pattern}%"
                    else:
                        cve_pattern = f"%{cve_pattern}%"
                else:
                    # Если введен полный CVE, делаем точный поиск
                    cve_pattern = f"{cve_pattern}%"
                conditions.append(f"cve ILIKE ${param_count}")
                params.append(cve_pattern)
            
            if ip_address:
                param_count += 1
                conditions.append(f"CAST(ip_address AS TEXT) ILIKE ${param_count}")
                params.append(f"%{ip_address}%")
            
            if criticality:
                param_count += 1
                conditions.append(f"criticality = ${param_count}")
                params.append(criticality)
            
            if exploits_only:
                conditions.append("has_exploits = TRUE")
            
            if epss_only:
                conditions.append("epss_score IS NOT NULL")
            
            where_clause = " AND ".join(conditions) if conditions else "1=1"
            
            # Определяем сортировку
            order_clause = "ORDER BY hostname, cve"  # По умолчанию
            if sort_by:
                if sort_by == "risk_score_desc":
                    order_clause = "ORDER BY risk_score DESC NULLS LAST, hostname, cve"
                elif sort_by == "risk_score_asc":
                    order_clause = "ORDER BY risk_score ASC NULLS LAST, hostname, cve"
                elif sort_by == "cvss_desc":
                    order_clause = "ORDER BY cvss DESC NULLS LAST, hostname, cve"
                elif sort_by == "cvss_asc":
                    order_clause = "ORDER BY cvss ASC NULLS LAST, hostname, cve"
                elif sort_by == "epss_score_desc":
                    order_clause = "ORDER BY epss_score DESC NULLS LAST, hostname, cve"
                elif sort_by == "epss_score_asc":
                    order_clause = "ORDER BY epss_score ASC NULLS LAST, hostname, cve"
                elif sort_by == "exploits_count_desc":
                    order_clause = "ORDER BY exploits_count DESC NULLS LAST, hostname, cve"
                elif sort_by == "exploits_count_asc":
                    order_clause = "ORDER BY exploits_count ASC NULLS LAST, hostname, cve"
            
            # Сначала получаем общее количество записей
            count_query = f"SELECT COUNT(*) FROM vulnanalizer.hosts WHERE {where_clause}"
            total_count = await conn.fetchval(count_query, *params)
            
            # Затем получаем данные с пагинацией
            offset = (page - 1) * limit
            query = f"""
                SELECT h.id, h.hostname, h.ip_address, h.cve, h.cvss, h.cvss_source, h.criticality, h.status,
                       h.os_name, h.zone, h.epss_score, h.epss_percentile, h.risk_score, h.risk_raw, h.impact_score,
                       h.exploits_count, h.verified_exploits_count, h.has_exploits, h.last_exploit_date,
                       h.epss_updated_at, h.exploits_updated_at, h.risk_updated_at, h.created_at,
                       h.metasploit_rank as msf_rank
                FROM vulnanalizer.hosts h
                WHERE {where_clause}
                {order_clause}
                LIMIT {limit} OFFSET {offset}
            """
            
            rows = await conn.fetch(query, *params)
            
            results = []
            for row in rows:
                results.append({
                    'id': row['id'],
                    'hostname': row['hostname'],
                    'ip_address': row['ip_address'],
                    'cve': row['cve'],
                    'cvss': float(row['cvss']) if row['cvss'] else None,
                    'cvss_source': row['cvss_source'],
                    'criticality': row['criticality'],
                    'status': row['status'],
                    'os_name': row['os_name'],
                    'zone': row['zone'],
                    'epss_score': float(row['epss_score']) if row['epss_score'] else None,
                    'epss_percentile': float(row['epss_percentile']) if row['epss_percentile'] else None,
                    'risk_score': float(row['risk_score']) if row['risk_score'] else None,
                    'risk_raw': float(row['risk_raw']) if row['risk_raw'] else None,
                    'impact_score': float(row['impact_score']) if row['impact_score'] else None,
                    'exploits_count': row['exploits_count'],
                    'verified_exploits_count': row['verified_exploits_count'],
                    'has_exploits': row['has_exploits'],
                    'last_exploit_date': row['last_exploit_date'].isoformat() if row['last_exploit_date'] else None,
                    'epss_updated_at': row['epss_updated_at'].isoformat() if row['epss_updated_at'] else None,
                    'exploits_updated_at': row['exploits_updated_at'].isoformat() if row['exploits_updated_at'] else None,
                    'risk_updated_at': row['risk_updated_at'].isoformat() if row['risk_updated_at'] else None,
                    'imported_at': row['created_at'].isoformat() if row['created_at'] else None,
                    'msf_rank': row['msf_rank']
                })
            
            return results, total_count
        except Exception as e:
            print(f"Error searching hosts: {e}")
            return [], 0
        finally:
            await self.release_connection(conn)

    async def get_host_by_id(self, host_id: int):
        """Получить хост по ID с расширенными данными"""
        conn = await self.get_connection()
        try:
            query = """
                SELECT h.id, h.hostname, h.ip_address, h.cve, h.cvss, h.criticality, h.status,
                       h.os_name, h.zone, h.epss_score, h.epss_percentile, h.risk_score, h.risk_raw, h.impact_score,
                       h.exploits_count, h.verified_exploits_count, h.has_exploits, h.last_exploit_date,
                       h.epss_updated_at, h.exploits_updated_at, h.risk_updated_at, h.created_at,
                       h.metasploit_rank as msf_rank
                FROM vulnanalizer.hosts h
                WHERE h.id = $1
            """
            row = await conn.fetchrow(query, host_id)
            
            if row:
                return {
                    'id': row['id'],
                    'hostname': row['hostname'],
                    'ip_address': row['ip_address'],
                    'cve': row['cve'],
                    'cvss': float(row['cvss']) if row['cvss'] else None,
                    'criticality': row['criticality'],
                    'status': row['status'],
                    'os_name': row['os_name'],
                    'zone': row['zone'],
                    'epss_score': float(row['epss_score']) if row['epss_score'] else None,
                    'epss_percentile': float(row['epss_percentile']) if row['epss_percentile'] else None,
                    'risk_score': float(row['risk_score']) if row['risk_score'] else None,
                    'risk_raw': float(row['risk_raw']) if row['risk_raw'] else None,
                    'impact_score': float(row['impact_score']) if row['impact_score'] else None,
                    'exploits_count': row['exploits_count'],
                    'verified_exploits_count': row['verified_exploits_count'],
                    'has_exploits': row['has_exploits'],
                    'last_exploit_date': row['last_exploit_date'].isoformat() if row['last_exploit_date'] else None,
                    'epss_updated_at': row['epss_updated_at'].isoformat() if row['epss_updated_at'] else None,
                    'exploits_updated_at': row['exploits_updated_at'].isoformat() if row['exploits_updated_at'] else None,
                    'risk_updated_at': row['risk_updated_at'].isoformat() if row['risk_updated_at'] else None,
                    'imported_at': row['created_at'].isoformat() if row['created_at'] else None,
                    'msf_rank': row['msf_rank']
                }
            return None
        except Exception as e:
            print(f"Error getting host by ID {host_id}: {e}")
            return None
        finally:
            await self.release_connection(conn)

    async def clear_hosts(self):
        """Очистка таблицы хостов с оптимизацией для больших таблиц"""
        conn = await self.get_connection()
        try:
            # Начинаем транзакцию
            async with conn.transaction():
                # Получаем количество записей перед удалением
                count_query = "SELECT COUNT(*) FROM vulnanalizer.hosts"
                count_before = await conn.fetchval(count_query)
                print(f"🗑️ Удаляем {count_before} записей из таблицы хостов")
                
                if count_before == 0:
                    print("✅ Таблица хостов уже пуста")
                    return {
                        'success': True,
                        'deleted_count': 0,
                        'message': 'Таблица хостов уже пуста'
                    }
                
                # Для больших таблиц используем TRUNCATE вместо DELETE
                if count_before > 10000:
                    print("📊 Большая таблица, используем TRUNCATE для оптимизации")
                    try:
                        truncate_query = "TRUNCATE TABLE vulnanalizer.hosts RESTART IDENTITY CASCADE"
                        await conn.execute(truncate_query)
                        deleted_count = count_before
                    except Exception as truncate_error:
                        print(f"⚠️ TRUNCATE не удался, пробуем батчевую очистку: {truncate_error}")
                        # Если TRUNCATE не удался, используем батчевую очистку
                        await self.release_connection(conn)
                        return await self.clear_hosts_batch()
                else:
                    # Для небольших таблиц используем DELETE
                    print("📊 Небольшая таблица, используем DELETE")
                    try:
                        delete_query = "DELETE FROM vulnanalizer.hosts"
                        result = await conn.execute(delete_query)
                        deleted_count = count_before
                    except Exception as delete_error:
                        print(f"⚠️ DELETE не удался, пробуем батчевую очистку: {delete_error}")
                        # Если DELETE не удался, используем батчевую очистку
                        await self.release_connection(conn)
                        return await self.clear_hosts_batch()
                
                # Проверяем результат
                count_after = await conn.fetchval(count_query)
                print(f"✅ Очистка завершена: удалено {deleted_count} записей")
                
                return {
                    'success': True,
                    'deleted_count': deleted_count,
                    'message': f'Удалено {deleted_count} записей хостов'
                }
        except Exception as e:
            print(f"❌ Ошибка очистки таблицы хостов: {e}")
            raise e
        finally:
            await self.release_connection(conn)
    
    async def clear_hosts_batch(self, batch_size=1000):
        """Очистка таблицы хостов батчами для очень больших таблиц"""
        conn = await self.get_connection()
        try:
            total_deleted = 0
            
            while True:
                # Удаляем батчами
                delete_query = f"""
                    DELETE FROM vulnanalizer.hosts 
                    WHERE id IN (
                        SELECT id FROM vulnanalizer.hosts 
                        LIMIT {batch_size}
                    )
                """
                result = await conn.execute(delete_query)
                
                # Получаем количество удаленных строк
                deleted_count = int(result.split()[-1]) if result.split()[-1].isdigit() else 0
                total_deleted += deleted_count
                
                print(f"🗑️ Удалено {deleted_count} записей (всего: {total_deleted})")
                
                # Если удалили меньше чем batch_size, значит таблица пуста
                if deleted_count < batch_size:
                    break
                    
                # Небольшая пауза между батчами
                import asyncio
                await asyncio.sleep(0.1)
            
            print(f"✅ Очистка завершена: удалено {total_deleted} записей")
            return {
                'success': True,
                'deleted_count': total_deleted,
                'message': f'Удалено {total_deleted} записей хостов (батчами)'
            }
            
        except Exception as e:
            print(f"❌ Ошибка батчевой очистки таблицы хостов: {e}")
            raise e
        finally:
            await self.release_connection(conn)

    async def import_vm_hosts(self, hosts_data: list):
        """Импортировать хосты из VM MaxPatrol"""
        conn = await self.get_connection()
        try:
            # Получаем количество записей до импорта
            count_before = await conn.fetchval("SELECT COUNT(*) FROM vulnanalizer.hosts")
            print(f"Hosts records in database before VM import: {count_before}")
            
            async with conn.transaction():
                inserted_count = 0
                updated_count = 0
                
                for host_data in hosts_data:
                    # Парсим hostname и IP из строки вида "hostname (IP)"
                    host_info = host_data.get('hostname', '')
                    ip_address = ''
                    hostname = host_info
                    
                    if '(' in host_info and ')' in host_info:
                        parts = host_info.split('(')
                        hostname = parts[0].strip()
                        ip_address = parts[1].rstrip(')').strip()
                    
                    # Извлекаем CVE из данных
                    cve = host_data.get('cve', '').strip()
                    if not cve:
                        continue
                    
                    # Используем критичность из VM или определяем на основе ОС
                    vm_criticality = host_data.get('criticality', '').strip()
                    os_name = host_data.get('os_name', '').lower()
                    
                    if vm_criticality and vm_criticality in ['Critical', 'High', 'Medium', 'Low']:
                        criticality = vm_criticality
                    else:
                        # Определяем критичность на основе ОС если не указана в VM
                        criticality = 'Medium'
                        if 'windows' in os_name:
                            criticality = 'High'
                        elif 'rhel' in os_name or 'centos' in os_name:
                            criticality = 'High'
                        elif 'ubuntu' in os_name or 'debian' in os_name:
                            criticality = 'Medium'
                    
                    # Проверяем, существует ли запись для этого хоста и CVE
                    existing = await conn.fetchval(
                        "SELECT id FROM vulnanalizer.hosts WHERE hostname = $1 AND cve = $2", 
                        hostname, cve
                    )
                    
                    if existing:
                        # Обновляем существующую запись
                        query = """
                            UPDATE vulnanalizer.hosts 
                            SET ip_address = $2, os_name = $3, criticality = $4, 
                                zone = $5, status = $6, updated_at = CURRENT_TIMESTAMP
                            WHERE hostname = $1 AND cve = $7
                        """
                        await conn.execute(query, 
                            hostname, ip_address, host_data.get('os_name', ''), 
                            criticality, host_data.get('zone', ''), 'Active', cve)
                        updated_count += 1
                    else:
                        # Вставляем новую запись
                        query = """
                            INSERT INTO vulnanalizer.hosts (hostname, ip_address, cve, cvss, criticality, status, os_name, zone)
                            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                            ON CONFLICT (hostname, cve) 
                            DO UPDATE SET 
                                ip_address = EXCLUDED.ip_address,
                                cvss = EXCLUDED.cvss,
                                criticality = EXCLUDED.criticality,
                                status = EXCLUDED.status,
                                os_name = EXCLUDED.os_name,
                                zone = EXCLUDED.zone,
                                updated_at = CURRENT_TIMESTAMP
                        """
                        await conn.execute(query, 
                            hostname, ip_address, cve, None, criticality, 'Active', 
                            host_data.get('os_name', ''), host_data.get('zone', ''))
                        inserted_count += 1
                
                # Получаем количество записей после импорта
                count_after = await conn.fetchval("SELECT COUNT(*) FROM vulnanalizer.hosts")
                print(f"Hosts records in database after VM import: {count_after}")
                print(f"New hosts records inserted: {inserted_count}")
                print(f"Existing hosts records updated: {updated_count}")
                print(f"Total VM hosts processed: {len(hosts_data)}")
                print(f"Net change in hosts database: {count_after - count_before}")
                
                return {
                    'inserted': inserted_count,
                    'updated': updated_count,
                    'total_processed': len(hosts_data),
                    'net_change': count_after - count_before
                }
                
        finally:
            await self.release_connection(conn)

    async def get_vm_import_status(self):
        """Получить статус последнего импорта VM"""
        conn = await self.get_connection()
        try:
            # Получаем последнюю запись о импорте
            query = """
                SELECT key, value, updated_at 
                FROM vulnanalizer.settings 
                WHERE key IN ('vm_last_import', 'vm_last_import_count', 'vm_last_import_error')
                ORDER BY updated_at DESC
                LIMIT 1
            """
            rows = await conn.fetch(query)
            
            status = {
                'last_import': None,
                'last_import_count': 0,
                'last_import_error': None,
                'vm_enabled': False  # Будет переопределено ниже на основе наличия настроек
            }
            
            for row in rows:
                if row['key'] == 'vm_last_import':
                    status['last_import'] = row['updated_at']
                elif row['key'] == 'vm_last_import_count':
                    status['last_import_count'] = int(row['value']) if row['value'].isdigit() else 0
                elif row['key'] == 'vm_last_import_error':
                    status['last_import_error'] = row['value']
            
            # Проверяем, настроен ли VM импорт (есть ли хост и пользователь)
            vm_host = await conn.fetchval("SELECT value FROM vulnanalizer.settings WHERE key = 'vm_host'")
            vm_username = await conn.fetchval("SELECT value FROM vulnanalizer.settings WHERE key = 'vm_username'")
            status['vm_enabled'] = bool(vm_host and vm_username)
            
            return status
        finally:
            await self.release_connection(conn)

    async def update_vm_import_status(self, count: int, error: str = None):
        """Обновить статус импорта VM"""
        conn = await self.get_connection()
        try:
            # Обновляем количество импортированных записей
            await conn.execute(
                "INSERT INTO vulnanalizer.settings (key, value) VALUES ('vm_last_import_count', $1) ON CONFLICT (key) DO UPDATE SET value = $1, updated_at = CURRENT_TIMESTAMP",
                str(count)
            )
            
            # Обновляем время последнего импорта
            await conn.execute(
                "INSERT INTO vulnanalizer.settings (key, value) VALUES ('vm_last_import', CURRENT_TIMESTAMP::text) ON CONFLICT (key) DO UPDATE SET value = CURRENT_TIMESTAMP::text, updated_at = CURRENT_TIMESTAMP"
            )
            
            # Обновляем ошибку, если есть
            if error:
                await conn.execute(
                    "INSERT INTO vulnanalizer.settings (key, value) VALUES ('vm_last_import_error', $1) ON CONFLICT (key) DO UPDATE SET value = $1, updated_at = CURRENT_TIMESTAMP",
                    error
                )
            else:
                # Очищаем ошибку, если импорт успешен
                await conn.execute("DELETE FROM vulnanalizer.settings WHERE key = 'vm_last_import_error'")
                
        finally:
            await self.release_connection(conn)
