"""
Репозиторий для работы с EPSS данными
"""
import asyncpg
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime
from .base import DatabaseBase


class EPSSRepository(DatabaseBase):
    """Репозиторий для работы с EPSS данными"""

    async def insert_records(self, records: list):
        """Вставить записи EPSS"""
        if not records:
            print("No EPSS records to insert")
            return
        
        conn = await self.get_connection()
        try:
            # Очищаем старые записи
            await conn.execute("DELETE FROM vulnanalizer.epss")
            
            # Вставляем новые записи батчами
            batch_size = 1000
            total_inserted = 0
            
            for i in range(0, len(records), batch_size):
                batch = records[i:i + batch_size]
                
                # Подготавливаем данные для вставки
                values = []
                for record in batch:
                    try:
                        cve = record.get('cve', '').strip()
                        epss_str = record.get('epss', '0')
                        percentile_str = record.get('percentile', '0')
                        
                        # Проверяем валидность CVE
                        if not cve or not cve.startswith('CVE-'):
                            continue
                        
                        # Конвертируем строки в числа
                        try:
                            epss = float(epss_str)
                            percentile = float(percentile_str)
                        except (ValueError, TypeError):
                            print(f"Invalid EPSS data for {cve}: epss={epss_str}, percentile={percentile_str}")
                            continue
                        
                        # Проверяем диапазоны
                        if not (0 <= epss <= 1):
                            print(f"EPSS score out of range for {cve}: {epss}")
                            continue
                        
                        if not (0 <= percentile <= 1):
                            print(f"Percentile out of range for {cve}: {percentile}")
                            continue
                        
                        values.append((cve, epss, percentile, datetime.now()))
                        
                    except Exception as e:
                        print(f"Error processing EPSS record: {e}")
                        continue
                
                if values:
                    # Массовая вставка
                    await conn.executemany("""
                        INSERT INTO vulnanalizer.epss (cve, epss, percentile, updated_at) 
                        VALUES ($1, $2, $3, $4)
                        ON CONFLICT (cve) DO UPDATE SET
                            epss = EXCLUDED.epss,
                            percentile = EXCLUDED.percentile,
                            updated_at = EXCLUDED.updated_at
                    """, values)
                    
                    total_inserted += len(values)
                    print(f"Inserted {len(values)} EPSS records (batch {i//batch_size + 1})")
            
            print(f"Successfully inserted {total_inserted} EPSS records")
            
        except Exception as e:
            print(f"Error inserting EPSS records: {e}")
            raise
        finally:
            await self.release_connection(conn)

    async def count_records(self):
        """Подсчитать количество записей EPSS"""
        conn = await self.get_connection()
        try:
            row = await conn.fetchrow("SELECT COUNT(*) as cnt FROM vulnanalizer.epss")
            return row['cnt'] if row else 0
        except Exception as e:
            print(f"Error counting EPSS records: {e}")
            return 0
        finally:
            await self.release_connection(conn)
    
    async def count_epss_records(self):
        """Алиас для count_records (для обратной совместимости)"""
        return await self.count_records()
    
    async def insert_epss_records(self, records: list):
        """Вставить записи EPSS с улучшенным управлением соединениями"""
        conn = None
        try:
            # Создаем отдельное соединение для массовой вставки
            conn = await asyncpg.connect(self.database_url)
            

            
            # Проверяем, что соединение активно
            await conn.execute("SELECT 1")
            
            # Получаем количество записей до вставки
            count_before = await conn.fetchval("SELECT COUNT(*) FROM vulnanalizer.epss")
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
                            existing = await conn.fetchval("SELECT id FROM vulnanalizer.epss WHERE cve = $1", cve)
                            
                            if existing:
                                # Обновляем существующую запись
                                query = """
                                    UPDATE vulnanalizer.epss 
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
                                    INSERT INTO vulnanalizer.epss (cve, epss, percentile, cvss, date)
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
            count_after = await conn.fetchval("SELECT COUNT(*) FROM vulnanalizer.epss")
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

    async def get_epss_by_cve(self, cve_id: str):
        """Получить данные EPSS по CVE ID"""
        conn = await self.get_connection()
        try:
            query = """
                SELECT cve, epss, percentile, cvss, date 
                FROM vulnanalizer.epss 
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

    async def get_all_epss_records(self):
        """Получить все записи EPSS"""
        conn = await self.get_connection()
        try:
            rows = await conn.fetch("SELECT cve, epss, percentile FROM vulnanalizer.epss ORDER BY cve")
            return [dict(row) for row in rows]
        except Exception as e:
            print(f"Error getting all epss records: {e}")
            raise
        finally:
            await self.release_connection(conn)

    async def clear_epss(self):
        """Очистка таблицы EPSS"""
        conn = await self.get_connection()
        try:
            query = "DELETE FROM vulnanalizer.epss"
            await conn.execute(query)
            print("EPSS table cleared successfully")
        except Exception as e:
            print(f"Error clearing EPSS table: {e}")
            raise e
        finally:
            await self.release_connection(conn)

    async def get_all_records(self):
        """Получить все записи EPSS"""
        conn = await self.get_connection()
        try:
            rows = await conn.fetch("SELECT cve, epss, percentile, updated_at FROM vulnanalizer.epss ORDER BY cve")
            return [dict(row) for row in rows]
        except Exception as e:
            print(f"Error getting EPSS records: {e}")
            return []
        finally:
            await self.release_connection(conn)

    async def get_by_cve(self, cve_id: str):
        """Получить данные EPSS по CVE ID"""
        if not cve_id:
            return None
            
        conn = await self.get_connection()
        try:
            row = await conn.fetchrow("""
                SELECT cve, epss, percentile, updated_at 
                FROM vulnanalizer.epss 
                WHERE cve = $1
            """, cve_id.upper())
            
            if row:
                return {
                    'cve': row['cve'],
                    'epss': float(row['epss']),
                    'percentile': float(row['percentile']),
                    'updated_at': row['updated_at'].isoformat() if row['updated_at'] else None
                }
            return None
        except Exception as e:
            print(f"Error getting EPSS data for {cve_id}: {e}")
            return None
        finally:
            await self.release_connection(conn)

    async def clear(self):
        """Очистить все записи EPSS"""
        conn = await self.get_connection()
        try:
            await conn.execute("DELETE FROM vulnanalizer.epss")
            print("EPSS data cleared")
        except Exception as e:
            print(f"Error clearing EPSS data: {e}")
            raise
        finally:
            await self.release_connection(conn)

    async def search_epss(self, cve_pattern: str = None, limit: int = 100, page: int = 1):
        """Поиск EPSS данных по CVE"""
        conn = await self.get_connection()
        try:
            conditions = []
            params = []
            param_count = 0
            
            if cve_pattern:
                param_count += 1
                # Поддержка поиска по части CVE ID
                cve_pattern = cve_pattern.upper()
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
            
            where_clause = " AND ".join(conditions) if conditions else "1=1"
            
            # Сначала получаем общее количество записей
            count_query = f"SELECT COUNT(*) FROM vulnanalizer.epss WHERE {where_clause}"
            total_count = await conn.fetchval(count_query, *params)
            
            # Затем получаем данные с пагинацией
            offset = (page - 1) * limit
            query = f"""
                SELECT cve, epss, percentile, created_at
                FROM vulnanalizer.epss 
                WHERE {where_clause}
                ORDER BY cve
                LIMIT {limit} OFFSET {offset}
            """
            
            rows = await conn.fetch(query, *params)
            
            results = []
            for row in rows:
                results.append({
                    'cve': row['cve'],
                    'epss': float(row['epss']) if row['epss'] else None,
                    'percentile': float(row['percentile']) if row['percentile'] else None,
                    'updated_at': row['created_at'].isoformat() if row['created_at'] else None
                })
            
            return results, total_count
        except Exception as e:
            print(f"Error searching EPSS: {e}")
            return [], 0
        finally:
            await self.release_connection(conn)
