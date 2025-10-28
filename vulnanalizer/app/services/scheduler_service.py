"""
Сервис планировщика задач для автоматического обновления данных
"""
import asyncio
import schedule
import time
import csv
import json
import os
import tempfile
import tarfile
import subprocess
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from pathlib import Path
from database import get_db
from utils.file_utils import split_file_by_size, extract_compressed_file
from utils.validation_utils import is_valid_ip
from services.vm_worker import VMWorker
import traceback

class SchedulerService:
    def __init__(self):
        self.db = get_db()
        self.running = False
        self.tasks = {}
    
    async def start_scheduler(self):
        """Запустить планировщик"""
        if self.running:
            print("🕐 Scheduler already running, skipping start")
            return
        
        self.running = True
        print("🕐 Scheduler started")
        
        # Очищаем предыдущее расписание
        schedule.clear()
        
        # Настраиваем расписание
        schedule.every().hour.do(self._run_async_task, self.hourly_check)
        schedule.every(30).minutes.do(self._run_async_task, self.cleanup_old_data)
        schedule.every(10).seconds.do(self._run_async_task, self.process_background_tasks)
        schedule.every(2).hours.do(self._run_async_task, self.vacuum_database)
        
        # Запускаем в отдельном потоке
        asyncio.create_task(self._run_scheduler())
    
    async def stop_scheduler(self):
        """Остановить планировщик"""
        self.running = False
        schedule.clear()
        print("🕐 Scheduler stopped")
    
    def _run_async_task(self, async_func):
        """Обертка для запуска async функций в schedule"""
        asyncio.create_task(async_func())
    
    async def _run_scheduler(self):
        """Основной цикл планировщика"""
        print("🕐 Планировщик запущен, начинаем основной цикл")
        error_count = 0
        max_errors = 5
        
        while self.running:
            try:
                schedule.run_pending()
                error_count = 0  # Сбрасываем счетчик ошибок при успешном выполнении
                # Делаем цикл более отзывчивым: проверяем pending каждые 1 секунду
                await asyncio.sleep(1)
            except Exception as e:
                error_count += 1
                print(f"❌ Ошибка в основном цикле планировщика ({error_count}/{max_errors}): {e}")
                print(f"❌ Error details: {traceback.format_exc()}")
                
                if error_count >= max_errors:
                    print(f"❌ Слишком много ошибок ({max_errors}), останавливаем планировщик")
                    self.running = False
                    break
                
                await asyncio.sleep(5)  # Увеличиваем паузу при ошибках
    
    async def hourly_check(self):
        """Ежечасная проверка системы"""
        conn = None
        try:
            print("🔍 Hourly system check")
            
            # Проверяем состояние базы данных
            conn = await self.db.get_connection()
            
            # Проверяем количество хостов без данных
            hosts_without_data = await conn.fetchval("""
                SELECT COUNT(*) FROM vulnanalizer.hosts 
                WHERE epss_score IS NULL AND exploits_count IS NULL
            """)
            
            if hosts_without_data > 0:
                print(f"⚠️ Found {hosts_without_data} hosts without data")
            
            # Проверяем последнее обновление
            last_update = await conn.fetchval("""
                SELECT MAX(GREATEST(epss_updated_at, exploits_updated_at, risk_updated_at)) 
                FROM vulnanalizer.hosts
            """)
            
            if last_update:
                hours_since_update = (datetime.now() - last_update).total_seconds() / 3600
                if hours_since_update > 24:
                    print(f"⚠️ Last update was {hours_since_update:.1f} hours ago")
            
        except Exception as e:
            print(f"❌ Error in hourly check: {e}")
        finally:
            if conn:
                await self.db.release_connection(conn)
    
    def _clean_import_data(self, raw_records: list) -> list:
        """Очистка данных от дублей и пустых записей"""
        print(f"🧹 Начинаем очистку {len(raw_records)} записей")
        
        # Удаляем пустые записи
        non_empty_records = []
        for record in raw_records:
            # Проверяем, что все обязательные поля заполнены
            if (record.get('hostname') and record.get('hostname').strip() and
                record.get('ip_address') and record.get('ip_address').strip() and
                record.get('cve') and record.get('cve').strip()):
                non_empty_records.append(record)
        
        print(f"🧹 После удаления пустых: {len(non_empty_records)} записей")
        
        # Удаляем дубли по комбинации hostname + ip_address + cve
        seen_combinations = set()
        unique_records = []
        
        for record in non_empty_records:
            # Создаем уникальный ключ для проверки дублей
            key = (
                record.get('hostname', '').strip().lower(),
                record.get('ip_address', '').strip(),
                record.get('cve', '').strip()
            )
            
            if key not in seen_combinations:
                seen_combinations.add(key)
                unique_records.append(record)
        
        print(f"🧹 После удаления дублей: {len(unique_records)} записей")
        print(f"🧹 Удалено {len(raw_records) - len(unique_records)} записей (пустые + дубли)")
        
        return unique_records

    async def _calculate_risks_for_imported_hosts(self, task_id: int, update_progress):
        """Расчет рисков для импортированных хостов"""
        try:
            print("🔍 Начинаем расчет рисков для импортированных хостов")
            
            # Получаем настройки для расчета рисков
            settings = await self.db.get_settings()
            
            # Создаем функцию обратного вызова для обновления прогресса
            async def risk_update_progress(step, message, progress_percent, processed_records=None):
                try:
                    # Обновляем все поля прогресса
                    update_data = {
                        'current_step': f'Расчет рисков: {message}',
                        'progress_percent': progress_percent
                    }
                    
                    # Если переданы processed_records, обновляем их
                    if processed_records is not None:
                        update_data['processed_records'] = processed_records
                    
                    await self.db.update_background_task(task_id, **update_data)
                    print(f"📊 Расчет рисков: {message} ({progress_percent:.1f}%)")
                except Exception as e:
                    print(f"⚠️ Ошибка обновления прогресса расчета рисков: {e}")
            
            # Используем правильный сервис расчета рисков
            from database.hosts_update_service import HostsUpdateService
            hosts_update_service = HostsUpdateService()
            
            # Запускаем расчет рисков
            await hosts_update_service.recalculate_all_risks(risk_update_progress)
            
            print("✅ Расчет рисков завершен")
            
        except Exception as e:
            print(f"❌ Ошибка расчета рисков: {e}")
            import traceback
            print(f"⚠️ Traceback: {traceback.format_exc()}")

    async def process_hosts_import_task(self, task_id: int, parameters: Dict[str, Any]):
        """Обработка фоновой задачи импорта хостов"""
        try:
            print(f"🔄 Начинаем обработку задачи импорта хостов {task_id}")
            print(f"📋 Параметры: {parameters}")
            print(f"📋 Тип параметров: {type(parameters)}")
            
            # Обновляем статус задачи
            await self.db.update_background_task(task_id, **{
                'status': 'processing',
                'current_step': 'Начало импорта хостов',
                'start_time': datetime.now()
            })
            
            file_path = parameters.get('file_path')
            filename = parameters.get('filename')
            criticality_filter = parameters.get('criticality_filter')
            os_filter = parameters.get('os_filter')
            
            # Парсим фильтр критичности (может быть строка с разделителями)
            criticality_list = []
            if criticality_filter:
                criticality_list = [c.strip() for c in criticality_filter.split(',') if c.strip()]
                print(f"🔍 Фильтр критичности: {criticality_list}")
            
            print(f"🔍 Фильтр ОС: {os_filter}")
            
            if not file_path or not Path(file_path).exists():
                await self.db.update_background_task(task_id, **{
                    'status': 'error',
                    'error_message': f'Файл не найден: {file_path}',
                    'end_time': datetime.now()
                })
                return
            
            # Читаем файл
            await self.db.update_background_task(task_id, **{
                'current_step': 'Чтение файла'
            })
            
            with open(file_path, 'rb') as f:
                content = f.read()
            
            # Определяем, является ли файл архивом
            is_archive = filename.lower().endswith(('.zip', '.gz', '.gzip'))
            
            if is_archive:
                await self.db.update_background_task(task_id, **{
                    'current_step': 'Распаковка архива'
                })
                decoded_content = extract_compressed_file(content, filename)
            else:
                decoded_content = content.decode('utf-8-sig')
            
            # Разделяем файл если нужно
            decoded_size_mb = len(decoded_content.encode('utf-8')) / (1024 * 1024)
            if decoded_size_mb > 100:
                await self.db.update_background_task(task_id, **{
                    'current_step': f'Разделение файла ({decoded_size_mb:.1f} МБ)'
                })
                parts = split_file_by_size(decoded_content, 100)
                total_parts = len(parts)
            else:
                parts = [decoded_content]
                total_parts = 1
            
            # Этап 1: Сбор всех записей для предварительной обработки
            await self.db.update_background_task(task_id, **{
                'current_step': 'Сбор данных для предварительной обработки'
            })
            
            all_raw_records = []
            total_processed_lines = 0
            
            for part_index, part_content in enumerate(parts, 1):
                await self.db.update_background_task(task_id, **{
                    'current_step': f'Сбор данных из части {part_index} из {total_parts}'
                })
                
                # Парсим CSV
                part_lines = part_content.splitlines()
                reader = csv.DictReader(part_lines, delimiter=';')
                
                for row in reader:
                    try:
                        # Парсим hostname и IP
                        host_info = row['@Host'].strip('"')
                        hostname = host_info.split(' (')[0] if ' (' in host_info else host_info
                        ip_address = host_info.split('(')[1].split(')')[0] if ' (' in host_info else ''
                        
                        # Проверяем валидность IP
                        if ip_address and not is_valid_ip(ip_address):
                            continue
                        
                        # Получаем данные
                        cve = row['Host.@Vulners.CVEs'].strip('"')
                        criticality = row['host.UF_Criticality'].strip('"')
                        zone = row['Host.UF_Zone'].strip('"')
                        os_name = row['Host.OsName'].strip('"')
                        
                        # Применяем фильтры
                        if criticality_list and criticality not in criticality_list:
                            continue
                        
                        if os_filter and os_filter.lower() not in os_name.lower():
                            continue
                        
                        all_raw_records.append({
                            'hostname': hostname,
                            'ip_address': ip_address,
                            'cve': cve,
                            'cvss': None,
                            'criticality': criticality,
                            'status': 'Active',
                            'os_name': os_name,
                            'zone': zone
                        })
                        
                    except Exception as e:
                        print(f"⚠️ Ошибка обработки строки: {e}")
                        continue
                
                total_processed_lines += len(part_lines)
            
            print(f"📊 Собрано {len(all_raw_records)} записей для предварительной обработки")
            
            # Этап 2: Предварительная очистка данных
            await self.db.update_background_task(task_id, **{
                'current_step': 'Предварительная очистка данных от дублей и пустых записей'
            })
            
            # Очищаем от дублей и пустых записей
            cleaned_records = self._clean_import_data(all_raw_records)
            
            print(f"📊 После очистки: {len(cleaned_records)} записей (удалено {len(all_raw_records) - len(cleaned_records)} дублей/пустых)")
            
            # Обновляем задачу с очищенными данными
            await self.db.update_background_task(task_id, **{
                'total_records': len(cleaned_records),
                'processed_records': 0
            })
            
            # Этап 3: Обработка очищенных данных
            await self.db.update_background_task(task_id, **{
                'current_step': 'Обработка очищенных данных'
            })
            
            print(f"💾 Начинаем сохранение {len(cleaned_records)} очищенных записей в базу данных...")
            
            # Создаем функцию обратного вызова для обновления прогресса
            async def update_progress(step, message, progress_percent, current_step_progress=None, processed_records=None):
                try:
                    print(f"🔧 Вызов update_progress: step={step}, message='{message}', progress_percent={progress_percent}, current_step_progress={current_step_progress}, processed_records={processed_records}")
                    
                    # Используем переданные значения для processed_records
                    current_processed = processed_records if processed_records is not None else 0
                    
                    print(f"🔧 Вычисленный current_processed: {current_processed}")
                    
                    # Обновляем задачу с правильными значениями
                    update_data = {
                        'current_step': message,
                        'processed_records': current_processed,
                        'total_records': len(cleaned_records)
                    }
                    
                    # Добавляем дополнительную информацию в зависимости от этапа
                    if step == 'cleaning':
                        update_data['current_step'] = f"Этап 1/3: {message}"
                    elif step == 'inserting':
                        update_data['current_step'] = f"Этап 2/3: {message}"
                    elif step == 'calculating_risk':
                        # Убираем проценты из сообщения о расчете рисков
                        if 'Расчет рисков...' in message:
                            # Извлекаем только часть с количеством CVE без процентов
                            import re
                            match = re.search(r'Расчет рисков\.\.\. \((\d+)/(\d+) CVE\)', message)
                            if match:
                                current_cve = match.group(1)
                                total_cve = match.group(2)
                                update_data['current_step'] = f"Этап 3/3: Расчет рисков... ({current_cve}/{total_cve} CVE)"
                            else:
                                update_data['current_step'] = f"Этап 3/3: {message}"
                        else:
                            update_data['current_step'] = f"Этап 3/3: {message}"
                    elif step == 'completed':
                        update_data['current_step'] = f"✅ {message}"
                    
                    await self.db.update_background_task(task_id, **update_data)
                    print(f"📊 Прогресс задачи {task_id}: {message} ({progress_percent:.1f}%) - {current_processed}/{len(cleaned_records)}")
                except Exception as e:
                    print(f"⚠️ Ошибка обновления прогресса: {e}")
                    import traceback
                    print(f"⚠️ Traceback: {traceback.format_exc()}")
            
            # Этап 4: Сохранение в базу с проверкой дублей
            await self.db.update_background_task(task_id, **{
                'current_step': 'Сохранение в базу данных с проверкой дублей'
            })
            
            # Сохраняем записи с проверкой дублей
            saved_count = await self.db.insert_hosts_records_with_duplicate_check(cleaned_records, update_progress)
            print(f"✅ Сохранение завершено: {saved_count} записей сохранено")
            
            total_records = saved_count
            
            await self.db.update_background_task(task_id, **{
                'processed_records': total_records,
                'total_records': total_records
            })
            
            # Этап 5: Расчет рисков
            if total_records > 0:
                await self.db.update_background_task(task_id, **{
                    'current_step': 'Расчет рисков для импортированных записей'
                })
                
                # Запускаем расчет рисков
                await self._calculate_risks_for_imported_hosts(task_id, update_progress)
            
            # Завершение
            await self.db.update_background_task(task_id, **{
                'status': 'completed',
                'current_step': 'Импорт завершен',
                'processed_records': total_records,
                'total_records': total_records,
                'end_time': datetime.now()
            })
            
            # Удаляем временный файл
            try:
                Path(file_path).unlink()
            except:
                pass
            
            print(f"✅ Импорт хостов завершен: {total_records} записей")
            print(f"🎉 Задача {task_id} успешно завершена")
            
        except Exception as e:
            error_msg = f"Ошибка импорта хостов: {str(e)}"
            print(f"❌ {error_msg}")
            print(f"❌ Задача {task_id} завершена с ошибкой")
            
            await self.db.update_background_task(task_id, **{
                'status': 'error',
                'error_message': error_msg,
                'end_time': datetime.now()
            })

    async def process_hosts_update_task(self, task_id: int, parameters: dict):
        """Обработать задачу обновления хостов"""
        try:
            print(f"🔄 Начинаем обработку задачи обновления хостов {task_id}")
            
            # Обновляем статус на 'processing'
            await self.db.update_background_task(task_id, **{
                'status': 'processing',
                'current_step': 'Запуск обновления данных хостов'
            })
            
            # Создаем функцию обратного вызова для обновления прогресса
            total_updated_hosts = 0  # Счетчик для накопления обновленных хостов
            
            async def update_progress(status, step, **kwargs):
                nonlocal total_updated_hosts
                try:
                    # Накапливаем количество обновленных хостов
                    if kwargs.get('updated_hosts', 0) > 0:
                        total_updated_hosts += kwargs.get('updated_hosts', 0)
                    
                    # Рассчитываем процент прогресса
                    total_cves = kwargs.get('total_cves', 0)
                    processed_cves = kwargs.get('processed_cves', 0)
                    progress_percent = 0
                    
                    if total_cves > 0:
                        progress_percent = int((processed_cves / total_cves) * 100)
                    
                    update_data = {
                        'current_step': step,
                        'total_items': total_cves,
                        'processed_items': processed_cves,
                        'total_records': kwargs.get('total_hosts', 0),
                        'updated_records': total_updated_hosts,
                        'progress_percent': progress_percent
                    }
                    
                    # Убираем None значения
                    update_data = {k: v for k, v in update_data.items() if v is not None}
                    
                    print(f"🔄 Обновляем задачу {task_id} с данными: {update_data}")
                    await self.db.update_background_task(task_id, **update_data)
                    print(f"✅ Задача {task_id} обновлена успешно")
                    print(f"📊 Прогресс hosts_update: {step} - {processed_cves}/{total_cves} CVE ({progress_percent}%), {total_updated_hosts} хостов (всего)")
                except Exception as e:
                    print(f"⚠️ Ошибка обновления прогресса hosts_update: {e}")
                    print(f"❌ Детали ошибки: {traceback.format_exc()}")
            
            # Проверяем тип обновления
            update_type = parameters.get('update_type', 'parallel')
            
            if update_type == 'optimized_batch':
                print(f"🚀 Используем полное обновление хостов")
                # Запускаем полное обновление данных хостов
                result = await self.db.hosts_update.update_hosts_complete(update_progress)
            else:
                print(f"🔄 Используем стандартный параллельный метод обновления")
                # Запускаем стандартное обновление данных хостов
                result = await self.db.hosts_update.update_hosts_complete(update_progress)
            
            # Обновляем финальный статус
            if result['success']:
                await self.db.update_background_task(task_id, **{
                    'status': 'completed',
                    'current_step': 'Завершено',
                    'total_items': result.get('processed_cves', 0),
                    'processed_items': result.get('processed_cves', 0),
                    'total_records': result.get('updated_count', 0),
                    'updated_records': result.get('updated_count', 0),
                    'end_time': datetime.now()
                })
                print(f"✅ Обновление хостов завершено: {result.get('updated_count', 0)} записей")
                print(f"📊 Финальная статистика: {result}")
            else:
                await self.db.update_background_task(task_id, **{
                    'status': 'error',
                    'current_step': 'Ошибка',
                    'error_message': result.get('message', 'Неизвестная ошибка'),
                    'end_time': datetime.now()
                })
                print(f"❌ Ошибка обновления хостов: {result.get('message', 'Неизвестная ошибка')}")
            
        except Exception as e:
            error_msg = f"Ошибка обработки задачи обновления хостов: {str(e)}"
            print(f"❌ {error_msg}")
            
            await self.db.update_background_task(task_id, **{
                'status': 'error',
                'error_message': error_msg,
                'end_time': datetime.now()
            })
    
    async def process_background_tasks(self):
        """Обработка фоновых задач с проверкой зависших задач"""
        try:
            print("🔍 Проверяем фоновые задачи...")
            
            # Получаем задачи в статусе 'idle'
            idle_tasks = await self.db.get_background_tasks_by_status('idle')
            print(f"📋 Найдено задач в статусе 'idle': {len(idle_tasks)}")
            
            if idle_tasks:
                print(f"📋 Детали idle задач: {[(t['id'], t['task_type'], t['status']) for t in idle_tasks]}")
            
            # Проверяем зависшие задачи (processing более 10 минут)
            stuck_tasks = await self._check_stuck_tasks()
            if stuck_tasks:
                print(f"⚠️ Найдено зависших задач: {len(stuck_tasks)}")
                for task in stuck_tasks:
                    print(f"⚠️ Зависшая задача {task['id']} ({task['task_type']}): {task['current_step']}")
                    # Перезапускаем зависшие задачи
                    await self._restart_stuck_task(task)
            
            if idle_tasks:
                print(f"📋 Детали задач: {[(t['id'], t['task_type'], t['status']) for t in idle_tasks]}")
                
                # Получаем список активных задач для проверки дублирования
                active_tasks = await self._get_active_tasks()
                active_task_types = {task['task_type'] for task in active_tasks}
                print(f"🔍 Активные типы задач: {active_task_types}")
                
                for task in idle_tasks:
                    task_id = task['id']
                    task_type = task['task_type']
                    parameters_str = task.get('parameters', '{}')
                    
                    print(f"🔄 Обрабатываем фоновую задачу {task_id} типа {task_type}")
                    print(f"📋 Параметры задачи: {parameters_str}")
                    
                    # Проверяем на дублирование задач
                    if task_type in active_task_types:
                        print(f"⚠️ Задача типа '{task_type}' уже выполняется, отменяем дублирующую задачу {task_id}")
                        await self.db.update_background_task(task_id, **{
                            'status': 'cancelled',
                            'current_step': 'Отменено: дублирование активной задачи',
                            'error_message': f'Задача типа {task_type} уже выполняется',
                            'end_time': datetime.now()
                        })
                        continue
                    
                    # Десериализуем параметры из JSON
                    import json
                    try:
                        parameters = json.loads(parameters_str) if parameters_str else {}
                        print(f"📋 Десериализованные параметры: {parameters}")
                    except json.JSONDecodeError:
                        print(f"⚠️ Ошибка десериализации параметров для задачи {task_id}")
                        parameters = {}
                    
                    # Обновляем статус на 'initializing'
                    await self.db.update_background_task(task_id, **{
                        'status': 'initializing',
                        'current_step': 'Инициализация задачи'
                    })
                    print(f"✅ Статус задачи {task_id} обновлен на 'initializing'")
                    
                    # Добавляем тип задачи в список активных
                    active_task_types.add(task_type)
                    
                    # Обрабатываем задачу в зависимости от типа в отдельной задаче
                    if task_type == 'hosts_import':
                        print(f"🚀 Запускаем обработку задачи импорта хостов {task_id} в отдельной задаче")
                        task = asyncio.create_task(self.process_hosts_import_task(task_id, parameters))
                        task.add_done_callback(lambda t: self._handle_task_completion(t, task_id, 'hosts_import'))
                    elif task_type == 'hosts_update':
                        print(f"🚀 Запускаем обработку задачи обновления хостов {task_id} в отдельной задаче")
                        task = asyncio.create_task(self.process_hosts_update_task(task_id, parameters))
                        task.add_done_callback(lambda t: self._handle_task_completion(t, task_id, 'hosts_update'))
                    elif task_type == 'risk_calculation':
                        print(f"🚀 Запускаем обработку задачи расчета рисков {task_id} в отдельной задаче")
                        task = asyncio.create_task(self.process_risk_calculation_task(task_id, parameters))
                        task.add_done_callback(lambda t: self._handle_task_completion(t, task_id, 'risk_calculation'))
                    elif task_type == 'risk_recalculation':
                        print(f"🚀 Запускаем обработку задачи пересчета рисков {task_id} в отдельной задаче")
                        task = asyncio.create_task(self.process_risk_recalculation_task(task_id, parameters))
                        task.add_done_callback(lambda t: self._handle_task_completion(t, task_id, 'risk_recalculation'))
                    elif task_type == 'backup_create':
                        print(f"🚀 Запускаем обработку задачи создания бэкапа {task_id} в отдельной задаче")
                        task = asyncio.create_task(self.process_backup_create_task(task_id, parameters))
                        task.add_done_callback(lambda t: self._handle_task_completion(t, task_id, 'backup_create'))
                    elif task_type == 'epss_download':
                        print(f"🚀 Запускаем обработку задачи загрузки EPSS {task_id} в отдельной задаче")
                        task = asyncio.create_task(self.process_epss_download_task(task_id, parameters))
                        task.add_done_callback(lambda t: self._handle_task_completion(t, task_id, 'epss_download'))
                    elif task_type == 'vm_import':
                        print(f"🚀 Запускаем обработку задачи импорта VM {task_id} в отдельной задаче")
                        task = asyncio.create_task(self.process_vm_import_task(task_id, parameters))
                        task.add_done_callback(lambda t: self._handle_task_completion(t, task_id, 'vm_import'))
                    elif task_type == 'vm_manual_import':
                        print(f"🚀 Запускаем обработку задачи ручного импорта VM {task_id} в отдельной задаче")
                        task = asyncio.create_task(self.process_vm_manual_import_task(task_id, parameters))
                        task.add_done_callback(lambda t: self._handle_task_completion(t, task_id, 'vm_manual_import'))
                    else:
                        print(f"❌ Неизвестный тип задачи: {task_type}")
                        await self.db.update_background_task(task_id, **{
                            'status': 'error',
                            'error_message': f'Неизвестный тип задачи: {task_type}',
                            'end_time': datetime.now()
                        })
            else:
                print("📋 Нет задач в статусе 'idle' для обработки")
                    
        except Exception as e:
            print(f"❌ Ошибка обработки фоновых задач: {e}")
            print(f"❌ Error details: {traceback.format_exc()}")
    
    async def _check_stuck_tasks(self):
        """Проверить зависшие задачи с динамическими лимитами времени"""
        try:
            conn = await self.db.get_connection()
            
            # Ищем задачи в статусе processing, initializing и running с динамическими лимитами
            query = """
                SELECT id, task_type, status, current_step, created_at, updated_at, start_time,
                       last_activity_at, activity_count
                FROM vulnanalizer.background_tasks 
                WHERE status IN ('processing', 'initializing', 'running')
                AND (
                    -- Если нет активности более 15 минут - зависла (увеличено с 5 минут)
                    (last_activity_at IS NULL AND updated_at < NOW() - INTERVAL '15 minutes')
                    OR
                    -- Если активность была, но давно - зависла (увеличено с 5 минут)
                    (last_activity_at IS NOT NULL AND last_activity_at < NOW() - INTERVAL '15 minutes')
                    OR
                    -- Если задача очень старая (более 4 часов) - зависла (увеличено с 2 часов)
                    (updated_at < NOW() - INTERVAL '4 hours')
                )
                ORDER BY updated_at ASC
            """
            stuck_tasks = await conn.fetch(query)
            return [dict(task) for task in stuck_tasks]
        except Exception as e:
            print(f"❌ Ошибка проверки зависших задач: {e}")
            return []
        finally:
            await self.db.release_connection(conn)
    
    async def _restart_stuck_task(self, task):
        """Перезапустить зависшую задачу"""
        try:
            task_id = task['id']
            task_type = task['task_type']
            
            print(f"🔄 Перезапускаем зависшую задачу {task_id} ({task_type})")
            
            # Создаем новую задачу с теми же параметрами
            parameters_str = task.get('parameters', '{}')
            import json
            try:
                parameters = json.loads(parameters_str) if parameters_str else {}
            except json.JSONDecodeError:
                parameters = {}
            
            # Отменяем старую задачу
            await self.db.update_background_task(task_id, **{
                'status': 'cancelled',
                'current_step': 'Отменено: зависла',
                'error_message': 'Задача зависла и была перезапущена автоматически',
                'end_time': datetime.now()
            })
            
            # Создаем новую задачу
            new_task_id = await self.db.create_background_task(
                task_type=task_type,
                parameters=parameters,
                description=f"Перезапуск зависшей задачи {task_id}"
            )
            
            print(f"✅ Зависшая задача {task_id} отменена, создана новая задача {new_task_id}")
            
        except Exception as e:
            print(f"❌ Ошибка перезапуска зависшей задачи {task['id']}: {e}")
    
    async def _get_active_tasks(self):
        """Получить список активных задач (processing, initializing)"""
        try:
            conn = await self.db.get_connection()
            
            # Ищем задачи в статусе processing или initializing
            query = """
                SELECT id, task_type, status, current_step, created_at, updated_at, start_time
                FROM vulnanalizer.background_tasks 
                WHERE status IN ('processing', 'initializing')
                ORDER BY created_at ASC
            """
            active_tasks = await conn.fetch(query)
            return [dict(task) for task in active_tasks]
        except Exception as e:
            print(f"❌ Ошибка получения активных задач: {e}")
            return []
        finally:
            await self.db.release_connection(conn)
    
    async def cleanup_old_data(self):
        """Очистка старых данных"""
        conn = None
        try:
            print("🧹 Cleaning up old data")
            
            conn = await self.db.get_connection()
            
            # Удаляем старые записи фоновых задач (старше 30 дней)
            deleted_tasks = await conn.execute("""
                DELETE FROM vulnanalizer.background_tasks 
                WHERE created_at < NOW() - INTERVAL '30 days'
            """)
            
            print(f"✅ Cleaned up old background tasks")
            
        except Exception as e:
            print(f"❌ Error in cleanup: {e}")
        finally:
            if conn:
                await self.db.release_connection(conn)
    
    async def vacuum_database(self):
        """Очистка мертвых записей в базе данных"""
        conn = None
        try:
            print("🧹 Выполняем очистку мертвых записей (VACUUM)")
            
            conn = await self.db.get_connection()
            
            # Очищаем основные таблицы
            tables_to_vacuum = [
                'vulnanalizer.hosts',
                'vulnanalizer.background_tasks', 
                'vulnanalizer.cve',
                'vulnanalizer.epss',
                'vulnanalizer.exploitdb',
                'vulnanalizer.metasploit_modules'
            ]
            
            for table in tables_to_vacuum:
                try:
                    await conn.execute(f"VACUUM ANALYZE {table}")
                    print(f"✅ Очищена таблица {table}")
                except Exception as e:
                    print(f"⚠️ Ошибка очистки {table}: {e}")
            
            print("✅ Очистка мертвых записей завершена")
            
        except Exception as e:
            print(f"❌ Ошибка очистки базы данных: {e}")
        finally:
            if conn:
                await self.db.release_connection(conn)
    
    async def add_custom_schedule(self, task_name: str, schedule_config: Dict[str, Any]):
        """Добавить пользовательское расписание"""
        try:
            frequency = schedule_config.get('frequency', 'daily')
            time_str = schedule_config.get('time', '02:00')
            
            if frequency == 'daily':
                schedule.every().day.at(time_str).do(self._run_custom_task, task_name)
            elif frequency == 'hourly':
                schedule.every().hour.do(self._run_custom_task, task_name)
            elif frequency == 'weekly':
                day = schedule_config.get('day', 'monday')
                schedule.every().monday.at(time_str).do(self._run_custom_task, task_name)
            
            self.tasks[task_name] = schedule_config
            print(f"✅ Added custom schedule for task: {task_name}")
            
        except Exception as e:
            print(f"❌ Error adding custom schedule: {e}")
    
    async def _run_custom_task(self, task_name: str):
        """Выполнить пользовательскую задачу"""
        try:
            print(f"🔄 Running custom task: {task_name}")
            
            if task_name == 'full_update':
                # Полное обновление
                result = await self.db.update_hosts_complete()
            elif task_name == 'incremental_update':
                # Инкрементальное обновление
                days = self.tasks.get(task_name, {}).get('days_old', 1)
                result = await self.db.update_hosts_incremental(days_old=days)
            else:
                print(f"⚠️ Unknown custom task: {task_name}")
                return
            
            print(f"✅ Custom task {task_name} completed")
            
        except Exception as e:
            print(f"❌ Error in custom task {task_name}: {e}")

    def _handle_task_completion(self, task, task_id: int, task_type: str):
        """Обработчик завершения асинхронной задачи"""
        try:
            if task.cancelled():
                print(f"⚠️ Задача {task_id} ({task_type}) была отменена")
            elif task.exception():
                error = task.exception()
                print(f"❌ Задача {task_id} ({task_type}) завершилась с ошибкой: {error}")
                # Создаем задачу для обновления статуса в БД
                asyncio.create_task(self._update_task_error_status(task_id, str(error)))
            else:
                result = task.result()
                print(f"✅ Задача {task_id} ({task_type}) успешно завершена")
        except Exception as e:
            print(f"❌ Ошибка в обработчике завершения задачи {task_id}: {e}")

    async def _update_task_error_status(self, task_id: int, error_message: str):
        """Обновить статус задачи на error"""
        try:
            await self.db.update_background_task(task_id, **{
                'status': 'error',
                'error_message': error_message,
                'end_time': datetime.now()
            })
            print(f"✅ Статус задачи {task_id} обновлен на error")
        except Exception as e:
            print(f"❌ Ошибка обновления статуса задачи {task_id}: {e}")

    async def process_risk_calculation_task(self, task_id: int, parameters: Dict[str, Any]):
        """Обработка задачи расчета рисков для хостов без данных"""
        try:
            print(f"🔍 Начинаем расчет рисков для хостов без данных (задача {task_id})")
            
            # Обновляем статус на 'processing'
            await self.db.update_background_task(task_id, **{
                'status': 'processing',
                'current_step': 'Поиск хостов без данных EPSS и Risk',
                'start_time': datetime.now()
            })
            
            # Получаем хосты без EPSS и Risk данных
            conn = await self.db.get_connection()
            
            # Находим CVE хостов без EPSS данных
            cve_query = """
                SELECT DISTINCT h.cve 
                FROM vulnanalizer.hosts h 
                LEFT JOIN vulnanalizer.epss e ON h.cve = e.cve 
                WHERE h.cve IS NOT NULL AND h.cve != '' 
                AND (h.epss_score IS NULL OR h.risk_score IS NULL)
                AND e.cve IS NOT NULL
                ORDER BY h.cve
            """
            cve_rows = await conn.fetch(cve_query)
            
            if not cve_rows:
                print("✅ Нет хостов для расчета рисков")
                await self.db.update_background_task(task_id, conn=conn, **{
                    'status': 'completed',
                    'current_step': 'Нет хостов для расчета рисков',
                    'end_time': datetime.now()
                })
                return
            
            total_cves = len(cve_rows)
            print(f"🔍 Найдено {total_cves} CVE для расчета рисков")
            
            # Обновляем общее количество
            await self.db.update_background_task(task_id, conn=conn, **{
                'total_items': total_cves,
                'current_step': f'Найдено {total_cves} CVE для расчета рисков'
            })
            
            # Получаем настройки
            settings_query = "SELECT key, value FROM vulnanalizer.settings"
            settings_rows = await conn.fetch(settings_query)
            settings = {row['key']: row['value'] for row in settings_rows}
            
            # Создаем функцию обратного вызова для прогресса
            async def update_progress(step: str, message: str, progress_percent: int = 0, **kwargs):
                await self.db.update_background_task(task_id, conn=conn, **{
                    'current_step': message,
                    'progress_percent': progress_percent,
                    'processed_items': kwargs.get('processed_cves', 0),
                    'total_items': total_cves,
                    'processed_records': kwargs.get('updated_hosts', 0)
                })
            
            # Используем полное обновление хостов
            await self.db.risk_calculation.update_hosts_complete(update_progress)
            
            # Завершаем задачу
            await self.db.update_background_task(task_id, conn=conn, **{
                'status': 'completed',
                'current_step': f'Расчет рисков завершен для {total_cves} CVE',
                'end_time': datetime.now()
            })
            
            print(f"✅ Расчет рисков завершен для {total_cves} CVE")
            
        except Exception as e:
            print(f"❌ Ошибка расчета рисков: {e}")
            print(f"❌ Error details: {traceback.format_exc()}")
            
            await self.db.update_background_task(task_id, **{
                'status': 'error',
                'current_step': 'Ошибка расчета рисков',
                'error_message': str(e),
                'end_time': datetime.now()
            })
        finally:
            if conn:
                await self.db.release_connection(conn)

    async def process_risk_recalculation_task(self, task_id: int, parameters: Dict[str, Any]):
        """Обработка задачи пересчета рисков для ВСЕХ хостов"""
        try:
            print(f"🔍 Начинаем пересчет рисков для ВСЕХ хостов (задача {task_id})")
            
            # Обновляем статус на 'processing'
            await self.db.update_background_task(task_id, **{
                'status': 'processing',
                'current_step': 'Поиск всех хостов для пересчета рисков',
                'start_time': datetime.now()
            })
            
            # Получаем ВСЕ хосты с CVE
            conn = await self.db.get_connection()
            
            # Находим все CVE хостов
            cve_query = """
                SELECT DISTINCT h.cve 
                FROM vulnanalizer.hosts h 
                WHERE h.cve IS NOT NULL AND h.cve != '' 
                ORDER BY h.cve
            """
            cve_rows = await conn.fetch(cve_query)
            
            if not cve_rows:
                print("✅ Нет хостов для пересчета рисков")
                await self.db.update_background_task(task_id, conn=conn, **{
                    'status': 'completed',
                    'current_step': 'Нет хостов для пересчета рисков',
                    'end_time': datetime.now()
                })
                return
            
            total_cves = len(cve_rows)
            print(f"🔍 Найдено {total_cves} CVE для пересчета рисков")
            
            # Обновляем общее количество
            await self.db.update_background_task(task_id, conn=conn, **{
                'total_items': total_cves,
                'current_step': f'Найдено {total_cves} CVE для пересчета рисков'
            })
            
            # Получаем настройки
            settings_query = "SELECT key, value FROM vulnanalizer.settings"
            settings_rows = await conn.fetch(settings_query)
            settings = {row['key']: row['value'] for row in settings_rows}
            
            # Создаем функцию обратного вызова для прогресса
            async def update_progress(step: str, message: str, progress_percent: int = 0, **kwargs):
                await self.db.update_background_task(task_id, conn=conn, **{
                    'current_step': message,
                    'progress_percent': progress_percent,
                    'processed_items': kwargs.get('processed_cves', 0),
                    'total_items': total_cves,
                    'processed_records': kwargs.get('updated_hosts', 0)
                })
            
            # Используем специальный метод для пересчета рисков
            from database.hosts_update_service import HostsUpdateService
            hosts_update_service = HostsUpdateService()
            await hosts_update_service.recalculate_all_risks(update_progress)
            
            # Завершаем задачу
            await self.db.update_background_task(task_id, conn=conn, **{
                'status': 'completed',
                'current_step': f'Пересчет рисков завершен для {total_cves} CVE',
                'end_time': datetime.now()
            })
            
            print(f"✅ Пересчет рисков завершен для {total_cves} CVE")
            
        except Exception as e:
            print(f"❌ Ошибка пересчета рисков: {e}")
            print(f"❌ Error details: {traceback.format_exc()}")
            
            await self.db.update_background_task(task_id, **{
                'status': 'error',
                'current_step': 'Ошибка пересчета рисков',
                'error_message': str(e),
                'end_time': datetime.now()
            })
        finally:
            if conn:
                await self.db.release_connection(conn)

    async def process_backup_create_task(self, task_id: int, parameters: Dict[str, Any]):
        """Обработка задачи создания бэкапа"""
        try:
            print(f"🔄 Начинаем создание бэкапа для задачи {task_id}")
            
            # Получаем параметры
            tables = parameters.get('tables', [])
            include_schema = parameters.get('include_schema', True)
            include_data = parameters.get('include_data', True)
            
            if not tables:
                raise ValueError("Не выбрано ни одной таблицы для бэкапа")
            
            # Настройки
            backup_dir = os.getenv('BACKUP_DIR', './backups')
            try:
                os.makedirs(backup_dir, exist_ok=True)
            except PermissionError:
                # Если нет прав на создание в текущей директории, используем /tmp
                backup_dir = '/tmp/backups'
                os.makedirs(backup_dir, exist_ok=True)
            
            # Создаем уникальный ID для бэкапа
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_id = f"backup_{timestamp}"
            
            # Обновляем статус
            await self.db.update_background_task(task_id, **{
                'status': 'processing',
                'current_step': 'Подготовка к созданию бэкапа',
                'progress_percent': 10
            })
            
            # Создаем временную директорию
            with tempfile.TemporaryDirectory() as temp_dir:
                backup_file = os.path.join(temp_dir, f"{backup_id}.sql")
                
                # Обновляем статус
                await self.db.update_background_task(task_id, **{
                    'current_step': 'Создание SQL дампа',
                    'progress_percent': 30
                })
                
                # Создаем SQL дамп через pg_dump
                print(f"🔄 Создаем SQL дамп для таблиц: {tables}")
                
                # Создаем SQL дамп через прямое подключение к базе данных
                # Используем стандартный подход с asyncpg для получения данных
                print(f"🔄 Создаем SQL дамп для таблиц: {tables}")
                
                # Получаем подключение к базе данных
                conn = await self.db.get_connection()
                
                try:
                    sql_content = []
                    
                    # Добавляем заголовок
                    sql_content.append("-- Backup created by STools with pg_dump-style output")
                    sql_content.append(f"-- Created at: {datetime.now().isoformat()}")
                    sql_content.append(f"-- Tables: {', '.join(tables)}")
                    sql_content.append("")
                    
                    # Для каждой таблицы создаем дамп в стиле pg_dump
                    for table in tables:
                        schema, table_name = table.split(".", 1) if "." in table else ("public", table)
                        
                        # Получаем структуру таблицы
                        structure_query = f"""
                        SELECT 
                            c.column_name, 
                            c.data_type, 
                            c.is_nullable, 
                            c.column_default,
                            c.character_maximum_length,
                            c.numeric_precision,
                            c.numeric_scale,
                            c.generation_expression
                        FROM information_schema.columns c
                        WHERE c.table_schema = '{schema}' AND c.table_name = '{table_name}'
                        ORDER BY c.ordinal_position;
                        """
                        
                        structure_result = await conn.fetch(structure_query)
                        
                        if structure_result:
                            # Создаем DROP TABLE
                            sql_content.append(f"DROP TABLE IF EXISTS {schema}.{table_name} CASCADE;")
                            sql_content.append("")
                            
                            # Создаем CREATE TABLE
                            columns = []
                            for col in structure_result:
                                # Базовый тип данных
                                data_type = col['data_type']
                                
                                # Добавляем размеры для типов
                                if col['character_maximum_length'] and data_type in ['character varying', 'varchar', 'char']:
                                    data_type += f"({col['character_maximum_length']})"
                                elif col['numeric_precision'] and col['numeric_scale'] and data_type in ['numeric', 'decimal']:
                                    data_type += f"({col['numeric_precision']},{col['numeric_scale']})"
                                elif col['numeric_precision'] and data_type in ['numeric', 'decimal']:
                                    data_type += f"({col['numeric_precision']})"
                                
                                # Экранируем зарезервированные слова
                                column_name = col['column_name']
                                if column_name.lower() in ['references', 'order', 'group', 'user', 'table', 'index']:
                                    column_name = f'"{column_name}"'
                                
                                col_def = f"{column_name} {data_type}"
                                
                                # NOT NULL
                                if col['is_nullable'] == 'NO':
                                    col_def += " NOT NULL"
                                
                                # DEFAULT (но не для SERIAL полей)
                                if col['column_default'] and not col['column_default'].startswith('nextval'):
                                    col_def += f" DEFAULT {col['column_default']}"
                                elif col['column_default'] and col['column_default'].startswith('nextval'):
                                    # Для SERIAL полей используем SERIAL вместо integer + nextval
                                    if data_type == 'integer' and col['column_name'] == 'id':
                                        col_def = f"{column_name} SERIAL PRIMARY KEY"
                                
                                # GENERATED ALWAYS AS
                                if col['generation_expression']:
                                    col_def += f" GENERATED ALWAYS AS ({col['generation_expression']}) STORED"
                                
                                columns.append(col_def)
                            
                            sql_content.append(f"CREATE TABLE {schema}.{table_name} (")
                            sql_content.append("    " + ",\n    ".join(columns))
                            sql_content.append(");")
                            sql_content.append("")
                            
                            # Получаем первичные ключи
                            pk_query = f"""
                            SELECT kcu.column_name
                            FROM information_schema.table_constraints tc
                            JOIN information_schema.key_column_usage kcu 
                                ON tc.constraint_name = kcu.constraint_name
                            WHERE tc.table_schema = '{schema}' 
                                AND tc.table_name = '{table_name}'
                                AND tc.constraint_type = 'PRIMARY KEY'
                            ORDER BY kcu.ordinal_position;
                            """
                            
                            pk_result = await conn.fetch(pk_query)
                            if pk_result:
                                pk_columns = [row['column_name'] for row in pk_result]
                                # Проверяем, есть ли PRIMARY KEY уже в CREATE TABLE (для SERIAL полей)
                                has_serial_pk = any(col['column_name'] == 'id' and col['column_default'] and col['column_default'].startswith('nextval') for col in structure_result)
                                
                                if not has_serial_pk:
                                    sql_content.append(f"ALTER TABLE ONLY {schema}.{table_name}")
                                    sql_content.append(f"    ADD CONSTRAINT {table_name}_pkey PRIMARY KEY ({', '.join(pk_columns)});")
                                    sql_content.append("")
                            
                            # Получаем UNIQUE ограничения
                            unique_query = f"""
                            SELECT tc.constraint_name, kcu.column_name
                            FROM information_schema.table_constraints tc
                            JOIN information_schema.key_column_usage kcu 
                                ON tc.constraint_name = kcu.constraint_name
                            WHERE tc.table_schema = '{schema}' 
                                AND tc.table_name = '{table_name}'
                                AND tc.constraint_type = 'UNIQUE'
                            ORDER BY tc.constraint_name, kcu.ordinal_position;
                            """
                            
                            unique_result = await conn.fetch(unique_query)
                            if unique_result:
                                # Группируем по constraint_name
                                unique_constraints = {}
                                for row in unique_result:
                                    constraint_name = row['constraint_name']
                                    if constraint_name not in unique_constraints:
                                        unique_constraints[constraint_name] = []
                                    unique_constraints[constraint_name].append(row['column_name'])
                                
                                # Добавляем UNIQUE ограничения
                                for constraint_name, columns in unique_constraints.items():
                                    sql_content.append(f"ALTER TABLE ONLY {schema}.{table_name}")
                                    sql_content.append(f"    ADD CONSTRAINT {constraint_name} UNIQUE ({', '.join(columns)});")
                                    sql_content.append("")
                            
                            # Получаем данные, исключая generated columns
                            non_generated_columns = []
                            for col in structure_result:
                                if not col['generation_expression']:
                                    non_generated_columns.append(col['column_name'])
                            
                            if non_generated_columns:
                                # Экранируем имена колонок
                                escaped_columns = []
                                for col in non_generated_columns:
                                    if col.lower() in ['references', 'order', 'group', 'select', 'from', 'where', 'table', 'index', 'constraint']:
                                        escaped_columns.append(f'"{col}"')
                                    else:
                                        escaped_columns.append(col)
                                columns_list = ', '.join(escaped_columns)
                                data_query = f"SELECT {columns_list} FROM {schema}.{table_name};"
                                data_result = await conn.fetch(data_query)
                                
                                if data_result:
                                    # Создаем INSERT statements
                                    for row in data_result:
                                        values = []
                                        for value in row.values():
                                            if value is None:
                                                values.append("NULL")
                                            elif isinstance(value, str):
                                                # Экранируем специальные символы
                                                escaped_value = value.replace("\\", "\\\\").replace("'", "''").replace("\n", "\\n").replace("\r", "\\r").replace("\t", "\\t")
                                                values.append(f"'{escaped_value}'")
                                            elif isinstance(value, (int, float)):
                                                values.append(str(value))
                                            elif isinstance(value, bool):
                                                values.append("TRUE" if value else "FALSE")
                                            else:
                                                # Для других типов конвертируем в строку и экранируем
                                                escaped_value = str(value).replace("\\", "\\\\").replace("'", "''").replace("\n", "\\n").replace("\r", "\\r").replace("\t", "\\t")
                                                values.append(f"'{escaped_value}'")
                                        
                                        sql_content.append(f"INSERT INTO {schema}.{table_name} ({columns_list}) VALUES ({', '.join(values)});")
                                
                                sql_content.append("")
                    
                    # Сохраняем SQL в файл
                    with open(backup_file, 'w', encoding='utf-8') as f:
                        f.write('\n'.join(sql_content))
                    
                    print(f"✅ SQL дамп создан: {backup_file}")
                        
                finally:
                    await self.db.release_connection(conn)
                
                # pg_dump уже создал файл, продолжаем
                # Проверяем, что файл создался
                if not os.path.exists(backup_file) or os.path.getsize(backup_file) == 0:
                    raise Exception("Ошибка создания бэкапа: файл пуст или не создан")
                
                # Обновляем статус
                await self.db.update_background_task(task_id, **{
                    'current_step': 'Архивация бэкапа',
                    'progress_percent': 70
                })
                
                # Создаем архив
                archive_path = os.path.join(backup_dir, f"{backup_id}.tar.gz")
                with tarfile.open(archive_path, "w:gz") as tar:
                    tar.add(backup_file, arcname=f"{backup_id}.sql")
                
                # Создаем метаданные бэкапа
                metadata = {
                    "id": backup_id,
                    "filename": f"{backup_id}.tar.gz",
                    "size": os.path.getsize(archive_path),
                    "created_at": datetime.now().isoformat(),
                    "tables": tables,
                    "status": "completed",
                    "includes_schema": True,
                    "includes_constraints": True,
                    "includes_indexes": True,
                    "includes_primary_keys": True,
                    "backup_type": "selective_with_schema"
                }
                
                # Сохраняем метаданные
                metadata_file = os.path.join(backup_dir, f"{backup_id}.json")
                with open(metadata_file, 'w') as f:
                    json.dump(metadata, f, indent=2)
                
                # Обновляем статус
                await self.db.update_background_task(task_id, **{
                    'status': 'completed',
                    'current_step': 'Бэкап создан успешно',
                    'progress_percent': 100,
                    'end_time': datetime.now(),
                    'result_data': {
                        'backup_id': backup_id,
                        'filename': f"{backup_id}.tar.gz",
                        'size': os.path.getsize(archive_path),
                        'tables': tables
                    }
                })
                
                print(f"✅ Бэкап {backup_id} создан успешно")
                print(f"📁 Файл: {archive_path}")
                print(f"📊 Размер: {os.path.getsize(archive_path)} байт")
                
        except Exception as e:
            print(f"❌ Ошибка создания бэкапа: {e}")
            print(f"❌ Error details: {traceback.format_exc()}")
            
            await self.db.update_background_task(task_id, **{
                'status': 'error',
                'current_step': 'Ошибка создания бэкапа',
                'error_message': str(e),
                'end_time': datetime.now()
            })

    async def process_epss_download_task(self, task_id: int, parameters: Dict[str, Any]):
        """Обработка задачи загрузки EPSS данных"""
        try:
            print(f"🔄 Начинаем загрузку EPSS для задачи {task_id}")
            
            # Получаем параметры
            url = parameters.get('url', 'https://epss.empiricalsecurity.com/epss_scores-current.csv.gz')
            
            # Обновляем статус задачи
            await self.db.update_background_task(task_id, **{
                'status': 'processing',
                'current_step': 'Начинаем загрузку EPSS данных',
                'start_time': datetime.now()
            })
            
            # Импортируем необходимые модули
            import aiohttp
            import gzip
            import io
            import csv
            
            print(f"📥 Downloading EPSS from {url}")
            
            # Обновляем прогресс в начале скачивания
            await self.db.update_background_task(task_id, **{
                'current_step': 'Скачивание файла',
                'progress_percent': 10
            })
            
            # Увеличиваем таймауты для больших файлов
            timeout = aiohttp.ClientTimeout(total=300, connect=60)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url, allow_redirects=True) as resp:
                    if resp.status != 200:
                        raise Exception(f"Failed to download: {resp.status} - {resp.reason}")
                    
                    print("📦 Reading compressed content...")
                    gz_content = await resp.read()
                    print(f"📊 Downloaded {len(gz_content)} bytes")
            
            await self.db.update_background_task(task_id, **{
                'current_step': 'Распаковка и обработка данных',
                'progress_percent': 15
            })
            
            print("🔓 Decompressing content...")
            with gzip.GzipFile(fileobj=io.BytesIO(gz_content)) as gz:
                decoded = gz.read().decode('utf-8').splitlines()
            
            print(f"📄 Decompressed {len(decoded)} lines")
            
            # Ищем строку с заголовками (пропускаем метаданные)
            header_line = None
            for i, line in enumerate(decoded):
                if line.startswith('cve,') or 'cve' in line.split(',')[0]:
                    header_line = i
                    break
            
            if header_line is None:
                raise Exception("Could not find header line with 'cve' column")
            
            print(f"📋 Found header at line {header_line}")
            
            # Создаем CSV reader начиная с найденной строки заголовков
            reader = csv.DictReader(decoded[header_line:])
            
            print("🔄 Processing CSV records...")
            records = []
            processed_count = 0
            
            # Обновляем прогресс в начале обработки
            await self.db.update_background_task(task_id, **{
                'current_step': 'Обработка CSV записей',
                'progress_percent': 20
            })
            
            for row in reader:
                try:
                    records.append({
                        'cve': row['cve'],
                        'epss': float(row['epss']),
                        'percentile': float(row['percentile']),
                        'cvss': None,  # Поле отсутствует в исходном файле EPSS
                        'date': None   # Поле отсутствует в исходном файле EPSS
                    })
                    processed_count += 1
                    
                    # Показываем прогресс каждые 10000 записей
                    if processed_count % 10000 == 0:
                        print(f"📊 Processed {processed_count} records...")
                        progress_percent = int((processed_count / len(records)) * 100) if records else 0
                        await self.db.update_background_task(task_id, **{
                            'current_step': f'Обработано {processed_count} записей',
                            'processed_records': processed_count,
                            'progress_percent': progress_percent
                        })
                        
                except (ValueError, KeyError) as e:
                    print(f"⚠️ Skipping invalid row: {e}, row data: {row}")
                    continue
            
            print(f"✅ Processed {len(records)} valid records")
            
            await self.db.update_background_task(task_id, **{
                'current_step': 'Сохранение в базу данных',
                'total_records': len(records),
                'processed_records': len(records),
                'progress_percent': 80
            })
            
            print("💾 Inserting records into database...")
            
            # Сохраняем в базу данных
            from database.epss_repository import EPSSRepository
            epss_repo = EPSSRepository()
            await epss_repo.insert_records(records)
            
            # Обновляем прогресс после сохранения
            await self.db.update_background_task(task_id, **{
                'current_step': 'Завершение обработки',
                'progress_percent': 95
            })
            
            print("🎉 EPSS download and processing completed successfully")
            
            # Завершаем задачу
            await self.db.update_background_task(task_id, **{
                'status': 'completed',
                'current_step': 'Загрузка EPSS завершена успешно',
                'processed_records': len(records),
                'progress_percent': 100,
                'end_time': datetime.now()
            })
            
        except Exception as e:
            print(f"Error in process_epss_download_task: {e}")
            await self.db.update_background_task(task_id, **{
                'status': 'error',
                'current_step': 'Ошибка загрузки EPSS',
                'error_message': str(e),
                'end_time': datetime.now()
            })

    async def process_vm_import_task(self, task_id: int, parameters: Dict[str, Any]):
        """Обработать задачу импорта VM данных"""
        try:
            print(f"🔄 Начинаем обработку задачи импорта VM {task_id}")
            
            # Создаем VM Worker
            vm_worker = VMWorker()
            
            # Запускаем импорт
            result = await vm_worker.start_import(task_id, parameters)
            
            if result.get('success'):
                print(f"✅ Импорт VM данных завершен успешно: {result.get('count', 0)} хостов")
            else:
                print(f"❌ Импорт VM данных завершен с ошибкой: {result.get('message', 'Неизвестная ошибка')}")
                
        except Exception as e:
            print(f"❌ Ошибка в process_vm_import_task: {e}")
            print(f"❌ Traceback: {traceback.format_exc()}")
            
            await self.db.update_background_task(task_id, **{
                'status': 'error',
                'current_step': 'Ошибка импорта VM данных',
                'error_message': str(e),
                'end_time': datetime.now()
            })

    async def process_vm_manual_import_task(self, task_id: int, parameters: Dict[str, Any]):
        """Обработать задачу ручного импорта VM данных"""
        try:
            print(f"🔄 Начинаем обработку задачи ручного импорта VM {task_id}")
            
            # Создаем VM Worker
            vm_worker = VMWorker()
            
            # Запускаем ручной импорт
            result = await vm_worker.start_manual_import(task_id, parameters)
            
            if result.get('success'):
                print(f"✅ Ручной импорт VM данных завершен успешно: {result.get('count', 0)} хостов")
            else:
                print(f"❌ Ручной импорт VM данных завершен с ошибкой: {result.get('message', 'Неизвестная ошибка')}")
                
        except Exception as e:
            print(f"❌ Ошибка в process_vm_manual_import_task: {e}")
            print(f"❌ Traceback: {traceback.format_exc()}")
            
            await self.db.update_background_task(task_id, **{
                'status': 'error',
                'current_step': 'Ошибка ручного импорта VM данных',
                'error_message': str(e),
                'end_time': datetime.now()
            })

# Глобальный экземпляр планировщика
scheduler_service = SchedulerService()
