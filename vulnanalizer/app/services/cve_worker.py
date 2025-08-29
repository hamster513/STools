#!/usr/bin/env python3
"""
Worker для фоновой загрузки CVE данных
"""

import asyncio
import aiohttp
import gzip
import io
import json
from datetime import datetime
from typing import List, Dict, Optional
from database import get_db
# Импортируем parse_cve_json напрямую, чтобы избежать циклического импорта
def parse_cve_json(data):
    """Парсить JSON данные CVE (поддерживает форматы 1.1 и 2.0)"""
    import json
    records = []
    
    try:
        cve_data = json.loads(data)
        
        # Определяем формат CVE
        if 'CVE_Items' in cve_data:
            # Формат CVE 1.1
            cve_items = cve_data.get('CVE_Items', [])
            format_version = "1.1"
        elif 'vulnerabilities' in cve_data:
            # Формат CVE 2.0
            cve_items = cve_data.get('vulnerabilities', [])
            format_version = "2.0"
        else:
            raise Exception("Неизвестный формат CVE данных")
        
        print(f"📄 Обрабатываем CVE формат {format_version}, найдено {len(cve_items)} записей")
        
        for item in cve_items:
            try:
                if format_version == "1.1":
                    # Формат CVE 1.1
                    cve_info = item.get('cve', {})
                    cve_id = cve_info.get('CVE_data_meta', {}).get('ID')
                    
                    # Получаем описание
                    description = ""
                    description_data = cve_info.get('description', {}).get('description_data', [])
                    for desc in description_data:
                        if desc.get('lang') == 'en':
                            description = desc.get('value', '')
                            break
                else:
                    # Формат CVE 2.0
                    cve_info = item.get('cve', {})
                    cve_id = cve_info.get('id')
                    
                    # Получаем описание
                    description = ""
                    descriptions = cve_info.get('descriptions', [])
                    for desc in descriptions:
                        if desc.get('lang') == 'en':
                            description = desc.get('value', '')
                            break
                
                if not cve_id:
                    continue
                
                # Парсим CVSS данные
                cvss_v3_base_score = None
                cvss_v3_base_severity = None
                cvss_v3_attack_vector = None
                cvss_v3_privileges_required = None
                cvss_v3_user_interaction = None
                cvss_v3_confidentiality_impact = None
                cvss_v3_integrity_impact = None
                cvss_v3_availability_impact = None
                
                cvss_v2_base_score = None
                cvss_v2_base_severity = None
                cvss_v2_access_vector = None
                cvss_v2_access_complexity = None
                cvss_v2_authentication = None
                cvss_v2_confidentiality_impact = None
                cvss_v2_integrity_impact = None
                cvss_v2_availability_impact = None
                
                if format_version == "1.1":
                    # Формат CVE 1.1
                    impact = item.get('impact', {})
                    
                    # CVSS v3.1
                    if 'baseMetricV3' in impact:
                        cvss_v3 = impact['baseMetricV3'].get('cvssV3', {})
                        cvss_v3_base_score = cvss_v3.get('baseScore')
                        cvss_v3_base_severity = cvss_v3.get('baseSeverity')
                    
                    # CVSS v2
                    if 'baseMetricV2' in impact:
                        cvss_v2 = impact['baseMetricV2'].get('cvssV2', {})
                        cvss_v2_base_score = cvss_v2.get('baseScore')
                        cvss_v2_base_severity = cvss_v2.get('baseSeverity')
                else:
                    # Формат CVE 2.0
                    metrics = cve_info.get('metrics', {})
                    
                    # CVSS v3.1 (приоритет) или v3.0
                    cvss_v3_metric = None
                    if 'cvssMetricV31' in metrics and metrics['cvssMetricV31']:
                        cvss_v3_metric = metrics['cvssMetricV31'][0]
                    elif 'cvssMetricV30' in metrics and metrics['cvssMetricV30']:
                        cvss_v3_metric = metrics['cvssMetricV30'][0]
                    
                    if cvss_v3_metric:
                        cvss_v3_data = cvss_v3_metric.get('cvssData', {})
                        cvss_v3_base_score = cvss_v3_data.get('baseScore')
                        cvss_v3_base_severity = cvss_v3_data.get('baseSeverity')  # В cvssData
                        cvss_v3_attack_vector = cvss_v3_data.get('attackVector')
                        cvss_v3_privileges_required = cvss_v3_data.get('privilegesRequired')
                        cvss_v3_user_interaction = cvss_v3_data.get('userInteraction')
                        cvss_v3_confidentiality_impact = cvss_v3_data.get('confidentialityImpact')
                        cvss_v3_integrity_impact = cvss_v3_data.get('integrityImpact')
                        cvss_v3_availability_impact = cvss_v3_data.get('availabilityImpact')
                    
                    # CVSS v2
                    if 'cvssMetricV2' in metrics and metrics['cvssMetricV2']:
                        cvss_v2_metric = metrics['cvssMetricV2'][0]
                        cvss_v2_data = cvss_v2_metric.get('cvssData', {})
                        cvss_v2_base_score = cvss_v2_data.get('baseScore')
                        cvss_v2_base_severity = cvss_v2_metric.get('baseSeverity')  # На верхнем уровне
                        cvss_v2_access_vector = cvss_v2_data.get('accessVector')
                        cvss_v2_access_complexity = cvss_v2_data.get('accessComplexity')
                        cvss_v2_authentication = cvss_v2_data.get('authentication')
                        cvss_v2_confidentiality_impact = cvss_v2_data.get('confidentialityImpact')
                        cvss_v2_integrity_impact = cvss_v2_data.get('integrityImpact')
                        cvss_v2_availability_impact = cvss_v2_data.get('availabilityImpact')
                
                # Создаем запись
                record = {
                    'cve_id': cve_id,
                    'description': description,
                    'cvss_v3_base_score': cvss_v3_base_score,
                    'cvss_v3_base_severity': cvss_v3_base_severity,
                    'cvss_v3_attack_vector': cvss_v3_attack_vector,
                    'cvss_v3_privileges_required': cvss_v3_privileges_required,
                    'cvss_v3_user_interaction': cvss_v3_user_interaction,
                    'cvss_v3_confidentiality_impact': cvss_v3_confidentiality_impact,
                    'cvss_v3_integrity_impact': cvss_v3_integrity_impact,
                    'cvss_v3_availability_impact': cvss_v3_availability_impact,
                    'cvss_v2_base_score': cvss_v2_base_score,
                    'cvss_v2_base_severity': cvss_v2_base_severity,
                    'cvss_v2_access_vector': cvss_v2_access_vector,
                    'cvss_v2_access_complexity': cvss_v2_access_complexity,
                    'cvss_v2_authentication': cvss_v2_authentication,
                    'cvss_v2_confidentiality_impact': cvss_v2_confidentiality_impact,
                    'cvss_v2_integrity_impact': cvss_v2_integrity_impact,
                    'cvss_v2_availability_impact': cvss_v2_availability_impact,
                    'published_date': item.get('publishedDate') or cve_info.get('published'),
                    'last_modified_date': item.get('lastModifiedDate') or cve_info.get('lastModified')
                }
                
                records.append(record)
                
            except Exception as e:
                print(f"⚠️ Ошибка парсинга CVE записи: {e}")
                continue
        
        print(f"✅ Успешно обработано {len(records)} CVE записей")
        return records
        
    except Exception as e:
        print(f"❌ Ошибка парсинга CVE JSON: {e}")
        return []


