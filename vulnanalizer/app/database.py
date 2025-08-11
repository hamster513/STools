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

    def _calculate_risk_score(self, epss: float, cvss: float, settings: dict) -> dict:
        """Рассчитать риск по формуле: raw_risk = EPSS * (CVSS / 10) * Impact"""
        if epss is None or cvss is None:
            return {
                'raw_risk': None,
                'risk_score': None,
                'calculation_possible': False,
                'impact': None
            }
        
        # Конвертируем decimal в float если нужно
        if hasattr(epss, 'as_tuple'):  # Это decimal.Decimal
            epss = float(epss)
        if hasattr(cvss, 'as_tuple'):  # Это decimal.Decimal
            cvss = float(cvss)
        
        # Рассчитываем Impact на основе настроек
        impact = self._calculate_impact(settings)
        
        raw_risk = epss * (cvss / 10) * impact
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

    async def update_hosts_epss_and_exploits(self):
        """Обновить данные EPSS и эксплойтов для всех хостов"""
        conn = await self.get_connection()
        try:
            # Получаем все уникальные CVE из хостов
            cve_query = "SELECT DISTINCT cve FROM hosts WHERE cve IS NOT NULL"
            cve_rows = await conn.fetch(cve_query)
            
            updated_count = 0
            for cve_row in cve_rows:
                cve = cve_row['cve']
                
                # Получаем данные EPSS для CVE
                epss_data = await self.get_epss_by_cve(cve)
                
                # Получаем данные эксплойтов для CVE
                exploitdb_data = await self.get_exploitdb_by_cve(cve)
                
                # Получаем настройки для расчета Impact
                settings_query = "SELECT key, value FROM settings"
                settings_rows = await conn.fetch(settings_query)
                settings = {row['key']: row['value'] for row in settings_rows}
                
                # Обновляем все хосты с этим CVE
                hosts_query = "SELECT id, cvss, criticality FROM hosts WHERE cve = $1"
                hosts_rows = await conn.fetch(hosts_query, cve)
                
                for host_row in hosts_rows:
                    # Рассчитываем риск для каждого хоста
                    risk_data = None
                    if epss_data and epss_data.get('epss') is not None:
                        cvss_score = epss_data.get('cvss') if epss_data.get('cvss') is not None else host_row['cvss']
                        if cvss_score is not None:
                            # Переопределяем критичность ресурса на основе хоста
                            settings['impact_resource_criticality'] = host_row['criticality']
                            risk_data = self._calculate_risk_score(epss_data['epss'], cvss_score, settings)
                    
                    # Обновляем запись хоста
                    update_query = """
                        UPDATE hosts SET
                            epss_score = $1,
                            epss_percentile = $2,
                            risk_score = $3,
                            risk_raw = $4,
                            impact_score = $5,
                            exploits_count = $6,
                            verified_exploits_count = $7,
                            has_exploits = $8,
                            last_exploit_date = $9,
                            epss_updated_at = $10,
                            exploits_updated_at = $11,
                            risk_updated_at = $12
                        WHERE id = $13
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
                    updated_count += 1
            
            return updated_count
        except Exception as e:
            print(f"Error updating hosts EPSS and exploits: {e}")
            raise e
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
        """Вставить записи хостов с отображением прогресса"""
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

    async def search_hosts(self, hostname_pattern: str = None, cve: str = None, ip_address: str = None, criticality: str = None, exploits_only: bool = False, limit: int = 100, page: int = 1):
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
                conditions.append(f"cve = ${param_count}")
                params.append(cve.upper())
            
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
            
            where_clause = " AND ".join(conditions) if conditions else "1=1"
            
            # Сначала получаем общее количество записей
            count_query = f"SELECT COUNT(*) FROM hosts WHERE {where_clause}"
            total_count = await conn.fetchval(count_query, *params)
            
            # Затем получаем данные с пагинацией
            offset = (page - 1) * limit
            query = f"""
                SELECT id, hostname, ip_address, cve, cvss, criticality, status,
                       os_name, zone, epss_score, epss_percentile, risk_score, risk_raw, impact_score,
                       exploits_count, verified_exploits_count, has_exploits, last_exploit_date,
                       epss_updated_at, exploits_updated_at, risk_updated_at, imported_at
                FROM hosts 
                WHERE {where_clause}
                ORDER BY hostname, cve
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

# Глобальный экземпляр базы данных
_db_instance = None

def get_db():
    """Получить экземпляр базы данных"""
    global _db_instance
    if _db_instance is None:
        _db_instance = Database()
    return _db_instance