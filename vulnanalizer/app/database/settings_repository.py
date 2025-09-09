"""
Repository for settings operations
"""
from typing import Dict, Any
from .base import DatabaseBase


class SettingsRepository(DatabaseBase):
    """Repository for settings operations"""
    
    async def get_settings(self) -> Dict[str, str]:
        """Получить все настройки"""
        conn = await self.get_connection()
        try:
            query = "SELECT key, value FROM vulnanalizer.settings"
            rows = await conn.fetch(query)
            
            settings = {}
            for row in rows:
                settings[row['key']] = row['value']
            
            # Устанавливаем значения по умолчанию
            defaults = {
                'max_concurrent_requests': '3',
                'risk_threshold': '75',
                # Impact настройки
                'impact_resource_criticality_critical': '0.33',
                'impact_resource_criticality_high': '0.25',
                'impact_resource_criticality_medium': '0.2',
                'impact_resource_criticality_none': '0.2',
                'impact_confidential_data_yes': '0.33',
                'impact_confidential_data_no': '0.2',
                'impact_internet_access_yes': '0.33',
                'impact_internet_access_no': '0.2',
                # ExploitDB настройки
                'exploitdb_remote': '0.8',
                'exploitdb_webapps': '0.85',
                'exploitdb_dos': '0.8',
                'exploitdb_local': '0.9',
                'exploitdb_hardware': '0.7',
                # Metasploit настройки
                'metasploit_excellent': '1.3',
                'metasploit_good': '1.1',
                'metasploit_normal': '1.0',
                'metasploit_average': '0.9',
                'metasploit_low': '0.8',
                'metasploit_unknown': '1.0',
                'metasploit_manual': '0.7',
                # CVSS v3 настройки
                'cvss_v3_attack_vector_network': '1.20',
                'cvss_v3_attack_vector_adjacent': '1.10',
                'cvss_v3_attack_vector_local': '0.95',
                'cvss_v3_attack_vector_physical': '0.85',
                'cvss_v3_privileges_required_none': '1.20',
                'cvss_v3_privileges_required_low': '1.00',
                'cvss_v3_privileges_required_high': '0.85',
                'cvss_v3_user_interaction_none': '1.15',
                'cvss_v3_user_interaction_required': '0.90',
                # CVSS v2 настройки
                'cvss_v2_access_vector_network': '1.20',
                'cvss_v2_access_vector_adjacent_network': '1.10',
                'cvss_v2_access_vector_local': '0.95',
                'cvss_v2_access_complexity_low': '1.10',
                'cvss_v2_access_complexity_medium': '1.00',
                'cvss_v2_access_complexity_high': '0.90',
                'cvss_v2_authentication_none': '1.15',
                'cvss_v2_authentication_single': '1.00',
                'cvss_v2_authentication_multiple': '0.90'
            }
            
            for key, default_value in defaults.items():
                if key not in settings:
                    settings[key] = default_value
            
            return settings
        finally:
            await self.release_connection(conn)
    
    async def update_settings(self, settings: Dict[str, str]) -> bool:
        """Обновить настройки"""
        conn = await self.get_connection()
        try:
            for key, value in settings.items():
                # Конвертируем значение в строку, так как в БД поле value имеет тип text
                value_str = str(value) if value is not None else ""
                
                query = """
                    INSERT INTO vulnanalizer.settings (key, value) 
                    VALUES ($1, $2) 
                    ON CONFLICT (key) 
                    DO UPDATE SET value = $2, updated_at = CURRENT_TIMESTAMP
                """
                await conn.execute(query, key, value_str)
            return True
        finally:
            await self.release_connection(conn)
    
    async def get_setting(self, key: str, default: str = None) -> str:
        """Получить конкретную настройку"""
        conn = await self.get_connection()
        try:
            query = "SELECT value FROM vulnanalizer.settings WHERE key = $1"
            value = await conn.fetchval(query, key)
            return value if value is not None else default
        finally:
            await self.release_connection(conn)
    
    async def set_setting(self, key: str, value: str) -> bool:
        """Установить конкретную настройку"""
        conn = await self.get_connection()
        try:
            # Конвертируем значение в строку, так как в БД поле value имеет тип text
            value_str = str(value) if value is not None else ""
            
            query = """
                INSERT INTO vulnanalizer.settings (key, value) 
                VALUES ($1, $2) 
                ON CONFLICT (key) 
                DO UPDATE SET value = $2, updated_at = CURRENT_TIMESTAMP
            """
            await conn.execute(query, key, value_str)
            return True
        finally:
            await self.release_connection(conn)

    async def get_vm_settings(self) -> Dict[str, str]:
        """Получить настройки VM MaxPatrol"""
        conn = await self.get_connection()
        try:
            query = "SELECT key, value FROM vulnanalizer.settings WHERE key LIKE 'vm_%'"
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
                'vm_os_filter': 'Windows 7,Windows 10,ESXi,IOS,NX-OS,IOS XE,FreeBSD',
                'vm_limit': '0',
                'vm_detailed_logging': 'false'
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
                    # Конвертируем значение в строку, так как в БД поле value имеет тип text
                    value_str = str(value) if value is not None else ""
                    
                    query = """
                        INSERT INTO vulnanalizer.settings (key, value) 
                        VALUES ($1, $2) 
                        ON CONFLICT (key) 
                        DO UPDATE SET value = $2, updated_at = CURRENT_TIMESTAMP
                    """
                    await conn.execute(query, key, value_str)
        finally:
            await self.release_connection(conn)
