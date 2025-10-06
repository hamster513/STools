"""
Сервис для обновления данных хостов
"""
import asyncio
from datetime import datetime, timedelta
from .base import DatabaseBase


class HostsUpdateService(DatabaseBase):
    """Сервис для обновления данных хостов"""
    
    def __init__(self):
        super().__init__()
        self._epss_cache = {}
        self._cve_cache = {}
        self._exploitdb_cache = {}

    async def update_hosts_complete(self, progress_callback=None):
        """Единая функция для полного обновления хостов: EPSS, CVSS, ExploitDB, Metasploit"""
        print("🚀 Starting complete hosts update...")
        
        conn = await self.get_connection()
        try:
            # Получаем настройки
            from .settings_repository import SettingsRepository
            settings_repo = SettingsRepository()
            settings = await settings_repo.get_settings()
            
            # Получаем все уникальные CVE из хостов
            hosts_query = """
                SELECT DISTINCT cve, criticality, confidential_data, internet_access
                FROM vulnanalizer.hosts 
                WHERE cve IS NOT NULL AND cve != ''
                ORDER BY cve
            """
            hosts_rows = await conn.fetch(hosts_query)
            cve_list = [row['cve'] for row in hosts_rows]
            
            if not cve_list:
                print("❌ No CVE found in hosts table")
                return
            
            print(f"📊 Found {len(cve_list)} unique CVE to process")
            
            # Получаем все EPSS данные одним batch запросом
            epss_query = "SELECT cve, epss, percentile FROM vulnanalizer.epss WHERE cve = ANY($1::text[])"
            epss_rows = await conn.fetch(epss_query, cve_list)
            epss_data = {row['cve']: row for row in epss_rows}
            print(f"✅ Loaded EPSS data: {len(epss_data)} CVE")
            
            # Получаем все CVSS данные одним batch запросом
            cve_query = "SELECT cve_id as cve, cvss_v3_base_score, cvss_v2_base_score, cvss_v3_attack_vector, cvss_v3_privileges_required, cvss_v3_user_interaction, cvss_v2_access_vector, cvss_v2_access_complexity, cvss_v2_authentication FROM vulnanalizer.cve WHERE cve_id = ANY($1::text[])"
            cve_rows_data = await conn.fetch(cve_query, cve_list)
            cve_data = {row['cve']: row for row in cve_rows_data}
            print(f"✅ Loaded CVSS data: {len(cve_data)} CVE")
            
            # Получаем все ExploitDB данные одним batch запросом (исправленная логика)
            exploitdb_query = """
                WITH cve_exploits AS (
                    SELECT 
                        unnest(string_to_array(codes, ';')) as cve_id,
                        exploit_id
                    FROM vulnanalizer.exploitdb 
                    WHERE codes IS NOT NULL AND codes LIKE '%CVE-%'
                )
                SELECT cve_id, COUNT(*) as exploit_count
                FROM cve_exploits 
                WHERE cve_id LIKE 'CVE-%'
                GROUP BY cve_id
                ORDER BY cve_id
            """
            try:
                exploitdb_rows = await asyncio.wait_for(conn.fetch(exploitdb_query), timeout=30.0)
                exploitdb_data = {row['cve_id']: row['exploit_count'] for row in exploitdb_rows}
                print(f"✅ Loaded ExploitDB data: {len(exploitdb_data)} CVE with exploits")
            except asyncio.TimeoutError:
                print("⚠️ ExploitDB query timeout, using empty data")
                exploitdb_data = {}
            
            # Получаем все Metasploit данные одним batch запросом (исправленная логика)
            metasploit_query = """
                WITH cve_metasploit AS (
                    SELECT 
                        unnest(string_to_array("references", ',')) as cve_ref,
                        rank
                    FROM vulnanalizer.metasploit_modules 
                    WHERE "references" IS NOT NULL AND "references" LIKE '%CVE-%'
                )
                SELECT 
                    TRIM(cve_ref) as cve_id, 
                    MAX(rank) as rank
                FROM cve_metasploit 
                WHERE TRIM(cve_ref) LIKE 'CVE-%'
                GROUP BY TRIM(cve_ref)
                ORDER BY TRIM(cve_ref)
            """
            try:
                metasploit_rows = await asyncio.wait_for(conn.fetch(metasploit_query), timeout=30.0)
                metasploit_data = {row['cve_id']: row['rank'] for row in metasploit_rows}
                print(f"✅ Loaded Metasploit data: {len(metasploit_data)} CVE with rank")
            except asyncio.TimeoutError:
                print("⚠️ Metasploit query timeout, using empty data")
                metasploit_data = {}
            
            # Обновляем хосты
            updated_count = 0
            for i, host_row in enumerate(hosts_rows):
                cve = host_row['cve']
                criticality = host_row['criticality']
                
                try:
                    # Получаем данные для CVE
                    epss_row = epss_data.get(cve)
                    cve_data_row = cve_data.get(cve)
                    
                    if not epss_row:
                        continue
                    
                    # Определяем CVSS score и source
                    cvss_score = None
                    cvss_source = None
                    
                    if cve_data_row and cve_data_row['cvss_v3_base_score'] is not None:
                        cvss_score = float(cve_data_row['cvss_v3_base_score'])
                        cvss_source = 'CVSS v3'
                    elif cve_data_row and cve_data_row['cvss_v2_base_score'] is not None:
                        cvss_score = float(cve_data_row['cvss_v2_base_score'])
                        cvss_source = 'CVSS v2'
                    
                    # Определяем информацию об эксплойтах
                    exploit_count = exploitdb_data.get(cve, 0)
                    has_exploits = exploit_count > 0
                    
                    # Рассчитываем риск если есть EPSS данные
                    risk_score = None
                    risk_raw = None
                    
                    if epss_row and epss_row['epss']:
                        try:
                            # Подготавливаем данные CVE для расчета
                            cve_param_data = {}
                            if cve_data_row:
                                cve_param_data.update({
                                    'cvss_v3_attack_vector': cve_data_row.get('cvss_v3_attack_vector'),
                                    'cvss_v3_privileges_required': cve_data_row.get('cvss_v3_privileges_required'),
                                    'cvss_v3_user_interaction': cve_data_row.get('cvss_v3_user_interaction'),
                                    'cvss_v2_access_vector': cve_data_row.get('cvss_v2_access_vector'),
                                    'cvss_v2_access_complexity': cve_data_row.get('cvss_v2_access_complexity'),
                                    'cvss_v2_authentication': cve_data_row.get('cvss_v2_authentication')
                                })
                            
                            # Добавляем данные ExploitDB для ExDB_param (исправленная логика)
                            if exploit_count > 0:
                                exdb_query = """
                                    SELECT type FROM vulnanalizer.exploitdb 
                                    WHERE codes LIKE $1 
                                    ORDER BY 
                                        CASE type 
                                            WHEN 'remote' THEN 1
                                            WHEN 'webapps' THEN 2
                                            WHEN 'local' THEN 3
                                            WHEN 'hardware' THEN 4
                                            WHEN 'dos' THEN 5
                                            ELSE 6
                                        END,
                                        date_published DESC
                                    LIMIT 1
                                """
                                exdb_row = await conn.fetchrow(exdb_query, f'%{cve}%')
                                if exdb_row and exdb_row['type']:
                                    cve_param_data['exploitdb_type'] = exdb_row['type']
                            
                            # Добавляем данные Metasploit для MSF_param
                            metasploit_rank = metasploit_data.get(cve)
                            if metasploit_rank is not None:
                                cve_param_data['msf_rank'] = metasploit_rank
                            
                            from database.risk_calculation import calculate_risk_score
                            risk_result = calculate_risk_score(
                                epss=epss_row['epss'] if epss_row else 0,
                                cvss=cvss_score,
                                criticality=criticality,
                                settings=settings,
                                cve_data=cve_param_data,
                                confidential_data=host_row.get('confidential_data', False),
                                internet_access=host_row.get('internet_access', False)
                            )
                            
                            if risk_result['calculation_possible']:
                                risk_score = risk_result['risk_score']
                                risk_raw = risk_result['raw_risk']
                        except Exception as risk_error:
                            print(f"⚠️ Error calculating risk for CVE {cve}: {risk_error}")
                    
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
                        WHERE cve = $13
                    """
                    
                    # Выполняем UPDATE с timeout для избежания блокировок
                    try:
                        await asyncio.wait_for(
                            conn.execute(update_query,
                                cvss_score,
                                cvss_source,
                                epss_row['epss'] if epss_row else None,
                                epss_row['percentile'] if epss_row else None,
                                exploit_count,
                                has_exploits,
                                risk_score,
                                risk_raw,
                                metasploit_data.get(cve),
                                datetime.now(),
                                datetime.now(),
                                datetime.now(),
                                cve
                            ),
                            timeout=30.0  # 30 секунд timeout
                        )
                    except asyncio.TimeoutError:
                        print(f"⚠️ Timeout updating host for CVE {cve}, skipping")
                        continue
                    
                    updated_count += 1
                    
                    # Обновляем прогресс
                    if progress_callback and i % 10 == 0:
                        progress = (i + 1) / len(hosts_rows) * 100
                        await progress_callback(progress, f"Updated {i + 1}/{len(hosts_rows)} hosts")
                
                except Exception as e:
                    print(f"⚠️ Error updating host for CVE {cve}: {e}")
                    continue
            
            print(f"✅ Complete update finished: {updated_count} hosts updated from {len(cve_list)} CVEs")
            
            # Вызываем полный пересчет рисков
            await self.recalculate_all_risks(progress_callback)
            
            return {
                'success': True,
                'updated_count': updated_count,
                'processed_cves': len(cve_list),
                'message': f'Обновлено {updated_count} хостов из {len(cve_list)} CVE'
            }
            
        finally:
            await self.release_connection(conn)

    async def recalculate_all_risks(self, progress_callback=None):
        """Пересчитать риски для ВСЕХ хостов по новой формуле"""
        print("🚀 Starting risk recalculation for ALL hosts")
        
        conn = await self.get_connection()
        try:
            # Получаем настройки
            from .settings_repository import SettingsRepository
            settings_repo = SettingsRepository()
            settings = await settings_repo.get_settings()
            print(f"🔍 DEBUG recalculate_all_risks: settings keys={list(settings.keys()) if settings else 'None'}")
            if settings:
                exploitdb_keys = [k for k in settings.keys() if 'exploitdb' in k]
                metasploit_keys = [k for k in settings.keys() if 'metasploit' in k]
                print(f"🔍 DEBUG recalculate_all_risks: exploitdb settings={exploitdb_keys}")
                print(f"🔍 DEBUG recalculate_all_risks: metasploit settings={metasploit_keys}")
            
            # Получаем все хосты
            hosts_query = """
                SELECT id, cve, criticality, epss_score, cvss, confidential_data, internet_access
                FROM vulnanalizer.hosts 
                WHERE cve IS NOT NULL AND cve != '' AND epss_score IS NOT NULL
                ORDER BY id
            """
            hosts_rows = await conn.fetch(hosts_query)
            
            if not hosts_rows:
                print("❌ No hosts found for risk recalculation")
                return
            
            print(f"📊 Found {len(hosts_rows)} hosts to recalculate")
            
            updated_count = 0
            for i, host_row in enumerate(hosts_rows):
                try:
                    # Получаем данные CVE для расчета параметров
                    cve_data = {}
                    
                    # Получаем CVSS данные
                    cve_query = "SELECT cvss_v3_attack_vector, cvss_v3_privileges_required, cvss_v3_user_interaction, cvss_v2_access_vector, cvss_v2_access_complexity, cvss_v2_authentication FROM vulnanalizer.cve WHERE cve_id = $1"
                    cve_row = await conn.fetchrow(cve_query, host_row['cve'])
                    if cve_row:
                        cve_data.update({
                            'cvss_v3_attack_vector': cve_row.get('cvss_v3_attack_vector'),
                            'cvss_v3_privileges_required': cve_row.get('cvss_v3_privileges_required'),
                            'cvss_v3_user_interaction': cve_row.get('cvss_v3_user_interaction'),
                            'cvss_v2_access_vector': cve_row.get('cvss_v2_access_vector'),
                            'cvss_v2_access_complexity': cve_row.get('cvss_v2_access_complexity'),
                            'cvss_v2_authentication': cve_row.get('cvss_v2_authentication')
                        })
                    
                    # Получаем ExploitDB данные и подсчитываем эксплойты (исправленная логика)
                    exdb_query = """
                        SELECT type FROM vulnanalizer.exploitdb 
                        WHERE codes LIKE $1 
                        ORDER BY 
                            CASE type 
                                WHEN 'remote' THEN 1
                                WHEN 'webapps' THEN 2
                                WHEN 'local' THEN 3
                                WHEN 'hardware' THEN 4
                                WHEN 'dos' THEN 5
                                ELSE 6
                            END,
                            date_published DESC
                        LIMIT 1
                    """
                    exdb_row = await conn.fetchrow(exdb_query, f'%{host_row["cve"]}%')
                    if exdb_row and exdb_row['type']:
                        cve_data['exploitdb_type'] = exdb_row['type']
                    
                    # Подсчитываем количество эксплойтов с исправленной логикой
                    exploit_count_query = """
                        WITH cve_exploits AS (
                            SELECT 
                                unnest(string_to_array(codes, ';')) as cve_id,
                                exploit_id
                            FROM vulnanalizer.exploitdb 
                            WHERE codes IS NOT NULL AND codes LIKE '%CVE-%'
                        )
                        SELECT COUNT(*) as exploit_count
                        FROM cve_exploits 
                        WHERE cve_id = $1
                    """
                    exploit_count_row = await conn.fetchrow(exploit_count_query, host_row['cve'])
                    exploit_count = exploit_count_row['exploit_count'] if exploit_count_row else 0
                    
                    # Получаем Metasploit данные (исправленная логика)
                    msf_query = "SELECT rank FROM vulnanalizer.metasploit_modules WHERE \"references\" ILIKE $1 ORDER BY rank DESC LIMIT 1"
                    msf_row = await conn.fetchrow(msf_query, f'%{host_row["cve"]}%')
                    if msf_row and msf_row['rank'] is not None:
                        cve_data['msf_rank'] = msf_row['rank']
                    
                    # Рассчитываем риск
                    from database.risk_calculation import calculate_risk_score
                    risk_result = calculate_risk_score(
                        epss=float(host_row['epss_score']),
                        cvss=float(host_row['cvss']) if host_row['cvss'] else None,
                        criticality=host_row['criticality'],
                        settings=settings,
                        cve_data=cve_data,
                        confidential_data=host_row.get('confidential_data', False),
                        internet_access=host_row.get('internet_access', False)
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
                            host_row['id']
                        )
                        
                        updated_count += 1
                    
                    # Обновляем прогресс
                    if progress_callback and i % 100 == 0:
                        progress = (i + 1) / len(hosts_rows) * 100
                        await progress_callback(progress, f"Recalculated {i + 1}/{len(hosts_rows)} hosts")
                
                except Exception as e:
                    print(f"⚠️ Error recalculating risk for host {host_row['id']}: {e}")
                    continue
            
            print(f"✅ Risk recalculation finished: {updated_count} hosts updated")
            
        finally:
            await self.release_connection(conn)
