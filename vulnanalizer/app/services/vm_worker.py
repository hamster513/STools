"""
VM MaxPatrol Worker для импорта данных
"""
import csv
import io
import json
import os
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
        self.vm_data_dir = "/app/data/vm_imports"
        self._ensure_data_dir()
    
    def _ensure_data_dir(self):
        """Создать директорию для сохранения данных VM если не существует"""
        try:
            if not os.path.exists(self.vm_data_dir):
                os.makedirs(self.vm_data_dir, exist_ok=True)
        except PermissionError:
            # Если нет прав на создание директории, используем временную директорию
            import tempfile
            self.vm_data_dir = os.path.join(tempfile.gettempdir(), 'stools_vm_imports')
            os.makedirs(self.vm_data_dir, exist_ok=True)
    
    def _get_vm_data_file_path(self, task_id: int) -> str:
        """Получить путь к файлу данных VM для задачи"""
        return os.path.join(self.vm_data_dir, f"vm_data_{task_id}.json")
    
    def _cleanup_old_vm_files(self):
        """Удалить старые файлы данных VM"""
        try:
            if os.path.exists(self.vm_data_dir):
                for filename in os.listdir(self.vm_data_dir):
                    if filename.startswith("vm_data_") and filename.endswith(".json"):
                        file_path = os.path.join(self.vm_data_dir, filename)
                        os.remove(file_path)
                        print(f"🗑️ Удален старый файл VM данных: {filename}")
        except Exception as e:
            print(f"⚠️ Ошибка удаления старых файлов VM: {e}")
    
    async def _save_vm_data_to_file(self, task_id: int, vm_data: List[Dict[str, str]]) -> str:
        """Сохранить данные VM в JSON файл"""
        try:
            file_path = self._get_vm_data_file_path(task_id)
            
            # Сохраняем данные в JSON файл
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(vm_data, f, ensure_ascii=False, indent=2)
            
            await self._log('info', f"Данные VM сохранены в файл: {file_path}", {
                "file_path": file_path,
                "records_count": len(vm_data)
            })
            
            return file_path
            
        except Exception as e:
            error_msg = f"Ошибка сохранения данных VM в файл: {str(e)}"
            await self._log('error', error_msg)
            raise Exception(error_msg)
    
    async def _load_vm_data_from_file(self, task_id: int) -> List[Dict[str, str]]:
        """Загрузить данные VM из JSON файла"""
        try:
            file_path = self._get_vm_data_file_path(task_id)
            
            if not os.path.exists(file_path):
                raise Exception(f"Файл данных VM не найден: {file_path}")
            
            with open(file_path, 'r', encoding='utf-8') as f:
                vm_data = json.load(f)
            
            await self._log('info', f"Данные VM загружены из файла: {file_path}", {
                "file_path": file_path,
                "records_count": len(vm_data)
            })
            
            return vm_data
            
        except Exception as e:
            error_msg = f"Ошибка загрузки данных VM из файла: {str(e)}"
            await self._log('error', error_msg)
            raise Exception(error_msg)
    
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
            
            # Удаляем старые файлы VM данных
            self._cleanup_old_vm_files()
            
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
                vm_settings['vm_host'].strip(),
                vm_settings['vm_username'].strip(),
                vm_settings['vm_password'].strip(),
                vm_settings['vm_client_secret'].strip()
            )
            await self._log('info', "Аутентификация в VM MaxPatrol успешна")
            
            # Получаем данные из VM API
            await self.db.update_background_task(task_id, **{
                'current_step': 'Получение данных из VM API'
            })
            await self._log('info', "Начинаем получение данных из VM API")
            
            vm_data = await self._get_vm_data(
                vm_settings['vm_host'].strip(),
                token,
                vm_settings
            )
            
            if not vm_data:
                error_msg = "Не удалось получить данные из VM API"
                await self._log('error', error_msg)
                raise Exception(error_msg)
            
            await self._log('info', f"Получено {len(vm_data)} записей из VM API")
            
            # Сохраняем данные в файл
            await self.db.update_background_task(task_id, **{
                'current_step': 'Сохранение данных в файл'
            })
            await self._log('info', "Начинаем сохранение данных VM в файл")
            
            file_path = await self._save_vm_data_to_file(task_id, vm_data)
            await self._log('info', f"Данные VM сохранены в файл: {file_path}")
            
            # НЕ запускаем автоматический импорт - только сохраняем файл
            await self.db.update_background_task(task_id, **{
                'status': 'completed',
                'current_step': 'Данные сохранены в файл. Готово к ручному импорту.',
                'end_time': datetime.now()
            })
            
            await self._log('info', f"Данные VM сохранены в файл: {file_path}. Импорт не запущен автоматически.")
            print(f"✅ Данные VM сохранены в файл: {file_path}")
            
            # Закрываем логгер
            if self.logger:
                await self.logger.close()
            
            return {
                "success": True,
                "count": len(vm_data),
                "message": f"Сохранено {len(vm_data)} записей в файл. Импорт не запущен автоматически.",
                "file_path": file_path
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
    
    async def start_manual_import(self, task_id: int, parameters: Dict[str, Any]) -> Dict:
        """Запустить ручной импорт данных из сохраненного файла VM"""
        try:
            print(f"🚀 Начинаем ручной импорт VM данных для задачи {task_id}")
            
            # Обновляем статус
            await self.db.update_background_task(task_id, **{
                'status': 'processing',
                'current_step': 'Загрузка данных из файла'
            })
            
            # Создаем логгер только если включено подробное логирование
            vm_settings = await self.db.get_vm_settings()
            if vm_settings.get('vm_detailed_logging') == 'true':
                self.logger = await simple_logging_service.create_task_logger(task_id, 'vm_manual_import')
                await self._log('info', "Начинаем ручной импорт VM данных", {"task_id": task_id, "parameters": parameters})
            
            # Загружаем данные из файла
            await self.db.update_background_task(task_id, **{
                'current_step': 'Загрузка данных из файла'
            })
            await self._log('info', "Начинаем загрузку данных из файла")
            
            vm_data_from_file = await self._load_vm_data_from_file(task_id)
            await self._log('info', f"Загружено {len(vm_data_from_file)} записей из файла")
            
            # Группируем данные по хостам
            await self.db.update_background_task(task_id, **{
                'current_step': 'Группировка данных по хостам'
            })
            await self._log('info', "Начинаем группировку данных по хостам")
            
            grouped_hosts = self._group_vm_data_by_hosts(vm_data_from_file)
            await self._log('info', f"Сгруппировано {len(grouped_hosts)} хостов из {len(vm_data_from_file)} записей")
            
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
            
            # Удаляем файл после успешного импорта
            try:
                file_path = self._get_vm_data_file_path(task_id)
                os.remove(file_path)
                await self._log('info', f"Файл данных VM удален: {file_path}")
            except Exception as e:
                await self._log('warning', f"Не удалось удалить файл данных VM: {e}")
            
            # Завершение
            await self.db.update_background_task(task_id, **{
                'status': 'completed',
                'current_step': 'Ручной импорт VM данных завершен',
                'processed_records': len(grouped_hosts),
                'total_records': len(grouped_hosts),
                'end_time': datetime.now()
            })
            
            await self._log('info', f"Ручной импорт VM данных завершен успешно: {len(grouped_hosts)} хостов")
            print(f"✅ Ручной импорт VM данных завершен: {len(grouped_hosts)} хостов")
            
            # Закрываем логгер
            if self.logger:
                await self.logger.close()
            
            return {
                "success": True,
                "count": len(grouped_hosts),
                "message": f"Импортировано {len(grouped_hosts)} хостов из файла VM"
            }
            
        except Exception as e:
            error_msg = f"Ошибка ручного импорта VM данных: {str(e)}"
            print(f"❌ {error_msg}")
            print(f"❌ Traceback: {traceback.format_exc()}")
            
            # Логируем ошибку
            await self._log('error', error_msg, {"traceback": traceback.format_exc()})
            
            # Обновляем статус задачи
            await self.db.update_background_task(task_id, **{
                'status': 'failed',
                'current_step': f'Ошибка: {error_msg}',
                'end_time': datetime.now()
            })
            
            # Закрываем логгер
            if self.logger:
                await self.logger.close()
            
            raise Exception(error_msg)
    
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
            
            # Получаем лимит записей из настроек
            vm_limit = int(settings.get('vm_limit', 0))
            await self._log('debug', f"Лимит записей: {vm_limit} (0 = без ограничений)")
            
            # PDQL запрос с лимитом записей
            if vm_limit > 0:
                pdql = f"""select(@Host, Host.OsName, Host.@Groups, Host.@Vulners.CVEs, Host.UF_Criticality, Host.UF_Zone) 
                | filter(Host.OsName != null) 
                | limit({vm_limit})"""
            else:
                pdql = """select(@Host, Host.OsName, Host.@Groups, Host.@Vulners.CVEs, Host.UF_Criticality, Host.UF_Zone) 
                | filter(Host.OsName != null)"""
            
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
                await self._log('debug', "Отправляем запрос для получения токена экспорта", {"url": url})
            
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
                await self._log('debug', "Запрашиваем CSV данные экспорта", {"export_url": export_url})
            
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
                'status': 'Active',
                'os_name': record.get('os_name', '')  # Добавляем os_name
            })
        
        if self.logger:
            import asyncio
            asyncio.create_task(self.logger.debug(f"Преобразование завершено: {len(result)} записей из {len(vm_data)} исходных"))
        
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
            async def update_progress(step, message, progress_percent, processed_records=None, current_step_progress=None, processed_cves=None, updated_hosts=None):
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
