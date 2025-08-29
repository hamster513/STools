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
            query = "SELECT key, value FROM settings"
            rows = await conn.fetch(query)
            
            settings = {}
            for row in rows:
                settings[row['key']] = row['value']
            
            # Устанавливаем значения по умолчанию
            defaults = {
                'max_concurrent_requests': '3',
                'impact_resource_criticality': 'Medium',
                'impact_confidential_data': 'Отсутствуют',
                'impact_internet_access': 'Недоступен',
                # CVSS v3 настройки
                'cvss_v3_attack_vector_network': '1.10',
                'cvss_v3_attack_vector_adjacent': '0.90',
                'cvss_v3_attack_vector_local': '0.60',
                'cvss_v3_attack_vector_physical': '0.30',
                'cvss_v3_privileges_required_none': '1.10',
                'cvss_v3_privileges_required_low': '0.70',
                'cvss_v3_privileges_required_high': '0.40',
                'cvss_v3_user_interaction_none': '1.10',
                'cvss_v3_user_interaction_required': '0.60',
                # CVSS v2 настройки
                'cvss_v2_access_vector_network': '1.10',
                'cvss_v2_access_vector_adjacent_network': '0.90',
                'cvss_v2_access_vector_local': '0.60',
                'cvss_v2_access_complexity_low': '1.10',
                'cvss_v2_access_complexity_medium': '0.80',
                'cvss_v2_access_complexity_high': '0.40',
                'cvss_v2_authentication_none': '1.10',
                'cvss_v2_authentication_single': '0.80',
                'cvss_v2_authentication_multiple': '0.40'
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
                query = """
                    INSERT INTO settings (key, value) 
                    VALUES ($1, $2) 
                    ON CONFLICT (key) 
                    DO UPDATE SET value = $2, updated_at = CURRENT_TIMESTAMP
                """
                await conn.execute(query, key, value)
            return True
        finally:
            await self.release_connection(conn)
    
    async def get_setting(self, key: str, default: str = None) -> str:
        """Получить конкретную настройку"""
        conn = await self.get_connection()
        try:
            query = "SELECT value FROM settings WHERE key = $1"
            value = await conn.fetchval(query, key)
            return value if value is not None else default
        finally:
            await self.release_connection(conn)
    
    async def set_setting(self, key: str, value: str) -> bool:
        """Установить конкретную настройку"""
        conn = await self.get_connection()
        try:
            query = """
                INSERT INTO settings (key, value) 
                VALUES ($1, $2) 
                ON CONFLICT (key) 
                DO UPDATE SET value = $2, updated_at = CURRENT_TIMESTAMP
            """
            await conn.execute(query, key, value)
            return True
        finally:
            await self.release_connection(conn)

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
