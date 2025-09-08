"""
VM MaxPatrol Worker для импорта данных
"""
import csv
import io
import requests
from typing import Dict, List, Any, Optional
from datetime import datetime
from database import get_db
from database.risk_calculation import calculate_risk_score
import traceback


class VMWorker:
    """Worker для импорта данных из VM MaxPatrol"""
    
    def __init__(self):
        self.db = get_db()
        self.is_running = True
    
    async def start_import(self, task_id: int, parameters: Dict[str, Any]) -> Dict:
        """Запустить импорт данных из VM MaxPatrol"""
        try:
            print(f"🚀 Начинаем импорт VM данных для задачи {task_id}")
            
            # Обновляем статус
            await self.db.update_background_task(task_id, **{
                'status': 'processing',
                'current_step': 'Инициализация импорта VM'
            })
            
            # Получаем настройки VM
            vm_settings = await self.db.get_vm_settings()
            
            if not vm_settings.get('vm_host') or not vm_settings.get('vm_username'):
                raise Exception("Настройки VM MaxPatrol не настроены")
            
            # Получаем токен аутентификации
            await self.db.update_background_task(task_id, **{
                'current_step': 'Аутентификация в VM MaxPatrol'
            })
            
            token = await self._get_vm_token(
                vm_settings['vm_host'],
                vm_settings['vm_username'],
                vm_settings['vm_password'],
                vm_settings['vm_client_secret']
            )
            
            # Получаем данные из VM API
            await self.db.update_background_task(task_id, **{
                'current_step': 'Получение данных из VM API'
            })
            
            vm_data = await self._get_vm_data(
                vm_settings['vm_host'],
                token,
                vm_settings
            )
            
            if not vm_data:
                raise Exception("Не удалось получить данные из VM API")
            
            # Группируем данные по хостам
            await self.db.update_background_task(task_id, **{
                'current_step': 'Группировка данных по хостам'
            })
            
            grouped_hosts = self._group_vm_data_by_hosts(vm_data)
            
            # Обновляем общее количество записей
            await self.db.update_background_task(task_id, **{
                'total_records': len(grouped_hosts),
                'processed_records': 0
            })
            
            # Сохраняем в базу данных с расчетом рисков
            await self.db.update_background_task(task_id, **{
                'current_step': 'Сохранение в базу данных с расчетом рисков'
            })
            
            result = await self._save_hosts_with_risks(task_id, grouped_hosts)
            
            # Завершение
            await self.db.update_background_task(task_id, **{
                'status': 'completed',
                'current_step': 'Импорт VM данных завершен',
                'processed_records': len(grouped_hosts),
                'total_records': len(grouped_hosts),
                'end_time': datetime.now()
            })
            
            print(f"✅ Импорт VM данных завершен: {len(grouped_hosts)} хостов")
            return {
                "success": True,
                "count": len(grouped_hosts),
                "message": f"Импортировано {len(grouped_hosts)} хостов из VM MaxPatrol"
            }
            
        except Exception as e:
            error_msg = f"Ошибка импорта VM данных: {str(e)}"
            print(f"❌ {error_msg}")
            print(f"❌ Traceback: {traceback.format_exc()}")
            
            await self.db.update_background_task(task_id, **{
                'status': 'error',
                'error_message': error_msg,
                'end_time': datetime.now()
            })
            
            return {"success": False, "message": error_msg}
    
    async def _get_vm_token(self, host: str, username: str, password: str, client_secret: str) -> str:
        """Получить токен аутентификации для VM MaxPatrol"""
        try:
            url = f'https://{host}:3334/connect/token'
            
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded'
            }
            
            data = {
                'username': username,
                'password': password,
                'client_id': 'mpx',
                'client_secret': client_secret,
                'grant_type': 'password',
                'response_type': 'code id_token',
                'scope': 'offline_access mpx.api'
            }
            
            response = requests.post(url, headers=headers, data=data, verify=False, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            if 'access_token' not in result:
                raise Exception(f"Токен не получен: {result}")
                
            return result['access_token']
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"Ошибка HTTP запроса: {str(e)}")
        except Exception as e:
            raise Exception(f"Ошибка получения токена: {str(e)}")
    
    async def _get_vm_data(self, host: str, token: str, settings: Dict[str, str]) -> List[Dict[str, str]]:
        """Получить данные из VM API"""
        try:
            # Получаем лимит из настроек
            vm_limit = int(settings.get('vm_limit', 0))
            
            # Формируем PDQL запрос
            if vm_limit > 0:
                pdql = f'select(@Host, Host.OsName, Host.@Groups, Host.@Vulners.CVEs) | limit({vm_limit})'
            else:
                pdql = 'select(@Host, Host.OsName, Host.@Groups, Host.@Vulners.CVEs) | limit(0)'
            
            # Добавляем фильтр по ОС если настроен
            os_filter = settings.get('vm_os_filter', '').strip()
            if os_filter:
                os_list = [os.strip() for os in os_filter.split(',') if os.strip()]
                if os_list:
                    os_conditions = ' or '.join([f'Host.OsName != "{os}"' for os in os_list])
                    pdql = f'select(@Host, Host.OsName, Host.@Groups, Host.@Vulners.CVEs) | filter({os_conditions}) | limit({vm_limit if vm_limit > 0 else 0})'
            
            url = f'https://{host}/api/assets_temporal_readmodel/v1/assets_grid'
            params = {
                'pdql': pdql,
                'includeNestedGroups': False
            }
            
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {token}'
            }
            
            # Делаем запрос для получения токена экспорта
            response = requests.post(url, headers=headers, json=params, verify=False, timeout=60)
            response.raise_for_status()
            
            result = response.json()
            if 'token' not in result:
                raise Exception(f"Токен экспорта не получен: {result}")
            
            export_token = result['token']
            
            # Получаем CSV данные
            export_url = f'https://{host}/api/assets_temporal_readmodel/v1/assets_grid/export?pdqlToken={export_token}'
            export_response = requests.get(export_url, headers=headers, verify=False, timeout=300)
            export_response.raise_for_status()
            
            # Парсим CSV данные
            csv_content = export_response.text
            csv_reader = csv.DictReader(io.StringIO(csv_content), delimiter=';')
            
            vm_data = []
            for row in csv_reader:
                vm_data.append({
                    'host': row['@Host'].strip('"'),
                    'os_name': row['Host.OsName'].strip('"'),
                    'groups': row['Host.@Groups'].strip('"'),
                    'cve': row['Host.@Vulners.CVEs'].strip('"')
                })
            
            print(f"✅ Получено {len(vm_data)} записей из VM API")
            return vm_data
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"Ошибка HTTP запроса к VM API: {str(e)}")
        except Exception as e:
            raise Exception(f"Ошибка получения данных из VM API: {str(e)}")
    
    def _group_vm_data_by_hosts(self, vm_data: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        """Группировать данные VM по хостам"""
        hosts_dict = {}
        
        for record in vm_data:
            host_info = record['host']
            
            # Парсим hostname и IP
            if ' (' in host_info:
                hostname = host_info.split(' (')[0]
                ip_address = host_info.split('(')[1].split(')')[0]
            else:
                hostname = host_info
                ip_address = ''
            
            # Создаем ключ для группировки
            host_key = f"{hostname}_{ip_address}"
            
            if host_key not in hosts_dict:
                hosts_dict[host_key] = {
                    'hostname': hostname,
                    'ip_address': ip_address,
                    'os_name': record['os_name'],
                    'groups': record['groups'],
                    'cves': [],
                    'criticality': 'Medium',  # По умолчанию
                    'status': 'Active'
                }
            
            # Добавляем CVE если он не пустой
            if record['cve'] and record['cve'].strip():
                hosts_dict[host_key]['cves'].append(record['cve'])
        
        # Конвертируем в список
        grouped_hosts = list(hosts_dict.values())
        
        # Объединяем CVE в строку
        for host in grouped_hosts:
            host['cve'] = ','.join(host['cves'])
            del host['cves']  # Удаляем список CVE
        
        print(f"✅ Сгруппировано {len(grouped_hosts)} хостов из {len(vm_data)} записей")
        return grouped_hosts
    
    async def _save_hosts_with_risks(self, task_id: int, hosts: List[Dict[str, Any]]) -> Dict:
        """Сохранить хосты в базу данных с расчетом рисков"""
        try:
            # Получаем настройки для расчета рисков
            settings = await self.db.get_settings()
            
            # Создаем функцию обратного вызова для обновления прогресса
            async def update_progress(step, message, progress_percent, current_step_progress=None, processed_records=None):
                try:
                    await self.db.update_background_task(task_id, **{
                        'current_step': message,
                        'processed_records': processed_records or 0,
                        'progress_percent': progress_percent
                    })
                except Exception as e:
                    print(f"⚠️ Ошибка обновления прогресса: {e}")
            
            # Используем существующий метод для сохранения с расчетом рисков
            result = await self.db.insert_hosts_records_with_progress(hosts, update_progress)
            
            return result
            
        except Exception as e:
            raise Exception(f"Ошибка сохранения хостов: {str(e)}")
    
    def stop(self):
        """Остановить worker"""
        self.is_running = False
