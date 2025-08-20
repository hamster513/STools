"""
Repository for hosts operations
"""
import asyncpg
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
from .base import DatabaseBase


class HostsRepository(DatabaseBase):
    """Repository for hosts operations"""
    
    async def get_hosts_count(self) -> int:
        """Получить количество хостов"""
        conn = await self.get_connection()
        try:
            count = await conn.fetchval("SELECT COUNT(*) FROM hosts")
            return count
        finally:
            await self.release_connection(conn)
    
    async def get_hosts(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """Получить список хостов"""
        conn = await self.get_connection()
        try:
            query = """
                SELECT id, hostname, ip_address, cve, cvss, criticality, status, 
                       os_name, zone, epss_score, risk_score, created_at, updated_at
                FROM hosts 
                ORDER BY created_at DESC 
                LIMIT $1 OFFSET $2
            """
            rows = await conn.fetch(query, limit, offset)
            return [dict(row) for row in rows]
        finally:
            await self.release_connection(conn)
    
    async def get_hosts_by_cve(self, cve: str) -> List[Dict[str, Any]]:
        """Получить хосты по CVE"""
        conn = await self.get_connection()
        try:
            query = """
                SELECT id, hostname, ip_address, cve, cvss, criticality, status, 
                       os_name, zone, epss_score, risk_score, created_at, updated_at
                FROM hosts 
                WHERE cve = $1
                ORDER BY hostname
            """
            rows = await conn.fetch(query, cve)
            return [dict(row) for row in rows]
        finally:
            await self.release_connection(conn)
    
    async def delete_all_hosts(self) -> int:
        """Удалить все хосты"""
        conn = await self.get_connection()
        try:
            count = await conn.fetchval("SELECT COUNT(*) FROM hosts")
            await conn.execute("DELETE FROM hosts")
            return count
        finally:
            await self.release_connection(conn)
    
    async def insert_hosts_records_with_progress(self, records: list, progress_callback=None):
        """Вставить записи хостов с детальным отображением прогресса и расчетом риска"""
        conn = None
        try:
            conn = await asyncpg.connect(self.database_url)
            await conn.execute('SET search_path TO vulnanalizer')
            await conn.execute("SELECT 1")
            
            # Подсчитываем только записи с CVE
            valid_records = [rec for rec in records if rec.get('cve', '').strip()]
            total_records = len(valid_records)
            skipped_records = len(records) - total_records
            
            print(f"🚀 Начинаем импорт {total_records:,} записей с CVE (пропущено {skipped_records:,} записей без CVE)")
            
            # Этап 1: Очистка старых записей (5%)
            if progress_callback:
                await progress_callback('cleaning', 'Очистка старых записей...', 5)
            
            await conn.execute("DELETE FROM hosts")
            print("🗑️ Старые записи очищены")
            
            # Этап 2: Вставка записей (70%)
            batch_size = 100
            inserted_count = 0
            
            query = """
                INSERT INTO hosts (hostname, ip_address, cve, cvss, criticality, status, os_name, zone)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            """
            
            for i in range(0, total_records, batch_size):
                batch_records = valid_records[i:i + batch_size]
                try:
                    await conn.execute("SELECT 1")
                except Exception as e:
                    print(f"Connection lost, reconnecting... Error: {e}")
                    await conn.close()
                    conn = await asyncpg.connect(self.database_url)
                    await conn.execute('SET search_path TO vulnanalizer')
                
                async with conn.transaction():
                    for rec in batch_records:
                        try:
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
                            print(f"Error inserting record for {rec.get('hostname', 'unknown')} ({rec.get('ip_address', 'no-ip')}): {e}")
                            continue
                
                progress_percent = 5 + (inserted_count / total_records) * 70
                if progress_callback:
                    await progress_callback('inserting', 
                        f'Сохранение в базу данных... ({inserted_count:,}/{total_records:,})', 
                        progress_percent, 
                        current_step_progress=inserted_count, 
                        processed_records=inserted_count)
                
                print(f"💾 Обработано записей: {inserted_count:,}/{total_records:,} ({progress_percent:.1f}%)")
            
            # Этап 3: Расчет рисков (25%)
            if progress_callback:
                await progress_callback('calculating_risk', 'Расчет рисков для загруженных хостов...', 75)
            
            print("🔍 Начинаем расчет рисков для загруженных хостов...")
            
            try:
                settings_query = "SELECT key, value FROM settings"
                settings_rows = await conn.fetch(settings_query)
                settings = {row['key']: row['value'] for row in settings_rows}
                print(f"📋 Загружено настроек: {len(settings)}")
            except Exception as e:
                print(f"⚠️ Ошибка загрузки настроек: {e}")
                settings = {}
            
            cve_query = """
                SELECT DISTINCT cve FROM hosts 
                WHERE cve IS NOT NULL AND cve != '' 
                ORDER BY cve
            """
            cve_rows = await conn.fetch(cve_query)
            
            if cve_rows:
                print(f"📊 Найдено {len(cve_rows)} уникальных CVE для расчета риска")
                
                print(f"🔄 Начинаем расчет рисков для {len(cve_rows)} CVE...")
                
                from .risk_calculation_service import RiskCalculationService
                risk_service = RiskCalculationService()
                await risk_service.process_cve_risk_calculation_optimized(cve_rows, conn, settings, progress_callback)
            
            # Завершение
            if progress_callback:
                await progress_callback('completed', 'Импорт и расчет рисков завершены', 100, 
                                      current_step_progress=inserted_count, 
                                      processed_records=inserted_count)
            
            print("✅ Расчет рисков завершен")
            print(f"🎯 Метод insert_hosts_records_with_progress завершен успешно")
            
            return inserted_count
            
        except Exception as e:
            print(f"❌ Ошибка в insert_hosts_records_with_progress: {e}")
            if progress_callback:
                await progress_callback('error', f'Ошибка импорта: {str(e)}', 0)
            raise
        finally:
            if conn:
                await conn.close()
    
    async def get_hosts_stats(self) -> Dict[str, Any]:
        """Получить статистику хостов"""
        conn = await self.get_connection()
        try:
            stats = {}
            
            # Общее количество
            stats['total'] = await conn.fetchval("SELECT COUNT(*) FROM hosts")
            
            # По статусам
            status_query = "SELECT status, COUNT(*) as count FROM hosts GROUP BY status"
            status_rows = await conn.fetch(status_query)
            stats['by_status'] = {row['status']: row['count'] for row in status_rows}
            
            # По критичности
            criticality_query = "SELECT criticality, COUNT(*) as count FROM hosts GROUP BY criticality"
            criticality_rows = await conn.fetch(criticality_query)
            stats['by_criticality'] = {row['criticality']: row['count'] for row in criticality_rows}
            
            # По зонам
            zone_query = "SELECT zone, COUNT(*) as count FROM hosts WHERE zone IS NOT NULL AND zone != '' GROUP BY zone"
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
            count_query = f"SELECT COUNT(*) FROM hosts WHERE {where_clause}"
            total_count = await conn.fetchval(count_query, *params)
            
            # Затем получаем данные с пагинацией
            offset = (page - 1) * limit
            query = f"""
                SELECT id, hostname, ip_address, cve, cvss, cvss_source, criticality, status,
                       os_name, zone, epss_score, epss_percentile, risk_score, risk_raw, impact_score,
                       exploits_count, verified_exploits_count, has_exploits, last_exploit_date,
                       epss_updated_at, exploits_updated_at, risk_updated_at, created_at
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
                    'imported_at': row['created_at'].isoformat() if row['created_at'] else None
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
                       epss_updated_at, exploits_updated_at, risk_updated_at, created_at
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
                    'imported_at': row['created_at'].isoformat() if row['created_at'] else None
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

    async def get_vm_import_status(self):
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
