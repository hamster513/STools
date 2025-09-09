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
from services.simple_logging_service import simple_logging_service
import traceback


class VMWorker:
    """Worker для импорта данных из VM MaxPatrol"""
    
    def __init__(self):
        self.db = get_db()
        self.is_running = True
        self.logger = None
    
    async def _log(self, level: str, message: str, data: dict = None):
        """Вспомогательный метод для логирования"""
        if self.logger:
            if level == 'info':
                await self.logger.info(message, data)
            elif level == 'debug':
                await self.logger.debug(message, data)
            elif level == 'warning':
                await self.logger.warning(message, data)
            elif level == 'error':
                await self.logger.error(message, data)
    
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
            
            # Создаем логгер только если включено подробное логирование
            if vm_settings.get('vm_detailed_logging') == 'true':
                self.logger = await simple_logging_service.create_task_logger(task_id, 'vm_import')
                await self._log('info', "Начинаем импорт VM данных", {"task_id": task_id, "parameters": parameters})
                await self._log('debug', "Получены настройки VM", {"vm_host": vm_settings.get('vm_host'), "vm_username": vm_settings.get('vm_username')})
            
            if not vm_settings.get('vm_host') or not vm_settings.get('vm_username'):
                error_msg = "Настройки VM MaxPatrol не настроены"
                await self._log('error', error_msg, {"vm_settings": vm_settings})
                raise Exception(error_msg)
            
            # Получаем токен аутентификации
            await self.db.update_background_task(task_id, **{
                'current_step': 'Аутентификация в VM MaxPatrol'
            })
            await self._log('info', "Начинаем аутентификацию в VM MaxPatrol")
            
            token = await self._get_vm_token(
                vm_settings['vm_host'],
                vm_settings['vm_username'],
                vm_settings['vm_password'],
                vm_settings['vm_client_secret']
            )
            await self._log('info', "Аутентификация в VM MaxPatrol успешна")
            
            # Получаем данные из VM API
            await self.db.update_background_task(task_id, **{
                'current_step': 'Получение данных из VM API'
            })
            await self._log('info', "Начинаем получение данных из VM API")
            
            vm_data = await self._get_vm_data(
                vm_settings['vm_host'],
                token,
                vm_settings
            )
            
            if not vm_data:
                error_msg = "Не удалось получить данные из VM API"
                await self._log('error', error_msg)
                raise Exception(error_msg)
            
            await self._log('info', f"Получено {len(vm_data)} записей из VM API")
            
            # Группируем данные по хостам
            await self.db.update_background_task(task_id, **{
                'current_step': 'Группировка данных по хостам'
            })
            await self._log('info', "Начинаем группировку данных по хостам")
            
            grouped_hosts = self._group_vm_data_by_hosts(vm_data)
            await self._log('info', f"Сгруппировано {len(grouped_hosts)} хостов из {len(vm_data)} записей")
            
            # Обновляем общее количество записей
            await self.db.update_background_task(task_id, **{
                'total_records': len(grouped_hosts),
                'processed_records': 0
            })
            
            # Сохраняем в базу данных с расчетом рисков
            await self.db.update_background_task(task_id, **{
                'current_step': 'Сохранение в базу данных с расчетом рисков'
            })
            await self._log('info', "Начинаем сохранение хостов в базу данных с расчетом рисков")
            
            result = await self._save_hosts_with_risks(task_id, grouped_hosts)
            await self._log('info', "Сохранение хостов в базу данных завершено", {"result": result})
            
            # Завершение
            await self.db.update_background_task(task_id, **{
                'status': 'completed',
                'current_step': 'Импорт VM данных завершен',
                'processed_records': len(grouped_hosts),
                'total_records': len(grouped_hosts),
                'end_time': datetime.now()
            })
            
            await self._log('info', f"Импорт VM данных завершен успешно: {len(grouped_hosts)} хостов")
            print(f"✅ Импорт VM данных завершен: {len(grouped_hosts)} хостов")
            
            # Закрываем логгер
            if self.logger:
                await self.logger.close()
            
            return {
                "success": True,
                "count": len(grouped_hosts),
                "message": f"Импортировано {len(grouped_hosts)} хостов из VM MaxPatrol"
            }
            
        except Exception as e:
            error_msg = f"Ошибка импорта VM данных: {str(e)}"
            print(f"❌ {error_msg}")
            print(f"❌ Traceback: {traceback.format_exc()}")
            
            # Логируем ошибку
            await self._log('error', error_msg, {"traceback": traceback.format_exc()})
            if self.logger:
                await self.logger.close()
            
            await self.db.update_background_task(task_id, **{
                'status': 'error',
                'error_message': error_msg,
                'end_time': datetime.now()
            })
            
            return {"success": False, "message": error_msg}
    
    async def _get_vm_token(self, host: str, username: str, password: str, client_secret: str) -> str:
        """Получить токен аутентификации для VM MaxPatrol"""
        try:
            if self.logger:
                await self._log('debug', "Начинаем получение токена аутентификации", {"host": host, "username": username})
            
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
                error_msg = f"Токен не получен: {result}"
                if self.logger:
                    await self._log('error', error_msg, {"response": result})
                raise Exception(error_msg)
            
            if self.logger:
                await self._log('debug', "Токен аутентификации получен успешно")
                
            return result['access_token']
            
        except requests.exceptions.RequestException as e:
            error_msg = f"Ошибка HTTP запроса: {str(e)}"
            if self.logger:
                await self._log('error', error_msg)
            raise Exception(error_msg)
        except Exception as e:
            error_msg = f"Ошибка получения токена: {str(e)}"
            if self.logger:
                await self._log('error', error_msg)
            raise Exception(error_msg)
    
    async def _get_vm_data(self, host: str, token: str, settings: Dict[str, str]) -> List[Dict[str, str]]:
        """Получить данные из VM API"""
        try:
            await self._log('debug', "Начинаем получение данных из VM API", {"host": host})
            
            # Получаем лимит из настроек
            vm_limit = int(settings.get('vm_limit', 0))
            await self._log('debug', "Настройки VM", {"vm_limit": vm_limit, "os_filter": settings.get('vm_os_filter')})
            
            # Формируем PDQL запрос
            if vm_limit > 0:
                pdql = f'select(@Host, Host.OsName, Host.@Groups, Host.@Vulners.CVEs, Host.UF_Criticality, Host.UF_Zone) | limit({vm_limit})'
            else:
                pdql = 'select(@Host, Host.OsName, Host.@Groups, Host.@Vulners.CVEs, Host.UF_Criticality, Host.UF_Zone) | limit(0)'
            
            # Добавляем фильтр по ОС если настроен
            os_filter = settings.get('vm_os_filter', '').strip()
            if os_filter:
                os_list = [os.strip() for os in os_filter.split(',') if os.strip()]
                if os_list:
                    os_conditions = ' or '.join([f'Host.OsName != "{os}"' for os in os_list])
                    pdql = f'select(@Host, Host.OsName, Host.@Groups, Host.@Vulners.CVEs, Host.UF_Criticality, Host.UF_Zone) | filter({os_conditions}) | limit({vm_limit if vm_limit > 0 else 0})'
            
            if self.logger:
                await self._log('debug', "Сформирован PDQL запрос", {"pdql": pdql})
            
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
            if self.logger:
                await self._log('debug', "Отправляем запрос для получения токена экспорта")
            
            response = requests.post(url, headers=headers, json=params, verify=False, timeout=60)
            response.raise_for_status()
            
            result = response.json()
            if 'token' not in result:
                error_msg = f"Токен экспорта не получен: {result}"
                if self.logger:
                    await self._log('error', error_msg, {"response": result})
                raise Exception(error_msg)
            
            export_token = result['token']
            if self.logger:
                await self._log('debug', "Токен экспорта получен успешно")
            
            # Получаем CSV данные
            export_url = f'https://{host}/api/assets_temporal_readmodel/v1/assets_grid/export?pdqlToken={export_token}'
            if self.logger:
                await self._log('debug', "Запрашиваем CSV данные экспорта")
            
            export_response = requests.get(export_url, headers=headers, verify=False, timeout=300)
            export_response.raise_for_status()
            
            # Парсим CSV данные
            csv_content = export_response.text
            if self.logger:
                await self._log('debug', f"Получен CSV контент размером {len(csv_content)} символов")
            
            # CSV файл больше не сохраняем для дебага
            
            csv_reader = csv.DictReader(io.StringIO(csv_content), delimiter=';')
            
            vm_data = []
            row_count = 0
            for row in csv_reader:
                row_count += 1
                if self.logger and row_count <= 5:  # Логируем первые 5 строк для отладки
                    await self._log('debug', f"Строка {row_count}: {dict(row)}")
                
                vm_data.append({
                    'host': row['@Host'].strip('"'),
                    'os_name': row['Host.OsName'].strip('"'),
                    'groups': row['Host.@Groups'].strip('"'),
                    'cve': row['Host.@Vulners.CVEs'].strip('"'),
                    'criticality': row['Host.UF_Criticality'].strip('"'),
                    'zone': row['Host.UF_Zone'].strip('"')
                })
            
            if self.logger:
                await self._log('debug', f"Обработано {row_count} строк CSV, создано {len(vm_data)} записей")
            
            if self.logger:
                await self._log('info', f"Парсинг CSV завершен: {len(vm_data)} записей")
            
            print(f"✅ Получено {len(vm_data)} записей из VM API")
            return vm_data
            
        except requests.exceptions.RequestException as e:
            error_msg = f"Ошибка HTTP запроса к VM API: {str(e)}"
            if self.logger:
                await self._log('error', error_msg)
            raise Exception(error_msg)
        except Exception as e:
            error_msg = f"Ошибка получения данных из VM API: {str(e)}"
            if self.logger:
                await self._log('error', error_msg)
            raise Exception(error_msg)
    
    def _group_vm_data_by_hosts(self, vm_data: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        """Преобразует данные VM в формат для hosts_repository (один CVE = одна запись)"""
        result = []
        
        if self.logger:
            import asyncio
            asyncio.create_task(self.logger.debug(f"Начинаем преобразование {len(vm_data)} записей (один CVE = одна запись)"))
        
        for record in vm_data:
            host_info = record['host']
            
            # Парсим hostname и IP
            if ' (' in host_info:
                hostname = host_info.split(' (')[0]
                ip_address = host_info.split('(')[1].split(')')[0]
            else:
                hostname = host_info
                ip_address = ''
            
            # Получаем CVE
            cve = record['cve']
            if not cve or not cve.strip():
                continue
            
            # Создаем запись для каждого CVE
            result.append({
                'hostname': hostname,
                'ip_address': ip_address,
                'cve': cve,
                'cvss': 0.0,  # По умолчанию CVSS = 0
                'criticality': record.get('criticality', 'Medium'),  # Из Host.UF_Criticality
                'zone': record.get('zone', ''),  # Из Host.UF_Zone
                'status': 'Active'
            })
        
        if self.logger:
            import asyncio
            asyncio.create_task(self.logger.debug(f"Преобразование завершено: {len(result)} записей из {len(vm_data)} исходных"))
        
        print(f"✅ Преобразовано {len(result)} записей из {len(vm_data)} исходных (один CVE = одна запись)")
        return result
    
    async def _save_hosts_with_risks(self, task_id: int, hosts: List[Dict[str, Any]]) -> Dict:
        """Сохранить хосты в базу данных с расчетом рисков"""
        try:
            if self.logger:
                await self._log('debug', f"Начинаем сохранение {len(hosts)} хостов в базу данных")
                # Логируем первые 3 хоста для отладки
                for i, host in enumerate(hosts[:3]):
                    await self._log('debug', f"Хост {i+1}: {host}")
            
            # Получаем настройки для расчета рисков
            settings = await self.db.get_settings()
            if self.logger:
                await self._log('debug', "Получены настройки для расчета рисков", {"settings_keys": list(settings.keys())})
            
            # Создаем функцию обратного вызова для обновления прогресса
            async def update_progress(step, message, progress_percent, processed_records=None, current_step_progress=None, processed_cves=None):
                try:
                    # Используем processed_cves если processed_records не передан
                    records_count = processed_records or processed_cves or 0
                    
                    await self.db.update_background_task(task_id, **{
                        'current_step': message,
                        'processed_records': records_count,
                        'progress_percent': progress_percent
                    })
                    
                    # Логируем прогресс если включено подробное логирование
                    if self.logger and records_count and records_count % 100 == 0:
                        await self._log('debug', f"Прогресс сохранения: {records_count}/{len(hosts)} ({progress_percent}%)")
                        
                except Exception as e:
                    print(f"⚠️ Ошибка обновления прогресса: {e}")
                    if self.logger:
                        await self._log('warning', f"Ошибка обновления прогресса: {e}")
            
            # Используем существующий метод для сохранения с расчетом рисков
            if self.logger:
                await self._log('debug', "Вызываем insert_hosts_records_with_progress")
            
            result = await self.db.insert_hosts_records_with_progress(hosts, update_progress)
            
            if self.logger:
                await self._log('info', "Сохранение хостов завершено", {
                    "result": result,
                    "result_type": type(result).__name__,
                    "result_keys": list(result.keys()) if isinstance(result, dict) else "not_dict"
                })
            
            return result
            
        except Exception as e:
            error_msg = f"Ошибка сохранения хостов: {str(e)}"
            if self.logger:
                await self._log('error', error_msg)
            raise Exception(error_msg)
    
    def stop(self):
        """Остановить worker"""
        self.is_running = False
