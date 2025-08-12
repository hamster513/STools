import os
import asyncpg
import asyncio
from typing import Dict, List, Any, Optional
import json
from datetime import datetime

class Database:
    def __init__(self):
        self.database_url = os.getenv("DATABASE_URL", "postgresql://vulnanalizer:vulnanalizer@postgres:5432/vulnanalizer")
        self.pool = None

    async def get_pool(self):
        """Получить или создать пул соединений"""
        if self.pool is None:
            self.pool = await asyncpg.create_pool(
                self.database_url,
                min_size=5,
                max_size=20,
                command_timeout=60
            )
        return self.pool

    async def get_connection(self):
        """Получить соединение из пула"""
        try:
            pool = await self.get_pool()
            return await pool.acquire()
        except Exception as e:
            print(f"Database connection failed: {e}")
            raise

    async def release_connection(self, conn):
        """Освободить соединение обратно в пул"""
        try:
            pool = await self.get_pool()
            await pool.release(conn)
        except Exception as e:
            print(f"Error releasing connection: {e}")

    async def test_connection(self):
        conn = await self.get_connection()
        try:
            await conn.execute("SELECT 1")
            return True
        except Exception as e:
            print(f"Database test failed: {e}")
            return False
        finally:
            await self.release_connection(conn)

    async def get_settings(self) -> Dict[str, str]:
        conn = await self.get_connection()
        try:
            query = "SELECT key, value FROM settings"
            rows = await conn.fetch(query)
            
            settings = {}
            for row in rows:
                settings[row['key']] = row['value']
            
            # Устанавливаем значение по умолчанию для max_concurrent_requests
            if 'max_concurrent_requests' not in settings:
                settings['max_concurrent_requests'] = '3'
            
            return settings
        finally:
            await self.release_connection(conn)

    async def update_settings(self, settings: Dict[str, str]):
        conn = await self.get_connection()
        try:
            for key, value in settings.items():
                query = """
                    INSERT INTO settings (key, value) 
                    VALUES ($1, $2) 
                    ON CONFLICT (key) 
                    DO UPDATE SET value = $2, updated_at = CURRENT_TIMESTAMP
                """
                await conn.execute(query, key, value)
        finally:
            await self.release_connection(conn)

    async def insert_epss_records(self, records: list):
        """Вставить записи EPSS с улучшенным управлением соединениями"""
        conn = None
        try:
            # Создаем отдельное соединение для массовой вставки
            conn = await asyncpg.connect(self.database_url)
            
            # Проверяем, что соединение активно
            await conn.execute("SELECT 1")
            
            # Получаем количество записей до вставки
            count_before = await conn.fetchval("SELECT COUNT(*) FROM epss")
            print(f"EPSS records in database before insert: {count_before}")
            
            # Группируем записи по CVE для обработки
            cve_groups = {}
            for rec in records:
                cve = rec['cve']
                if cve not in cve_groups:
                    cve_groups[cve] = []
                cve_groups[cve].append(rec)
            
            inserted_count = 0
            updated_count = 0
            
            # Обрабатываем записи батчами для избежания проблем с соединением
            batch_size = 1000
            cve_list = list(cve_groups.keys())
            
            for i in range(0, len(cve_list), batch_size):
                batch_cves = cve_list[i:i + batch_size]
                
                # Проверяем соединение перед каждым батчем
                try:
                    await conn.execute("SELECT 1")
                except Exception as e:
                    print(f"Connection lost, reconnecting... Error: {e}")
                    await conn.close()
                    conn = await asyncpg.connect(self.database_url)
                
                # Обрабатываем каждую запись отдельно с повторными попытками
                for cve in batch_cves:
                    cve_records = cve_groups[cve]
                    # Берем самую свежую запись для каждого CVE
                    latest_record = max(cve_records, key=lambda x: x['date'])
                    
                    max_retries = 3
                    for retry in range(max_retries):
                        try:
                            # Проверяем соединение перед каждой операцией
                            await conn.execute("SELECT 1")
                            
                            # Проверяем, существует ли запись для этого CVE
                            existing = await conn.fetchval("SELECT id FROM epss WHERE cve = $1", cve)
                            
                            if existing:
                                # Обновляем существующую запись
                                query = """
                                    UPDATE epss 
                                    SET epss = $2, percentile = $3, cvss = $4, date = $5
                                    WHERE cve = $1
                                """
                                await conn.execute(query, 
                                    cve, latest_record['epss'], latest_record['percentile'], 
                                    latest_record.get('cvss'), latest_record['date'])
                                updated_count += 1
                            else:
                                # Вставляем новую запись
                                query = """
                                    INSERT INTO epss (cve, epss, percentile, cvss, date)
                                    VALUES ($1, $2, $3, $4, $5)
                                """
                                await conn.execute(query, 
                                    cve, latest_record['epss'], latest_record['percentile'], 
                                    latest_record.get('cvss'), latest_record['date'])
                                inserted_count += 1
                            
                            # Если успешно, выходим из цикла повторных попыток
                            break
                            
                        except Exception as e:
                            print(f"Error processing CVE {cve} (attempt {retry + 1}/{max_retries}): {e}")
                            if retry < max_retries - 1:
                                # Переподключаемся и продолжаем
                                try:
                                    await conn.close()
                                except:
                                    pass
                                conn = await asyncpg.connect(self.database_url)
                                await asyncio.sleep(1)  # Небольшая пауза перед повторной попыткой
                            else:
                                print(f"Failed to process CVE {cve} after {max_retries} attempts")
                                continue
                
                print(f"Processed batch {i//batch_size + 1}/{(len(cve_list) + batch_size - 1)//batch_size}")
            
            # Получаем количество записей после вставки
            count_after = await conn.fetchval("SELECT COUNT(*) FROM epss")
            print(f"EPSS records in database after insert: {count_after}")
            print(f"New EPSS records inserted: {inserted_count}")
            print(f"Existing EPSS records updated: {updated_count}")
            print(f"Total unique CVE records processed: {len(cve_groups)}")
            print(f"Net change in EPSS database: {count_after - count_before}")
            
        except Exception as e:
            print(f"Error in insert_epss_records: {e}")
            raise e
        finally:
            if conn:
                try:
                    await conn.close()
                except Exception as e:
                    print(f"Error closing connection: {e}")

    async def count_epss_records(self):
        conn = await self.get_connection()
        try:
            # Проверяем, что таблица существует
            table_exists = await conn.fetchval(
                "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'epss')"
            )
            if not table_exists:
                print("Table epss does not exist")
                return 0
            
            row = await conn.fetchrow("SELECT COUNT(*) as cnt FROM epss")
            return row['cnt'] if row else 0
        except Exception as e:
            print(f"Error counting epss records: {e}")
            raise
        finally:
            await self.release_connection(conn)

    async def get_all_epss_records(self):
        """Получить все записи EPSS"""
        conn = await self.get_connection()
        try:
            rows = await conn.fetch("SELECT cve, epss, percentile FROM epss ORDER BY cve")
            return [dict(row) for row in rows]
        except Exception as e:
            print(f"Error getting all epss records: {e}")
            raise
        finally:
            await self.release_connection(conn)

    async def insert_exploitdb_records(self, records: list):
        """Вставить записи ExploitDB с улучшенным управлением соединениями"""
        conn = None
        try:
            # Создаем отдельное соединение для массовой вставки
            conn = await asyncpg.connect(self.database_url)
            
            # Проверяем, что соединение активно
            await conn.execute("SELECT 1")
            
            # Получаем количество записей до вставки
            count_before = await conn.fetchval("SELECT COUNT(*) FROM exploitdb")
            print(f"Records in database before insert: {count_before}")
            
            inserted_count = 0
            updated_count = 0
            
            # Обрабатываем записи батчами для избежания проблем с соединением
            batch_size = 1000
            
            for i in range(0, len(records), batch_size):
                batch_records = records[i:i + batch_size]
                
                # Проверяем соединение перед каждым батчем
                try:
                    await conn.execute("SELECT 1")
                except Exception as e:
                    print(f"Connection lost, reconnecting... Error: {e}")
                    await conn.close()
                    conn = await asyncpg.connect(self.database_url)
                
                async with conn.transaction():
                    query = """
                        INSERT INTO exploitdb (exploit_id, file_path, description, date_published, author, type, platform, port, date_added, date_updated, verified, codes, tags, aliases, screenshot_url, application_url, source_url)
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17)
                        ON CONFLICT (exploit_id) DO UPDATE SET 
                            file_path = $2, description = $3, date_published = $4, author = $5, type = $6, platform = $7, port = $8, date_added = $9, date_updated = $10, verified = $11, codes = $12, tags = $13, aliases = $14, screenshot_url = $15, application_url = $16, source_url = $17
                    """
                    
                    for rec in batch_records:
                        try:
                            # Проверяем, существует ли запись
                            existing = await conn.fetchval("SELECT exploit_id FROM exploitdb WHERE exploit_id = $1", rec['exploit_id'])
                            
                            await conn.execute(query, 
                                rec['exploit_id'], rec.get('file_path'), rec.get('description'), 
                                rec.get('date_published'), rec.get('author'), rec.get('type'), 
                                rec.get('platform'), rec.get('port'), rec.get('date_added'), 
                                rec.get('date_updated'), rec.get('verified', False), rec.get('codes'), 
                                rec.get('tags'), rec.get('aliases'), rec.get('screenshot_url'), 
                                rec.get('application_url'), rec.get('source_url'))
                            
                            if existing:
                                updated_count += 1
                            else:
                                inserted_count += 1
                                
                        except Exception as e:
                            print(f"Error inserting record {rec['exploit_id']}: {e}")
                            continue
                
                print(f"Processed batch {i//batch_size + 1}/{(len(records) + batch_size - 1)//batch_size}")
            
            # Получаем количество записей после вставки
            count_after = await conn.fetchval("SELECT COUNT(*) FROM exploitdb")
            print(f"Records in database after insert: {count_after}")
            print(f"New records inserted: {inserted_count}")
            print(f"Existing records updated: {updated_count}")
            print(f"Total records processed: {len(records)}")
            print(f"Net change in database: {count_after - count_before}")
            
        except Exception as e:
            print(f"Error in insert_exploitdb_records: {e}")
            raise e
        finally:
            if conn:
                try:
                    await conn.close()
                except Exception as e:
                    print(f"Error closing connection: {e}")

    async def count_exploitdb_records(self):
        conn = await self.get_connection()
        try:
            # Проверяем, что таблица существует
            table_exists = await conn.fetchval(
                "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'exploitdb')"
            )
            if not table_exists:
                print("Table exploitdb does not exist")
                return 0
            
            row = await conn.fetchrow("SELECT COUNT(*) as cnt FROM exploitdb")
            return row['cnt'] if row else 0
        except Exception as e:
            print(f"Error counting exploitdb records: {e}")
            raise
        finally:
            await self.release_connection(conn)

    async def get_all_exploitdb_records(self):
        """Получить все записи ExploitDB"""
        conn = await self.get_connection()
        try:
            rows = await conn.fetch("SELECT exploit_id, description, date_published, verified, aliases, tags FROM exploitdb ORDER BY exploit_id")
            return [dict(row) for row in rows]
        except Exception as e:
            print(f"Error getting all exploitdb records: {e}")
            raise
        finally:
            await self.release_connection(conn)

    async def get_epss_by_cve(self, cve_id: str):
        """Получить данные EPSS по CVE ID"""
        conn = await self.get_connection()
        try:
            query = """
                SELECT cve, epss, percentile, cvss, date 
                FROM epss 
                WHERE cve = $1 
                ORDER BY date DESC 
                LIMIT 1
            """
            row = await conn.fetchrow(query, cve_id)
            
            if row:
                return {
                    'cve': row['cve'],
                    'epss': float(row['epss']) if row['epss'] else None,
                    'percentile': float(row['percentile']) if row['percentile'] else None,
                    'cvss': float(row['cvss']) if row['cvss'] else None,
                    'date': row['date'].isoformat() if row['date'] else None
                }
            return None
        except Exception as e:
            print(f"Error getting EPSS data for {cve_id}: {e}")
            return None
        finally:
            await self.release_connection(conn)

    async def get_exploitdb_by_cve(self, cve_id: str):
        """Получить данные ExploitDB по CVE ID"""
        conn = await self.get_connection()
        try:
            # Нормализуем CVE ID для поиска в разных форматах
            cve_normalized = cve_id.upper()
            cve_with_underscores = cve_normalized.replace('-', '_')
            cve_without_dashes = cve_normalized.replace('-', '')
            
            # Извлекаем год и номер из CVE для более гибкого поиска
            cve_parts = cve_normalized.split('-')
            if len(cve_parts) >= 3:
                cve_year = cve_parts[1]
                cve_number = cve_parts[2]
                cve_year_number = f"{cve_year}-{cve_number}"
                cve_year_underscore_number = f"{cve_year}_{cve_number}"
            else:
                cve_year_number = cve_normalized
                cve_year_underscore_number = cve_normalized
            
            # Ищем в поле aliases, tags, description с разными форматами CVE
            query = """
                SELECT exploit_id, file_path, description, date_published, 
                       author, type, platform, port, date_added, date_updated, 
                       verified, codes, tags, aliases, screenshot_url, 
                       application_url, source_url
                FROM exploitdb 
                WHERE aliases ILIKE $1 
                   OR tags ILIKE $1 
                   OR description ILIKE $1
                   OR aliases ILIKE $2
                   OR tags ILIKE $2
                   OR description ILIKE $2
                   OR aliases ILIKE $3
                   OR tags ILIKE $3
                   OR description ILIKE $3
                   OR aliases ILIKE $4
                   OR tags ILIKE $4
                   OR description ILIKE $4
                   OR aliases ILIKE $5
                   OR tags ILIKE $5
                   OR description ILIKE $5
                ORDER BY date_published DESC
            """
            rows = await conn.fetch(query, 
                f'%{cve_normalized}%', 
                f'%{cve_with_underscores}%', 
                f'%{cve_without_dashes}%',
                f'%{cve_year_number}%',
                f'%{cve_year_underscore_number}%')
            
            results = []
            for row in rows:
                results.append({
                    'exploit_id': row['exploit_id'],
                    'file_path': row['file_path'],
                    'description': row['description'],
                    'date_published': row['date_published'].isoformat() if row['date_published'] else None,
                    'author': row['author'],
                    'type': row['type'],
                    'platform': row['platform'],
                    'port': row['port'],
                    'date_added': row['date_added'].isoformat() if row['date_added'] else None,
                    'date_updated': row['date_updated'].isoformat() if row['date_updated'] else None,
                    'verified': row['verified'],
                    'codes': row['codes'],
                    'tags': row['tags'],
                    'aliases': row['aliases'],
                    'screenshot_url': row['screenshot_url'],
                    'application_url': row['application_url'],
                    'source_url': row['source_url']
                })
            
            return results
        except Exception as e:
            print(f"Error getting ExploitDB data for {cve_id}: {e}")
            return []
        finally:
            await self.release_connection(conn)

    def _get_latest_exploit_date(self, exploitdb_data):
        """Получить самую позднюю дату эксплойта"""
        if not exploitdb_data:
            return None
        
        exploit_dates = [e.get('date_published') for e in exploitdb_data if e.get('date_published')]
        if not exploit_dates:
            return None
        
        # Берем самую позднюю дату
        latest_date = max(exploit_dates)
        if isinstance(latest_date, str):
            try:
                # Парсим строку даты
                from datetime import datetime
                return datetime.strptime(latest_date, '%Y-%m-%d').date()
            except:
                return None
        else:
            return latest_date

    def _calculate_risk_score(self, epss: float, cvss: float = None, settings: dict = None) -> dict:
        """Рассчитать риск по формуле: raw_risk = EPSS * Impact (без CVSS)"""
        if epss is None:
            return {
                'raw_risk': None,
                'risk_score': None,
                'calculation_possible': False,
                'impact': None
            }
        
        # Конвертируем decimal в float если нужно
        if hasattr(epss, 'as_tuple'):  # Это decimal.Decimal
            epss = float(epss)
        
        # Рассчитываем Impact на основе настроек (если есть)
        if settings:
            impact = self._calculate_impact(settings)
        else:
            # Используем базовый Impact если настройки не предоставлены
            impact = 0.5
        
        # Рассчитываем риск только на основе EPSS и Impact
        raw_risk = epss * impact
        risk_score = min(1, raw_risk) * 100
        
        return {
            'raw_risk': raw_risk,
            'risk_score': risk_score,
            'calculation_possible': True,
            'impact': impact
        }

    def _calculate_impact(self, settings: dict) -> float:
        """Рассчитать Impact на основе настроек"""
        # Веса для критичности ресурса
        resource_weights = {
            'Critical': 0.33,
            'High': 0.25,
            'Medium': 0.15,
            'None': 0.1
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
        resource_criticality = settings.get('impact_resource_criticality', 'Medium')
        confidential_data = settings.get('impact_confidential_data', 'Отсутствуют')
        internet_access = settings.get('impact_internet_access', 'Недоступен')
        
        # Рассчитываем Impact
        impact = (
            resource_weights.get(resource_criticality, 0.15) +
            data_weights.get(confidential_data, 0.1) +
            internet_weights.get(internet_access, 0.1)
        )
        
        # Конвертируем в float если это decimal
        if hasattr(impact, 'as_tuple'):  # Это decimal.Decimal
            impact = float(impact)
        
        return impact

    async def update_hosts_epss_and_exploits_background_parallel(self, progress_callback=None, max_concurrent=10):
        """Обновить данные EPSS и эксплойтов для всех хостов с параллельной обработкой"""
        print("🔄 Starting parallel update_hosts_epss_and_exploits_background function")
        conn = await self.get_connection()
        try:
            print("🔄 Got database connection")
            
            # Получаем все уникальные CVE из хостов
            cve_query = """
                SELECT DISTINCT cve FROM hosts 
                WHERE cve IS NOT NULL AND cve != '' 
                ORDER BY cve
            """
            print("🔄 Executing CVE query")
            cve_rows = await conn.fetch(cve_query)
            print(f"🔄 CVE query returned {len(cve_rows)} rows")
            
            if not cve_rows:
                return {"success": True, "message": "Нет CVE для обновления", "updated_count": 0}
            
            total_cves = len(cve_rows)
            updated_count = 0
            skipped_cves = 0
            processed_cves = 0
            
            print(f"🔄 Starting parallel update: found {total_cves} unique CVEs")
            
            if progress_callback:
                progress_callback('initializing', f'Найдено {total_cves} уникальных CVE для обновления', 
                                total_cves=total_cves, processed_cves=0)
            
            # Создаем семафор для ограничения параллельных операций
            semaphore = asyncio.Semaphore(max_concurrent)
            
            async def process_single_cve(cve, index):
                """Обработать один CVE"""
                async with semaphore:
                    # Проверяем, не была ли задача отменена
                    task = await self.get_background_task('hosts_update')
                    if task and task.get('status') == 'cancelled':
                        return None
                    
                    print(f"🔄 Processing CVE {index+1}/{total_cves}: {cve}")
                    
                    if progress_callback:
                        progress_callback('processing', f'Обработка CVE {index+1}/{total_cves}: {cve}', 
                                        processed_cves=index+1, total_cves=total_cves)
                    
                    # Получаем данные параллельно
                    cve_data, epss_data, exploitdb_data = await asyncio.gather(
                        self.get_cve_by_id(cve),
                        self.get_epss_by_cve(cve),
                        self.get_exploitdb_by_cve(cve),
                        return_exceptions=True
                    )
                    
                    # Обрабатываем исключения
                    if isinstance(cve_data, Exception):
                        print(f"⚠️ Error getting CVE data for {cve}: {cve_data}")
                        cve_data = None
                    if isinstance(epss_data, Exception):
                        print(f"⚠️ Error getting EPSS data for {cve}: {epss_data}")
                        epss_data = None
                    if isinstance(exploitdb_data, Exception):
                        print(f"⚠️ Error getting ExploitDB data for {cve}: {exploitdb_data}")
                        exploitdb_data = None
                    
                    # Проверяем, есть ли данные для обновления
                    has_cve_data = cve_data is not None
                    has_epss_data = epss_data is not None
                    has_exploit_data = exploitdb_data is not None
                    
                    if not has_cve_data and not has_epss_data and not has_exploit_data:
                        print(f"🔄 Skipping CVE {cve} - no data found")
                        return {'skipped': True, 'updated_hosts': 0}
                    
                    # Обновляем хосты с этим CVE
                    hosts_query = "SELECT id, cvss, criticality FROM hosts WHERE cve = $1"
                    hosts_rows = await conn.fetch(hosts_query, cve)
                    
                    if not hosts_rows:
                        print(f"🔄 No hosts found for CVE {cve}")
                        return {'skipped': True, 'updated_hosts': 0}
                    
                    updated_hosts = 0
                    for host_row in hosts_rows:
                        # Priority CVSS: CVE database > EPSS > original host CVSS
                        cvss_score = None
                        cvss_source = None

                        if cve_data and cve_data.get('cvss_v3_base_score') is not None:
                            cvss_score = cve_data['cvss_v3_base_score']
                            cvss_source = 'CVSS v3'
                        elif cve_data and cve_data.get('cvss_v2_base_score') is not None:
                            cvss_score = cve_data['cvss_v2_base_score']
                            cvss_source = 'CVSS v2'
                        elif epss_data and epss_data.get('cvss') is not None:
                            cvss_score = epss_data['cvss']
                            cvss_source = 'EPSS'
                        elif host_row['cvss'] is not None:
                            cvss_score = host_row['cvss']
                            cvss_source = 'Host'

                        # Обновляем данные хоста
                        update_query = """
                            UPDATE hosts SET
                                cvss = $1,
                                cvss_source = $2,
                                epss_score = $3,
                                epss_percentile = $4,
                                exploits_count = $5,
                                verified_exploits_count = $6,
                                has_exploits = $7,
                                epss_updated_at = $8,
                                exploits_updated_at = $9
                            WHERE id = $10
                        """
                        
                        await conn.execute(update_query,
                            cvss_score,
                            cvss_source,
                            epss_data.get('epss') if has_epss_data else None,
                            epss_data.get('percentile') if has_epss_data else None,
                            len(exploitdb_data) if has_exploit_data else 0,
                            len([e for e in exploitdb_data if e.get('verified', False)]) if has_exploit_data else 0,
                            len(exploitdb_data) > 0 if has_exploit_data else False,
                            datetime.now() if has_epss_data else None,
                            datetime.now() if has_exploit_data else None,
                            host_row['id']
                        )
                        
                        # Рассчитываем риск если есть EPSS данные
                        if has_epss_data and epss_data.get('epss'):
                            try:
                                settings = await self.get_settings()
                                risk_result = self._calculate_risk_score(
                                    epss=epss_data.get('epss'),
                                    settings=settings
                                )
                                
                                if risk_result['calculation_possible']:
                                    risk_update_query = """
                                        UPDATE hosts SET
                                            risk_score = $1,
                                            risk_raw = $2,
                                            risk_updated_at = $3
                                        WHERE id = $4
                                    """
                                    await conn.execute(risk_update_query,
                                        risk_result['risk_score'],
                                        risk_result['raw_risk'],
                                        datetime.now(),
                                        host_row['id']
                                    )
                            except Exception as risk_error:
                                print(f"⚠️ Error calculating risk for host {host_row['id']}: {risk_error}")
                        
                        updated_hosts += 1
                    
                    print(f"🔄 Updated {updated_hosts} hosts for CVE {cve}")
                    return {'skipped': False, 'updated_hosts': updated_hosts}
            
            # Запускаем параллельную обработку
            tasks = [process_single_cve(cve_row['cve'], i) for i, cve_row in enumerate(cve_rows)]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Обрабатываем результаты
            for result in results:
                if isinstance(result, Exception):
                    print(f"⚠️ Task error: {result}")
                    skipped_cves += 1
                elif result is None:
                    skipped_cves += 1
                elif result.get('skipped'):
                    skipped_cves += 1
                else:
                    processed_cves += 1
                    updated_count += result.get('updated_hosts', 0)
            
            print(f"🔄 Completed: updated {updated_count} hosts, processed {processed_cves} CVEs, skipped {skipped_cves} CVEs")
            
            if progress_callback:
                progress_callback('completed', 'Завершено', 
                                processed_cves=total_cves, total_cves=total_cves, 
                                updated_hosts=updated_count)
            
            return {
                "success": True,
                "message": f"Обновлено {updated_count} записей хостов из {processed_cves} CVE (пропущено {skipped_cves} CVE)",
                "updated_count": updated_count,
                "processed_cves": processed_cves,
                "skipped_cves": skipped_cves
            }
        except Exception as e:
            print(f"❌ Error updating hosts EPSS and exploits: {e}")
            return {
                "success": False,
                "message": f"Ошибка обновления: {str(e)}",
                "updated_count": 0,
                "processed_cves": 0
            }
        finally:
            await self.release_connection(conn)

    async def insert_hosts_records(self, records: list):
        """Вставить записи хостов"""
        conn = await self.get_connection()
        try:
            # Очищаем старые записи перед импортом
            await conn.execute("DELETE FROM hosts")
            
            query = """
                INSERT INTO hosts (hostname, ip_address, cve, cvss, criticality, status, os_name, zone)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            """
            for rec in records:
                await conn.execute(query, 
                    rec['hostname'], rec['ip_address'], rec['cve'], 
                    rec['cvss'], rec['criticality'], rec['status'],
                    rec.get('os_name', ''), rec.get('zone', ''))
            
            return len(records)
        except Exception as e:
            print(f"Error inserting hosts records: {e}")
            raise e
        finally:
            await self.release_connection(conn)

    async def insert_hosts_records_with_progress(self, records: list, progress_callback=None):
        """Вставить записи хостов с отображением прогресса и расчетом риска"""
        conn = None
        try:
            # Создаем отдельное соединение для массовой вставки
            conn = await asyncpg.connect(self.database_url)
            
            # Проверяем, что соединение активно
            await conn.execute("SELECT 1")
            
            # Очищаем старые записи перед импортом
            await conn.execute("DELETE FROM hosts")
            print("🗑️ Старые записи очищены")
            
            # Обрабатываем записи батчами для отображения прогресса
            batch_size = 1000
            total_records = len(records)
            inserted_count = 0
            
            query = """
                INSERT INTO hosts (hostname, ip_address, cve, cvss, criticality, status, os_name, zone)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            """
            
            for i in range(0, total_records, batch_size):
                batch_records = records[i:i + batch_size]
                
                # Проверяем соединение перед каждым батчем
                try:
                    await conn.execute("SELECT 1")
                except Exception as e:
                    print(f"Connection lost, reconnecting... Error: {e}")
                    await conn.close()
                    conn = await asyncpg.connect(self.database_url)
                
                async with conn.transaction():
                    for rec in batch_records:
                        try:
                            await conn.execute(query, 
                                rec['hostname'], rec['ip_address'], rec['cve'], 
                                rec['cvss'], rec['criticality'], rec['status'],
                                rec.get('os_name', ''), rec.get('zone', ''))
                            inserted_count += 1
                        except Exception as e:
                            print(f"Error inserting record for {rec.get('hostname', 'unknown')} ({rec.get('ip_address', 'no-ip')}): {e}")
                            continue
                
                # Обновляем прогресс
                progress_percent = min(100, 75 + (inserted_count / total_records) * 25)
                if progress_callback:
                    progress_callback('inserting', f'Сохранение в базу данных... ({inserted_count:,}/{total_records:,})', 
                                    progress_percent, current_step_progress=inserted_count, 
                                    processed_records=inserted_count)
                
                print(f"💾 Обработано записей: {inserted_count:,}/{total_records:,} ({progress_percent:.1f}%)")
            
            # После вставки всех записей запускаем расчет риска
            if progress_callback:
                progress_callback('calculating_risk', 'Расчет рисков для загруженных хостов...', 90)
            
            print("🔍 Начинаем расчет рисков для загруженных хостов...")
            
            # Получаем настройки для расчета Impact
            settings_query = "SELECT key, value FROM settings"
            settings_rows = await conn.fetch(settings_query)
            settings = {row['key']: row['value'] for row in settings_rows}
            
            # Получаем все уникальные CVE из загруженных хостов
            cve_query = """
                SELECT DISTINCT cve FROM hosts 
                WHERE cve IS NOT NULL AND cve != '' 
                ORDER BY cve
            """
            cve_rows = await conn.fetch(cve_query)
            
            if cve_rows:
                print(f"📊 Найдено {len(cve_rows)} уникальных CVE для расчета риска")
                
                for i, cve_row in enumerate(cve_rows):
                    cve = cve_row['cve']
                    
                    # Получаем данные EPSS для CVE
                    epss_data = await self.get_epss_by_cve(cve)
                    
                    # Получаем данные CVE для CVSS оценок
                    cve_data = await self.get_cve_by_id(cve)
                    
                    # Получаем данные эксплойтов для CVE
                    exploitdb_data = await self.get_exploitdb_by_cve(cve)
                    
                    # Обновляем все хосты с этим CVE
                    hosts_query = "SELECT id, cvss, criticality FROM hosts WHERE cve = $1"
                    hosts_rows = await conn.fetch(hosts_query, cve)
                    
                    for host_row in hosts_rows:
                        # Рассчитываем риск для каждого хоста
                        risk_data = None
                        
                        # Приоритет CVSS: CVE база > EPSS > исходный CVSS хоста
                        cvss_score = None
                        cvss_source = None
                        
                        if cve_data and cve_data.get('cvss_v3_base_score') is not None:
                            cvss_score = cve_data['cvss_v3_base_score']
                            cvss_source = 'CVSS v3'
                        elif cve_data and cve_data.get('cvss_v2_base_score') is not None:
                            cvss_score = cve_data['cvss_v2_base_score']
                            cvss_source = 'CVSS v2'
                        elif epss_data and epss_data.get('cvss') is not None:
                            cvss_score = epss_data['cvss']
                            cvss_source = 'EPSS'
                        elif host_row['cvss'] is not None:
                            cvss_score = host_row['cvss']
                            cvss_source = 'Host'
                        
                        if cvss_score is not None and epss_data and epss_data.get('epss') is not None:
                            # Переопределяем критичность ресурса на основе хоста
                            settings['impact_resource_criticality'] = host_row['criticality']
                            risk_data = self._calculate_risk_score(epss_data['epss'], cvss_score, settings)
                        
                        # Обновляем запись хоста
                        update_query = """
                            UPDATE hosts SET
                                cvss = $1,
                                cvss_source = $2,
                                epss_score = $3,
                                epss_percentile = $4,
                                risk_score = $5,
                                risk_raw = $6,
                                impact_score = $7,
                                exploits_count = $8,
                                verified_exploits_count = $9,
                                has_exploits = $10,
                                last_exploit_date = $11,
                                epss_updated_at = $12,
                                exploits_updated_at = $13,
                                risk_updated_at = $14
                            WHERE id = $15
                        """
                        
                        # Обрабатываем дату последнего эксплойта
                        last_exploit_date = None
                        if exploitdb_data:
                            exploit_dates = [e.get('date_published') for e in exploitdb_data if e.get('date_published')]
                            if exploit_dates:
                                # Берем самую позднюю дату
                                latest_date = max(exploit_dates)
                                if isinstance(latest_date, str):
                                    try:
                                        # Парсим строку даты
                                        last_exploit_date = datetime.strptime(latest_date, '%Y-%m-%d').date()
                                    except:
                                        last_exploit_date = None
                                else:
                                    last_exploit_date = latest_date
                        
                        await conn.execute(update_query,
                            cvss_score,
                            cvss_source,
                            epss_data.get('epss') if epss_data else None,
                            epss_data.get('percentile') if epss_data else None,
                            risk_data.get('risk_score') if risk_data else None,
                            risk_data.get('raw_risk') if risk_data else None,
                            risk_data.get('impact') if risk_data else None,
                            len(exploitdb_data) if exploitdb_data else 0,
                            len([e for e in exploitdb_data if e.get('verified', False)]) if exploitdb_data else 0,
                            len(exploitdb_data) > 0 if exploitdb_data else False,
                            last_exploit_date,
                            datetime.now() if epss_data else None,
                            datetime.now() if exploitdb_data else None,
                            datetime.now() if risk_data else None,
                            host_row['id']
                        )
                    
                    # Обновляем прогресс расчета риска
                    if progress_callback and (i + 1) % 10 == 0:
                        risk_progress = 90 + ((i + 1) / len(cve_rows)) * 10
                        progress_callback('calculating_risk', f'Расчет рисков... ({i+1}/{len(cve_rows)} CVE)', risk_progress)
            
            if progress_callback:
                progress_callback('completed', 'Импорт и расчет рисков завершены', 100)
            
            print("✅ Расчет рисков завершен")
            
            return inserted_count
            
        except Exception as e:
            print(f"Error in insert_hosts_records_with_progress: {e}")
            raise e
        finally:
            if conn:
                try:
                    await conn.close()
                except Exception as e:
                    print(f"Error closing connection: {e}")

    async def count_hosts_records(self):
        """Подсчитать количество записей хостов"""
        conn = await self.get_connection()
        try:
            row = await conn.fetchrow("SELECT COUNT(*) as cnt FROM hosts")
            return row['cnt'] if row else 0
        except Exception as e:
            print(f"Error counting hosts records: {e}")
            return 0
        finally:
            await self.release_connection(conn)

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
                conditions.append(f"ip_address ILIKE ${param_count}")
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
            count_query = f"SELECT COUNT(*) FROM hosts WHERE {where_clause}"
            total_count = await conn.fetchval(count_query, *params)
            
            # Затем получаем данные с пагинацией
            offset = (page - 1) * limit
            query = f"""
                SELECT id, hostname, ip_address, cve, cvss, cvss_source, criticality, status,
                       os_name, zone, epss_score, epss_percentile, risk_score, risk_raw, impact_score,
                       exploits_count, verified_exploits_count, has_exploits, last_exploit_date,
                       epss_updated_at, exploits_updated_at, risk_updated_at, imported_at
                FROM hosts 
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
                    'imported_at': row['imported_at'].isoformat() if row['imported_at'] else None
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
                SELECT id, hostname, ip_address, cve, cvss, criticality, status,
                       os_name, zone, epss_score, epss_percentile, risk_score, risk_raw, impact_score,
                       exploits_count, verified_exploits_count, has_exploits, last_exploit_date,
                       epss_updated_at, exploits_updated_at, risk_updated_at, imported_at
                FROM hosts 
                WHERE id = $1
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
                    'imported_at': row['imported_at'].isoformat() if row['imported_at'] else None
                }
            return None
        except Exception as e:
            print(f"Error getting host by ID {host_id}: {e}")
            return None
        finally:
            await self.release_connection(conn)

    async def clear_hosts(self):
        """Очистка таблицы хостов"""
        conn = await self.get_connection()
        try:
            query = "DELETE FROM hosts"
            await conn.execute(query)
            print("Hosts table cleared successfully")
        except Exception as e:
            print(f"Error clearing hosts table: {e}")
            raise e
        finally:
            await self.release_connection(conn)

    async def clear_epss(self):
        """Очистка таблицы EPSS"""
        conn = await self.get_connection()
        try:
            query = "DELETE FROM epss"
            await conn.execute(query)
            print("EPSS table cleared successfully")
        except Exception as e:
            print(f"Error clearing EPSS table: {e}")
            raise e
        finally:
            await self.release_connection(conn)

    async def clear_exploitdb(self):
        """Очистка таблицы ExploitDB"""
        conn = await self.get_connection()
        try:
            query = "DELETE FROM exploitdb"
            await conn.execute(query)
            print("ExploitDB table cleared successfully")
        except Exception as e:
            print(f"Error clearing ExploitDB table: {e}")
            raise e
        finally:
            await self.release_connection(conn)

    # ===== VM MAXPATROL ИНТЕГРАЦИЯ =====
    
    async def get_vm_settings(self) -> Dict[str, str]:
        """Получить настройки VM MaxPatrol"""
        conn = await self.get_connection()
        try:
            query = "SELECT key, value FROM settings WHERE key LIKE 'vm_%'"
            rows = await conn.fetch(query)
            
            settings = {}
            for row in rows:
                settings[row['key']] = row['value']
            
            # Устанавливаем значения по умолчанию
            defaults = {
                'vm_host': '',
                'vm_username': '',
                'vm_password': '',
                'vm_client_secret': '',
                'vm_enabled': 'false',
                'vm_os_filter': 'Windows 7,Windows 10,ESXi,IOS,NX-OS,IOS XE,FreeBSD',
                'vm_limit': '0'
            }
            
            for key, default_value in defaults.items():
                if key not in settings:
                    settings[key] = default_value
            
            return settings
        finally:
            await self.release_connection(conn)

    async def update_vm_settings(self, settings: Dict[str, str]):
        """Обновить настройки VM MaxPatrol"""
        conn = await self.get_connection()
        try:
            for key, value in settings.items():
                if key.startswith('vm_'):
                    query = """
                        INSERT INTO settings (key, value) 
                        VALUES ($1, $2) 
                        ON CONFLICT (key) 
                        DO UPDATE SET value = $2, updated_at = CURRENT_TIMESTAMP
                    """
                    await conn.execute(query, key, value)
        finally:
            await self.release_connection(conn)

    async def import_vm_hosts(self, hosts_data: list):
        """Импортировать хосты из VM MaxPatrol"""
        conn = await self.get_connection()
        try:
            # Получаем количество записей до импорта
            count_before = await conn.fetchval("SELECT COUNT(*) FROM hosts")
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
                        "SELECT id FROM hosts WHERE hostname = $1 AND cve = $2", 
                        hostname, cve
                    )
                    
                    if existing:
                        # Обновляем существующую запись
                        query = """
                            UPDATE hosts 
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
                            INSERT INTO hosts (hostname, ip_address, cve, cvss, criticality, status, os_name, zone)
                            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                        """
                        await conn.execute(query, 
                            hostname, ip_address, cve, None, criticality, 'Active', 
                            host_data.get('os_name', ''), host_data.get('zone', ''))
                        inserted_count += 1
                
                # Получаем количество записей после импорта
                count_after = await conn.fetchval("SELECT COUNT(*) FROM hosts")
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

    async def get_vm_import_status(self) -> Dict[str, Any]:
        """Получить статус последнего импорта VM"""
        conn = await self.get_connection()
        try:
            # Получаем последнюю запись о импорте
            query = """
                SELECT key, value, updated_at 
                FROM settings 
                WHERE key IN ('vm_last_import', 'vm_last_import_count', 'vm_last_import_error')
                ORDER BY updated_at DESC
                LIMIT 1
            """
            rows = await conn.fetch(query)
            
            status = {
                'last_import': None,
                'last_import_count': 0,
                'last_import_error': None,
                'vm_enabled': False
            }
            
            for row in rows:
                if row['key'] == 'vm_last_import':
                    status['last_import'] = row['updated_at']
                elif row['key'] == 'vm_last_import_count':
                    status['last_import_count'] = int(row['value']) if row['value'].isdigit() else 0
                elif row['key'] == 'vm_last_import_error':
                    status['last_import_error'] = row['value']
            
            # Проверяем, включен ли VM импорт
            vm_enabled = await conn.fetchval("SELECT value FROM settings WHERE key = 'vm_enabled'")
            status['vm_enabled'] = vm_enabled == 'true' if vm_enabled else False
            
            return status
        finally:
            await self.release_connection(conn)

    async def update_vm_import_status(self, count: int, error: str = None):
        """Обновить статус импорта VM"""
        conn = await self.get_connection()
        try:
            # Обновляем количество импортированных записей
            await conn.execute(
                "INSERT INTO settings (key, value) VALUES ('vm_last_import_count', $1) ON CONFLICT (key) DO UPDATE SET value = $1, updated_at = CURRENT_TIMESTAMP",
                str(count)
            )
            
            # Обновляем время последнего импорта
            await conn.execute(
                "INSERT INTO settings (key, value) VALUES ('vm_last_import', CURRENT_TIMESTAMP::text) ON CONFLICT (key) DO UPDATE SET value = CURRENT_TIMESTAMP::text, updated_at = CURRENT_TIMESTAMP"
            )
            
            # Обновляем ошибку, если есть
            if error:
                await conn.execute(
                    "INSERT INTO settings (key, value) VALUES ('vm_last_import_error', $1) ON CONFLICT (key) DO UPDATE SET value = $1, updated_at = CURRENT_TIMESTAMP",
                    error
                )
            else:
                # Очищаем ошибку, если импорт успешен
                await conn.execute("DELETE FROM settings WHERE key = 'vm_last_import_error'")
                
        finally:
            await self.release_connection(conn)

    # ===== УПРАВЛЕНИЕ ПОЛЬЗОВАТЕЛЯМИ =====

    async def create_user(self, username: str, password: str, email: str = None, is_admin: bool = False) -> int:
        """Создать нового пользователя"""
        conn = await self.get_connection()
        try:
            # Проверяем, существует ли пользователь
            existing_user = await conn.fetchval(
                "SELECT id FROM users WHERE username = $1", username
            )
            if existing_user:
                raise Exception("User already exists")

            # Создаем пользователя
            user_id = await conn.fetchval(
                """
                INSERT INTO users (username, password, email, is_admin, is_active, created_at)
                VALUES ($1, $2, $3, $4, $5, CURRENT_TIMESTAMP)
                RETURNING id
                """,
                username, password, email, is_admin, True
            )
            return user_id
        finally:
            await self.release_connection(conn)

    async def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """Получить пользователя по имени"""
        conn = await self.get_connection()
        try:
            user = await conn.fetchrow(
                "SELECT id, username, password, email, is_admin, is_active, created_at FROM users WHERE username = $1",
                username
            )
            if user:
                return dict(user)
            return None
        finally:
            await self.release_connection(conn)

    async def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Получить пользователя по ID"""
        conn = await self.get_connection()
        try:
            user = await conn.fetchrow(
                "SELECT id, username, password, email, is_admin, is_active, created_at FROM users WHERE id = $1",
                user_id
            )
            if user:
                return dict(user)
            return None
        finally:
            await self.release_connection(conn)

    async def get_all_users(self) -> List[Dict[str, Any]]:
        """Получить всех пользователей"""
        conn = await self.get_connection()
        try:
            users = await conn.fetch(
                "SELECT id, username, email, is_admin, is_active, created_at FROM users ORDER BY created_at DESC"
            )
            return [dict(user) for user in users]
        finally:
            await self.release_connection(conn)

    async def update_user(self, user_id: int, username: str, email: str = None, is_active: bool = True, is_admin: bool = False) -> bool:
        """Обновить пользователя"""
        conn = await self.get_connection()
        try:
            # Проверяем, существует ли пользователь с таким именем (кроме текущего)
            existing_user = await conn.fetchval(
                "SELECT id FROM users WHERE username = $1 AND id != $2", username, user_id
            )
            if existing_user:
                raise Exception("Username already exists")

            await conn.execute(
                """
                UPDATE users 
                SET username = $1, email = $2, is_active = $3, is_admin = $4, updated_at = CURRENT_TIMESTAMP
                WHERE id = $5
                """,
                username, email, is_active, is_admin, user_id
            )
            return True
        finally:
            await self.release_connection(conn)

    async def update_user_password(self, user_id: int, password: str) -> bool:
        """Обновить пароль пользователя"""
        conn = await self.get_connection()
        try:
            await conn.execute(
                "UPDATE users SET password = $1, updated_at = CURRENT_TIMESTAMP WHERE id = $2",
                password, user_id
            )
            return True
        finally:
            await self.release_connection(conn)

    async def delete_user(self, user_id: int) -> bool:
        """Удалить пользователя"""
        conn = await self.get_connection()
        try:
            # Не удаляем пользователя с ID 1 (админ)
            if user_id == 1:
                raise Exception("Cannot delete admin user")
            
            await conn.execute("DELETE FROM users WHERE id = $1", user_id)
            return True
        finally:
            await self.release_connection(conn)

    async def initialize_admin_user(self):
        """Инициализировать админа при первом запуске"""
        conn = await self.get_connection()
        try:
            # Проверяем, есть ли уже пользователи
            user_count = await conn.fetchval("SELECT COUNT(*) FROM users")
            if user_count == 0:
                # Создаем админа
                await conn.execute(
                    """
                    INSERT INTO users (username, password, email, is_admin, is_active, created_at)
                    VALUES ($1, $2, $3, $4, $5, CURRENT_TIMESTAMP)
                    """,
                    "admin", "admin", "admin@stools.local", True, True
                )
                print("Admin user created: admin/admin")
        finally:
            await self.release_connection(conn)

    # Методы для работы с CVE
    async def insert_cve_records(self, records: list):
        """Вставить записи CVE с улучшенным управлением соединениями"""
        conn = None
        try:
            # Создаем отдельное соединение для массовой вставки
            conn = await asyncpg.connect(self.database_url)
            
            # Проверяем, что соединение активно
            await conn.execute("SELECT 1")
            
            # Получаем количество записей до вставки
            count_before = await conn.fetchval("SELECT COUNT(*) FROM cve")
            print(f"CVE records in database before insert: {count_before}")
            
            inserted_count = 0
            updated_count = 0
            
            # Обрабатываем записи батчами для избежания проблем с соединением
            batch_size = 1000
            print(f"Начинаем обработку {len(records)} записей CVE батчами по {batch_size} записей")
            
            for i in range(0, len(records), batch_size):
                batch_records = records[i:i + batch_size]
                
                # Проверяем соединение перед каждым батчем
                try:
                    await conn.execute("SELECT 1")
                except Exception as e:
                    print(f"Connection lost, reconnecting... Error: {e}")
                    await conn.close()
                    conn = await asyncpg.connect(self.database_url)
                
                async with conn.transaction():
                    query = """
                        INSERT INTO cve (cve_id, description, cvss_v3_base_score, cvss_v3_base_severity, 
                                        cvss_v2_base_score, cvss_v2_base_severity, exploitability_score, 
                                        impact_score, published_date, last_modified_date)
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                        ON CONFLICT (cve_id) DO UPDATE SET 
                            description = $2, cvss_v3_base_score = $3, cvss_v3_base_severity = $4,
                            cvss_v2_base_score = $5, cvss_v2_base_severity = $6, exploitability_score = $7,
                            impact_score = $8, published_date = $9, last_modified_date = $10,
                            updated_at = CURRENT_TIMESTAMP
                    """
                    
                    for rec in batch_records:
                        try:
                            # Проверяем, существует ли запись
                            existing = await conn.fetchval("SELECT cve_id FROM cve WHERE cve_id = $1", rec['cve_id'])
                            
                            await conn.execute(query, 
                                rec['cve_id'], rec.get('description'), rec.get('cvss_v3_base_score'),
                                rec.get('cvss_v3_base_severity'), rec.get('cvss_v2_base_score'),
                                rec.get('cvss_v2_base_severity'), rec.get('exploitability_score'),
                                rec.get('impact_score'), rec.get('published_date'), rec.get('last_modified_date'))
                            
                            if existing:
                                updated_count += 1
                            else:
                                inserted_count += 1
                                
                        except Exception as e:
                            print(f"Error inserting CVE record {rec['cve_id']}: {e}")
                            continue
                
                # Показываем прогресс
                print(f"Обработка CVE: {i + len(batch_records)}/{len(records)} записей")
            
            # Получаем количество записей после вставки
            count_after = await conn.fetchval("SELECT COUNT(*) FROM cve")
            print(f"CVE records in database after insert: {count_after}")
            print(f"New CVE records inserted: {inserted_count}")
            print(f"Existing CVE records updated: {updated_count}")
            print(f"Total CVE records processed: {len(records)}")
            print(f"Net change in CVE database: {count_after - count_before}")
            
        except Exception as e:
            print(f"Error in insert_cve_records: {e}")
            raise e
        finally:
            if conn:
                try:
                    await conn.close()
                except Exception as e:
                    print(f"Error closing connection: {e}")

    async def count_cve_records(self):
        """Подсчитать количество записей CVE"""
        conn = await self.get_connection()
        try:
            # Проверяем, что таблица существует
            table_exists = await conn.fetchval(
                "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'cve')"
            )
            if not table_exists:
                print("Table cve does not exist")
                return 0
            
            row = await conn.fetchrow("SELECT COUNT(*) as cnt FROM cve")
            return row['cnt'] if row else 0
        except Exception as e:
            print(f"Error counting cve records: {e}")
            raise
        finally:
            await self.release_connection(conn)

    async def get_cve_by_id(self, cve_id: str):
        """Получить данные CVE по ID"""
        conn = await self.get_connection()
        try:
            query = """
                SELECT cve_id, description, cvss_v3_base_score, cvss_v3_base_severity,
                       cvss_v2_base_score, cvss_v2_base_severity, exploitability_score,
                       impact_score, published_date, last_modified_date
                FROM cve 
                WHERE cve_id = $1
            """
            row = await conn.fetchrow(query, cve_id)
            
            if row:
                return {
                    'cve_id': row['cve_id'],
                    'description': row['description'],
                    'cvss_v3_base_score': float(row['cvss_v3_base_score']) if row['cvss_v3_base_score'] else None,
                    'cvss_v3_base_severity': row['cvss_v3_base_severity'],
                    'cvss_v2_base_score': float(row['cvss_v2_base_score']) if row['cvss_v2_base_score'] else None,
                    'cvss_v2_base_severity': row['cvss_v2_base_severity'],
                    'exploitability_score': float(row['exploitability_score']) if row['exploitability_score'] else None,
                    'impact_score': float(row['impact_score']) if row['impact_score'] else None,
                    'published_date': row['published_date'].isoformat() if row['published_date'] else None,
                    'last_modified_date': row['last_modified_date'].isoformat() if row['last_modified_date'] else None
                }
            return None
        except Exception as e:
            print(f"Error getting CVE data for {cve_id}: {e}")
            return None
        finally:
            await self.release_connection(conn)

    async def clear_cve(self):
        """Очистить все CVE данные"""
        conn = await self.get_connection()
        try:
            await conn.execute("DELETE FROM cve")
            print("All CVE data cleared")
        except Exception as e:
            print(f"Error clearing CVE data: {e}")
            raise
        finally:
            await self.release_connection(conn)

    # Методы для работы с фоновыми задачами
    async def create_background_task(self, task_type: str) -> int:
        """Создать новую фоновую задачу"""
        conn = await self.get_connection()
        try:
            query = """
                INSERT INTO background_tasks (task_type, status, current_step, start_time)
                VALUES ($1, 'processing', 'Инициализация...', CURRENT_TIMESTAMP)
                RETURNING id
            """
            task_id = await conn.fetchval(query, task_type)
            return task_id
        finally:
            await self.release_connection(conn)

    async def update_background_task(self, task_id: int, **kwargs):
        """Обновить статус фоновой задачи"""
        conn = await self.get_connection()
        try:
            # Формируем SET часть запроса динамически
            set_parts = []
            params = []
            param_count = 1
            
            for key, value in kwargs.items():
                if key in ['status', 'current_step', 'total_items', 'processed_items', 
                          'total_records', 'updated_records', 'error_message', 'cancelled']:
                    set_parts.append(f"{key} = ${param_count}")
                    params.append(value)
                    param_count += 1
            
            if set_parts:
                set_parts.append("updated_at = CURRENT_TIMESTAMP")
                if 'status' in kwargs and kwargs['status'] in ['completed', 'error', 'cancelled']:
                    set_parts.append("end_time = CURRENT_TIMESTAMP")
                
                query = f"""
                    UPDATE background_tasks 
                    SET {', '.join(set_parts)}
                    WHERE id = ${param_count}
                """
                params.append(task_id)
                await conn.execute(query, *params)
        finally:
            await self.release_connection(conn)

    async def get_background_task(self, task_type: str) -> Optional[Dict[str, Any]]:
        """Получить последнюю фоновую задачу определенного типа"""
        conn = await self.get_connection()
        try:
            query = """
                SELECT id, task_type, status, current_step, total_items, processed_items,
                       total_records, updated_records, start_time, end_time, error_message, cancelled
                FROM background_tasks 
                WHERE task_type = $1 
                ORDER BY created_at DESC 
                LIMIT 1
            """
            row = await conn.fetchrow(query, task_type)
            if row:
                return dict(row)
            return None
        finally:
            await self.release_connection(conn)

    async def cancel_background_task(self, task_type: str) -> bool:
        """Отменить фоновую задачу"""
        conn = await self.get_connection()
        try:
            query = """
                UPDATE background_tasks 
                SET status = 'cancelled', current_step = 'Отменено пользователем', 
                    cancelled = TRUE, end_time = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
                WHERE task_type = $1 AND status IN ('running', 'processing')
            """
            result = await conn.execute(query, task_type)
            return result != 'UPDATE 0'
        finally:
            await self.release_connection(conn)

    async def update_hosts_incremental(self, progress_callback=None, days_old=1):
        """Инкрементальное обновление хостов, которые не обновлялись N дней"""
        print(f"🔄 Starting incremental update for hosts older than {days_old} days")
        conn = await self.get_connection()
        try:
            # Получаем CVE из хостов, которые не обновлялись давно
            cve_query = """
                SELECT DISTINCT h.cve FROM hosts h
                WHERE h.cve IS NOT NULL AND h.cve != '' 
                AND (h.epss_updated_at IS NULL OR h.epss_updated_at < NOW() - INTERVAL $1)
                ORDER BY h.cve
            """
            cve_rows = await conn.fetch(cve_query, f'{days_old} days')
            
            if not cve_rows:
                return {"success": True, "message": f"Нет хостов для обновления (старше {days_old} дней)", "updated_count": 0}
            
            total_cves = len(cve_rows)
            print(f"🔄 Found {total_cves} CVE for incremental update")
            
            if progress_callback:
                progress_callback('initializing', f'Найдено {total_cves} CVE для инкрементального обновления', 
                                total_cves=total_cves, processed_cves=0)
            
            # Используем параллельную обработку для инкрементального обновления
            return await self.update_hosts_epss_and_exploits_background_parallel(
                progress_callback=progress_callback, 
                max_concurrent=5,  # Меньше параллелизма для инкрементального обновления
                cve_list=[row['cve'] for row in cve_rows]
            )
            
        except Exception as e:
            print(f"❌ Error in incremental update: {e}")
            return {
                "success": False,
                "message": f"Ошибка инкрементального обновления: {str(e)}",
                "updated_count": 0
            }
        finally:
            await self.release_connection(conn)

# Глобальный экземпляр базы данных
_db_instance = None

def get_db():
    """Получить экземпляр базы данных"""
    global _db_instance
    if _db_instance is None:
        _db_instance = Database()
    return _db_instance