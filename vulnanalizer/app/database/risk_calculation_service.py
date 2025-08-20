"""
Сервис для быстрого расчета рисков
"""
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime
import async_timeout
from .base import DatabaseBase


class RiskCalculationService(DatabaseBase):
    """Оптимизированный сервис для расчета рисков"""

    def __init__(self):
        super().__init__()
        self._epss_cache = {}
        self._cve_cache = {}
        self._exploitdb_cache = {}

    def calculate_risk_score_fast(self, epss: float, cvss: float = None, criticality: str = 'Medium', settings: dict = None) -> dict:
        """Полный расчет риска с учетом всех факторов"""
        if epss is None:
            return {
                'raw_risk': None,
                'risk_score': None,
                'calculation_possible': False,
                'impact': None
            }
        
        # Конвертируем decimal в float если нужно
        if hasattr(epss, 'as_tuple'):
            epss = float(epss)
        
        # Полный расчет Impact на основе критичности и других факторов
        impact = self._calculate_impact_full(criticality, settings)
        
        # Полная формула расчета риска
        raw_risk = epss * impact
        risk_score = min(1, raw_risk) * 100
        
        return {
            'raw_risk': raw_risk,
            'risk_score': risk_score,
            'calculation_possible': True,
            'impact': impact
        }

    def _calculate_impact_full(self, criticality: str, settings: dict = None) -> float:
        """Полный расчет Impact с учетом всех факторов"""
        # Веса для критичности ресурса
        resource_weights = {
            'Critical': 0.33,
            'High': 0.25,
            'Medium': 0.15,
            'Low': 0.1,
            'None': 0.05
        }
        
        # Веса для конфиденциальных данных
        data_weights = {
            'Есть': 0.33,
            'Отсутствуют': 0.1
        }
        
        # Веса для доступа к интернету
        internet_weights = {
            'Доступен': 0.33,
            'Недоступен': 0.1
        }
        
        # Получаем значения из настроек или используем значения по умолчанию
        if settings:
            confidential_data = settings.get('impact_confidential_data', 'Отсутствуют')
            internet_access = settings.get('impact_internet_access', 'Недоступен')
        else:
            confidential_data = 'Отсутствуют'
            internet_access = 'Недоступен'
        
        # Рассчитываем Impact с учетом всех факторов
        impact = (
            resource_weights.get(criticality, 0.15) +
            data_weights.get(confidential_data, 0.1) +
            internet_weights.get(internet_access, 0.1)
        )
        
        # Конвертируем в float если это decimal
        if hasattr(impact, 'as_tuple'):
            impact = float(impact)
        
        return impact

    async def process_cve_risk_calculation_optimized(self, cve_rows, conn, settings=None, progress_callback=None):
        """Оптимизированная параллельная обработка CVE для расчета рисков"""
        print(f"🚀 Начинаем оптимизированную обработку {len(cve_rows)} CVE")
        
        # Оптимальная параллельность для избежания перегрузки БД
        max_concurrent = 5  # Уменьшили до 5 для стабильности БД
        timeout_seconds = 5  # Уменьшили с 30 до 5 секунд
        
        print(f"⚙️ Оптимизированные настройки: max_concurrent={max_concurrent}, timeout={timeout_seconds}s")
        
        # Обновляем прогресс в начале
        if progress_callback:
            await progress_callback('calculating_risk', f'Запуск оптимизированной обработки {len(cve_rows)} CVE...', 75, 
                                  current_step_progress=0, processed_records=0)
        
        # Создаем семафор для ограничения параллельных операций
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def process_single_cve_optimized(cve_row, index):
            """Оптимизированная обработка одного CVE"""
            async with semaphore:
                cve = cve_row['cve']
                start_time = datetime.now()
                
                try:
                    # Проверяем кэш
                    if cve in self._epss_cache:
                        epss_data = self._epss_cache[cve]
                    else:
                        # Получаем только EPSS данные (самые важные для расчета риска)
                        try:
                            async with async_timeout.timeout(timeout_seconds):
                                epss_data = await self._get_epss_by_cve_fast(cve, conn)
                                self._epss_cache[cve] = epss_data
                        except Exception as e:
                            print(f"⚠️ [{index+1}] EPSS ошибка для {cve}: {e}")
                            epss_data = None
                    
                    # Получаем хосты для этого CVE
                    hosts_query = "SELECT id, cvss, criticality FROM hosts WHERE cve = $1"
                    hosts_rows = await conn.fetch(hosts_query, cve)
                    
                    if not hosts_rows:
                        return {'processed': True, 'hosts_updated': 0, 'error': None}
                    
                    hosts_updated = 0
                    for host_row in hosts_rows:
                        # Быстрый расчет риска только на основе EPSS
                        risk_data = None
                        
                        if epss_data and epss_data.get('epss') is not None:
                            # Передаем настройки для точного расчета
                            risk_data = self.calculate_risk_score_fast(
                                epss_data['epss'], 
                                host_row['cvss'], 
                                host_row['criticality'],
                                settings
                            )
                        
                        # Быстрое обновление хоста
                        update_query = """
                            UPDATE hosts SET
                                epss_score = $1,
                                epss_percentile = $2,
                                risk_score = $3,
                                risk_raw = $4,
                                impact_score = $5,
                                epss_updated_at = $6,
                                risk_updated_at = $7
                            WHERE id = $8
                        """
                        
                        await conn.execute(update_query,
                            epss_data.get('epss') if epss_data else None,
                            epss_data.get('percentile') if epss_data else None,
                            risk_data.get('risk_score') if risk_data else None,
                            risk_data.get('raw_risk') if risk_data else None,
                            risk_data.get('impact') if risk_data else None,
                            datetime.now() if epss_data else None,
                            datetime.now() if risk_data else None,
                            host_row['id']
                        )
                        hosts_updated += 1
                    
                    elapsed = (datetime.now() - start_time).total_seconds()
                    print(f"✅ [{index+1}] CVE {cve}: обновлено {hosts_updated} хостов за {elapsed:.2f}s")
                    
                    # Обновляем прогресс каждые 10 CVE
                    if progress_callback and (index + 1) % 10 == 0:
                        risk_progress = 75 + ((index + 1) / len(cve_rows)) * 20
                        await progress_callback('calculating_risk', 
                            f'Расчет рисков... ({index+1}/{len(cve_rows)} CVE)', 
                            risk_progress, 
                            current_step_progress=index+1, 
                            processed_records=index+1)
                    
                    return {'processed': True, 'hosts_updated': hosts_updated, 'error': None}
                    
                except asyncio.TimeoutError:
                    elapsed = (datetime.now() - start_time).total_seconds()
                    print(f"⏰ [{index+1}] Таймаут для CVE {cve} после {elapsed:.2f}s")
                    return {'processed': False, 'hosts_updated': 0, 'error': 'timeout'}
                except Exception as e:
                    elapsed = (datetime.now() - start_time).total_seconds()
                    print(f"❌ [{index+1}] Ошибка обработки CVE {cve} после {elapsed:.2f}s: {e}")
                    return {'processed': False, 'hosts_updated': 0, 'error': str(e)}
        
        # Запускаем параллельную обработку
        tasks = [process_single_cve_optimized(cve_row, i) for i, cve_row in enumerate(cve_rows)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Анализируем результаты
        successful = 0
        failed = 0
        total_hosts_updated = 0
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                print(f"❌ [{i+1}] Исключение в задаче: {result}")
                failed += 1
            elif result and result.get('processed'):
                successful += 1
                total_hosts_updated += result.get('hosts_updated', 0)
            else:
                failed += 1
        
        print(f"🎯 Оптимизированная обработка завершена:")
        print(f"   ✅ Успешно: {successful}/{len(cve_rows)} CVE")
        print(f"   ❌ Ошибок: {failed}/{len(cve_rows)} CVE")
        print(f"   🏠 Обновлено хостов: {total_hosts_updated}")
        
        # Обновляем прогресс в конце
        if progress_callback:
            await progress_callback('calculating_risk', f'Оптимизированная обработка завершена: {successful}/{len(cve_rows)} CVE', 95, 
                                  current_step_progress=len(cve_rows), processed_records=len(cve_rows))

    async def _get_epss_by_cve_fast(self, cve_id: str, conn):
        """Быстрое получение EPSS данных с переданным соединением"""
        try:
            async with async_timeout.timeout(3):
                # Устанавливаем схему если нужно
                await conn.execute('SET search_path TO vulnanalizer')
                
                row = await conn.fetchrow("""
                    SELECT cve, epss, percentile, updated_at 
                    FROM epss 
                    WHERE cve = $1
                """, cve_id.upper())
                
                if row:
                    return {
                        'cve': row['cve'],
                        'epss': float(row['epss']),
                        'percentile': float(row['percentile']),
                        'updated_at': row['updated_at'].isoformat() if row['updated_at'] else None
                    }
                return None
        except Exception as e:
            print(f"Error getting EPSS data for {cve_id}: {e}")
            return None

    async def update_hosts_epss_and_exploits_background_parallel(self, progress_callback=None, max_concurrent=10):
        """Обновить данные EPSS и эксплойтов для всех хостов с параллельной обработкой"""
        print("🔄 Starting parallel update_hosts_epss_and_exploits_background function")
        conn = await self.get_connection()
        try:
            print("🔄 Got database connection")
            
            # Получаем все уникальные CVE из хостов
            cve_query = """
                SELECT DISTINCT cve FROM hosts 
                WHERE cve IS NOT NULL AND cve != '' 
                ORDER BY cve
            """
            print("🔄 Executing CVE query")
            cve_rows = await conn.fetch(cve_query)
            print(f"🔄 CVE query returned {len(cve_rows)} rows")
            
            if not cve_rows:
                return {"success": True, "message": "Нет CVE для обновления", "updated_count": 0}
            
            total_cves = len(cve_rows)
            updated_count = 0
            skipped_cves = 0
            processed_cves = 0
            
            print(f"🔄 Starting parallel update: found {total_cves} unique CVEs")
            
            if progress_callback:
                await progress_callback('initializing', f'Найдено {total_cves} уникальных CVE для обновления', 
                                total_cves=total_cves, processed_cves=0)
            
            # Создаем семафор для ограничения параллельных операций
            # Уменьшаем параллелизм для избежания блокировок БД
            semaphore = asyncio.Semaphore(min(max_concurrent, 3))  # Максимум 3 параллельных CVE
            
            # Получаем настройки один раз для всех CVE
            settings = await self.get_settings()
            
            async def process_single_cve(cve, index):
                """Обработать один CVE"""
                async with semaphore:
                    # Проверяем, не была ли задача отменена
                    task = await self.get_background_task_by_type('hosts_update')
                    if task and task.get('status') == 'cancelled':
                        return None
                    
                    print(f"🔄 Processing CVE {index+1}/{total_cves}: {cve}")
                    
                    if progress_callback:
                        await progress_callback('processing', f'Обработка CVE {index+1}/{total_cves}: {cve}', 
                                        processed_cves=index+1, total_cves=total_cves)
                    
                    # Получаем данные параллельно
                    cve_data, epss_data, exploitdb_data = await asyncio.gather(
                        self.get_cve_by_id(cve),
                        self.get_epss_by_cve(cve),
                        self.get_exploitdb_by_cve(cve),
                        return_exceptions=True
                    )
                    

                    
                    # Обрабатываем исключения
                    if isinstance(cve_data, Exception):
                        print(f"⚠️ Error getting CVE data for {cve}: {cve_data}")
                        cve_data = None
                    if isinstance(epss_data, Exception):
                        print(f"⚠️ Error getting EPSS data for {cve}: {epss_data}")
                        epss_data = None
                    if isinstance(exploitdb_data, Exception):
                        print(f"⚠️ Error getting ExploitDB data for {cve}: {exploitdb_data}")
                        exploitdb_data = None
                    
                    # Проверяем, есть ли данные для обновления
                    has_cve_data = cve_data is not None
                    has_epss_data = epss_data is not None
                    has_exploit_data = exploitdb_data is not None
                    
                    if not has_cve_data and not has_epss_data and not has_exploit_data:
                        print(f"🔄 Skipping CVE {cve} - no data found")
                        return {'skipped': True, 'updated_hosts': 0}
                    
                    # Обновляем хосты с этим CVE
                    hosts_query = "SELECT id, cvss, criticality FROM hosts WHERE cve = $1"
                    hosts_rows = await conn.fetch(hosts_query, cve)
                    
                    if not hosts_rows:
                        print(f"🔄 No hosts found for CVE {cve}")
                        return {'skipped': True, 'updated_hosts': 0}
                    
                    updated_hosts = 0
                    for host_row in hosts_rows:
                        # Priority CVSS: CVE database > EPSS > original host CVSS
                        cvss_score = None
                        cvss_source = None

                        if cve_data and cve_data.get('cvss_v3_base_score') is not None:
                            cvss_score = cve_data['cvss_v3_base_score']
                            cvss_source = 'CVSS v3'
                        elif cve_data and cve_data.get('cvss_v2_base_score') is not None:
                            cvss_score = cve_data['cvss_v2_base_score']
                            cvss_source = 'CVSS v2'
                        elif epss_data and epss_data.get('cvss') is not None:
                            cvss_score = epss_data['cvss']
                            cvss_source = 'EPSS'
                        elif host_row['cvss'] is not None:
                            cvss_score = host_row['cvss']
                            cvss_source = 'Host'

                        # Рассчитываем риск если есть EPSS данные
                        risk_score = None
                        risk_raw = None
                        
                        if has_epss_data and epss_data.get('epss'):
                            try:
                                risk_result = self.calculate_risk_score_fast(
                                    epss=epss_data.get('epss'),
                                    criticality=host_row['criticality'],
                                    settings=settings
                                )
                                
                                if risk_result['calculation_possible']:
                                    risk_score = risk_result['risk_score']
                                    risk_raw = risk_result['raw_risk']
                            except Exception as risk_error:
                                print(f"⚠️ Error calculating risk for host {host_row['id']}: {risk_error}")
                        
                        # Обновляем данные хоста одним запросом
                        update_query = """
                            UPDATE hosts SET
                                cvss = $1,
                                cvss_source = $2,
                                epss_score = $3,
                                epss_percentile = $4,
                                exploits_count = $5,
                                verified_exploits_count = $6,
                                has_exploits = $7,
                                risk_score = $8,
                                risk_raw = $9,
                                epss_updated_at = $10,
                                exploits_updated_at = $11,
                                risk_updated_at = $12
                            WHERE id = $13
                        """
                        
                        await conn.execute(update_query,
                            cvss_score,
                            cvss_source,
                            epss_data.get('epss') if has_epss_data else None,
                            epss_data.get('percentile') if has_epss_data else None,
                            len(exploitdb_data) if has_exploit_data else 0,
                            len([e for e in exploitdb_data if e.get('verified', False)]) if has_exploit_data else 0,
                            len(exploitdb_data) > 0 if has_exploit_data else False,
                            risk_score,
                            risk_raw,
                            datetime.now() if has_epss_data else None,
                            datetime.now() if has_exploit_data else None,
                            datetime.now() if risk_score is not None else None,
                            host_row['id']
                        )
                        
                        updated_hosts += 1
                    
                    print(f"🔄 Updated {updated_hosts} hosts for CVE {cve}")
                    
                    # Обновляем прогресс с количеством обновленных хостов
                    if progress_callback:
                        await progress_callback('processing', f'Обработка CVE {index+1}/{total_cves}: {cve}', 
                                        processed_cves=index+1, total_cves=total_cves, updated_hosts=updated_hosts)
                    
                    return {'skipped': False, 'updated_hosts': updated_hosts}
            
            # Запускаем параллельную обработку
            tasks = [process_single_cve(cve_row['cve'], i) for i, cve_row in enumerate(cve_rows)]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Обрабатываем результаты
            for result in results:
                if isinstance(result, Exception):
                    print(f"⚠️ Task error: {result}")
                    skipped_cves += 1
                elif result is None:
                    skipped_cves += 1
                elif result.get('skipped'):
                    skipped_cves += 1
                else:
                    processed_cves += 1
                    updated_count += result.get('updated_hosts', 0)
            
            print(f"🔄 Completed: updated {updated_count} hosts, processed {processed_cves} CVEs, skipped {skipped_cves} CVEs")
            
            if progress_callback:
                await progress_callback('completed', 'Завершено', 
                                processed_cves=total_cves, total_cves=total_cves, 
                                updated_hosts=updated_count)
            
            return {
                "success": True,
                "message": f"Обновлено {updated_count} записей хостов из {processed_cves} CVE (пропущено {skipped_cves} CVE)",
                "updated_count": updated_count,
                "processed_cves": processed_cves,
                "skipped_cves": skipped_cves
            }
        except Exception as e:
            print(f"❌ Error updating hosts EPSS and exploits: {e}")
            return {
                "success": False,
                "message": f"Ошибка обновления: {str(e)}",
                "updated_count": 0,
                "processed_cves": 0
            }
        finally:
            await self.release_connection(conn)

    async def update_hosts_optimized_batch(self, progress_callback=None):
        """Оптимизированное обновление хостов с batch запросами (как в импорте)"""
        print("🚀 Starting optimized batch update (import-style)")
        conn = await self.get_connection()
        try:
            print("🚀 Got database connection")
            
            # Получаем все уникальные CVE из хостов
            cve_query = """
                SELECT DISTINCT cve FROM hosts 
                WHERE cve IS NOT NULL AND cve != '' 
                ORDER BY cve
            """
            cve_rows = await conn.fetch(cve_query)
            
            if not cve_rows:
                return {"success": True, "message": "Нет CVE для обновления", "updated_count": 0}
            
            total_cves = len(cve_rows)
            print(f"🚀 Found {total_cves} unique CVEs for batch update")
            
            if progress_callback:
                await progress_callback('initializing', f'Найдено {total_cves} уникальных CVE для обновления', 
                                total_cves=total_cves, processed_cves=0)
            
            # Получаем все EPSS данные одним batch запросом
            cve_list = [cve_row['cve'] for cve_row in cve_rows]
            epss_query = "SELECT cve, epss, percentile FROM epss WHERE cve = ANY($1::text[])"
            epss_rows = await conn.fetch(epss_query, cve_list)
            epss_data = {row['cve']: row for row in epss_rows}
            
            # Получаем все CVSS данные одним batch запросом
            cve_query = "SELECT cve_id as cve, cvss_v3_base_score, cvss_v2_base_score FROM cve WHERE cve_id = ANY($1::text[])"
            cve_rows_data = await conn.fetch(cve_query, cve_list)
            cve_data = {row['cve']: row for row in cve_rows_data}
            
            # Получаем все ExploitDB данные одним batch запросом
            # В таблице exploitdb нет колонки cve, поэтому пропускаем
            exploitdb_data = {}
            
            print(f"✅ Загружено EPSS данных: {len(epss_data)} из {len(cve_list)} CVE")
            print(f"✅ Загружено CVSS данных: {len(cve_data)} из {len(cve_list)} CVE")
            print(f"✅ Загружено ExploitDB данных: {len(exploitdb_data)} из {len(cve_list)} CVE")
            
            # Получаем настройки
            settings = await self.get_settings()
            
            # Счетчики
            processed_cves = 0
            updated_hosts = 0
            error_cves = 0
            
            # Обрабатываем каждый CVE
            for i, cve_row in enumerate(cve_rows):
                cve = cve_row['cve']
                
                try:
                    # Обновляем прогресс каждые 100 CVE
                    if progress_callback and i % 100 == 0:
                        progress_percent = (i / total_cves) * 100
                        await progress_callback('processing', 
                            f'Обработка CVE {i+1}/{total_cves} (обновлено хостов: {updated_hosts})', 
                            progress_percent, 
                            processed_cves=i+1, 
                            total_cves=total_cves)
                    
                    # Получаем данные из кэша
                    epss_row = epss_data.get(cve)
                    cve_data_row = cve_data.get(cve)
                    exploit_count = exploitdb_data.get(cve, 0)
                    
                    # Получаем хосты для этого CVE
                    hosts_query = "SELECT id, cvss, criticality FROM hosts WHERE cve = $1"
                    hosts_rows = await conn.fetch(hosts_query, cve)
                    
                    if not hosts_rows:
                        continue
                    
                    # Обновляем хосты
                    for host_row in hosts_rows:
                        try:
                            # Определяем CVSS score (приоритет: CVE v3 > CVE v2 > хост)
                            cvss_score = None
                            cvss_source = None
                            
                            if cve_data_row and cve_data_row['cvss_v3_base_score'] is not None:
                                cvss_score = float(cve_data_row['cvss_v3_base_score'])
                                cvss_source = 'CVSS v3'
                            elif cve_data_row and cve_data_row['cvss_v2_base_score'] is not None:
                                cvss_score = float(cve_data_row['cvss_v2_base_score'])
                                cvss_source = 'CVSS v2'
                            elif host_row['cvss'] is not None:
                                cvss_score = float(host_row['cvss'])
                                cvss_source = 'Host'
                            
                            # Рассчитываем риск если есть EPSS данные
                            risk_score = None
                            risk_raw = None
                            
                            if epss_row and epss_row['epss']:
                                try:
                                    risk_result = self.calculate_risk_score_fast(
                                        epss=epss_row['epss'],
                                        criticality=host_row['criticality'],
                                        settings=settings
                                    )
                                    
                                    if risk_result['calculation_possible']:
                                        risk_score = risk_result['risk_score']
                                        risk_raw = risk_result['raw_risk']
                                except Exception as risk_error:
                                    print(f"⚠️ Error calculating risk for host {host_row['id']}: {risk_error}")
                            
                            # Обновляем хост
                            update_query = """
                                UPDATE hosts SET
                                    cvss = $1,
                                    cvss_source = $2,
                                    epss_score = $3,
                                    epss_percentile = $4,
                                    exploits_count = $5,
                                    has_exploits = $6,
                                    risk_score = $7,
                                    risk_raw = $8,
                                    epss_updated_at = $9,
                                    exploits_updated_at = $10,
                                    risk_updated_at = $11
                                WHERE id = $12
                            """
                            
                            await conn.execute(update_query,
                                cvss_score,
                                cvss_source,
                                epss_row['epss'] if epss_row else None,
                                float(epss_row['percentile']) if epss_row and epss_row['percentile'] else None,
                                exploit_count,
                                exploit_count > 0,
                                risk_score,
                                risk_raw,
                                datetime.now() if epss_row else None,
                                datetime.now() if exploit_count > 0 else None,
                                datetime.now() if risk_score is not None else None,
                                host_row['id']
                            )
                            
                            updated_hosts += 1
                            
                        except Exception as host_error:
                            print(f"⚠️ Error updating host {host_row['id']} for {cve}: {host_error}")
                            continue
                    
                    processed_cves += 1
                    
                    # Логируем прогресс каждые 500 CVE
                    if i % 500 == 0:
                        print(f"🚀 Обработано {i+1}/{total_cves} CVE (обновлено хостов: {updated_hosts}, ошибок: {error_cves})")
                    
                except Exception as e:
                    error_cves += 1
                    print(f"❌ Error processing CVE {cve}: {e}")
                    continue
            
            print(f"🚀 Optimized batch update completed:")
            print(f"   📊 Processed CVEs: {processed_cves}/{total_cves}")
            print(f"   🏠 Updated hosts: {updated_hosts}")
            print(f"   ❌ Errors: {error_cves}")
            
            if progress_callback:
                await progress_callback('completed', f'Обновление завершено: {updated_hosts} хостов', 
                                processed_cves=total_cves, total_cves=total_cves, updated_hosts=updated_hosts)
            
            return {
                "success": True,
                "message": f"Обновлено {updated_hosts} записей хостов из {processed_cves} CVE (ошибок {error_cves})",
                "updated_count": updated_hosts,
                "processed_cves": processed_cves,
                "error_cves": error_cves
            }
            
        except Exception as e:
            print(f"❌ Error in optimized batch update: {e}")
            return {
                "success": False,
                "message": f"Ошибка обновления: {str(e)}",
                "updated_count": 0,
                "processed_cves": 0
            }
        finally:
            await self.release_connection(conn)

    async def update_hosts_incremental(self, progress_callback=None, days_old=1):
        """Инкрементальное обновление хостов, которые не обновлялись N дней"""
        print(f"🔄 Starting incremental update for hosts older than {days_old} days")
        conn = await self.get_connection()
        try:
            # Получаем CVE из хостов, которые не обновлялись давно
            cve_query = """
                SELECT DISTINCT h.cve FROM hosts h
                WHERE h.cve IS NOT NULL AND h.cve != '' 
                AND (h.epss_updated_at IS NULL OR h.epss_updated_at < NOW() - INTERVAL $1)
                ORDER BY h.cve
            """
            cve_rows = await conn.fetch(cve_query, f'{days_old} days')
            
            if not cve_rows:
                return {"success": True, "message": f"Нет хостов для обновления (старше {days_old} дней)", "updated_count": 0}
            
            total_cves = len(cve_rows)
            print(f"🔄 Found {total_cves} CVE for incremental update")
            
            if progress_callback:
                await progress_callback('initializing', f'Найдено {total_cves} CVE для инкрементального обновления', 
                                total_cves=total_cves, processed_cves=0)
            
            # Используем параллельную обработку для инкрементального обновления
            return await self.update_hosts_epss_and_exploits_background_parallel(
                progress_callback=progress_callback, 
                max_concurrent=5,  # Меньше параллелизма для инкрементального обновления
            )
            
        except Exception as e:
            print(f"❌ Error in incremental update: {e}")
            return {
                "success": False,
                "message": f"Ошибка инкрементального обновления: {str(e)}",
                "updated_count": 0
            }
        finally:
            await self.release_connection(conn)

    async def get_background_task_by_type(self, task_type: str):
        """Получить последнюю фоновую задачу определенного типа"""
        from .background_tasks_repository import BackgroundTasksRepository
        background_tasks = BackgroundTasksRepository()
        return await background_tasks.get_background_task_by_type(task_type)

    async def get_settings(self):
        """Получить настройки"""
        from .settings_repository import SettingsRepository
        settings = SettingsRepository()
        return await settings.get_settings()

    async def get_epss_by_cve(self, cve_id: str):
        """Получить данные EPSS по CVE ID"""
        from .epss_repository import EPSSRepository
        epss = EPSSRepository()
        return await epss.get_epss_by_cve(cve_id)

    async def get_cve_by_id(self, cve_id: str):
        """Получить данные CVE по ID"""
        from .cve_repository import CVERepository
        cve = CVERepository()
        return await cve.get_cve_by_id(cve_id)

    async def get_exploitdb_by_cve(self, cve_id: str):
        """Получить данные ExploitDB по CVE ID"""
        from .exploitdb_repository import ExploitDBRepository
        exploitdb = ExploitDBRepository()
        return await exploitdb.get_exploitdb_by_cve(cve_id)
