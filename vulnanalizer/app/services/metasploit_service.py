import json
import logging
import aiohttp
import asyncio
from typing import Dict, Optional
from datetime import datetime
from database import get_db

logger = logging.getLogger(__name__)

class MetasploitService:
    def __init__(self):
        self.metasploit_url = "https://raw.githubusercontent.com/rapid7/metasploit-framework/master/db/modules_metadata_base.json"
        
    async def download_metasploit_data(self) -> Optional[Dict]:
        """Загрузка данных Metasploit с GitHub"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.metasploit_url) as response:
                    if response.status == 200:
                        # Читаем содержимое как текст, а не как JSON
                        content = await response.text()
                        # Парсим JSON из текста
                        data = json.loads(content)
                        logger.info(f"Downloaded {len(data)} metasploit modules")
                        return data
                    else:
                        logger.error(f"Failed to download metasploit data: HTTP {response.status}")
                        return None
        except Exception as e:
            logger.error(f"Error downloading metasploit data: {e}")
            return None

    async def create_table(self):
        """Создание таблицы metasploit_modules если она не существует"""
        try:
            db = get_db()
            conn = await db.get_connection()
            
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS metasploit_modules (
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
                                            "references" TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Создание индексов
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_metasploit_module_name 
                ON metasploit_modules(module_name)
            """)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_metasploit_rank 
                ON metasploit_modules(rank)
            """)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_metasploit_type 
                ON metasploit_modules(type)
            """)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_metasploit_disclosure_date 
                ON metasploit_modules(disclosure_date)
            """)
            
            await db.release_connection(conn)
            logger.info("Metasploit table created successfully")
        except Exception as e:
            logger.error(f"Error creating metasploit table: {e}")
            raise

    async def clear_all_data(self):
        """Очистка всех данных из таблицы"""
        try:
            db = get_db()
            conn = await db.get_connection()
            await conn.execute("DELETE FROM metasploit_modules")
            await db.release_connection(conn)
            logger.info("Metasploit data cleared successfully")
        except Exception as e:
            logger.error(f"Error clearing metasploit data: {e}")
            raise

    async def insert_modules(self, modules_data: Dict) -> int:
        """Вставка модулей Metasploit в базу данных"""
        try:
            db = get_db()
            conn = await db.get_connection()
            
            # Подготовка данных для вставки
            modules_to_insert = []
            
            for module_name, module_info in modules_data.items():
                # Обработка disclosure_date
                disclosure_date = None
                if module_info.get('disclosure_date'):
                    try:
                        disclosure_date = datetime.strptime(
                            module_info['disclosure_date'], '%Y-%m-%d'
                        ).date()
                    except (ValueError, TypeError):
                        disclosure_date = None
                
                # Обработка references
                references = None
                if module_info.get('references'):
                    if isinstance(module_info['references'], list):
                        references = json.dumps(module_info['references'])
                    else:
                        references = str(module_info['references'])
                
                modules_to_insert.append((
                    module_name,
                    module_info.get('name', ''),
                    module_info.get('fullname', ''),
                    module_info.get('rank', 0),
                    disclosure_date,
                    module_info.get('type', ''),
                    module_info.get('description', ''),
                    references
                ))
            
            # Вставка данных
            await conn.executemany("""
                INSERT INTO metasploit_modules 
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
            
            await db.release_connection(conn)
            logger.info(f"Inserted {len(modules_to_insert)} metasploit modules")
            return len(modules_to_insert)
            
        except Exception as e:
            logger.error(f"Error inserting metasploit modules: {e}")
            raise

    async def process_and_save_metasploit_data(self, data: Dict) -> int:
        """Обработка и сохранение данных Metasploit"""
        try:
            # Создаем таблицу если не существует
            await self.create_table()
            
            # Сохраняем данные
            inserted_count = await self.insert_modules(data)
            
            logger.info(f"Successfully processed and saved {inserted_count} metasploit modules")
            return inserted_count
            
        except Exception as e:
            logger.error(f"Error processing metasploit data: {e}")
            raise

    async def download_and_save_metasploit(self) -> Dict:
        """Полная загрузка и сохранение данных Metasploit"""
        try:
            # Загружаем данные
            data = await self.download_metasploit_data()
            if not data:
                return {
                    'success': False,
                    'error': 'Failed to download metasploit data',
                    'count': 0
                }
            
            # Обрабатываем и сохраняем
            count = await self.process_and_save_metasploit_data(data)
            
            return {
                'success': True,
                'count': count,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error in download_and_save_metasploit: {e}")
            return {
                'success': False,
                'error': str(e),
                'count': 0
            }

    async def get_modules_count(self) -> int:
        """Получение количества модулей в базе"""
        try:
            db = get_db()
            conn = await db.get_connection()
            result = await conn.fetchval("SELECT COUNT(*) FROM metasploit_modules")
            await db.release_connection(conn)
            return result or 0
        except Exception as e:
            logger.error(f"Error getting metasploit modules count: {e}")
            return 0

    async def get_metasploit_status(self) -> Dict:
        """Получение статуса базы Metasploit"""
        try:
            count = await self.get_modules_count()
            
            db = get_db()
            conn = await db.get_connection()
            
            # По типам
            type_stats = await conn.fetch("""
                SELECT type, COUNT(*) as count
                FROM metasploit_modules
                GROUP BY type
                ORDER BY count DESC
            """)
            
            # По рангам
            rank_stats = await conn.fetch("""
                SELECT rank_text, COUNT(*) as count
                FROM metasploit_modules
                GROUP BY rank_text
                ORDER BY count DESC
            """)
            
            # Последнее обновление
            last_update = await conn.fetchval("""
                SELECT MAX(updated_at) FROM metasploit_modules
            """)
            
            await db.release_connection(conn)
            
            # Конвертируем datetime в строку для JSON
            last_update_str = last_update.isoformat() if last_update else None
            
            return {
                'total_count': count,
                'statistics': {
                    'by_type': [dict(row) for row in type_stats],
                    'by_rank': [dict(row) for row in rank_stats]
                },
                'last_update': last_update_str,
                'has_data': count > 0
            }
            
        except Exception as e:
            logger.error(f"Error getting metasploit status: {e}")
            return {
                'total_count': 0,
                'statistics': {},
                'last_update': None,
                'has_data': False,
                'error': str(e)
            }

    async def clear_metasploit_data(self) -> bool:
        """Очистка всех данных Metasploit"""
        try:
            await self.clear_all_data()
            return True
        except Exception as e:
            logger.error(f"Error clearing metasploit data: {e}")
            return False
