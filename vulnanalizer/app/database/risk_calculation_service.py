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

    def calculate_risk_score_fast(self, epss: float, cvss: float = None, criticality: str = 'Medium', settings: dict = None, cve_data: dict = None) -> dict:
        """Полный расчет риска с учетом всех факторов по новой формуле"""
        if epss is None:
            return {
                'raw_risk': None,
                'risk_score': None,
                'calculation_possible': False,
                'impact': None,
                'cve_param': None
            }
        
        # Конвертируем decimal в float если нужно
        if hasattr(epss, 'as_tuple'):
            epss = float(epss)
        
        # Полный расчет Impact на основе критичности и других факторов
        impact = self._calculate_impact_full(criticality, settings)
        
        # Расчет CVE_param
        cve_param = self._calculate_cve_param(cve_data, settings)
        
        # Новая формула: Risk = EPSS × (CVSS ÷ 10) × Impact × CVE_param × ExDB_param × MSF_param
        cvss_factor = (cvss / 10) if cvss is not None else 1.0
        
        # Получаем ExDB_param и MSF_param
        exdb_param = self._calculate_exdb_param(cve_data, settings)
        msf_param = self._calculate_msf_param(cve_data, settings)
        
        raw_risk = epss * cvss_factor * impact * cve_param * exdb_param * msf_param
        risk_score = min(1, raw_risk) * 100
        
        return {
            'raw_risk': raw_risk,
            'risk_score': risk_score,
            'calculation_possible': True,
            'impact': impact,
            'cve_param': cve_param,
            'exdb_param': exdb_param,
            'msf_param': msf_param
        }

    def _calculate_impact_full(self, criticality: str, settings: dict = None) -> float:
        """Полный расчет Impact с учетом всех факторов"""
        # Получаем настройки Impact параметров
        impact_settings = self._get_impact_settings(settings)
        
        # Получаем значения из настроек или используем значения по умолчанию
        if settings:
            confidential_data = settings.get('impact_confidential_data', 'Отсутствуют')
            internet_access = settings.get('impact_internet_access', 'Недоступен')
        else:
            confidential_data = 'Отсутствуют'
            internet_access = 'Недоступен'
        
        # Рассчитываем Impact с учетом всех факторов
        impact = (
            impact_settings['resource_criticality'].get(criticality, 0.15) +
            impact_settings['confidential_data'].get(confidential_data, 0.1) +
            impact_settings['internet_access'].get(internet_access, 0.1)
        )
        
        # Конвертируем в float если это decimal
        if hasattr(impact, 'as_tuple'):
            impact = float(impact)
        
        return impact

    def _calculate_cve_param(self, cve_data: dict = None, settings: dict = None) -> float:
        """Расчет CVE_param на основе CVSS метрик"""
        if not cve_data:
            return 1.0
        
        # Получаем настройки CVSS параметров
        cvss_settings = self._get_cvss_settings(settings)
        
        # Пытаемся использовать CVSS v3
        if cve_data.get('cvss_v3_attack_vector') and cve_data.get('cvss_v3_privileges_required') and cve_data.get('cvss_v3_user_interaction'):
            try:
                av_factor = cvss_settings['v3']['attack_vector'].get(cve_data['cvss_v3_attack_vector'], 1.0)
                pr_factor = cvss_settings['v3']['privileges_required'].get(cve_data['cvss_v3_privileges_required'], 1.0)
                ui_factor = cvss_settings['v3']['user_interaction'].get(cve_data['cvss_v3_user_interaction'], 1.0)
                
                cve_param = av_factor * pr_factor * ui_factor
                return cve_param if cve_param > 0 else 1.0
            except Exception:
                pass
        
        # Если CVSS v3 недоступен, используем CVSS v2
        if cve_data.get('cvss_v2_access_vector') and cve_data.get('cvss_v2_access_complexity') and cve_data.get('cvss_v2_authentication'):
            try:
                av_factor = cvss_settings['v2']['access_vector'].get(cve_data['cvss_v2_access_vector'], 1.0)
                ac_factor = cvss_settings['v2']['access_complexity'].get(cve_data['cvss_v2_access_complexity'], 1.0)
                au_factor = cvss_settings['v2']['authentication'].get(cve_data['cvss_v2_authentication'], 1.0)
                
                cve_param = av_factor * ac_factor * au_factor
                return cve_param if cve_param > 0 else 1.0
            except Exception:
                pass
        
        # Если не удалось рассчитать, возвращаем 1.0
        return 1.0

    def _get_cvss_settings(self, settings: dict = None) -> dict:
        """Получение настроек CVSS параметров"""
        # Значения по умолчанию
        default_settings = {
            'v3': {
                'attack_vector': {
                    'NETWORK': 1.20,
                    'ADJACENT': 1.10,
                    'LOCAL': 0.95,
                    'PHYSICAL': 0.85
                },
                'privileges_required': {
                    'NONE': 1.20,
                    'LOW': 1.00,
                    'HIGH': 0.85
                },
                'user_interaction': {
                    'NONE': 1.15,
                    'REQUIRED': 0.90
                }
            },
            'v2': {
                'access_vector': {
                    'NETWORK': 1.20,
                    'ADJACENT_NETWORK': 1.10,
                    'LOCAL': 0.95
                },
                'access_complexity': {
                    'LOW': 1.10,
                    'MEDIUM': 1.00,
                    'HIGH': 0.90
                },
                'authentication': {
                    'NONE': 1.15,
                    'SINGLE': 1.00,
                    'MULTIPLE': 0.90
                }
            }
        }
        
        if not settings:
            return default_settings
        
        # Обновляем значения из настроек если они есть
        for version in ['v3', 'v2']:
            for metric in default_settings[version]:
                for value in default_settings[version][metric]:
                    setting_key = f'cvss_{version}_{metric.lower()}_{value.lower()}'
                    if setting_key in settings:
                        default_settings[version][metric][value] = float(settings[setting_key])
        
        return default_settings

    def _get_impact_settings(self, settings: dict = None) -> dict:
        """Получение настроек Impact параметров"""
        # Значения по умолчанию
        default_settings = {
            'resource_criticality': {
                'Critical': 0.33,
                'High': 0.25,
                'Medium': 0.2,
                'Low': 0.1,
                'None': 0.2
            },
            'confidential_data': {
                'Есть': 0.33,
                'Отсутствуют': 0.2
            },
            'internet_access': {
                'Доступен': 0.33,
                'Недоступен': 0.2
            }
        }
        
        if not settings:
            return default_settings
        
        # Обновляем значения из настроек если они есть
        impact_mappings = {
            'impact_resource_criticality_critical': ('resource_criticality', 'Critical'),
            'impact_resource_criticality_high': ('resource_criticality', 'High'),
            'impact_resource_criticality_medium': ('resource_criticality', 'Medium'),
            'impact_resource_criticality_none': ('resource_criticality', 'None'),
            'impact_confidential_data_yes': ('confidential_data', 'Есть'),
            'impact_confidential_data_no': ('confidential_data', 'Отсутствуют'),
            'impact_internet_access_yes': ('internet_access', 'Доступен'),
            'impact_internet_access_no': ('internet_access', 'Недоступен')
        }
        
        for setting_key, (category, value) in impact_mappings.items():
            if setting_key in settings:
                default_settings[category][value] = float(settings[setting_key])
        
        return default_settings

    def _get_exdb_settings(self, settings: dict = None) -> dict:
        """Получение настроек ExploitDB параметров"""
        # Значения по умолчанию
        default_settings = {
            'remote': 1.3,
            'webapps': 1.2,
            'dos': 0.85,
            'local': 1.05,
            'hardware': 1.0
        }
        
        if not settings:
            return default_settings
        
        # Обновляем значения из настроек если они есть
        exdb_mappings = {
            'exdb_remote': 'remote',
            'exdb_webapps': 'webapps',
            'exdb_dos': 'dos',
            'exdb_local': 'local',
            'exdb_hardware': 'hardware'
        }
        
        for setting_key, exdb_type in exdb_mappings.items():
            if setting_key in settings:
                default_settings[exdb_type] = float(settings[setting_key])
        
        return default_settings

    def _get_msf_settings(self, settings: dict = None) -> dict:
        """Получение настроек Metasploit параметров"""
        # Значения по умолчанию
        default_settings = {
            'excellent': 1.3,
            'good': 1.25,
            'normal': 1.2,
            'average': 1.1,
            'low': 0.8,
            'unknown': 0.8,
            'manual': 1.0
        }
        
        if not settings:
            return default_settings
        
        # Обновляем значения из настроек если они есть
        msf_mappings = {
            'msf_excellent': 'excellent',
            'msf_good': 'good',
            'msf_normal': 'normal',
            'msf_average': 'average',
            'msf_low': 'low',
            'msf_unknown': 'unknown',
            'msf_manual': 'manual'
        }
        
        for setting_key, msf_rank in msf_mappings.items():
            if setting_key in settings:
                default_settings[msf_rank] = float(settings[setting_key])
        
        return default_settings

    def _calculate_exdb_param(self, cve_data: dict = None, settings: dict = None) -> float:
        """Расчет ExDB_param на основе типа эксплойта"""
        # Если нет данных о CVE или типе эксплойта, возвращаем 1.0
        if not cve_data or not cve_data.get('exploitdb_type'):
            return 1.0
        
        exdb_settings = self._get_exdb_settings(settings)
        exploit_type = cve_data['exploitdb_type'].lower()
        
        # Ищем подходящий тип
        for exdb_type, factor in exdb_settings.items():
            if exdb_type in exploit_type:
                return factor
        
        # Если тип не найден, возвращаем 1.0
        return 1.0

    def _calculate_msf_param(self, cve_data: dict = None, settings: dict = None) -> float:
        """Расчет MSF_param на основе ранга Metasploit"""
        # Если нет данных о CVE или ранге Metasploit, возвращаем 1.0
        if not cve_data or not cve_data.get('msf_rank'):
            return 1.0
        
        msf_settings = self._get_msf_settings(settings)
        msf_rank_value = cve_data['msf_rank']
        
        # Преобразуем числовой ранг в текстовый для поиска
        if msf_rank_value == 600:
            rank_text = 'excellent'
        elif msf_rank_value == 500:
            rank_text = 'good'
        elif msf_rank_value == 400:
            rank_text = 'normal'
        elif msf_rank_value == 300:
            rank_text = 'average'
        elif msf_rank_value == 200:
            rank_text = 'low'
        elif msf_rank_value == 0:
            rank_text = 'manual'
        else:
            rank_text = 'unknown'
        
        # Ищем подходящий ранг
        for rank, factor in msf_settings.items():
            if rank == rank_text:
                return factor
        
        # Если ранг не найден, возвращаем 1.0
        return 1.0

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
                    
                    # Получаем данные CVE для расчета CVE_param
                    cve_data = None
                    try:
                        cve_query = """
                            SELECT cvss_v3_attack_vector, cvss_v3_privileges_required, cvss_v3_user_interaction,
                                   cvss_v2_access_vector, cvss_v2_access_complexity, cvss_v2_authentication
                            FROM vulnanalizer.cve WHERE cve_id = $1
                        """
                        cve_row = await conn.fetchrow(cve_query, cve)
                        if cve_row:
                            cve_data = {
                                'cvss_v3_attack_vector': cve_row['cvss_v3_attack_vector'],
                                'cvss_v3_privileges_required': cve_row['cvss_v3_privileges_required'],
                                'cvss_v3_user_interaction': cve_row['cvss_v3_user_interaction'],
                                'cvss_v2_access_vector': cve_row['cvss_v2_access_vector'],
                                'cvss_v2_access_complexity': cve_row['cvss_v2_access_complexity'],
                                'cvss_v2_authentication': cve_row['cvss_v2_authentication']
                            }
                    except Exception as e:
                        print(f"⚠️ Error getting CVE data for {cve}: {e}")
                    
                    # Получаем хосты для этого CVE
                    hosts_query = "SELECT id, cvss, criticality FROM vulnanalizer.hosts WHERE cve = $1"
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
                                settings,
                                cve_data
                            )
                        
                        # Быстрое обновление хоста
                        update_query = """
                            UPDATE vulnanalizer.hosts SET
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
                row = await conn.fetchrow("""
                    SELECT cve, epss, percentile, updated_at 
                    FROM vulnanalizer.epss 
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



    async def update_hosts_complete(self, progress_callback=None):
        """Единая функция для полного обновления хостов: EPSS, CVSS, ExploitDB, Metasploit"""
        print("🚀 Starting complete hosts update (EPSS + CVSS + ExploitDB + Metasploit)")
        conn = await self.get_connection()
        try:
            print("🚀 Got database connection")
            
            # Получаем все уникальные CVE из хостов
            cve_query = """
                SELECT DISTINCT cve FROM vulnanalizer.hosts 
                WHERE cve IS NOT NULL AND cve != '' 
                ORDER BY cve
            """
            cve_rows = await conn.fetch(cve_query)
            
            if not cve_rows:
                return {"success": True, "message": "Нет CVE для обновления", "updated_count": 0}
            
            total_cves = len(cve_rows)
            print(f"🚀 Found {total_cves} unique CVEs for complete update")
            
            if progress_callback:
                await progress_callback('initializing', f'Найдено {total_cves} уникальных CVE для обновления', 
                                total_cves=total_cves, processed_cves=0)
            
            # Получаем все EPSS данные одним batch запросом
            cve_list = [cve_row['cve'] for cve_row in cve_rows]
            epss_query = "SELECT cve, epss, percentile FROM vulnanalizer.epss WHERE cve = ANY($1::text[])"
            epss_rows = await conn.fetch(epss_query, cve_list)
            epss_data = {row['cve']: row for row in epss_rows}
            
            # Получаем все CVSS данные одним batch запросом
            cve_query = "SELECT cve_id as cve, cvss_v3_base_score, cvss_v2_base_score FROM vulnanalizer.cve WHERE cve_id = ANY($1::text[])"
            cve_rows_data = await conn.fetch(cve_query, cve_list)
            cve_data = {row['cve']: row for row in cve_rows_data}
            
            # Получаем все ExploitDB данные одним batch запросом (исправленный запрос)
            exploitdb_query = """
                SELECT DISTINCT split_part(codes, ';', 1) as cve_id, COUNT(*) as exploit_count
                FROM vulnanalizer.exploitdb 
                WHERE codes IS NOT NULL AND split_part(codes, ';', 1) LIKE 'CVE-%'
                GROUP BY split_part(codes, ';', 1)
                ORDER BY cve_id
            """
            try:
                # Добавляем таймаут для запроса
                import asyncio
                exploitdb_rows = await asyncio.wait_for(conn.fetch(exploitdb_query), timeout=30.0)
                exploitdb_data = {row['cve_id']: row['exploit_count'] for row in exploitdb_rows}
                print(f"✅ Загружено ExploitDB данных: {len(exploitdb_data)} CVE с эксплойтами")
                
                # Отладочная информация
                if 'CVE-2015-1635' in exploitdb_data:
                    print(f"🔍 DEBUG: CVE-2015-1635 найден в exploitdb_data: {exploitdb_data['CVE-2015-1635']}")
                else:
                    print(f"🔍 DEBUG: CVE-2015-1635 НЕ найден в exploitdb_data")
                    print(f"🔍 DEBUG: Первые 5 ключей: {list(exploitdb_data.keys())[:5]}")
                    print(f"🔍 DEBUG: Последние 5 ключей: {list(exploitdb_data.keys())[-5:]}")
                    print(f"🔍 DEBUG: Общее количество ключей: {len(exploitdb_data)}")
                    
                    # Проверяем, есть ли CVE-2015-1635 в базе
                    test_query = """
                        SELECT DISTINCT split_part(codes, ';', 1) as cve_id, COUNT(*) as exploit_count
                        FROM vulnanalizer.exploitdb 
                        WHERE codes IS NOT NULL AND split_part(codes, ';', 1) = 'CVE-2015-1635'
                        GROUP BY split_part(codes, ';', 1)
                    """
                    test_result = await conn.fetch(test_query)
                    print(f"🔍 DEBUG: Тестовый запрос для CVE-2015-1635 вернул: {test_result}")
                    
            except asyncio.TimeoutError:
                print("⚠️ Таймаут при загрузке ExploitDB данных, пропускаем анализ эксплойтов")
                exploitdb_data = {}
            except Exception as e:
                print(f"⚠️ Ошибка загрузки ExploitDB данных: {e}")
                exploitdb_data = {}
            
            # Получаем все Metasploit данные одним batch запросом (исправленный - максимальный ранг)
            metasploit_query = """
                WITH metasploit_cves AS (
                    SELECT 
                        unnest(regexp_matches("references", 'CVE-[0-9]{4}-[0-9]+', 'g')) as cve_id,
                        rank
                    FROM vulnanalizer.metasploit_modules 
                    WHERE "references" LIKE '%CVE-%'
                )
                SELECT cve_id, MAX(rank) as rank
                FROM metasploit_cves
                WHERE cve_id IS NOT NULL
                GROUP BY cve_id
            """
            try:
                metasploit_rows = await asyncio.wait_for(conn.fetch(metasploit_query), timeout=30.0)
                metasploit_data = {row['cve_id']: row['rank'] for row in metasploit_rows if row['cve_id']}
                print(f"✅ Загружено Metasploit данных: {len(metasploit_data)} CVE с рангом")
            except asyncio.TimeoutError:
                print("⚠️ Таймаут при загрузке Metasploit данных, пропускаем анализ")
                metasploit_data = {}
            except Exception as e:
                print(f"⚠️ Ошибка загрузки Metasploit данных: {e}")
                metasploit_data = {}
            
            print(f"✅ Загружено EPSS данных: {len(epss_data)} из {len(cve_list)} CVE")
            print(f"✅ Загружено CVSS данных: {len(cve_data)} из {len(cve_list)} CVE")
            print(f"✅ Загружено ExploitDB данных: {len(exploitdb_data)} из {len(cve_list)} CVE")
            print(f"✅ Загружено Metasploit данных: {len(metasploit_data)} из {len(cve_list)} CVE")
            
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
                    metasploit_rank = metasploit_data.get(cve)
                    
                    # Отладочная информация для CVE-2015-1635
                    if cve == 'CVE-2015-1635':
                        print(f"🔍 DEBUG CVE-2015-1635: exploit_count={exploit_count}, metasploit_rank={metasploit_rank}")
                    
                    # Получаем хосты для этого CVE
                    hosts_query = "SELECT id, cvss, criticality FROM vulnanalizer.hosts WHERE cve = $1"
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
                                    # Подготавливаем данные CVE для расчета CVE_param
                                    cve_param_data = None
                                    if cve_data_row:
                                        cve_param_data = {
                                            'cvss_v3_attack_vector': cve_data_row.get('cvss_v3_attack_vector'),
                                            'cvss_v3_privileges_required': cve_data_row.get('cvss_v3_privileges_required'),
                                            'cvss_v3_user_interaction': cve_data_row.get('cvss_v3_user_interaction'),
                                            'cvss_v2_access_vector': cve_data_row.get('cvss_v2_access_vector'),
                                            'cvss_v2_access_complexity': cve_data_row.get('cvss_v2_access_complexity'),
                                            'cvss_v2_authentication': cve_data_row.get('cvss_v2_authentication')
                                        }
                                    
                                    risk_result = self.calculate_risk_score_fast(
                                        epss=epss_row['epss'],
                                        cvss=cvss_score,
                                        criticality=host_row['criticality'],
                                        settings=settings,
                                        cve_data=cve_param_data
                                    )
                                    
                                    if risk_result['calculation_possible']:
                                        risk_score = risk_result['risk_score']
                                        risk_raw = risk_result['raw_risk']
                                except Exception as risk_error:
                                    print(f"⚠️ Error calculating risk for host {host_row['id']}: {risk_error}")
                            
                            # Определяем информацию об эксплойтах
                            exploit_count = exploitdb_data.get(cve, 0)
                            has_exploits = exploit_count > 0
                            
                            # Обновляем хост
                            update_query = """
                                UPDATE vulnanalizer.hosts SET
                                    cvss = $1,
                                    cvss_source = $2,
                                    epss_score = $3,
                                    epss_percentile = $4,
                                    exploits_count = $5,
                                    has_exploits = $6,
                                    risk_score = $7,
                                    risk_raw = $8,
                                    metasploit_rank = $9,
                                    epss_updated_at = $10,
                                    exploits_updated_at = $11,
                                    risk_updated_at = $12
                                WHERE id = $13
                            """
                            
                            await conn.execute(update_query,
                                cvss_score,
                                cvss_source,
                                epss_row['epss'] if epss_row else None,
                                float(epss_row['percentile']) if epss_row and epss_row['percentile'] else None,
                                exploit_count,
                                has_exploits,
                                risk_score,
                                risk_raw,
                                metasploit_rank,
                                datetime.now() if epss_row else None,
                                datetime.now() if has_exploits else None,
                                datetime.now() if risk_score is not None else None,
                                host_row['id']
                            )
                            
                            updated_hosts += 1
                            
                        except Exception as host_error:
                            print(f"⚠️ Error updating host {host_row['id']} for {cve}: {host_error}")
                            continue
                    
                    processed_cves += 1
                    
                except Exception as cve_error:
                    print(f"⚠️ Error processing CVE {cve}: {cve_error}")
                    error_cves += 1
                    continue
            
            print(f"✅ Complete update finished: {updated_hosts} hosts updated from {processed_cves} CVEs")
            
            return {
                "success": True,
                "message": f"Обновлено {updated_hosts} записей хостов из {processed_cves} CVE",
                "updated_count": updated_hosts,
                "processed_cves": processed_cves,
                "error_cves": error_cves
            }
            
        except Exception as e:
            print(f"❌ Error in complete hosts update: {e}")
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
                SELECT DISTINCT h.cve FROM vulnanalizer.hosts h
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
            
            # Используем полное обновление для инкрементального обновления
            return await self.update_hosts_complete(progress_callback)
            
        except Exception as e:
            print(f"❌ Error in incremental update: {e}")
            return {
                "success": False,
                "message": f"Ошибка инкрементального обновления: {str(e)}",
                "updated_count": 0
            }
        finally:
            await self.release_connection(conn)

    async def recalculate_all_risks(self, progress_callback=None):
        """Пересчитать риски для ВСЕХ хостов по новой формуле"""
        print("🚀 Starting risk recalculation for ALL hosts")
        conn = await self.get_connection()
        try:
            # Получаем ВСЕ хосты с CVE
            hosts_query = """
                SELECT h.id, h.cve, h.criticality, h.epss_score, h.cvss
                FROM vulnanalizer.hosts h 
                WHERE h.cve IS NOT NULL AND h.cve != '' 
                ORDER BY h.cve
            """
            hosts_rows = await conn.fetch(hosts_query)
            
            if not hosts_rows:
                return {"success": True, "message": "Нет хостов для пересчета рисков", "updated_count": 0}
            
            total_hosts = len(hosts_rows)
            print(f"🚀 Found {total_hosts} hosts for risk recalculation")
            
            if progress_callback:
                await progress_callback('initializing', f'Найдено {total_hosts} хостов для пересчета рисков', 
                                total_cves=total_hosts, processed_cves=0)
            
            # Получаем настройки
            settings = await self.get_settings()
            
            # Счетчики
            updated_hosts = 0
            error_hosts = 0
            
            # Обрабатываем каждый хост
            for i, host_row in enumerate(hosts_rows):
                try:
                    # Обновляем прогресс каждые 10 хостов
                    if progress_callback and i % 10 == 0:
                        progress_percent = (i / total_hosts) * 100
                        await progress_callback('processing', 
                            f'Пересчет рисков для хоста {i+1}/{total_hosts} (обновлено: {updated_hosts})', 
                            progress_percent=progress_percent, processed_cves=i, updated_hosts=updated_hosts)
                    
                    host_id = host_row['id']
                    cve = host_row['cve']
                    criticality = host_row['criticality']
                    epss_score = host_row['epss_score']
                    cvss_score = host_row['cvss']
                    
                    # Пропускаем хосты без EPSS или CVSS данных
                    if not epss_score or not cvss_score:
                        print(f"⚠️ Host {host_id} ({cve}) skipped: missing EPSS or CVSS data")
                        continue
                    
                    # Получаем данные CVE для расчета CVE_param
                    cve_query = """
                        SELECT cvss_v3_attack_vector, cvss_v3_privileges_required, cvss_v3_user_interaction,
                               cvss_v2_access_vector, cvss_v2_access_complexity, cvss_v2_authentication
                        FROM vulnanalizer.cve 
                        WHERE cve_id = $1
                    """
                    cve_row = await conn.fetchrow(cve_query, cve)
                    cve_data = dict(cve_row) if cve_row else {}
                    
                    # Получаем реальный тип эксплойта из ExploitDB
                    exdb_query = """
                        SELECT type FROM vulnanalizer.exploitdb 
                        WHERE cve = $1 
                        ORDER BY date_published DESC 
                        LIMIT 1
                    """
                    try:
                        exdb_row = await conn.fetchrow(exdb_query, cve)
                        if exdb_row and exdb_row['type']:
                            cve_data['exploitdb_type'] = exdb_row['type'].lower()
                        else:
                            cve_data['exploitdb_type'] = None
                    except Exception as e:
                        print(f"⚠️ Error getting ExploitDB data for {cve}: {e}")
                        cve_data['exploitdb_type'] = None
                    
                    # Получаем реальный ранг Metasploit
                    msf_query = """
                        SELECT rank FROM vulnanalizer.metasploit 
                        WHERE cve = $1 
                        ORDER BY rank DESC 
                        LIMIT 1
                    """
                    try:
                        msf_row = await conn.fetchrow(msf_query, cve)
                        if msf_row and msf_row['rank']:
                            cve_data['msf_rank'] = msf_row['rank'].lower()
                        else:
                            cve_data['msf_rank'] = None
                    except Exception as e:
                        print(f"⚠️ Error getting Metasploit data for {cve}: {e}")
                        cve_data['msf_rank'] = None
                    
                    # Рассчитываем риск по новой формуле
                    risk_result = self.calculate_risk_score_fast(
                        epss=float(epss_score),
                        cvss=float(cvss_score),
                        criticality=criticality,
                        settings=settings,
                        cve_data=cve_data
                    )
                    
                    if risk_result['calculation_possible']:
                        new_risk_score = risk_result['risk_score']
                        new_risk_raw = risk_result['raw_risk']
                        
                        # Обновляем риск в базе данных
                        update_query = """
                            UPDATE vulnanalizer.hosts SET
                                risk_score = $1,
                                risk_raw = $2,
                                risk_updated_at = $3
                            WHERE id = $4
                        """
                        
                        await conn.execute(update_query,
                            new_risk_score,
                            new_risk_raw,
                            datetime.now(),
                            host_id
                        )
                        
                        updated_hosts += 1
                        print(f"✅ Host {host_id} ({cve}): risk updated from {host_row.get('risk_score', 'N/A')} to {new_risk_score}")
                    else:
                        print(f"⚠️ Host {host_id} ({cve}): risk calculation failed")
                        
                except Exception as host_error:
                    print(f"⚠️ Error recalculating risk for host {host_row['id']} ({cve}): {host_error}")
                    error_hosts += 1
                    continue
            
            print(f"✅ Risk recalculation finished: {updated_hosts} hosts updated, {error_hosts} errors")
            
            return {
                "success": True,
                "message": f"Пересчет рисков завершен: {updated_hosts} хостов обновлено, {error_hosts} ошибок",
                "updated_count": updated_hosts,
                "error_count": error_hosts
            }
            
        except Exception as e:
            print(f"❌ Error in risk recalculation: {e}")
            return {
                "success": False,
                "message": f"Ошибка пересчета рисков: {str(e)}",
                "updated_count": 0,
                "error_count": 0
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

    async def get_metasploit_by_cve(self, cve_id: str):
        """Получить данные Metasploit по CVE ID"""
        from .metasploit_repository import MetasploitRepository
        metasploit = MetasploitRepository()
        return await metasploit.get_metasploit_by_cve(cve_id)
