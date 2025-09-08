"""
Репозиторий для работы с CVE данными
"""
import asyncpg
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime
from .base import DatabaseBase


class CVERepository(DatabaseBase):
    """Репозиторий для работы с CVE данными"""

    async def insert_records(self, records: list):
        """Вставить записи CVE"""
        if not records:
            print("No CVE records to insert")
            return
        
        conn = await self.get_connection()
        try:
            # Очищаем старые записи
            await conn.execute("DELETE FROM vulnanalizer.cve")
            
            # Вставляем новые записи батчами
            batch_size = 1000
            total_inserted = 0
            
            for i in range(0, len(records), batch_size):
                batch = records[i:i + batch_size]
                
                # Подготавливаем данные для вставки
                values = []
                for record in batch:
                    try:
                        cve_id = record.get('cve_id', '').strip()
                        description = record.get('description', '').strip()
                        cvss_v2_base_score = record.get('cvss_v2_base_score')
                        cvss_v3_base_score = record.get('cvss_v3_base_score')
                        published_date_str = record.get('published_date')
                        modified_date_str = record.get('modified_date')
                        
                        # Проверяем обязательные поля
                        if not cve_id or not cve_id.startswith('CVE-'):
                            continue
                        
                        # Конвертируем CVSS scores
                        cvss_v2 = None
                        cvss_v3 = None
                        
                        if cvss_v2_base_score is not None:
                            try:
                                cvss_v2 = float(cvss_v2_base_score)
                                if not (0 <= cvss_v2 <= 10):
                                    cvss_v2 = None
                            except (ValueError, TypeError):
                                cvss_v2 = None
                        
                        if cvss_v3_base_score is not None:
                            try:
                                cvss_v3 = float(cvss_v3_base_score)
                                if not (0 <= cvss_v3 <= 10):
                                    cvss_v3 = None
                            except (ValueError, TypeError):
                                cvss_v3 = None
                        
                        # Парсим даты
                        published_date = None
                        modified_date = None
                        
                        if published_date_str:
                            try:
                                published_date = datetime.fromisoformat(published_date_str.replace('Z', '+00:00'))
                            except (ValueError, TypeError):
                                try:
                                    published_date = datetime.strptime(published_date_str, '%Y-%m-%d')
                                except (ValueError, TypeError):
                                    pass
                        
                        if modified_date_str:
                            try:
                                modified_date = datetime.fromisoformat(modified_date_str.replace('Z', '+00:00'))
                            except (ValueError, TypeError):
                                try:
                                    modified_date = datetime.strptime(modified_date_str, '%Y-%m-%d')
                                except (ValueError, TypeError):
                                    pass
                        
                        # Получаем новые поля CVSS
                        cvss_v3_base_severity = record.get('cvss_v3_base_severity')
                        cvss_v3_attack_vector = record.get('cvss_v3_attack_vector')
                        cvss_v3_privileges_required = record.get('cvss_v3_privileges_required')
                        cvss_v3_user_interaction = record.get('cvss_v3_user_interaction')
                        cvss_v3_confidentiality_impact = record.get('cvss_v3_confidentiality_impact')
                        cvss_v3_integrity_impact = record.get('cvss_v3_integrity_impact')
                        cvss_v3_availability_impact = record.get('cvss_v3_availability_impact')
                        
                        cvss_v2_base_severity = record.get('cvss_v2_base_severity')
                        cvss_v2_access_vector = record.get('cvss_v2_access_vector')
                        cvss_v2_access_complexity = record.get('cvss_v2_access_complexity')
                        cvss_v2_authentication = record.get('cvss_v2_authentication')
                        cvss_v2_confidentiality_impact = record.get('cvss_v2_confidentiality_impact')
                        cvss_v2_integrity_impact = record.get('cvss_v2_integrity_impact')
                        cvss_v2_availability_impact = record.get('cvss_v2_availability_impact')
                        
                        values.append((
                            cve_id.upper(),
                            description[:2000] if description else None,  # Ограничиваем длину
                            cvss_v2,
                            cvss_v3,
                            cvss_v3_base_severity,
                            cvss_v3_attack_vector,
                            cvss_v3_privileges_required,
                            cvss_v3_user_interaction,
                            cvss_v3_confidentiality_impact,
                            cvss_v3_integrity_impact,
                            cvss_v3_availability_impact,
                            cvss_v2_base_severity,
                            cvss_v2_access_vector,
                            cvss_v2_access_complexity,
                            cvss_v2_authentication,
                            cvss_v2_confidentiality_impact,
                            cvss_v2_integrity_impact,
                            cvss_v2_availability_impact,
                            published_date,
                            modified_date,
                            datetime.now()
                        ))
                        
                    except Exception as e:
                        print(f"Error processing CVE record: {e}")
                        continue
                
                if values:
                    # Массовая вставка
                    await conn.executemany("""
                        INSERT INTO vulnanalizer.cve (
                            cve_id, description, cvss_v2_base_score, cvss_v3_base_score,
                            cvss_v3_base_severity, cvss_v3_attack_vector, cvss_v3_privileges_required,
                            cvss_v3_user_interaction, cvss_v3_confidentiality_impact, cvss_v3_integrity_impact,
                            cvss_v3_availability_impact, cvss_v2_base_severity, cvss_v2_access_vector,
                            cvss_v2_access_complexity, cvss_v2_authentication, cvss_v2_confidentiality_impact,
                            cvss_v2_integrity_impact, cvss_v2_availability_impact, published_date, last_modified_date, created_at
                        ) 
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20, $21)
                        ON CONFLICT (cve_id) DO UPDATE SET
                            description = EXCLUDED.description,
                            cvss_v2_base_score = EXCLUDED.cvss_v2_base_score,
                            cvss_v3_base_score = EXCLUDED.cvss_v3_base_score,
                            cvss_v3_base_severity = EXCLUDED.cvss_v3_base_severity,
                            cvss_v3_attack_vector = EXCLUDED.cvss_v3_attack_vector,
                            cvss_v3_privileges_required = EXCLUDED.cvss_v3_privileges_required,
                            cvss_v3_user_interaction = EXCLUDED.cvss_v3_user_interaction,
                            cvss_v3_confidentiality_impact = EXCLUDED.cvss_v3_confidentiality_impact,
                            cvss_v3_integrity_impact = EXCLUDED.cvss_v3_integrity_impact,
                            cvss_v3_availability_impact = EXCLUDED.cvss_v3_availability_impact,
                            cvss_v2_base_severity = EXCLUDED.cvss_v2_base_severity,
                            cvss_v2_access_vector = EXCLUDED.cvss_v2_access_vector,
                            cvss_v2_access_complexity = EXCLUDED.cvss_v2_access_complexity,
                            cvss_v2_authentication = EXCLUDED.cvss_v2_authentication,
                            cvss_v2_confidentiality_impact = EXCLUDED.cvss_v2_confidentiality_impact,
                            cvss_v2_integrity_impact = EXCLUDED.cvss_v2_integrity_impact,
                            cvss_v2_availability_impact = EXCLUDED.cvss_v2_availability_impact,
                            published_date = EXCLUDED.published_date,
                            last_modified_date = EXCLUDED.last_modified_date,
                            created_at = EXCLUDED.created_at
                    """, values)
                    
                    total_inserted += len(values)
                    print(f"Inserted {len(values)} CVE records (batch {i//batch_size + 1})")
            
            print(f"Successfully inserted {total_inserted} CVE records")
            
        except Exception as e:
            print(f"Error inserting CVE records: {e}")
            raise
        finally:
            await self.release_connection(conn)

    async def count_records(self):
        """Подсчитать количество записей CVE"""
        conn = await self.get_connection()
        try:
            row = await conn.fetchrow("SELECT COUNT(*) as cnt FROM vulnanalizer.cve")
            return row['cnt'] if row else 0
        except Exception as e:
            print(f"Error counting CVE records: {e}")
            return 0
        finally:
            await self.release_connection(conn)

    async def get_by_id(self, cve_id: str):
        """Получить данные CVE по ID"""
        if not cve_id:
            return None
            
        conn = await self.get_connection()
        try:
            row = await conn.fetchrow("""
                SELECT cve_id, description, cvss_v3_base_score, cvss_v3_base_severity,
                       cvss_v3_attack_vector, cvss_v3_privileges_required, cvss_v3_user_interaction,
                       cvss_v3_confidentiality_impact, cvss_v3_integrity_impact, cvss_v3_availability_impact,
                       cvss_v2_base_score, cvss_v2_base_severity, cvss_v2_access_vector,
                       cvss_v2_access_complexity, cvss_v2_authentication, cvss_v2_confidentiality_impact,
                       cvss_v2_integrity_impact, cvss_v2_availability_impact, exploitability_score,
                       impact_score, published_date, last_modified_date, created_at
                FROM vulnanalizer.cve 
                WHERE cve_id = $1
            """, cve_id.upper())
            
            if row:
                return {
                    'cve_id': row['cve_id'],
                    'description': row['description'],
                    'cvss_v3_base_score': float(row['cvss_v3_base_score']) if row['cvss_v3_base_score'] else None,
                    'cvss_v3_base_severity': row['cvss_v3_base_severity'],
                    'cvss_v3_attack_vector': row['cvss_v3_attack_vector'],
                    'cvss_v3_privileges_required': row['cvss_v3_privileges_required'],
                    'cvss_v3_user_interaction': row['cvss_v3_user_interaction'],
                    'cvss_v3_confidentiality_impact': row['cvss_v3_confidentiality_impact'],
                    'cvss_v3_integrity_impact': row['cvss_v3_integrity_impact'],
                    'cvss_v3_availability_impact': row['cvss_v3_availability_impact'],
                    'cvss_v2_base_score': float(row['cvss_v2_base_score']) if row['cvss_v2_base_score'] else None,
                    'cvss_v2_base_severity': row['cvss_v2_base_severity'],
                    'cvss_v2_access_vector': row['cvss_v2_access_vector'],
                    'cvss_v2_access_complexity': row['cvss_v2_access_complexity'],
                    'cvss_v2_authentication': row['cvss_v2_authentication'],
                    'cvss_v2_confidentiality_impact': row['cvss_v2_confidentiality_impact'],
                    'cvss_v2_integrity_impact': row['cvss_v2_integrity_impact'],
                    'cvss_v2_availability_impact': row['cvss_v2_availability_impact'],
                    'exploitability_score': float(row['exploitability_score']) if row['exploitability_score'] else None,
                    'impact_score': float(row['impact_score']) if row['impact_score'] else None,
                    'published_date': row['published_date'].isoformat() if row['published_date'] else None,
                    'last_modified_date': row['last_modified_date'].isoformat() if row['last_modified_date'] else None,
                    'created_at': row['created_at'].isoformat() if row['created_at'] else None
                }
            return None
        except Exception as e:
            print(f"Error getting CVE data for {cve_id}: {e}")
            return None
        finally:
            await self.release_connection(conn)

    async def search(self, query: str = None, limit: int = 100, offset: int = 0):
        """Поиск CVE записей"""
        conn = await self.get_connection()
        try:
            if query:
                # Поиск по CVE ID или описанию
                rows = await conn.fetch("""
                    SELECT cve_id, description, cvss_v2_base_score, cvss_v3_base_score, published_date, modified_date, updated_at
                    FROM vulnanalizer.cve 
                    WHERE cve_id ILIKE $1 OR description ILIKE $1
                    ORDER BY published_date DESC
                    LIMIT $2 OFFSET $3
                """, f"%{query}%", limit, offset)
            else:
                # Получить все записи
                rows = await conn.fetch("""
                    SELECT cve_id, description, cvss_v2_base_score, cvss_v3_base_score, published_date, modified_date, updated_at
                    FROM vulnanalizer.cve 
                    ORDER BY published_date DESC
                    LIMIT $1 OFFSET $2
                """, limit, offset)
            
            results = []
            for row in rows:
                results.append({
                    'cve_id': row['cve_id'],
                    'description': row['description'],
                    'cvss_v2_base_score': float(row['cvss_v2_base_score']) if row['cvss_v2_base_score'] else None,
                    'cvss_v3_base_score': float(row['cvss_v3_base_score']) if row['cvss_v3_base_score'] else None,
                    'published_date': row['published_date'].isoformat() if row['published_date'] else None,
                    'modified_date': row['modified_date'].isoformat() if row['modified_date'] else None,
                    'updated_at': row['updated_at'].isoformat() if row['updated_at'] else None
                })
            
            return results
        except Exception as e:
            print(f"Error searching CVE records: {e}")
            return []
        finally:
            await self.release_connection(conn)

    async def clear(self):
        """Очистить все записи CVE"""
        conn = await self.get_connection()
        try:
            await conn.execute("DELETE FROM vulnanalizer.cve")
            print("CVE data cleared")
        except Exception as e:
            print(f"Error clearing CVE data: {e}")
            raise
        finally:
            await self.release_connection(conn)
    
    async def count_cve_records(self):
        """Алиас для count_records (для обратной совместимости)"""
        return await self.count_records()

    async def insert_cve_records(self, records: list):
        """Вставить записи CVE с улучшенным управлением соединениями"""
        conn = None
        try:
            # Создаем отдельное соединение для массовой вставки
            conn = await asyncpg.connect(self.database_url)
            
            # Проверяем, что соединение активно
            await conn.execute("SELECT 1")
            
            # Получаем количество записей до вставки
            count_before = await conn.fetchval("SELECT COUNT(*) FROM vulnanalizer.cve")
            
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
                    await conn.close()
                    conn = await asyncpg.connect(self.database_url)
                
                query = """
                    INSERT INTO vulnanalizer.cve (
                        cve_id, description, cvss_v3_base_score, cvss_v3_base_severity,
                        cvss_v3_attack_vector, cvss_v3_privileges_required, cvss_v3_user_interaction,
                        cvss_v3_confidentiality_impact, cvss_v3_integrity_impact, cvss_v3_availability_impact,
                        cvss_v2_base_score, cvss_v2_base_severity, cvss_v2_access_vector,
                        cvss_v2_access_complexity, cvss_v2_authentication, cvss_v2_confidentiality_impact,
                        cvss_v2_integrity_impact, cvss_v2_availability_impact, exploitability_score,
                        impact_score, published_date, last_modified_date
                    )
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20, $21, $22)
                    ON CONFLICT (cve_id) DO UPDATE SET 
                        description = $2, cvss_v3_base_score = $3, cvss_v3_base_severity = $4,
                        cvss_v3_attack_vector = $5, cvss_v3_privileges_required = $6, cvss_v3_user_interaction = $7,
                        cvss_v3_confidentiality_impact = $8, cvss_v3_integrity_impact = $9, cvss_v3_availability_impact = $10,
                        cvss_v2_base_score = $11, cvss_v2_base_severity = $12, cvss_v2_access_vector = $13,
                        cvss_v2_access_complexity = $14, cvss_v2_authentication = $15, cvss_v2_confidentiality_impact = $16,
                        cvss_v2_integrity_impact = $17, cvss_v2_availability_impact = $18, exploitability_score = $19,
                        impact_score = $20, published_date = $21, last_modified_date = $22
                """
                
                for rec in batch_records:
                    try:
                        # Обрабатываем каждую запись в отдельной транзакции
                        async with conn.transaction():
                            # Проверяем, существует ли запись
                            existing = await conn.fetchval("SELECT cve_id FROM vulnanalizer.cve WHERE cve_id = $1", rec['cve_id'])
                            
                            # Конвертируем даты в объекты datetime
                            published_date = None
                            last_modified_date = None
                            
                            if rec.get('published_date'):
                                if isinstance(rec['published_date'], str):
                                    try:
                                        # Убираем часовой пояс для совместимости
                                        date_str = rec['published_date'].replace('Z', '').replace('+00:00', '')
                                        published_date = datetime.fromisoformat(date_str)
                                    except:
                                        published_date = None
                                else:
                                    published_date = rec['published_date']
                            
                            if rec.get('last_modified_date'):
                                if isinstance(rec['last_modified_date'], str):
                                    try:
                                        # Убираем часовой пояс для совместимости
                                        date_str = rec['last_modified_date'].replace('Z', '').replace('+00:00', '')
                                        last_modified_date = datetime.fromisoformat(date_str)
                                    except:
                                        last_modified_date = None
                                else:
                                    last_modified_date = rec['last_modified_date']
                            
                            await conn.execute(query, 
                                rec['cve_id'], rec.get('description'), rec.get('cvss_v3_base_score'),
                                rec.get('cvss_v3_base_severity'), rec.get('cvss_v3_attack_vector'),
                                rec.get('cvss_v3_privileges_required'), rec.get('cvss_v3_user_interaction'),
                                rec.get('cvss_v3_confidentiality_impact'), rec.get('cvss_v3_integrity_impact'),
                                rec.get('cvss_v3_availability_impact'), rec.get('cvss_v2_base_score'),
                                rec.get('cvss_v2_base_severity'), rec.get('cvss_v2_access_vector'),
                                rec.get('cvss_v2_access_complexity'), rec.get('cvss_v2_authentication'),
                                rec.get('cvss_v2_confidentiality_impact'), rec.get('cvss_v2_integrity_impact'),
                                rec.get('cvss_v2_availability_impact'), rec.get('exploitability_score'),
                                rec.get('impact_score'), published_date, last_modified_date)
                            
                            if existing:
                                updated_count += 1
                            else:
                                inserted_count += 1
                                
                    except Exception as e:
                        continue
                
                # Показываем прогресс
            
            # Получаем количество записей после вставки
            count_after = await conn.fetchval("SELECT COUNT(*) FROM vulnanalizer.cve")
            
        except Exception as e:
            raise e
        finally:
            if conn:
                try:
                    await conn.close()
                except Exception as e:
                    pass

    async def get_cve_by_id(self, cve_id: str):
        """Получить данные CVE по ID"""
        conn = await self.get_connection()
        try:
            query = """
                SELECT cve_id, description, cvss_v3_base_score, cvss_v3_base_severity,
                       cvss_v3_attack_vector, cvss_v3_privileges_required, cvss_v3_user_interaction,
                       cvss_v3_confidentiality_impact, cvss_v3_integrity_impact, cvss_v3_availability_impact,
                       cvss_v2_base_score, cvss_v2_base_severity, cvss_v2_access_vector,
                       cvss_v2_access_complexity, cvss_v2_authentication, cvss_v2_confidentiality_impact,
                       cvss_v2_integrity_impact, cvss_v2_availability_impact, exploitability_score,
                       impact_score, published_date, last_modified_date
                FROM vulnanalizer.cve 
                WHERE cve_id = $1
            """
            row = await conn.fetchrow(query, cve_id)
            
            if row:
                return {
                    'cve_id': row['cve_id'],
                    'description': row['description'],
                    'cvss_v3_base_score': float(row['cvss_v3_base_score']) if row['cvss_v3_base_score'] else None,
                    'cvss_v3_base_severity': row['cvss_v3_base_severity'],
                    'cvss_v3_attack_vector': row['cvss_v3_attack_vector'],
                    'cvss_v3_privileges_required': row['cvss_v3_privileges_required'],
                    'cvss_v3_user_interaction': row['cvss_v3_user_interaction'],
                    'cvss_v3_confidentiality_impact': row['cvss_v3_confidentiality_impact'],
                    'cvss_v3_integrity_impact': row['cvss_v3_integrity_impact'],
                    'cvss_v3_availability_impact': row['cvss_v3_availability_impact'],
                    'cvss_v2_base_score': float(row['cvss_v2_base_score']) if row['cvss_v2_base_score'] else None,
                    'cvss_v2_base_severity': row['cvss_v2_base_severity'],
                    'cvss_v2_access_vector': row['cvss_v2_access_vector'],
                    'cvss_v2_access_complexity': row['cvss_v2_access_complexity'],
                    'cvss_v2_authentication': row['cvss_v2_authentication'],
                    'cvss_v2_confidentiality_impact': row['cvss_v2_confidentiality_impact'],
                    'cvss_v2_integrity_impact': row['cvss_v2_integrity_impact'],
                    'cvss_v2_availability_impact': row['cvss_v2_availability_impact'],
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
            await conn.execute("DELETE FROM vulnanalizer.cve")
            print("All CVE data cleared")
        except Exception as e:
            print(f"Error clearing CVE data: {e}")
            raise
        finally:
            await self.release_connection(conn)
    

