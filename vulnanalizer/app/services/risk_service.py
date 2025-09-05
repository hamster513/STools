"""
Сервис расчета рисков
"""
from typing import Dict


def calculate_impact(settings: dict) -> float:
    """Рассчитать Impact на основе настроек"""
    # Веса для критичности ресурса
    resource_weights = {
        'Critical': 0.33,
        'High': 0.25,
        'Medium': 0.15,
        'None': 0.1
    }
    
    # Веса для конфиденциальных данных
    data_weights = {
        'Есть': 0.33,
        'Отсутствуют': 0.1
    }
    
    # Веса для доступа из интернета
    internet_weights = {
        'Доступен': 0.33,
        'Недоступен': 0.1
    }
    
    # Получаем значения из настроек
    resource_criticality = settings.get('impact_resource_criticality', 'Medium')
    confidential_data = settings.get('impact_confidential_data', 'Отсутствуют')
    internet_access = settings.get('impact_internet_access', 'Недоступен')
    
    # Рассчитываем Impact
    impact = (
        resource_weights.get(resource_criticality, 0.15) +
        data_weights.get(confidential_data, 0.1) +
        internet_weights.get(internet_access, 0.1)
    )
    
    return impact


async def get_risk_calculation_details(host_id: int, cve: str) -> Dict:
    """Получить детали расчета риска для конкретного хоста и CVE"""
    print(f"🔍 Risk service: host_id={host_id}, cve={cve}")
    try:
        from database import get_db
        
        db = get_db()
        conn = await db.get_connection()
        
        try:
            # Получаем данные хоста
            host_query = """
                SELECT 
                    h.hostname, h.ip_address, h.criticality, h.risk_score,
                    h.cvss, h.cvss_source, h.epss_score, h.exploits_count,
                    h.epss_updated_at, h.exploits_updated_at, h.risk_updated_at,
                    h.confidential_data, h.internet_access
                FROM vulnanalizer.hosts h
                WHERE h.id = $1 AND h.cve = $2
            """
            
            host_row = await conn.fetchrow(host_query, host_id, cve)
            
            if not host_row:
                return {}
            
            # Получаем настройки системы
            from database.settings_repository import SettingsRepository
            settings_repo = SettingsRepository()
            settings = await settings_repo.get_settings()
            
            # Используем реальный сервис расчета риска
            try:
                from database.hosts_update_service import HostsUpdateService
                hosts_update_service = HostsUpdateService()
                
                # Получаем данные CVE для расчета
                cve_query = """
                    SELECT cvss_v3_attack_vector, cvss_v3_privileges_required, cvss_v3_user_interaction,
                           cvss_v2_access_vector, cvss_v2_access_complexity, cvss_v2_authentication
                    FROM vulnanalizer.cve 
                    WHERE cve_id = $1
                """
                cve_row = await conn.fetchrow(cve_query, cve)
                cve_data = dict(cve_row) if cve_row else {}
                cve_data['cve_id'] = cve
                
                # Сохраняем CVSS метрики для отображения в деталях
                cvss_metrics = {
                    'cvss_v3_attack_vector': cve_data.get('cvss_v3_attack_vector'),
                    'cvss_v3_privileges_required': cve_data.get('cvss_v3_privileges_required'),
                    'cvss_v3_user_interaction': cve_data.get('cvss_v3_user_interaction'),
                    'cvss_v2_access_vector': cve_data.get('cvss_v2_access_vector'),
                    'cvss_v2_access_complexity': cve_data.get('cvss_v2_access_complexity'),
                    'cvss_v2_authentication': cve_data.get('cvss_v2_authentication')
                }
                
                # Получаем реальный тип эксплойта из ExploitDB
                exdb_query = """
                    SELECT type FROM vulnanalizer.exploitdb 
                    WHERE codes LIKE '%' || $1 || '%' 
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
                    print(f"⚠️ Error getting ExploitDB data: {e}")
                    cve_data['exploitdb_type'] = None
                
                # Получаем реальный ранг Metasploit
                msf_query = """
                    SELECT rank FROM vulnanalizer.metasploit_modules 
                    WHERE "references" LIKE '%' || $1 || '%' 
                    ORDER BY rank DESC 
                    LIMIT 1
                """
                try:
                    msf_row = await conn.fetchrow(msf_query, cve)
                    if msf_row and msf_row['rank']:
                        cve_data['msf_rank'] = msf_row['rank']
                    else:
                        cve_data['msf_rank'] = None
                except Exception as e:
                    print(f"⚠️ Error getting Metasploit data: {e}")
                    cve_data['msf_rank'] = None
                
                # Рассчитываем риск по единой функции
                from database.risk_calculation import calculate_risk_score
                risk_result = calculate_risk_score(
                    epss=float(host_row['epss_score']) if host_row['epss_score'] else 0,
                    cvss=float(host_row['cvss']) if host_row['cvss'] else 0,
                    criticality=host_row['criticality'],
                    settings=settings,
                    cve_data=cve_data,
                    confidential_data=host_row.get('confidential_data', False),
                    internet_access=host_row.get('internet_access', False)
                )
                
                # Формируем детали расчета
                calculation_details = {
                    "base_risk": round(risk_result.get('raw_risk', 0) * 100, 2),
                    "criticality_multiplier": get_criticality_multiplier(host_row['criticality']),
                    "epss_multiplier": get_epss_multiplier(host_row['epss_score']),
                    "exploits_multiplier": get_exploits_multiplier(host_row['exploits_count']),
                    "final_calculation": f"{risk_result.get('risk_score', 0):.2f}%",
                    "impact": risk_result.get('impact', 1.0),
                    "cve_param": risk_result.get('cve_param', 1.0),
                    "exdb_param": risk_result.get('exdb_param', 1.0),
                    "msf_param": risk_result.get('msf_param', 1.0),
                    "calculated_risk": risk_result.get('raw_risk', 0),
                    "calculated_risk_percent": risk_result.get('risk_score', 0),
                    "formula_components": {
                        "epss": float(host_row['epss_score']) if host_row['epss_score'] else 0,
                        "cvss": float(host_row['cvss']) if host_row['cvss'] else 0,
                        "cvss_factor": (float(host_row['cvss']) / 10) if host_row['cvss'] else 0,
                        "impact": risk_result.get('impact', 1.0),
                        "cve_param": risk_result.get('cve_param', 1.0),
                        "exdb_param": risk_result.get('exdb_param', 1.0),
                        "msf_param": risk_result.get('msf_param', 1.0)
                    },
                    **cvss_metrics
                }
                
            except Exception as e:
                print(f"⚠️ Error using real risk service: {e}")
                # Возвращаем пустые детали в случае ошибки
                calculation_details = {
                    "error": f"Ошибка расчета риска: {str(e)}",
                    "base_risk": 0,
                    "final_calculation": "0.00%",
                    "impact": 0,
                    "cve_param": 1.0,
                    "exdb_param": 1.0,
                    "msf_param": 1.0,
                    "calculated_risk": 0,
                    "calculated_risk_percent": 0,
                    "formula_components": {
                        "epss": 0,
                        "cvss": 0,
                        "cvss_factor": 0,
                        "impact": 0,
                        "cve_param": 1.0,
                        "exdb_param": 1.0,
                        "msf_param": 1.0
                    },
                    **cvss_metrics
                }
            
            return calculation_details
            
        finally:
            await db.release_connection(conn)
            
    except Exception as e:
        print(f"Error getting risk calculation details: {e}")
        return {}


def get_criticality_multiplier(criticality: str) -> float:
    """Получить множитель критичности"""
    multipliers = {
        'Critical': 1.5,
        'High': 1.3,
        'Medium': 1.1,
        'Low': 1.0,
        'None': 0.9
    }
    return multipliers.get(criticality, 1.0)


def get_epss_multiplier(epss_score: float) -> float:
    """Получить множитель EPSS"""
    if epss_score is None:
        return 1.0
    if epss_score >= 0.8:
        return 1.4
    elif epss_score >= 0.6:
        return 1.2
    elif epss_score >= 0.4:
        return 1.1
    elif epss_score >= 0.2:
        return 1.0
    else:
        return 0.9


def get_exploits_multiplier(exploits_count: int) -> float:
    """Получить множитель эксплойтов"""
    if not exploits_count:
        return 1.0
    if exploits_count >= 10:
        return 1.5
    elif exploits_count >= 5:
        return 1.3
    elif exploits_count >= 2:
        return 1.2
    else:
        return 1.1
