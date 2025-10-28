"""
VM MaxPatrol Worker для импорта данных
"""
import csv
import io
import json
import os
import requests
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime
from database import get_db
from database.risk_calculation import calculate_risk_score
from services.simple_logging_service import simple_logging_service
from utils.json_splitter import JSONSplitter
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
    
    def _get_latest_vm_data_file(self) -> Optional[str]:
        """Получить путь к последнему созданному файлу данных VM"""
        try:
            if not os.path.exists(self.vm_data_dir):
                return None
            
            vm_files = []
            for filename in os.listdir(self.vm_data_dir):
                # Ищем только исходные файлы VM (без суффикса _filtered)
                if filename.startswith("vm_data_") and filename.endswith(".json") and "_filtered" not in filename:
                    file_path = os.path.join(self.vm_data_dir, filename)
                    # Получаем время создания файла
                    mtime = os.path.getmtime(file_path)
                    vm_files.append((file_path, mtime))
            
            if not vm_files:
                return None
            
            # Сортируем по времени создания (последний созданный)
            vm_files.sort(key=lambda x: x[1], reverse=True)
            latest_file = vm_files[0][0]
            
            print(f"📁 Найден последний файл VM данных: {os.path.basename(latest_file)}")
            return latest_file
            
        except Exception as e:
            print(f"⚠️ Ошибка поиска файла VM данных: {e}")
            return None
    
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
    
    async def _load_vm_data_from_file(self, task_id: int, file_path: str = None) -> List[Dict[str, str]]:
        """Загрузить данные VM из JSON файла"""
        try:
            # Если путь не указан, получаем путь к файлу данных VM
            if not file_path:
                file_path = self._get_latest_vm_data_file()
                
            if not file_path or not os.path.exists(file_path):
                raise Exception(f"Файл данных VM не найден: {file_path}")
            
            file_size = os.path.getsize(file_path)
            print(f"📁 Загружаем файл VM данных: {os.path.basename(file_path)} ({file_size / (1024*1024):.1f} MB)")
            
            # Загружаем данные
            if file_size > 100 * 1024 * 1024:  # 100MB
                print(f"🔄 Используем потоковую загрузку для файла")
                vm_data = await self._load_large_json_file(file_path, task_id)
            else:
                # Для небольших файлов используем обычную загрузку
                with open(file_path, 'r', encoding='utf-8') as f:
                    vm_data = json.load(f)
            
            await self._log('info', f"Данные VM загружены из файла: {file_path}", {
                "file_path": file_path,
                "records_count": len(vm_data),
                "file_size_mb": round(file_size / (1024*1024), 2)
            })
            
            return vm_data
            
        except Exception as e:
            error_msg = f"Ошибка загрузки данных VM из файла: {str(e)}"
            await self._log('error', error_msg)
            raise Exception(error_msg)
    
    async def _load_large_json_file(self, file_path: str, task_id: int) -> List[Dict[str, str]]:
        """Потоковая загрузка большого JSON файла с использованием ijson"""
        try:
            import ijson
            
            file_size = os.path.getsize(file_path)
            print(f"🔄 Начинаем потоковую загрузку файла {os.path.basename(file_path)} ({file_size / (1024*1024):.1f} MB)")
            
            vm_data = []
            processed_count = 0
            
            # Обновляем прогресс
            await self.db.update_background_task(task_id, **{
                'current_step': 'Потоковая загрузка JSON данных',
                'progress_percent': 10
            })
            
            # Используем ijson для потокового парсинга
            with open(file_path, 'rb') as f:
                # Парсим JSON массив по элементам
                parser = ijson.items(f, 'item')
                
                for item in parser:
                    vm_data.append(item)
                    processed_count += 1
                    
                    # Обновляем прогресс каждые 10000 записей
                    if processed_count % 10000 == 0:
                        progress = min(90, 10 + (processed_count / 100000) * 80)  # Предполагаем ~100k записей
                        await self.db.update_background_task(task_id, **{
                            'current_step': f'Загружено {processed_count} записей',
                            'progress_percent': int(progress)
                        })
                        # Обновляем активность задачи
                        await self._update_task_activity(task_id, f"Загружено {processed_count} записей")
                        print(f"📊 Загружено {processed_count} записей...")
            
            await self.db.update_background_task(task_id, **{
                'current_step': 'Данные загружены',
                'progress_percent': 100
            })
            
            print(f"✅ Потоковая загрузка завершена: {len(vm_data)} записей")
            return vm_data
            
        except ImportError:
            print("⚠️ ijson не установлен, используем обычную загрузку")
            # Fallback к обычной загрузке
            await self.db.update_background_task(task_id, **{
                'current_step': 'Загрузка JSON данных (обычный режим)',
                'progress_percent': 50
            })
            
            with open(file_path, 'r', encoding='utf-8') as f:
                vm_data = json.load(f)
            
            await self.db.update_background_task(task_id, **{
                'current_step': 'Данные загружены',
                'progress_percent': 100
            })
            
            print(f"✅ Обычная загрузка завершена: {len(vm_data)} записей")
            return vm_data
            
        except Exception as e:
            print(f"❌ Ошибка потоковой загрузки: {e}")
            raise Exception(f"Ошибка потоковой загрузки файла: {str(e)}")
    
    async def _apply_filters_to_large_file(self, file_path: str, task_id: int, 
                                         criticality_filter: str = None, 
                                         os_filter: str = None, 
                                         zone_filter: str = None) -> str:
        """
        Применить фильтры к большому файлу ДО разбивки
        
        Args:
            file_path: Путь к исходному файлу
            task_id: ID задачи для обновления прогресса
            criticality_filter: Фильтр критичности
            os_filter: Фильтр ОС
            zone_filter: Фильтр зоны
            
        Returns:
            Путь к отфильтрованному файлу
        """
        try:
            import ijson
            
            file_size = os.path.getsize(file_path)
            print(f"🔍 Применяем фильтры к файлу {os.path.basename(file_path)} ({file_size / (1024*1024):.1f} MB)")
            
            await self.db.update_background_task(task_id, **{
                'current_step': 'Потоковая фильтрация исходного файла',
                'progress_percent': 5
            })
            await self._update_task_activity(task_id, "Начинаем потоковую фильтрацию")
            
            # Создаем путь для отфильтрованного файла
            file_dir = os.path.dirname(file_path)
            file_name = os.path.splitext(os.path.basename(file_path))[0]
            filtered_file_path = os.path.join(file_dir, f"{file_name}_filtered.json")
            
            filtered_count = 0
            total_count = 0
            
            # Потоковая фильтрация с записью в новый файл
            with open(file_path, 'rb') as input_file, open(filtered_file_path, 'w', encoding='utf-8') as output_file:
                output_file.write('[')  # Начинаем JSON массив
                first_item = True
                
                parser = ijson.items(input_file, 'item')
                
                for item in parser:
                    total_count += 1
                    
                    # Применяем фильтры
                    if self._matches_filters(item, criticality_filter, os_filter, zone_filter):
                        if not first_item:
                            output_file.write(',\n')
                        json.dump(item, output_file, ensure_ascii=False, indent=2)
                        first_item = False
                        filtered_count += 1
                    
                    # Обновляем прогресс каждые 10000 записей
                    if total_count % 10000 == 0:
                        progress = min(80, 5 + (total_count / 100000) * 75)  # Предполагаем ~100k записей
                        await self.db.update_background_task(task_id, **{
                            'current_step': f'Отфильтровано {filtered_count} из {total_count} записей',
                            'progress_percent': int(progress)
                        })
                        await self._update_task_activity(task_id, f"Отфильтровано {filtered_count} из {total_count} записей")
                        print(f"📊 Отфильтровано {filtered_count} из {total_count} записей...")
                
                output_file.write('\n]')  # Заканчиваем JSON массив
            
            await self.db.update_background_task(task_id, **{
                'current_step': f'Фильтрация завершена: {filtered_count} из {total_count} записей',
                'progress_percent': 80
            })
            await self._update_task_activity(task_id, f"Фильтрация завершена: {filtered_count} из {total_count} записей")
            
            print(f"✅ Потоковая фильтрация завершена: {filtered_count} из {total_count} записей")
            print(f"📁 Отфильтрованный файл: {os.path.basename(filtered_file_path)}")
            
            return filtered_file_path
            
        except ImportError:
            print("⚠️ ijson не установлен, используем обычную фильтрацию")
            # Fallback к обычной фильтрации
            return await self._apply_filters_fallback(file_path, task_id, criticality_filter, os_filter, zone_filter)
        except Exception as e:
            print(f"❌ Ошибка потоковой фильтрации: {e}")
            raise Exception(f"Ошибка потоковой фильтрации файла: {str(e)}")
    
    async def _apply_filters_fallback(self, file_path: str, task_id: int, 
                                   criticality_filter: str = None, 
                                   os_filter: str = None, 
                                   zone_filter: str = None) -> str:
        """Fallback метод фильтрации для случаев без ijson"""
        try:
            await self.db.update_background_task(task_id, **{
                'current_step': 'Загрузка файла для фильтрации (обычный режим)',
                'progress_percent': 20
            })
            
            with open(file_path, 'r', encoding='utf-8') as f:
                vm_data = json.load(f)
            
            await self.db.update_background_task(task_id, **{
                'current_step': 'Применение фильтров к загруженным данным',
                'progress_percent': 50
            })
            
            filtered_data = []
            for item in vm_data:
                if self._matches_filters(item, criticality_filter, os_filter, zone_filter):
                    filtered_data.append(item)
            
            # Сохраняем отфильтрованные данные
            file_dir = os.path.dirname(file_path)
            file_name = os.path.splitext(os.path.basename(file_path))[0]
            filtered_file_path = os.path.join(file_dir, f"{file_name}_filtered.json")
            
            with open(filtered_file_path, 'w', encoding='utf-8') as f:
                json.dump(filtered_data, f, ensure_ascii=False, indent=2)
            
            await self.db.update_background_task(task_id, **{
                'current_step': f'Фильтрация завершена: {len(filtered_data)} из {len(vm_data)} записей',
                'progress_percent': 80
            })
            
            print(f"✅ Обычная фильтрация завершена: {len(filtered_data)} из {len(vm_data)} записей")
            return filtered_file_path
            
        except Exception as e:
            print(f"❌ Ошибка обычной фильтрации: {e}")
            raise Exception(f"Ошибка фильтрации файла: {str(e)}")
    
    def _matches_filters(self, item: dict, criticality_filter: str = None, 
                        os_filter: str = None, zone_filter: str = None) -> bool:
        """Проверить, соответствует ли запись фильтрам"""
        try:
            # Фильтр критичности
            if criticality_filter:
                item_criticality = item.get('criticality', '').lower()
                if criticality_filter.lower() not in item_criticality:
                    return False
            
            # Фильтр ОС
            if os_filter:
                item_os = item.get('os_name', '').lower()
                if os_filter.lower() not in item_os:
                    return False
            
            # Фильтр зоны
            if zone_filter:
                item_zone = item.get('zone', '').lower()
                if zone_filter.lower() not in item_zone:
                    return False
            
            return True
        except Exception:
            return False

    async def _split_large_file_if_needed(self, file_path: str, task_id: int) -> List[str]:
        """
        Разбить большой файл на части если необходимо
        
        Args:
            file_path: Путь к файлу
            task_id: ID задачи для обновления прогресса
            
        Returns:
            Список путей к файлам для обработки (исходный файл или все части)
        """
        try:
            file_size = os.path.getsize(file_path)
            max_size_mb = 200  # Максимальный размер файла в MB
            
            if file_size <= max_size_mb * 1024 * 1024:
                print(f"📁 Файл {os.path.basename(file_path)} ({file_size / (1024*1024):.1f} MB) не требует разбивки")
                return [file_path]
            
            print(f"🔄 Файл {os.path.basename(file_path)} ({file_size / (1024*1024):.1f} MB) слишком большой, разбиваем на части")
            
            await self.db.update_background_task(task_id, **{
                'current_step': 'Разбивка большого файла на части',
                'progress_percent': 5
            })
            
            # Создаем директорию для частей
            file_dir = os.path.dirname(file_path)
            file_name = os.path.splitext(os.path.basename(file_path))[0]
            parts_dir = os.path.join(file_dir, f"{file_name}_parts")
            
            # Разбиваем файл
            splitter = JSONSplitter(records_per_file=50000)  # 50k записей в части
            created_files = splitter.split_json_file(file_path, parts_dir)
            
            await self.db.update_background_task(task_id, **{
                'current_step': f'Файл разбит на {len(created_files)} частей',
                'progress_percent': 10
            })
            
            print(f"✅ Файл разбит на {len(created_files)} частей")
            await self._log('info', f"Файл разбит на {len(created_files)} частей", {
                "original_file": file_path,
                "parts_count": len(created_files),
                "parts_dir": parts_dir
            })
            
            # Возвращаем все части для обработки
            return created_files
            
        except Exception as e:
            print(f"❌ Ошибка разбивки файла: {e}")
            await self._log('error', f"Ошибка разбивки файла: {str(e)}")
            # В случае ошибки возвращаем исходный файл
            return [file_path]
    
    async def _update_task_activity(self, task_id: int, activity_message: str = None):
        """Обновить активность задачи"""
        try:
            await self.db.update_background_task(task_id, **{
                'last_activity_at': datetime.now(),
                'activity_count': await self._get_activity_count(task_id) + 1
            })
            
            if activity_message:
                print(f"🔄 [{task_id}] {activity_message}")
                
        except Exception as e:
            print(f"⚠️ Ошибка обновления активности задачи {task_id}: {e}")
    
    async def _get_activity_count(self, task_id: int) -> int:
        """Получить текущий счетчик активности"""
        try:
            conn = await self.db.get_connection()
            try:
                count = await conn.fetchval(
                    "SELECT activity_count FROM vulnanalizer.background_tasks WHERE id = $1",
                    task_id
                )
                return count or 0
            finally:
                await self.db.release_connection(conn)
        except Exception:
            return 0
    
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
    
    async def _cleanup_vm_imports_folder(self, task_id: int, keep_original_file: str = None) -> None:
        """
        Очистить папку vm_imports от всех созданных файлов, кроме исходного
        
        Args:
            task_id: ID задачи для обновления прогресса
            keep_original_file: Путь к исходному файлу, который нужно сохранить
        """
        try:
            vm_imports_dir = os.path.join(self.data_dir, 'vm_imports')
            if not os.path.exists(vm_imports_dir):
                return
            
            await self.db.update_background_task(task_id, **{
                'current_step': 'Очистка временных файлов',
                'progress_percent': 0
            })
            await self._update_task_activity(task_id, "Очистка временных файлов")
            
            deleted_files = []
            kept_files = []
            
            for filename in os.listdir(vm_imports_dir):
                file_path = os.path.join(vm_imports_dir, filename)
                
                # Пропускаем директории
                if os.path.isdir(file_path):
                    continue
                
                # Сохраняем исходный файл
                if keep_original_file and os.path.samefile(file_path, keep_original_file):
                    kept_files.append(filename)
                    continue
                
                # Удаляем все остальные файлы
                try:
                    os.remove(file_path)
                    deleted_files.append(filename)
                except Exception as e:
                    print(f"⚠️ Не удалось удалить файл {filename}: {e}")
            
            print(f"🧹 Очистка завершена: удалено {len(deleted_files)} файлов, сохранено {len(kept_files)} файлов")
            if deleted_files:
                print(f"🗑️ Удаленные файлы: {', '.join(deleted_files)}")
            if kept_files:
                print(f"💾 Сохраненные файлы: {', '.join(kept_files)}")
                
            await self._log('info', f"Очистка папки vm_imports завершена", {
                "deleted_files": deleted_files,
                "kept_files": kept_files
            })
            
        except Exception as e:
            print(f"❌ Ошибка очистки папки vm_imports: {e}")
            await self._log('error', f"Ошибка очистки папки vm_imports: {e}")

    async def start_manual_import(self, task_id: int, parameters: Dict[str, Any]) -> Dict:
        """Запустить ручной импорт данных из сохраненного файла VM с предварительной очисткой"""
        try:
            print(f"🚀 Начинаем ручной импорт VM данных для задачи {task_id}")
            print(f"📋 Параметры: {parameters}")
            
            # Получаем фильтры из параметров
            criticality_filter = parameters.get('criticality_filter', '')
            os_filter = parameters.get('os_filter', '')
            zone_filter = parameters.get('zone_filter', '')
            
            print(f"🔍 Фильтр критичности: {criticality_filter}")
            print(f"🔍 Фильтр ОС: {os_filter}")
            print(f"🔍 Фильтр зоны: {zone_filter}")
            
            # Обновляем статус
            await self.db.update_background_task(task_id, **{
                'status': 'processing',
                'current_step': 'Инициализация импорта'
            })
            
            # Создаем логгер только если включено подробное логирование
            vm_settings = await self.db.get_vm_settings()
            if vm_settings.get('vm_detailed_logging') == 'true':
                self.logger = await simple_logging_service.create_task_logger(task_id, 'vm_manual_import')
                await self._log('info', "Начинаем ручной импорт VM данных", {"task_id": task_id, "parameters": parameters})
            
            # Этап 1: Получаем путь к файлу данных VM
            await self.db.update_background_task(task_id, **{
                'current_step': 'Поиск файла данных VM',
                'progress_percent': 1
            })
            await self._update_task_activity(task_id, "Поиск файла данных VM")
            
            vm_data_file_path = self._get_latest_vm_data_file()
            if not vm_data_file_path or not os.path.exists(vm_data_file_path):
                raise Exception(f"Файл данных VM не найден: {vm_data_file_path}")
            
            await self._log('info', f"Найден файл данных VM: {vm_data_file_path}")
            
            # Этап 1.5: Очищаем папку vm_imports от временных файлов
            await self._cleanup_vm_imports_folder(task_id, vm_data_file_path)
            
            # Этап 2: Применяем фильтры ДО разбивки файла
            file_to_process = vm_data_file_path
            
            if criticality_filter or os_filter or zone_filter:
                await self.db.update_background_task(task_id, **{
                    'current_step': 'Применение фильтров к исходному файлу',
                    'progress_percent': 5
                })
                await self._update_task_activity(task_id, "Применение фильтров к исходному файлу")
                
                file_to_process = await self._apply_filters_to_large_file(
                    vm_data_file_path, task_id, criticality_filter, os_filter, zone_filter
                )
                await self._log('info', f"Фильтры применены, файл для обработки: {file_to_process}")
            else:
                await self._log('info', "Фильтры не применены, используем исходный файл")
            
            # Этап 3: Разбиваем файл на части если необходимо
            await self.db.update_background_task(task_id, **{
                'current_step': 'Проверка необходимости разбивки файла',
                'progress_percent': 80
            })
            await self._update_task_activity(task_id, "Проверка необходимости разбивки файла")
            
            files_to_process = await self._split_large_file_if_needed(file_to_process, task_id)
            await self._log('info', f"Файлы для обработки: {files_to_process}")
            
            # Этап 4: Загружаем данные из всех файлов
            await self.db.update_background_task(task_id, **{
                'current_step': f'Загрузка данных из {len(files_to_process)} файлов',
                'progress_percent': 85
            })
            await self._update_task_activity(task_id, f"Загрузка данных из {len(files_to_process)} файлов")
            await self._log('info', f"Начинаем загрузку данных из {len(files_to_process)} файлов")
            
            # Загружаем данные из всех файлов
            all_vm_data = []
            for i, file_path in enumerate(files_to_process):
                await self.db.update_background_task(task_id, **{
                    'current_step': f'Загрузка файла {i+1} из {len(files_to_process)}: {os.path.basename(file_path)}',
                    'progress_percent': 85 + (i * 5 // len(files_to_process))
                })
                
                vm_data_from_file = await self._load_vm_data_from_file(task_id, file_path)
                all_vm_data.extend(vm_data_from_file)
                await self._log('info', f"Загружено {len(vm_data_from_file)} записей из файла {os.path.basename(file_path)}")
            
            vm_data_from_file = all_vm_data
            await self._log('info', f"Всего загружено {len(vm_data_from_file)} записей из всех файлов")
            
            # Этап 5: Очищаем данные от дублей и пустых записей
            await self.db.update_background_task(task_id, **{
                'current_step': 'Очистка данных от дублей и пустых записей',
                'progress_percent': 90
            })
            await self._update_task_activity(task_id, "Очистка данных от дублей и пустых записей")
            await self._log('info', "Начинаем очистку данных от дублей и пустых записей")
            
            # Создаем функцию обновления прогресса для очистки
            async def update_cleanup_progress(step, message, progress_percent):
                await self.db.update_background_task(task_id, **{
                    'current_step': message,
                    'progress_percent': progress_percent
                })
                await self._update_task_activity(task_id, message)
            
            clean_records = await self._clean_import_data_async(vm_data_from_file, task_id, update_cleanup_progress)
            await self._log('info', f"После очистки: {len(clean_records)} записей (удалено {len(vm_data_from_file) - len(clean_records)} дублей/пустых)")
            
            # Этап 6: Сохраняем очищенные данные в базу
            await self.db.update_background_task(task_id, **{
                'current_step': 'Сохранение данных в базу',
                'progress_percent': 95
            })
            await self._update_task_activity(task_id, "Сохранение данных в базу")
            await self._log('info', f"Начинаем сохранение {len(clean_records)} записей в базу данных")
            
            # Создаем функцию обновления прогресса для сохранения
            async def update_save_progress(step, message, progress_percent):
                await self.db.update_background_task(task_id, **{
                    'current_step': message,
                    'progress_percent': progress_percent
                })
                await self._update_task_activity(task_id, message)
            
            saved_count = await self._save_clean_records_to_db(clean_records, task_id, update_save_progress)
            await self._log('info', f"Сохранено {saved_count} записей в базу данных")
            
            # Этап 7: Расчет рисков уже выполнен в _save_hosts_with_risks
            await self.db.update_background_task(task_id, **{
                'current_step': 'Расчет рисков завершен',
                'progress_percent': 98
            })
            await self._update_task_activity(task_id, "Расчет рисков завершен")
            await self._log('info', "Расчет рисков для импортированных хостов завершен")
            
            # Удаляем файл после успешного импорта
            try:
                file_path = self._get_vm_data_file_path(task_id)
                os.remove(file_path)
                await self._log('info', f"Файл данных VM удален: {file_path}")
            except Exception as e:
                await self._log('warning', f"Не удалось удалить файл данных VM: {e}")
            
            # Завершаем задачу
            await self.db.update_background_task(task_id, **{
                'status': 'completed',
                'current_step': 'Ручной импорт VM данных завершен',
                'progress_percent': 100,
                'end_time': datetime.now()
            })
            await self._update_task_activity(task_id, "Ручной импорт VM данных завершен")
            await self._log('info', f"Ручной импорт VM данных успешно завершен. Обработано {saved_count} записей")
            print(f"✅ Ручной импорт VM данных завершен: {saved_count} записей")
            
            # Закрываем логгер
            if self.logger:
                await self.logger.close()
            
            return {
                "success": True,
                "count": saved_count,
                "message": f"Импортировано {saved_count} записей из файла VM"
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
            
            # Подсчитываем количество строк в CSV для отладки
            csv_lines = csv_content.split('\n')
            non_empty_lines = [line for line in csv_lines if line.strip()]
            if self.logger:
                await self._log('debug', f"Всего строк в CSV: {len(csv_lines)}, непустых строк: {len(non_empty_lines)}")
            
            # CSV файл больше не сохраняем для дебага
            
            # Парсим CSV построчно для лучшего контроля
            csv_lines = csv_content.split('\n')
            if not csv_lines:
                raise Exception("CSV файл пуст")
            
            # Получаем заголовки из первой строки
            header_line = csv_lines[0]
            headers = [h.strip('"') for h in header_line.split(';')]
            
            if self.logger:
                await self._log('debug', f"Заголовки CSV: {headers}")
            
            vm_data = []
            row_count = 0
            
            # Обрабатываем строки данных (пропускаем заголовок)
            for line in csv_lines[1:]:
                if not line.strip():  # Пропускаем пустые строки
                    continue
                    
                row_count += 1
                
                # Парсим строку вручную
                values = [v.strip('"') for v in line.split(';')]
                if len(values) != len(headers):
                    if self.logger:
                        await self._log('warning', f"Строка {row_count}: несоответствие количества колонок ({len(values)} != {len(headers)})")
                    continue
                
                row_dict = dict(zip(headers, values))
                
                if self.logger and row_count <= 5:  # Логируем первые 5 строк для отладки
                    await self._log('debug', f"Строка {row_count}: {row_dict}")
                
                # Логируем каждые 10000 записей для отслеживания прогресса
                if self.logger and row_count % 10000 == 0:
                    await self._log('debug', f"Обработано {row_count} строк CSV...")
                
                vm_data.append({
                    'host': row_dict.get('@Host', '').strip('"'),
                    'os_name': row_dict.get('Host.OsName', '').strip('"'),
                    'groups': row_dict.get('Host.@Groups', '').strip('"'),
                    'cve': row_dict.get('Host.@Vulners.CVEs', '').strip('"'),
                    'criticality': row_dict.get('Host.UF_Criticality', '').strip('"'),
                    'zone': row_dict.get('Host.UF_Zone', '').strip('"')
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
    
    def _clean_import_data(self, raw_records: list) -> list:
        """Очистка данных от дублей и пустых записей для формата VM"""
        print(f"🧹 Начинаем очистку {len(raw_records)} записей")
        
        # Удаляем пустые записи
        non_empty_records = []
        for record in raw_records:
            # Проверяем, что все обязательные поля заполнены для формата VM
            if (record.get('host') and record.get('host').strip() and
                record.get('cve') and record.get('cve').strip()):
                non_empty_records.append(record)
        
        print(f"🧹 После удаления пустых: {len(non_empty_records)} записей")
        
        # Удаляем дубли по комбинации host + cve (для формата VM)
        seen_combinations = set()
        unique_records = []
        
        for record in non_empty_records:
            # Создаем уникальный ключ для проверки дублей
            key = (
                record.get('host', '').strip().lower(),
                record.get('cve', '').strip()
            )
            
            if key not in seen_combinations:
                seen_combinations.add(key)
                unique_records.append(record)
        
        print(f"🧹 После удаления дублей: {len(unique_records)} записей")
        print(f"🧹 Удалено {len(raw_records) - len(unique_records)} записей (пустые + дубли)")
        
        return unique_records

    async def _clean_import_data_async(self, raw_records: list, task_id: int, update_progress) -> list:
        """Асинхронная очистка данных от дублей и пустых записей для формата VM"""
        print(f"🧹 Начинаем очистку {len(raw_records)} записей")
        
        # Удаляем пустые записи
        non_empty_records = []
        total_records = len(raw_records)
        processed = 0
        
        for record in raw_records:
            # Проверяем, что все обязательные поля заполнены для формата VM
            if (record.get('host') and record.get('host').strip() and
                record.get('cve') and record.get('cve').strip()):
                non_empty_records.append(record)
            
            processed += 1
            if processed % 10000 == 0:
                progress_percent = (processed / total_records) * 50  # 50% на удаление пустых
                await update_progress('cleaning', f'Удаление пустых записей... ({processed}/{total_records})', progress_percent)
                await asyncio.sleep(0.001)
        
        print(f"🧹 После удаления пустых: {len(non_empty_records)} записей")
        
        # Удаляем дубли по комбинации host + cve (для формата VM)
        seen_combinations = set()
        unique_records = []
        processed = 0
        
        for record in non_empty_records:
            # Создаем уникальный ключ для проверки дублей
            key = (
                record.get('host', '').strip().lower(),
                record.get('cve', '').strip()
            )
            
            if key not in seen_combinations:
                seen_combinations.add(key)
                unique_records.append(record)
            
            processed += 1
            if processed % 10000 == 0:
                progress_percent = 50 + (processed / len(non_empty_records)) * 50  # 50-100% на удаление дублей
                await update_progress('cleaning', f'Удаление дублей... ({processed}/{len(non_empty_records)})', progress_percent)
                await asyncio.sleep(0.001)
        
        print(f"🧹 После удаления дублей: {len(unique_records)} записей")
        print(f"🧹 Удалено {len(raw_records) - len(unique_records)} записей (пустые + дубли)")
        
        return unique_records

    async def _apply_filters_async(self, records: list, criticality_filter: str, os_filter: str, zone_filter: str, task_id: int, update_progress) -> list:
        """Применение фильтров к записям для формата VM"""
        if not criticality_filter and not os_filter and not zone_filter:
            return records
        
        print(f"🔍 Применяем фильтры: критичность='{criticality_filter}', ОС='{os_filter}', зона='{zone_filter}'")
        
        filtered_records = []
        criticality_list = []
        
        # Парсим фильтр критичности
        if criticality_filter:
            criticality_list = [c.strip() for c in criticality_filter.split(',') if c.strip()]
            print(f"🔍 Список критичностей для фильтрации: {criticality_list}")
        
        total_records = len(records)
        processed = 0
        
        for i, record in enumerate(records):
            # Применяем фильтр критичности (поле criticality в формате VM)
            if criticality_list:
                record_criticality = record.get('criticality', '').strip()
                if record_criticality not in criticality_list:
                    continue
            
            # Применяем фильтр ОС (поле os_name в формате VM)
            if os_filter:
                record_os = record.get('os_name', '').strip()
                if os_filter.lower() not in record_os.lower():
                    continue
            
            # Применяем фильтр зоны (поле zone в формате VM)
            if zone_filter:
                record_zone = record.get('zone', '').strip()
                if zone_filter.lower() not in record_zone.lower():
                    continue
            
            filtered_records.append(record)
            
            # Обновляем прогресс каждые 10000 записей
            processed += 1
            if processed % 10000 == 0:
                progress_percent = (processed / total_records) * 100
                await update_progress('filtering', f'Фильтрация данных... ({processed}/{total_records})', progress_percent)
                # Небольшая пауза для освобождения event loop
                await asyncio.sleep(0.001)
        
        print(f"🔍 После фильтрации: {len(filtered_records)} записей (удалено {len(records) - len(filtered_records)})")
        return filtered_records

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
                    
                    # Обновляем активность задачи
                    await self._update_task_activity(task_id, message)
                    
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
    
    async def _save_clean_records_to_db(self, clean_records: List[Dict[str, str]], task_id: int, update_progress) -> int:
        """Сохранить очищенные записи в базу данных"""
        try:
            await self._log('info', f"Начинаем сохранение {len(clean_records)} очищенных записей в базу данных")
            
            # Группируем записи по хостам
            await self._update_task_activity(task_id, "Группировка записей по хостам")
            grouped_hosts = self._group_vm_data_by_hosts(clean_records)
            await self._log('info', f"Сгруппировано {len(grouped_hosts)} хостов из {len(clean_records)} записей")
            
            # Обновляем общее количество записей
            await self.db.update_background_task(task_id, **{
                'total_records': len(grouped_hosts),
                'processed_records': 0
            })
            await self._update_task_activity(task_id, f"Начинаем сохранение {len(grouped_hosts)} хостов")
            
            # Сохраняем хосты с расчетом рисков
            result = await self._save_hosts_with_risks(task_id, grouped_hosts)
            await self._log('info', "Сохранение хостов в базу данных завершено", {"result": result})
            
            return len(grouped_hosts)
            
        except Exception as e:
            print(f"❌ Ошибка сохранения очищенных записей: {e}")
            await self._log('error', f"Ошибка сохранения очищенных записей: {str(e)}")
            raise Exception(f"Ошибка сохранения очищенных записей: {str(e)}")
    
    def stop(self):
        """Остановить worker"""
        self.is_running = False
