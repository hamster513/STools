"""
Database package for vulnanalizer
"""
from .base import DatabaseBase
from .epss_repository import EPSSRepository
from .exploitdb_repository import ExploitDBRepository
from .cve_repository import CVERepository
from .hosts_repository import HostsRepository
from .background_tasks_repository import BackgroundTasksRepository
from .settings_repository import SettingsRepository
from .hosts_update_service import HostsUpdateService
from .metasploit_repository import MetasploitRepository

# Класс Database для обратной совместимости
class Database:
    """Класс Database для обратной совместимости"""
    
    def __init__(self):
        self._db = NewDatabase()
    
    def __getattr__(self, name):
        """Делегируем все атрибуты к новому Database"""
        return getattr(self._db, name)

class NewDatabase:
        def __init__(self):
            self.hosts = HostsRepository()
            self.epss = EPSSRepository()
            self.exploitdb = ExploitDBRepository()
            self.cve = CVERepository()
            self.metasploit = MetasploitRepository()
            self.background_tasks = BackgroundTasksRepository()
            self.settings = SettingsRepository()
            self.hosts_update = HostsUpdateService()
        
        async def get_connection(self):
            """Получить соединение из базового класса"""
            return await self.hosts.get_connection()
        
        async def release_connection(self, conn):
            """Освободить соединение"""
            await self.hosts.release_connection(conn)
        
        async def test_connection(self):
            """Тестировать соединение"""
            return await self.hosts.test_connection()
        
        # Методы для обратной совместимости
        async def get_settings(self):
            """Получить настройки"""
            return await self.settings.get_settings()
        
        async def update_settings(self, settings):
            """Обновить настройки"""
            return await self.settings.update_settings(settings)
        
        async def insert_hosts_records_with_progress(self, records, progress_callback=None):
            """Вставить записи хостов с прогрессом"""
            return await self.hosts.insert_hosts_records_with_progress(records, progress_callback)
        
        async def insert_hosts_records_with_duplicate_check(self, records, progress_callback=None):
            """Вставить записи хостов с проверкой дублей"""
            return await self.hosts.insert_hosts_records_with_duplicate_check(records, progress_callback)
        
        async def get_hosts_count(self):
            """Получить количество хостов"""
            return await self.hosts.get_hosts_count()
        
        async def count_hosts_records(self):
            """Подсчитать количество записей хостов (для обратной совместимости)"""
            return await self.hosts.get_hosts_count()
        
        async def search_hosts(self, **kwargs):
            """Поиск хостов (пока используем старый метод)"""
            # Временно используем старый метод
            import sys
            import os
            parent_dir = os.path.dirname(os.path.dirname(__file__))
            if parent_dir not in sys.path:
                sys.path.insert(0, parent_dir)
            
            import importlib.util
            spec = importlib.util.spec_from_file_location("old_database", os.path.join(parent_dir, "database.py"))
            old_database = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(old_database)
            
            old_db = old_database.get_db()
            return await old_db.search_hosts(**kwargs)
        
        
        async def insert_exploitdb_records(self, records):
            """Вставить записи ExploitDB"""
            return await self.exploitdb.insert_exploitdb_records(records)
        
        async def insert_cve_records(self, records):
            """Вставить записи CVE"""
            return await self.cve.insert_cve_records(records)
        
        async def get_background_task_by_type(self, task_type: str):
            """Получить последнюю фоновую задачу определенного типа"""
            return await self.background_tasks.get_background_task_by_type(task_type)
        
        async def cancel_background_task(self, task_type: str):
            """Отменить фоновую задачу по типу"""
            return await self.background_tasks.cancel_background_task(task_type)
        
        async def get_background_tasks_by_status(self, status: str):
            """Получить задачи по статусу"""
            return await self.background_tasks.get_background_tasks_by_status(status)
        
        async def count_epss_records(self):
            """Подсчитать количество записей EPSS"""
            return await self.epss.count_epss_records()
        
        async def count_exploitdb_records(self):
            """Подсчитать количество записей ExploitDB"""
            return await self.exploitdb.count_exploitdb_records()
        
        async def count_cve_records(self):
            """Подсчитать количество записей CVE"""
            return await self.cve.count_cve_records()
        
        async def create_background_task(self, task_type: str, parameters: dict = None, description: str = None):
            """Создать новую фоновую задачу"""
            return await self.background_tasks.create_task(task_type, description, parameters)
        
        async def update_background_task(self, task_id: int, conn=None, **kwargs):
            """Обновить статус фоновой задачи
            
            Args:
                task_id: ID задачи
                conn: Опциональное существующее подключение
                **kwargs: Поля для обновления
            """
            return await self.background_tasks.update_task(task_id, conn=conn, **kwargs)

        async def get_background_task(self, task_id: int):
            """Получить фоновую задачу по ID"""
            return await self.background_tasks.get_task(task_id)

        async def get_epss_by_cve(self, cve_id: str):
            """Получить данные EPSS по CVE ID"""
            return await self.epss.get_epss_by_cve(cve_id)

        async def search_epss(self, **kwargs):
            """Поиск EPSS данных"""
            return await self.epss.search_epss(**kwargs)

        async def update_hosts_epss_and_exploits_background(self, progress_callback=None):
            """Обновить EPSS и ExploitDB данные для хостов"""
            return await self.hosts_update.update_hosts_complete(progress_callback)

        async def get_exploitdb_by_cve(self, cve_id: str):
            """Получить данные ExploitDB по CVE ID"""
            return await self.exploitdb.get_exploitdb_by_cve(cve_id)

        async def get_cve_by_id(self, cve_id: str):
            """Получить данные CVE по ID"""
            return await self.cve.get_cve_by_id(cve_id)

        async def search_hosts(self, **kwargs):
            """Поиск хостов"""
            return await self.hosts.search_hosts(**kwargs)

        async def get_host_by_id(self, host_id: int):
            """Получить хост по ID"""
            return await self.hosts.get_host_by_id(host_id)

        async def clear_hosts(self):
            """Очистка таблицы хостов"""
            return await self.hosts.clear_hosts()

        async def clear_epss(self):
            """Очистка таблицы EPSS"""
            return await self.epss.clear_epss()

        async def clear_exploitdb(self):
            """Очистка таблицы ExploitDB"""
            return await self.exploitdb.clear_exploitdb()

        async def clear_cve(self):
            """Очистка таблицы CVE"""
            return await self.cve.clear_cve()

        async def insert_metasploit_modules(self, records):
            """Вставить записи Metasploit"""
            return await self.metasploit.insert_modules(records)

        async def count_metasploit_modules(self):
            """Получить количество записей Metasploit"""
            return await self.metasploit.get_modules_count()

        async def clear_metasploit_data(self):
            """Очистка таблицы Metasploit"""
            return await self.metasploit.clear_all_data()

        async def get_vm_settings(self):
            """Получить настройки VM MaxPatrol"""
            return await self.settings.get_vm_settings()

        async def update_vm_settings(self, settings):
            """Обновить настройки VM MaxPatrol"""
            return await self.settings.update_vm_settings(settings)

        async def import_vm_hosts(self, hosts_data):
            """Импортировать хосты из VM MaxPatrol"""
            return await self.hosts.import_vm_hosts(hosts_data)

        async def get_vm_import_status(self):
            """Получить статус последнего импорта VM"""
            return await self.hosts.get_vm_import_status()

        async def update_vm_import_status(self, count, error=None):
            """Обновить статус импорта VM"""
            return await self.hosts.update_vm_import_status(count, error)

        async def update_hosts_complete(self, progress_callback=None):
            """Полное обновление хостов: EPSS, CVSS, ExploitDB, Metasploit"""
            return await self.hosts_update.update_hosts_complete(progress_callback)


# Функция get_db для обратной совместимости
def get_db():
    """Получить экземпляр базы данных с новыми репозиториями"""
    return NewDatabase()

__all__ = [
    'DatabaseBase',
    'EPSSRepository', 
    'ExploitDBRepository',
    'CVERepository',
    'HostsRepository',
    'BackgroundTasksRepository',
    'SettingsRepository',
    'HostsUpdateService',
    'Database',
    'get_db'
]