class CVEWorker:
    def __init__(self):
        self.db = get_db()
        self.is_running = False
        self.current_task_id = None
        self.selected_years = []
        
    async def start_download(self, years: List[int], task_id: int) -> Dict:
        """Запуск загрузки CVE для выбранных лет"""
        self.is_running = True
        self.current_task_id = task_id
        self.selected_years = sorted(years, reverse=True)  # Сначала новые годы
        
        try:
            total_records = 0
            total_files = len(self.selected_years)
            
            # Обновляем статус задачи
            await self.db.update_background_task(
                task_id,
                status='running',
                current_step='Инициализация загрузки',
                total_items=total_files,
                processed_items=0,
                progress_percent=0
            )
            
            for i, year in enumerate(self.selected_years):
                if not self.is_running:
                    await self.db.update_background_task(
                        task_id,
                        status='cancelled',
                        current_step='Загрузка отменена пользователем'
                    )
                    return {"success": False, "message": "Загрузка отменена"}
                
                try:
                    # Этап A: Показываем какой файл обрабатываем
                    current_file = f"nvdcve-2.0-{year}.json.gz"
                    remaining_files = total_files - i - 1
                    
                    # Рассчитываем прогресс
                    progress = (i * 100) // total_files
                    await self.db.update_background_task(
                        task_id,
                        current_step=f"Обработка файла: {current_file}",
                        details=f"Осталось файлов: {remaining_files}",
                        processed_items=i,
                        total_items=total_files,
                        progress_percent=progress
                    )
                    
                    # Этап B: Загрузка архива с сайта
                    url = f"https://nvd.nist.gov/feeds/json/cve/2.0/nvdcve-2.0-{year}.json.gz"
                    
                    await self.db.update_background_task(
                        task_id,
                        current_step=f"Загрузка архива: {current_file}",
                        details=f"URL: {url}"
                    )
                    
                    timeout = aiohttp.ClientTimeout(total=600, connect=60)
                    async with aiohttp.ClientSession(timeout=timeout) as session:
                        async with session.get(url) as resp:
                            if resp.status != 200:
                                error_msg = f"Ошибка загрузки {year}: HTTP {resp.status}"
                                await self.db.update_background_task(
                                    task_id,
                                    current_step=f"Ошибка: {error_msg}",
                                    details="Пропускаем файл и продолжаем"
                                )
                                continue
                            
                            # Показываем прогресс загрузки
                            content_length = resp.headers.get('content-length')
                            if content_length:
                                await self.db.update_background_task(
                                    task_id,
                                    current_step=f"Загрузка: {current_file}",
                                    details=f"Размер: {int(content_length):,} байт"
                                )
                            
                            gz_content = await resp.read()
                            
                            await self.db.update_background_task(
                                task_id,
                                current_step=f"Загружено: {current_file}",
                                details=f"Получено: {len(gz_content):,} байт"
                            )
                    
                    # Этап C: Разархивирование
                    await self.db.update_background_task(
                        task_id,
                        current_step=f"Разархивирование: {current_file}",
                        details="Обработка сжатых данных..."
                    )
                    
                    with gzip.GzipFile(fileobj=io.BytesIO(gz_content)) as gz:
                        content = gz.read().decode('utf-8')
                    
                    await self.db.update_background_task(
                        task_id,
                        current_step=f"Разархивировано: {current_file}",
                        details=f"Размер: {len(content):,} символов"
                    )
                    
                    # Этап D: Парсинг JSON
                    await self.db.update_background_task(
                        task_id,
                        current_step=f"Парсинг JSON: {current_file}",
                        details="Извлечение CVE записей..."
                    )
                    
                    records = parse_cve_json(content)
                    
                    if records:
                        await self.db.update_background_task(
                            task_id,
                            current_step=f"Найдено CVE: {current_file}",
                            details=f"Записей: {len(records):,}"
                        )
                        
                        # Этап E: Укладка в базу
                        await self.db.update_background_task(
                            task_id,
                            current_step=f"Загрузка в БД: {current_file}",
                            details=f"Загружено: 0/{len(records):,}"
                        )
                        
                        # Загружаем записи батчами для отображения прогресса
                        batch_size = 1000
                        for j in range(0, len(records), batch_size):
                            if not self.is_running:
                                break
                                
                            batch = records[j:j + batch_size]
                            await self.db.insert_cve_records(batch)
                            
                            loaded = min(j + batch_size, len(records))
                            # Рассчитываем прогресс для текущего файла (50-90% от общего прогресса)
                            file_progress = 50 + (loaded * 40) // len(records)
                            total_progress = (i * 100 + file_progress) // total_files
                            await self.db.update_background_task(
                                task_id,
                                current_step=f"Загрузка в БД: {current_file}",
                                details=f"Загружено: {loaded:,}/{len(records):,}",
                                progress_percent=total_progress
                            )
                        
                        total_records += len(records)
                        
                        await self.db.update_background_task(
                            task_id,
                            current_step=f"Завершено: {current_file}",
                            details=f"Всего загружено: {total_records:,} CVE"
                        )
                    else:
                        await self.db.update_background_task(
                            task_id,
                            current_step=f"Пустой файл: {current_file}",
                            details="CVE записи не найдены"
                        )
                
                except Exception as e:
                    error_msg = f"Ошибка обработки {year}: {str(e)}"
                    await self.db.update_background_task(
                        task_id,
                        current_step=f"Ошибка: {error_msg}",
                        details="Пропускаем файл и продолжаем"
                    )
                    continue
            
            # Завершение
            if self.is_running:
                await self.db.update_background_task(
                    task_id,
                    status='completed',
                    current_step='Загрузка завершена успешно',
                    details=f"Всего загружено: {total_records:,} CVE из {total_files} файлов",
                    total_records=total_records,
                    updated_records=total_records,
                    progress_percent=100
                )
                
                return {
                    "success": True,
                    "count": total_records,
                    "files_processed": total_files,
                    "message": f"Загружено {total_records:,} CVE из {total_files} файлов"
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
cve_worker = CVEWorker()
