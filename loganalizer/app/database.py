import asyncpg
import os
import json
from typing import Dict, List, Optional
from datetime import datetime
import uuid

class Database:
    def __init__(self):
        self.pool = None
        self.database_url = os.getenv('DATABASE_URL', 'postgresql://stools_user:stools_pass@postgres:5432/stools_db')

    async def get_pool(self):
        if self.pool is None:
            self.pool = await asyncpg.create_pool(self.database_url)
        return self.pool

    async def test_connection(self):
        try:
            pool = await self.get_pool()
            async with pool.acquire() as conn:
                await conn.execute('SELECT 1')
            print("Database connection successful")
        except Exception as e:
            print(f"Database connection failed: {e}")
            raise

    async def init_database(self):
        """Инициализация базы данных"""
        pool = await self.get_pool()
        async with pool.acquire() as conn:
            # Создаем таблицу настроек
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS settings (
                    id SERIAL PRIMARY KEY,
                    key VARCHAR(255) UNIQUE NOT NULL,
                    value TEXT NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Создаем таблицу файлов логов
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS log_files (
                    id VARCHAR(255) PRIMARY KEY,
                    original_name VARCHAR(500) NOT NULL,
                    file_path TEXT NOT NULL,
                    file_type VARCHAR(50),
                    file_size BIGINT,
                    upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    parent_file_id VARCHAR(255),
                    FOREIGN KEY (parent_file_id) REFERENCES log_files(id) ON DELETE CASCADE
                )
            ''')

            # Создаем таблицу пресетов анализа
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS analysis_presets (
                    id VARCHAR(255) PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    description TEXT,
                    system_context TEXT,
                    questions JSONB,
                    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_default BOOLEAN DEFAULT FALSE
                )
            ''')

            # Создаем таблицу пользовательских настроек анализа
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS custom_analysis_settings (
                    id VARCHAR(255) PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    pattern TEXT NOT NULL,
                    description TEXT,
                    enabled BOOLEAN DEFAULT TRUE,
                    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Создаем таблицу отфильтрованных файлов
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS filtered_files (
                    id VARCHAR(255) PRIMARY KEY,
                    original_file_id VARCHAR(255) NOT NULL,
                    filtered_file_path TEXT NOT NULL,
                    filter_settings JSONB,
                    lines_count INTEGER,
                    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (original_file_id) REFERENCES log_files(id) ON DELETE CASCADE
                )
            ''')

            # Вставляем настройки по умолчанию
            default_settings = {
                'max_file_size_mb': 100,
                'supported_formats': ['.log', '.txt', '.csv', '.json', '.xml', '.zip', '.tar', '.gz', '.bz2', '.xz'],
                'extract_nested_archives': True,
                'max_extraction_depth': 5,
                'max_filtering_file_size_mb': 50,  # Максимальный размер файла для автоматической фильтрации
                'important_log_levels': ['ERROR', 'WARN', 'CRITICAL', 'FATAL', 'ALERT', 'EMERGENCY', 'INFO', 'DEBUG'],
                'enable_ml_analysis': True
            }

            for key, value in default_settings.items():
                # Для всех настроек используем DO NOTHING, чтобы сохранить пользовательские изменения
                await conn.execute('''
                    INSERT INTO settings (key, value) VALUES ($1, $2)
                    ON CONFLICT (key) DO NOTHING
                ''', key, json.dumps(value))

            # Создаем пресет по умолчанию
            default_preset = {
                'id': str(uuid.uuid4()),
                'name': 'Общий анализ логов',
                'description': 'Базовый анализ логов для выявления ошибок и предупреждений',
                'system_context': 'Система логирования',
                'questions': [
                    'Какие ошибки наиболее часто встречаются в логах?',
                    'Есть ли критические проблемы, требующие немедленного внимания?',
                    'Какие паттерны в логах указывают на проблемы производительности?',
                    'Есть ли признаки атак или подозрительной активности?'
                ],
                'is_default': True
            }

            await conn.execute('''
                INSERT INTO analysis_presets (id, name, description, system_context, questions, is_default)
                VALUES ($1, $2, $3, $4, $5, $6)
                ON CONFLICT (id) DO NOTHING
            ''', default_preset['id'], default_preset['name'], default_preset['description'],
                 default_preset['system_context'], json.dumps(default_preset['questions']), default_preset['is_default'])

            # Добавляем пользовательские настройки анализа для MP SIEM
            mp_siem_settings = [
                {
                    'id': str(uuid.uuid4()),
                    'name': 'MP SIEM - Атаки и инциденты',
                    'pattern': r'(?i)(attack|intrusion|breach|compromise|malware|virus|trojan|ransomware|phishing|ddos|brute.?force|sql.?injection|xss|csrf)',
                    'description': 'Обнаружение признаков атак и инцидентов безопасности',
                    'enabled': True
                },
                {
                    'id': str(uuid.uuid4()),
                    'name': 'MP SIEM - Аутентификация',
                    'pattern': r'(?i)(login|logout|authentication|authorization|failed.?login|successful.?login|invalid.?credentials|password|session|token)',
                    'description': 'События аутентификации и авторизации',
                    'enabled': True
                },
                {
                    'id': str(uuid.uuid4()),
                    'name': 'MP SIEM - Сетевые события',
                    'pattern': r'(?i)(connection|disconnect|timeout|network|firewall|block|allow|port|ip|dns|dhcp|vpn)',
                    'description': 'Сетевые события и подключения',
                    'enabled': True
                },
                {
                    'id': str(uuid.uuid4()),
                    'name': 'MP SIEM - Системные ошибки',
                    'pattern': r'(?i)(error|exception|crash|failure|fatal|critical|emergency|panic|kernel|system|service|daemon)',
                    'description': 'Системные ошибки и критические события',
                    'enabled': True
                },
                {
                    'id': str(uuid.uuid4()),
                    'name': 'MP SIEM - Доступ к файлам',
                    'pattern': r'(?i)(file|directory|access|permission|read|write|delete|create|modify|upload|download|copy|move)',
                    'description': 'События доступа к файлам и директориям',
                    'enabled': True
                },
                {
                    'id': str(uuid.uuid4()),
                    'name': 'MP SIEM - База данных',
                    'pattern': r'(?i)(database|sql|query|transaction|commit|rollback|connection|deadlock|timeout|performance|slow|optimization)',
                    'description': 'События базы данных и SQL запросы',
                    'enabled': True
                },
                {
                    'id': str(uuid.uuid4()),
                    'name': 'MP SIEM - API и веб-сервисы',
                    'pattern': r'(?i)(api|rest|soap|http|https|request|response|status|code|endpoint|service|microservice)',
                    'description': 'API вызовы и веб-сервисы',
                    'enabled': True
                },
                {
                    'id': str(uuid.uuid4()),
                    'name': 'MP SIEM - Производительность',
                    'pattern': r'(?i)(performance|slow|timeout|latency|response.?time|throughput|memory|cpu|load|bottleneck|optimization)',
                    'description': 'События производительности системы',
                    'enabled': True
                },
                {
                    'id': str(uuid.uuid4()),
                    'name': 'MP SIEM - Конфигурация',
                    'pattern': r'(?i)(config|configuration|setting|parameter|option|property|environment|variable|init|startup|shutdown)',
                    'description': 'Изменения конфигурации и настроек',
                    'enabled': True
                },
                {
                    'id': str(uuid.uuid4()),
                    'name': 'MP SIEM - Резервное копирование',
                    'pattern': r'(?i)(backup|restore|recovery|snapshot|archive|sync|replication|mirror|copy|export|import)',
                    'description': 'События резервного копирования и восстановления',
                    'enabled': True
                }
            ]

            # Проверяем, есть ли уже настройки MP SIEM
            existing_settings = await conn.fetch('''
                SELECT COUNT(*) as count FROM loganalizer.custom_analysis_settings 
                WHERE name LIKE 'MP SIEM - %'
            ''')
            
            if existing_settings[0]['count'] == 0:
                # Добавляем настройки только если их еще нет
                for setting in mp_siem_settings:
                    await conn.execute('''
                        INSERT INTO loganalizer.custom_analysis_settings (id, name, pattern, description, enabled)
                        VALUES ($1, $2, $3, $4, $5)
                        ON CONFLICT (id) DO NOTHING
                    ''', setting['id'], setting['name'], setting['pattern'], 
                         setting['description'], setting['enabled'])
                print("✅ MP SIEM настройки добавлены")
            else:
                print("ℹ️ MP SIEM настройки уже существуют, пропускаем")

    async def get_settings(self) -> Dict:
        """Получение настроек"""
        pool = await self.get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch('SELECT key, value FROM loganalizer.settings')
            settings = {}
            for row in rows:
                try:
                    settings[row['key']] = json.loads(row['value'])
                except:
                    settings[row['key']] = row['value']
            print(f"🔍 Database settings loaded: {settings}")
            return settings

    async def update_settings(self, settings: Dict):
        """Обновление настроек"""
        pool = await self.get_pool()
        async with pool.acquire() as conn:
            for key, value in settings.items():
                await conn.execute('''
                    INSERT INTO loganalizer.settings (key, value) VALUES ($1, $2)
                    ON CONFLICT (key) DO UPDATE SET value = $2, updated_at = CURRENT_TIMESTAMP
                ''', key, json.dumps(value))
            print(f"💾 Settings updated in database: {settings}")

    async def insert_log_file(self, file_data: Dict):
        """Вставка информации о файле лога"""
        pool = await self.get_pool()
        async with pool.acquire() as conn:
            await conn.execute('''
                INSERT INTO loganalizer.log_files (id, original_name, file_path, file_type, file_size, upload_date, parent_file_id)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
            ''', file_data['id'], file_data['original_name'], file_data['file_path'],
                 file_data['file_type'], file_data['file_size'], file_data['upload_date'],
                 file_data.get('parent_file_id'))

    async def insert_log_files_batch(self, files_data: List[Dict]):
        """Batch вставка информации о файлах логов"""
        pool = await self.get_pool()
        async with pool.acquire() as conn:
            # Подготавливаем данные для batch insert
            values = []
            for file_data in files_data:
                values.append((
                    file_data['id'], file_data['original_name'], file_data['file_path'],
                    file_data['file_type'], file_data['file_size'], file_data['upload_date'],
                    file_data.get('parent_file_id')
                ))
            
            # Выполняем batch insert
            await conn.executemany('''
                INSERT INTO loganalizer.log_files (id, original_name, file_path, file_type, file_size, upload_date, parent_file_id)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
            ''', values)

    async def get_log_files(self) -> List[Dict]:
        """Получение списка файлов логов с информацией о фильтрации"""
        pool = await self.get_pool()
        async with pool.acquire() as conn:
            # Получаем все файлы
            rows = await conn.fetch('''
                SELECT id, original_name, file_path, file_type, file_size, upload_date, parent_file_id
                FROM loganalizer.log_files ORDER BY upload_date DESC
            ''')
            
            files = []
            for row in rows:
                file_data = dict(row)
                
                # Проверяем, есть ли отфильтрованная версия файла
                filtered_row = await conn.fetchrow('''
                    SELECT id FROM loganalizer.filtered_files WHERE original_file_id = $1
                ''', file_data['id'])
                
                file_data['has_filtered_version'] = filtered_row is not None
                files.append(file_data)
            
            return files

    async def get_log_file(self, file_id: str) -> Optional[Dict]:
        """Получение информации о конкретном файле"""
        pool = await self.get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow('''
                SELECT id, original_name, file_path, file_type, file_size, upload_date, parent_file_id
                FROM loganalizer.log_files WHERE id = $1
            ''', file_id)
            return dict(row) if row else None

    async def delete_log_file(self, file_id: str):
        """Удаление файла лога"""
        pool = await self.get_pool()
        async with pool.acquire() as conn:
            await conn.execute('DELETE FROM loganalizer.log_files WHERE id = $1', file_id)

    async def clear_log_files(self):
        """Очистка всех файлов логов"""
        pool = await self.get_pool()
        async with pool.acquire() as conn:
            await conn.execute('DELETE FROM loganalizer.log_files')

    async def get_presets(self) -> List[Dict]:
        """Получение пресетов анализа"""
        pool = await self.get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch('''
                SELECT id, name, description, system_context, questions, created_date, is_default
                FROM loganalizer.analysis_presets ORDER BY is_default DESC, created_date DESC
            ''')
            presets = []
            for row in rows:
                preset = dict(row)
                preset['questions'] = json.loads(preset['questions'])
                presets.append(preset)
            return presets

    async def create_preset(self, preset_data: Dict) -> str:
        """Создание нового пресета"""
        preset_id = str(uuid.uuid4())
        pool = await self.get_pool()
        async with pool.acquire() as conn:
            await conn.execute('''
                INSERT INTO loganalizer.analysis_presets (id, name, description, system_context, questions)
                VALUES ($1, $2, $3, $4, $5)
            ''', preset_id, preset_data['name'], preset_data['description'],
                 preset_data['system_context'], json.dumps(preset_data['questions']))
        return preset_id

    async def get_custom_analysis_settings(self) -> List[Dict]:
        """Получение пользовательских настроек анализа"""
        pool = await self.get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch('''
                SELECT id, name, pattern, description, enabled, created_date
                FROM loganalizer.custom_analysis_settings ORDER BY created_date DESC
            ''')
            return [dict(row) for row in rows]

    async def create_custom_analysis_setting(self, setting_data: Dict) -> str:
        """Создание новой пользовательской настройки анализа"""
        pool = await self.get_pool()
        async with pool.acquire() as conn:
            setting_id = str(uuid.uuid4())
            await conn.execute('''
                INSERT INTO loganalizer.custom_analysis_settings (id, name, pattern, description, enabled)
                VALUES ($1, $2, $3, $4, $5)
            ''', setting_id, setting_data['name'], setting_data['pattern'],
                 setting_data.get('description'), setting_data.get('enabled', True))
            return setting_id

    async def update_custom_analysis_setting(self, setting_id: str, setting_data: Dict):
        """Обновление пользовательской настройки анализа"""
        pool = await self.get_pool()
        async with pool.acquire() as conn:
            await conn.execute('''
                UPDATE loganalizer.custom_analysis_settings 
                SET name = $2, pattern = $3, description = $4, enabled = $5
                WHERE id = $1
            ''', setting_id, setting_data['name'], setting_data['pattern'],
                 setting_data.get('description'), setting_data.get('enabled', True))

    async def delete_custom_analysis_setting(self, setting_id: str):
        """Удаление пользовательской настройки анализа"""
        pool = await self.get_pool()
        async with pool.acquire() as conn:
            await conn.execute('DELETE FROM loganalizer.custom_analysis_settings WHERE id = $1', setting_id)

    async def insert_filtered_file(self, filtered_file_data: Dict):
        """Вставка информации об отфильтрованном файле"""
        try:
            print(f"💾 Inserting filtered file data: {filtered_file_data}")
            pool = await self.get_pool()
            async with pool.acquire() as conn:
                await conn.execute('''
                    INSERT INTO loganalizer.filtered_files (id, original_file_id, filtered_file_path, filter_settings, lines_count)
                    VALUES ($1, $2, $3, $4, $5)
                ''', filtered_file_data['id'], filtered_file_data['original_file_id'],
                     filtered_file_data['filtered_file_path'], json.dumps(filtered_file_data['filter_settings']),
                     filtered_file_data['lines_count'])
            print(f"✅ Successfully inserted filtered file data")
        except Exception as e:
            print(f"❌ Error inserting filtered file data: {e}")
            raise

    async def get_filtered_file(self, original_file_id: str) -> Optional[Dict]:
        """Получение информации об отфильтрованном файле"""
        pool = await self.get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow('''
                SELECT id, original_file_id, filtered_file_path, filter_settings, lines_count, created_date
                FROM loganalizer.filtered_files WHERE original_file_id = $1
            ''', original_file_id)
            if row:
                result = dict(row)
                result['filter_settings'] = json.loads(row['filter_settings'])
                return result
            return None

    async def delete_filtered_file(self, original_file_id: str):
        """Удаление отфильтрованного файла"""
        pool = await self.get_pool()
        async with pool.acquire() as conn:
            await conn.execute('DELETE FROM loganalizer.filtered_files WHERE original_file_id = $1', original_file_id)

    async def close(self):
        """Закрытие соединения с базой данных"""
        if self.pool:
            await self.pool.close() 