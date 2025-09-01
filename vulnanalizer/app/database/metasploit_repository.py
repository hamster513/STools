import json
import logging
from typing import Dict, List, Optional
from datetime import datetime
from .base import DatabaseBase

logger = logging.getLogger(__name__)

class MetasploitRepository(DatabaseBase):
    def __init__(self):
        super().__init__()

    async def create_table(self):
        """Создание таблицы metasploit_modules если она не существует"""
        try:
            conn = await self.get_connection()
            try:
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS vulnanalizer.metasploit_modules (
                        id SERIAL PRIMARY KEY,
                        module_name VARCHAR(500) NOT NULL UNIQUE,
                        name TEXT NOT NULL,
                        fullname VARCHAR(500) NOT NULL,
                        rank INTEGER NOT NULL,
                        rank_text VARCHAR(20) GENERATED ALWAYS AS (
                            CASE 
                                WHEN rank = 0 THEN 'manual'
                                WHEN rank = 200 THEN 'low'
                                WHEN rank = 300 THEN 'average'
                                WHEN rank = 400 THEN 'normal'
                                WHEN rank = 500 THEN 'good'
                                WHEN rank = 600 THEN 'excellent'
                                ELSE 'unknown'
                            END
                        ) STORED,
                        disclosure_date DATE,
                        type VARCHAR(50) NOT NULL,
                        description TEXT,
                        references TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Создание индексов
                await conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_metasploit_module_name 
                    ON vulnanalizer.metasploit_modules(module_name)
                """)
                await conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_metasploit_rank 
                    ON vulnanalizer.metasploit_modules(rank)
                """)
                await conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_metasploit_modules_type 
                    ON vulnanalizer.metasploit_modules(type)
                """)
                await conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_metasploit_disclosure_date 
                    ON vulnanalizer.metasploit_modules(disclosure_date)
                """)
                
                logger.info("Metasploit table created successfully")
            finally:
                await self.release_connection(conn)
        except Exception as e:
            logger.error(f"Error creating metasploit table: {e}")
            raise

    async def clear_all_data(self):
        """Очистка всех данных из таблицы"""
        try:
            conn = await self.get_connection()
            try:
                await conn.execute("DELETE FROM vulnanalizer.metasploit_modules")
                logger.info("Metasploit data cleared successfully")
            finally:
                await self.release_connection(conn)
        except Exception as e:
            logger.error(f"Error clearing metasploit data: {e}")
            raise

    async def insert_modules(self, modules_data: List[Dict]):
        """Вставка модулей Metasploit в базу данных"""
        try:
            conn = await self.get_connection()
            try:
                # Подготовка данных для вставки
                modules_to_insert = []
                
                for module_info in modules_data:
                    # Обработка disclosure_date
                    disclosure_date = None
                    if module_info.get('disclosure_date'):
                        if isinstance(module_info['disclosure_date'], datetime):
                            disclosure_date = module_info['disclosure_date'].date()
                        else:
                            try:
                                disclosure_date = datetime.strptime(
                                    str(module_info['disclosure_date']), '%Y-%m-%d'
                                ).date()
                            except (ValueError, TypeError):
                                disclosure_date = None
                    
                    # Обработка references
                    references = module_info.get('references', '')
                    if isinstance(references, list):
                        references = ', '.join(references)
                    elif not isinstance(references, str):
                        references = str(references) if references else ''
                    
                    # Обработка fullname - если отсутствует, используем module_name
                    fullname = module_info.get('fullname')
                    if not fullname or fullname.strip() == '':
                        fullname = module_info.get('module_name', '')
                    
                    modules_to_insert.append((
                        module_info.get('module_name', ''),
                        module_info.get('name', ''),
                        fullname,
                        module_info.get('rank', 0),
                        disclosure_date,
                        module_info.get('type', ''),
                        module_info.get('description', ''),
                        references
                    ))
                
                # Вставка данных
                await conn.executemany("""
                    INSERT INTO vulnanalizer.metasploit_modules 
                    (module_name, name, fullname, rank, disclosure_date, type, description, "references")
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                    ON CONFLICT (module_name) 
                    DO UPDATE SET
                        name = EXCLUDED.name,
                        fullname = EXCLUDED.fullname,
                        rank = EXCLUDED.rank,
                        disclosure_date = EXCLUDED.disclosure_date,
                        type = EXCLUDED.type,
                        description = EXCLUDED.description,
                        "references" = EXCLUDED."references",
                        updated_at = CURRENT_TIMESTAMP
                """, modules_to_insert)
                
                logger.info(f"Inserted {len(modules_to_insert)} metasploit modules")
                return len(modules_to_insert)
            finally:
                await self.release_connection(conn)
        except Exception as e:
            logger.error(f"Error inserting metasploit modules: {e}")
            raise

    async def get_modules_count(self) -> int:
        """Получение количества модулей в базе"""
        try:
            conn = await self.get_connection()
            try:
                result = await conn.fetchval("SELECT COUNT(*) FROM vulnanalizer.metasploit_modules")
                return result or 0
            finally:
                await self.release_connection(conn)
        except Exception as e:
            logger.error(f"Error getting metasploit modules count: {e}")
            return 0

    async def search_modules(self, 
                           search_term: str = None, 
                           module_type: str = None,
                           rank: int = None,
                           limit: int = 100,
                           offset: int = 0) -> List[Dict]:
        """Поиск модулей Metasploit"""
        try:
            conn = await self.get_connection()
            try:
                query = """
                    SELECT 
                        module_name, name, fullname, rank, rank_text,
                        disclosure_date, type, description, references,
                        created_at, updated_at
                    FROM vulnanalizer.metasploit_modules
                    WHERE 1=1
                """
                params = []
                param_count = 0
                
                if search_term:
                    param_count += 1
                    query += f" AND (name ILIKE ${param_count} OR description ILIKE ${param_count})"
                    params.append(f"%{search_term}%")
                
                if module_type:
                    param_count += 1
                    query += f" AND type = ${param_count}"
                    params.append(module_type)
                
                if rank is not None:
                    param_count += 1
                    query += f" AND rank = ${param_count}"
                    params.append(rank)
                
                query += " ORDER BY rank DESC, name ASC"
                query += f" LIMIT {limit} OFFSET {offset}"
                
                rows = await conn.fetch(query, *params)
                
                return [dict(row) for row in rows]
            finally:
                await self.release_connection(conn)
        except Exception as e:
            logger.error(f"Error searching metasploit modules: {e}")
            return []

    async def get_module_by_name(self, module_name: str) -> Optional[Dict]:
        """Получение модуля по имени"""
        try:
            conn = await self.get_connection()
            try:
                row = await conn.fetchrow("""
                    SELECT 
                        module_name, name, fullname, rank, rank_text,
                        disclosure_date, type, description, references,
                        created_at, updated_at
                    FROM vulnanalizer.metasploit_modules
                    WHERE module_name = $1
                """, module_name)
                
                return dict(row) if row else None
            finally:
                await self.release_connection(conn)
        except Exception as e:
            logger.error(f"Error getting metasploit module: {e}")
            return None

    async def get_statistics(self) -> Dict:
        """Получение статистики по модулям"""
        try:
            conn = await self.get_connection()
            try:
                # Общее количество
                total_count = await conn.fetchval("SELECT COUNT(*) FROM vulnanalizer.metasploit_modules")
                
                # По типам
                type_stats = await conn.fetch("""
                    SELECT type, COUNT(*) as count
                    FROM vulnanalizer.metasploit_modules
                    GROUP BY type
                    ORDER BY count DESC
                """)
                
                # По рангам
                rank_stats = await conn.fetch("""
                    SELECT rank_text, COUNT(*) as count
                    FROM vulnanalizer.metasploit_modules
                    GROUP BY rank_text
                    ORDER BY count DESC
                """)
                
                # Последнее обновление
                last_update = await conn.fetchval("""
                    SELECT MAX(updated_at) FROM vulnanalizer.metasploit_modules
                """)
                
                return {
                    'total_count': total_count or 0,
                    'by_type': [dict(row) for row in type_stats],
                    'by_rank': [dict(row) for row in rank_stats],
                    'last_update': last_update
                }
            finally:
                await self.release_connection(conn)
        except Exception as e:
            logger.error(f"Error getting metasploit statistics: {e}")
            return {
                'total_count': 0,
                'by_type': [],
                'by_rank': [],
                'last_update': None
            }
