#!/usr/bin/env python3
"""
Worker для фоновой загрузки Metasploit данных
"""

import asyncio
import aiohttp
import json
import traceback
from datetime import datetime
from typing import Dict, List, Optional
from database import get_db


class MetasploitWorker:
    """Worker для фоновой загрузки Metasploit данных"""
    
    def __init__(self):
        self.is_running = False
        self.current_task_id = None
        self.metasploit_url = "https://raw.githubusercontent.com/rapid7/metasploit-framework/master/db/modules_metadata_base.json"
        self.db = get_db()
    
    async def start_download(self, task_id: int) -> Dict:
        """Запуск загрузки Metasploit данных"""
        self.is_running = True
        self.current_task_id = task_id
        
        try:
            # Обновляем статус задачи
            await self.db.update_background_task(
                task_id,
                status='running',
                current_step='Инициализация загрузки Metasploit',
                total_items=1,
                processed_items=0,
                progress_percent=0
            )
            
            # Этап 1: Подключение к GitHub
            await self.db.update_background_task(
                task_id,
                current_step='Подключение к GitHub',
                details=f'URL: {self.metasploit_url}',
                progress_percent=10
            )
            
            # Этап 2: Скачивание данных
            await self.db.update_background_task(
                task_id,
                current_step='Скачивание данных Metasploit',
                details='Загрузка JSON файла...',
                progress_percent=20
            )
            
            timeout = aiohttp.ClientTimeout(total=300, connect=60)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(self.metasploit_url) as response:
                    if response.status != 200:
                        error_msg = f"Ошибка загрузки: HTTP {response.status}"
                        await self.db.update_background_task(
                            task_id,
                            status='error',
                            current_step=f'Ошибка: {error_msg}',
                            error_message=error_msg
                        )
                        return {"success": False, "error": error_msg}
                    
                    # Показываем размер файла
                    content_length = response.headers.get('content-length')
                    if content_length:
                        await self.db.update_background_task(
                            task_id,
                            current_step='Скачивание данных Metasploit',
                            details=f'Размер: {int(content_length):,} байт',
                            progress_percent=30
                        )
                    
                    content = await response.text()
                    
                    await self.db.update_background_task(
                        task_id,
                        current_step='Данные загружены',
                        details=f'Получено: {len(content):,} символов',
                        progress_percent=40
                    )
            
            # Этап 3: Парсинг JSON
            await self.db.update_background_task(
                task_id,
                current_step='Парсинг JSON данных',
                details='Обработка структуры данных...',
                progress_percent=50
            )
            
            try:
                data = json.loads(content)
                total_modules = len(data)
                
                await self.db.update_background_task(
                    task_id,
                    current_step='JSON данные обработаны',
                    details=f'Найдено модулей: {total_modules:,}',
                    progress_percent=60
                )
            except json.JSONDecodeError as e:
                error_msg = f"Ошибка парсинга JSON: {str(e)}"
                await self.db.update_background_task(
                    task_id,
                    status='error',
                    current_step='Ошибка парсинга JSON',
                    error_message=error_msg
                )
                return {"success": False, "error": error_msg}
            
            # Этап 4: Подготовка данных для вставки
            await self.db.update_background_task(
                task_id,
                current_step='Подготовка данных',
                details='Форматирование записей...',
                progress_percent=70
            )
            
            records = []
                        # Проверяем формат данных и обрабатываем их
            if isinstance(data, dict):
                # Данные в формате словаря
                for module_name, module_data in data.items():
                    if not self.is_running:
                        await self.db.update_background_task(
                            task_id,
                            status='cancelled',
                            current_step='Загрузка отменена пользователем'
                        )
                        return {"success": False, "message": "Загрузка отменена"}
                    
                    try:
                        # Извлекаем данные модуля
                        name = module_data.get('name', '')
                        rank = module_data.get('rank', 0)
                        disclosure_date_str = module_data.get('disclosure_date')
                        module_type = module_data.get('type', '')
                        description = module_data.get('description', '')
                        references = module_data.get('references', '')
                        
                        # Парсим дату
                        disclosure_date = None
                        if disclosure_date_str:
                            try:
                                disclosure_date = datetime.fromisoformat(disclosure_date_str.replace('Z', '+00:00'))
                            except (ValueError, TypeError):
                                try:
                                    disclosure_date = datetime.strptime(disclosure_date_str, '%Y-%m-%d')
                                except (ValueError, TypeError):
                                    pass
                        
                        # Конвертируем references в строку
                        if isinstance(references, list):
                            references = ', '.join(references)
                        elif not isinstance(references, str):
                            references = str(references) if references else ''
                        
                        records.append({
                            'module_name': module_name,
                            'name': name,
                            'rank': rank,
                            'disclosure_date': disclosure_date,
                            'type': module_type,
                            'description': description,
                            'references': references
                        })
                        
                    except Exception as e:
                        print(f"Ошибка обработки модуля {module_name}: {str(e)}")
                        continue
                        
            elif isinstance(data, list):
                # Данные в формате списка
                for module_data in data:
                    if not self.is_running:
                        await self.db.update_background_task(
                            task_id,
                            status='cancelled',
                            current_step='Загрузка отменена пользователем'
                        )
                        return {"success": False, "message": "Загрузка отменена"}
                    
                    try:
                        # Извлекаем данные модуля
                        module_name = module_data.get('module_name', '')
                        name = module_data.get('name', '')
                        rank = module_data.get('rank', 0)
                        disclosure_date_str = module_data.get('disclosure_date')
                        module_type = module_data.get('type', '')
                        description = module_data.get('description', '')
                        references = module_data.get('references', '')
                        
                        # Парсим дату
                        disclosure_date = None
                        if disclosure_date_str:
                            try:
                                disclosure_date = datetime.fromisoformat(disclosure_date_str.replace('Z', '+00:00'))
                            except (ValueError, TypeError):
                                try:
                                    disclosure_date = datetime.strptime(disclosure_date_str, '%Y-%m-%d')
                                except (ValueError, TypeError):
                                    pass
                        
                        # Конвертируем references в строку
                        if isinstance(references, list):
                            references = ', '.join(references)
                        elif not isinstance(references, str):
                            references = str(references) if references else ''
                        
                        records.append({
                            'module_name': module_name,
                            'name': name,
                            'rank': rank,
                            'disclosure_date': disclosure_date,
                            'type': module_type,
                            'description': description,
                            'references': references
                        })
                        
                    except Exception as e:
                        print(f"Ошибка обработки модуля: {str(e)}")
                        continue
            else:
                raise Exception(f"Неизвестный формат данных: {type(data)}")
            
            await self.db.update_background_task(
                task_id,
                current_step='Данные подготовлены',
                details=f'Готово к вставке: {len(records):,} модулей',
                progress_percent=80
            )
            
            # Этап 5: Сохранение в базу данных
            await self.db.update_background_task(
                task_id,
                current_step='Сохранение в базу данных',
                details='Очистка старых данных...',
                progress_percent=85
            )
            
            # Очищаем старые данные
            await self.db.clear_metasploit_data()
            
            await self.db.update_background_task(
                task_id,
                current_step='Сохранение в базу данных',
                details='Вставка новых данных...',
                progress_percent=90
            )
            
            # Вставляем новые данные батчами
            batch_size = 1000
            total_inserted = 0
            
            for i in range(0, len(records), batch_size):
                if not self.is_running:
                    break
                
                batch = records[i:i + batch_size]
                await self.db.insert_metasploit_modules(batch)
                
                total_inserted += len(batch)
                progress = 90 + (total_inserted * 10) // len(records)
                
                await self.db.update_background_task(
                    task_id,
                    current_step='Сохранение в базу данных',
                    details=f'Вставлено: {total_inserted:,}/{len(records):,}',
                    progress_percent=progress
                )
            
            # Завершение
            if self.is_running:
                await self.db.update_background_task(
                    task_id,
                    status='completed',
                    current_step='Загрузка завершена успешно',
                    details=f'Загружено: {total_inserted:,} модулей Metasploit',
                    total_records=total_inserted,
                    updated_records=total_inserted,
                    progress_percent=100
                )
                
                return {
                    "success": True,
                    "count": total_inserted,
                    "message": f"Загружено {total_inserted:,} модулей Metasploit"
                }
            else:
                return {"success": False, "message": "Загрузка отменена"}
                
        except Exception as e:
            error_msg = f"Критическая ошибка: {str(e)}"
            await self.db.update_background_task(
                task_id,
                status='error',
                current_step='Критическая ошибка',
                error_message=error_msg
            )
            return {"success": False, "error": error_msg}
        
        finally:
            self.is_running = False
            self.current_task_id = None
    
    async def cancel_download(self) -> bool:
        """Отмена текущей загрузки"""
        if self.is_running and self.current_task_id:
            self.is_running = False
            await self.db.update_background_task(
                self.current_task_id,
                status='cancelled',
                current_step='Загрузка отменена пользователем'
            )
            return True
        return False
    
    def is_downloading(self) -> bool:
        """Проверка, идет ли загрузка"""
        return self.is_running
    
    def get_current_task_id(self) -> Optional[int]:
        """Получить ID текущей задачи"""
        return self.current_task_id


# Глобальный экземпляр worker'а
metasploit_worker = MetasploitWorker()
