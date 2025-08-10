import requests
import csv
import io
from typing import Dict, List, Any, Optional
from urllib.parse import quote
import re

class VMMaxPatrolIntegration:
    """Интеграция с MaxPatrol VM для импорта хостов"""
    
    def __init__(self, host: str, username: str, password: str, client_secret: str):
        self.host = host
        self.username = username
        self.password = password
        self.client_secret = client_secret
        self.token = None
        
    def get_token(self) -> Optional[str]:
        """Получить токен аутентификации"""
        try:
            url = f'https://{self.host}:3334/connect/token'
            
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded'
            }
            
            data = {
                'username': self.username,
                'password': self.password,
                'client_id': 'mpx',
                'client_secret': self.client_secret,
                'grant_type': 'password',
                'response_type': 'code id_token',
                'scope': 'offline_access mpx.api'
            }
            
            response = requests.post(url, headers=headers, data=data, verify=False, timeout=30)
            response.raise_for_status()
            
            token_data = response.json()
            self.token = token_data.get('access_token')
            return self.token
            
        except Exception as e:
            print(f"Error getting VM token: {e}")
            return None
    
    def get_hosts_data(self, os_filter: str = None, limit: int = 0) -> List[Dict[str, str]]:
        """Получить данные хостов из VM"""
        try:
            if not self.token:
                if not self.get_token():
                    raise Exception("Failed to get authentication token")
            
            # Формируем PDQL запрос с фильтрацией по ОС
            
            # Базовые фильтры ОС (всегда применяются)
            base_os_filters = [
                "Host.OsName != 'Windows 7'",
                "Host.OsName != 'Windows 10'", 
                "Host.OsName != 'ESXi'",
                "Host.OsName != 'IOS'",
                "Host.OsName != 'NX-OS'",
                "Host.OsName != 'IOS XE'",
                "Host.OsName != 'FreeBSD'"
            ]
            
            # Пользовательские фильтры ОС (из настроек)
            user_os_filters = []
            if os_filter:
                os_list = [os.strip() for os in os_filter.split(',') if os.strip()]
                for os_name in os_list:
                    user_os_filters.append(f"Host.OsName != '{os_name}'")
            
            # Объединяем все фильтры
            all_os_filters = base_os_filters + user_os_filters
            os_filter_conditions = " and ".join(all_os_filters)
            
            pdql_query = f"""select(@Host, Host.OsName, Host.@Vulners.CVEs, host.UF_Criticality, Host.UF_Zone) 
            | filter(   Host.OsName != null 
                    and {os_filter_conditions}) 
            | limit({limit})"""
            
            # Первый запрос для получения токена
            url = f'https://{self.host}/api/assets_temporal_readmodel/v1/assets_grid'
            params = {
                'pdql': pdql_query,
                'includeNestedGroups': False
            }
            
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {self.token}'
            }
            
            response = requests.post(url, headers=headers, json=params, verify=False, timeout=30)
            response.raise_for_status()
            
            token_data = response.json()
            token_vm = token_data.get('token')
            
            if not token_vm:
                raise Exception("Failed to get VM query token")
            
            # Второй запрос для получения данных
            token_vm_urlencoded = quote(token_vm, safe='')
            export_url = f'https://{self.host}/api/assets_temporal_readmodel/v1/assets_grid/export?pdqlToken={token_vm_urlencoded}'
            
            response = requests.get(export_url, headers=headers, verify=False, timeout=60)
            response.raise_for_status()
            
            # Парсим CSV данные
            csv_data = response.text
            hosts_data = self._parse_csv_data(csv_data)
            
            return hosts_data
            
        except Exception as e:
            print(f"Error getting VM hosts data: {e}")
            raise
    
    def _parse_csv_data(self, csv_data: str) -> List[Dict[str, str]]:
        """Парсить CSV данные в список словарей"""
        hosts_data = []
        
        try:
            # Создаем StringIO объект для парсинга CSV
            csv_file = io.StringIO(csv_data)
            reader = csv.DictReader(csv_file, delimiter=';')
            
            for row in reader:
                # Очищаем данные от кавычек
                hostname = row.get('@Host', '').strip('"')
                os_name = row.get('Host.OsName', '').strip('"')
                cve = row.get('Host.@Vulners.CVEs', '').strip('"')
                criticality = row.get('host.UF_Criticality', '').strip('"')
                zone = row.get('Host.UF_Zone', '').strip('"')
                
                # Пропускаем строки без CVE
                if not cve or cve == '""':
                    continue
                
                # Если у хоста несколько CVE, создаем отдельную запись для каждого
                cve_list = [c.strip() for c in cve.split(',') if c.strip()]
                
                for single_cve in cve_list:
                    # Очищаем CVE от лишних символов
                    clean_cve = re.sub(r'[^\w\-]', '', single_cve)
                    if clean_cve.startswith('CVE-'):
                        hosts_data.append({
                            'hostname': hostname,
                            'os_name': os_name,
                            'cve': clean_cve,
                            'criticality': criticality,
                            'zone': zone
                        })
            
            print(f"Parsed {len(hosts_data)} host-CVE combinations from VM")
            return hosts_data
            
        except Exception as e:
            print(f"Error parsing CSV data: {e}")
            return []
    
    def test_connection(self) -> Dict[str, Any]:
        """Тестировать подключение к VM"""
        try:
            if not self.get_token():
                return {
                    'success': False,
                    'error': 'Failed to get authentication token'
                }
            
            # Пробуем получить небольшое количество данных для теста
            test_hosts = self.get_hosts_data()
            
            return {
                'success': True,
                'message': f'Successfully connected to VM. Found {len(test_hosts)} host-CVE combinations',
                'sample_count': len(test_hosts)
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_connection_info(self) -> Dict[str, str]:
        """Получить информацию о подключении"""
        return {
            'host': self.host,
            'username': self.username,
            'has_password': 'Yes' if self.password else 'No',
            'has_client_secret': 'Yes' if self.client_secret else 'No',
            'has_token': 'Yes' if self.token else 'No'
        }
