"""
Сервис планировщика задач для автоматического обновления данных
"""
import asyncio
import schedule
import time
import csv
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from pathlib import Path
from database import get_db
from utils.file_utils import split_file_by_size, extract_compressed_file
from utils.validation_utils import is_valid_ip
import traceback

class SchedulerService:
    def __init__(self):
        self.db = get_db()
        self.running = False
        self.tasks = {}
    
    async def start_scheduler(self):
        """Запустить планировщик"""
        if self.running:
            return
        
        self.running = True
        print("🕐 Scheduler started")
        
        # Настраиваем расписание
        schedule.every().day.at("02:00").do(self._run_async_task, self.daily_update)
        schedule.every().hour.do(self._run_async_task, self.hourly_check)
        schedule.every(30).minutes.do(self._run_async_task, self.cleanup_old_data)
        schedule.every(10).seconds.do(self._run_async_task, self.process_background_tasks)
        
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
        while self.running:
            try:
                schedule.run_pending()
                # Делаем цикл более отзывчивым: проверяем pending каждые 1 секунду
                await asyncio.sleep(1)
            except Exception as e:
                print(f"❌ Ошибка в основном цикле планировщика: {e}")
                print(f"❌ Error details: {traceback.format_exc()}")
                await asyncio.sleep(1)  # Продолжаем работу
    
    async def daily_update(self):
        """Ежедневное обновление данных"""
        try:
            print("🔄 Starting daily update")
            
            # Проверяем, не запущено ли уже обновление
            existing_task = await self.db.get_background_task_by_type('hosts_update')
            if existing_task and existing_task['status'] in ['processing', 'initializing']:
                print("⚠️ Update already running, skipping daily update")
                return
            
            # Запускаем инкрементальное обновление
            result = await self.db.update_hosts_incremental(days_old=1)
            
            if result['success']:
                print(f"✅ Daily update completed: {result['updated_count']} hosts updated")
            else:
                print(f"❌ Daily update failed: {result['message']}")
                
        except Exception as e:
            print(f"❌ Error in daily update: {e}")
    
    async def hourly_check(self):
        """Ежечасная проверка системы"""
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
            
            # Обработка частей
            total_records = 0
            total_processed_lines = 0
            
            # Сначала подсчитаем общее количество записей для установки total_records
            total_expected_records = 0
            for part_content in parts:
                part_lines = part_content.splitlines()
                reader = csv.DictReader(part_lines, delimiter=';')
                total_expected_records += len(list(reader))
            
            print(f"📊 Ожидается обработка {total_expected_records} записей")
            
            # Обновляем задачу с общим количеством записей
            await self.db.update_background_task(task_id, **{
                'total_records': total_expected_records,
                'processed_records': 0
            })
            
            for part_index, part_content in enumerate(parts, 1):
                await self.db.update_background_task(task_id, **{
                    'current_step': f'Обработка части {part_index} из {total_parts}',
                    'processed_items': part_index,
                    'total_items': total_parts
                })
                
                # Парсим CSV
                part_lines = part_content.splitlines()
                reader = csv.DictReader(part_lines, delimiter=';')
                
                part_records = []
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
                        
                        part_records.append({
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
                
                # Сохраняем в базу данных
                await self.db.update_background_task(task_id, **{
                    'current_step': f'Сохранение части {part_index} в базу данных'
                })
                
                print(f"💾 Начинаем сохранение {len(part_records)} записей в базу данных...")
                
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
                            'total_records': total_expected_records
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
                        print(f"📊 Прогресс задачи {task_id}: {message} ({progress_percent:.1f}%) - {current_processed}/{total_expected_records}")
                    except Exception as e:
                        print(f"⚠️ Ошибка обновления прогресса: {e}")
                        import traceback
                        print(f"⚠️ Traceback: {traceback.format_exc()}")
                
                await self.db.insert_hosts_records_with_progress(part_records, update_progress)
                print(f"✅ Сохранение завершено")
                
                total_records += len(part_records)
                total_processed_lines += len(part_lines)
                
                await self.db.update_background_task(task_id, **{
                    'processed_items': part_index,
                    'total_items': total_parts,
                    'processed_records': total_records,
                    'total_records': total_records
                })
            
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
                
                for task in idle_tasks:
                    task_id = task['id']
                    task_type = task['task_type']
                    parameters_str = task.get('parameters', '{}')
                    
                    print(f"🔄 Обрабатываем фоновую задачу {task_id} типа {task_type}")
                    print(f"📋 Параметры задачи: {parameters_str}")
                    
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
        """Проверить зависшие задачи (processing более 10 минут)"""
        try:
            conn = await self.db.get_connection()
            
            # Ищем задачи в статусе processing, которые не обновлялись более 10 минут
            query = """
                SELECT id, task_type, status, current_step, created_at, updated_at, start_time
                FROM vulnanalizer.background_tasks 
                WHERE status IN ('processing', 'initializing')
                AND updated_at < NOW() - INTERVAL '10 minutes'
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
    
    async def cleanup_old_data(self):
        """Очистка старых данных"""
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
                await self.db.update_background_task(task_id, **{
                    'status': 'completed',
                    'current_step': 'Нет хостов для расчета рисков',
                    'end_time': datetime.now()
                })
                return
            
            total_cves = len(cve_rows)
            print(f"🔍 Найдено {total_cves} CVE для расчета рисков")
            
            # Обновляем общее количество
            await self.db.update_background_task(task_id, **{
                'total_items': total_cves,
                'current_step': f'Найдено {total_cves} CVE для расчета рисков'
            })
            
            # Получаем настройки
            settings_query = "SELECT key, value FROM vulnanalizer.settings"
            settings_rows = await conn.fetch(settings_query)
            settings = {row['key']: row['value'] for row in settings_rows}
            
            # Создаем функцию обратного вызова для прогресса
            async def update_progress(step: str, message: str, progress_percent: int = 0, **kwargs):
                await self.db.update_background_task(task_id, **{
                    'current_step': message,
                    'progress_percent': progress_percent,
                    'processed_items': kwargs.get('processed_cves', 0),
                    'total_items': total_cves,
                    'processed_records': kwargs.get('updated_hosts', 0)
                })
            
            # Используем полное обновление хостов
            await self.db.risk_calculation.update_hosts_complete(update_progress)
            
            # Завершаем задачу
            await self.db.update_background_task(task_id, **{
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
                await self.db.update_background_task(task_id, **{
                    'status': 'completed',
                    'current_step': 'Нет хостов для пересчета рисков',
                    'end_time': datetime.now()
                })
                return
            
            total_cves = len(cve_rows)
            print(f"🔍 Найдено {total_cves} CVE для пересчета рисков")
            
            # Обновляем общее количество
            await self.db.update_background_task(task_id, **{
                'total_items': total_cves,
                'current_step': f'Найдено {total_cves} CVE для пересчета рисков'
            })
            
            # Получаем настройки
            settings_query = "SELECT key, value FROM vulnanalizer.settings"
            settings_rows = await conn.fetch(settings_query)
            settings = {row['key']: row['value'] for row in settings_rows}
            
            # Создаем функцию обратного вызова для прогресса
            async def update_progress(step: str, message: str, progress_percent: int = 0, **kwargs):
                await self.db.update_background_task(task_id, **{
                    'current_step': message,
                    'progress_percent': progress_percent,
                    'processed_items': kwargs.get('processed_cves', 0),
                    'total_items': total_cves,
                    'processed_records': kwargs.get('updated_hosts', 0)
                })
            
            # Используем специальный метод для пересчета рисков
            await self.db.risk_calculation.recalculate_all_risks(update_progress)
            
            # Завершаем задачу
            await self.db.update_background_task(task_id, **{
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

# Глобальный экземпляр планировщика
scheduler_service = SchedulerService()
