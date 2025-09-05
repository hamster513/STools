"""
Единая функция расчета риска для всей системы
"""


def calculate_risk_score(epss: float, cvss: float = None, criticality: str = 'Medium', 
                        settings: dict = None, cve_data: dict = None, 
                        confidential_data: bool = False, internet_access: bool = False) -> dict:
    """
    Единая функция расчета риска по формуле:
    Risk = EPSS × (CVSS ÷ 10) × Impact × CVE_param × ExDB_param × MSF_param
    
    Args:
        epss: EPSS score
        cvss: CVSS score
        criticality: Критичность ресурса (Critical, High, Medium, Low, None)
        settings: Настройки системы
        cve_data: Данные CVE (CVSS v3/v2 метрики, ExploitDB тип, Metasploit ранг)
        confidential_data: Есть ли конфиденциальные данные
        internet_access: Есть ли доступ к интернету
    
    Returns:
        dict: Результат расчета с деталями
    """
    if epss is None:
        return {
            'raw_risk': None,
            'risk_score': None,
            'calculation_possible': False,
            'impact': None,
            'cve_param': None,
            'exdb_param': None,
            'msf_param': None,
            'formula_components': None
        }
    
    # Конвертируем decimal в float если нужно
    if hasattr(epss, 'as_tuple'):
        epss = float(epss)
    
    # Полный расчет Impact на основе критичности и других факторов
    impact = _calculate_impact_full(criticality, settings, confidential_data, internet_access)
    
    # Расчет CVE_param
    cve_param = _calculate_cve_param(cve_data, settings)
    
    # Новая формула: Risk = EPSS × (CVSS ÷ 10) × Impact × CVE_param × ExDB_param × MSF_param
    cvss_factor = (cvss / 10) if cvss is not None else 1.0
    
    # Получаем ExDB_param и MSF_param
    exdb_param = _calculate_exdb_param(cve_data, settings)
    msf_param = _calculate_msf_param(cve_data, settings)
    
    raw_risk = epss * cvss_factor * impact * cve_param * exdb_param * msf_param
    risk_score = round(min(1, raw_risk) * 100)
    
    # Отладочный вывод для CVE-2017-0144
    if cve_data and cve_data.get('cve_id') == 'CVE-2017-0144':
        print(f"🔍 DEBUG CVE-2017-0144: epss={epss}, cvss_factor={cvss_factor}, impact={impact}")
        print(f"🔍 DEBUG CVE-2017-0144: cve_param={cve_param}, exdb_param={exdb_param}, msf_param={msf_param}")
        print(f"🔍 DEBUG CVE-2017-0144: raw_risk={raw_risk}, risk_score={risk_score}")
        print(f"🔍 DEBUG CVE-2017-0144: cve_data={cve_data}")
        print(f"🔍 DEBUG CVE-2017-0144: settings keys={list(settings.keys()) if settings else 'None'}")
        if settings:
            exploitdb_keys = [k for k in settings.keys() if 'exploitdb' in k]
            metasploit_keys = [k for k in settings.keys() if 'metasploit' in k]
            print(f"🔍 DEBUG CVE-2017-0144: exploitdb settings={exploitdb_keys}")
            print(f"🔍 DEBUG CVE-2017-0144: metasploit settings={metasploit_keys}")
    
    return {
        'raw_risk': raw_risk,
        'risk_score': risk_score,
        'calculation_possible': True,
        'impact': impact,
        'cve_param': cve_param,
        'exdb_param': exdb_param,
        'msf_param': msf_param,
        'formula_components': {
            'epss': epss,
            'cvss': cvss,
            'cvss_factor': cvss_factor,
            'impact': impact,
            'cve_param': cve_param,
            'exdb_param': exdb_param,
            'msf_param': msf_param
        }
    }


def _calculate_impact_full(criticality: str, settings: dict = None, confidential_data: bool = False, internet_access: bool = False) -> float:
    """Полный расчет Impact с учетом всех факторов"""
    # Получаем настройки Impact параметров
    if not settings:
        settings = {}
    
    impact_settings = settings.get('impact', {})
    
    # Настройки по умолчанию
    default_impact = {
        'resource_criticality': {
            'Critical': 0.33, 'High': 0.25, 'Medium': 0.2, 'Low': 0.1, 'None': 0.2
        },
        'confidential_data': {
            'Есть': 0.33, 'Отсутствуют': 0.2
        },
        'internet_access': {
            'Доступен': 0.33, 'Недоступен': 0.2
        }
    }
    
    # Объединяем настройки
    for key, value in default_impact.items():
        if key not in impact_settings:
            impact_settings[key] = value
    
    # Расчет Impact как суммы всех факторов
    resource_impact = impact_settings['resource_criticality'].get(criticality, 0.2)
    
    # Конвертируем boolean в строки для настроек
    confidential_str = 'Есть' if confidential_data else 'Отсутствуют'
    internet_str = 'Доступен' if internet_access else 'Недоступен'
    
    confidential_impact = impact_settings['confidential_data'].get(confidential_str, 0.2)
    internet_impact = impact_settings['internet_access'].get(internet_str, 0.2)
    
    total_impact = resource_impact + confidential_impact + internet_impact
    
    return total_impact


def _calculate_cve_param(cve_data: dict = None, settings: dict = None) -> float:
    """Расчет CVE_param на основе CVSS метрик"""
    if not cve_data or not settings:
        return 1.0
    
    # Получаем настройки CVE параметров
    cve_settings = settings.get('cve', {})
    
    # Настройки по умолчанию для CVSS v3
    default_cve_v3 = {
        'attack_vector': {'NETWORK': 1.2, 'ADJACENT_NETWORK': 1.1, 'LOCAL': 1.0, 'PHYSICAL': 0.9},
        'privileges_required': {'NONE': 1.2, 'LOW': 1.1, 'HIGH': 1.0},
        'user_interaction': {'NONE': 1.2, 'REQUIRED': 1.0}
    }
    
    # Настройки по умолчанию для CVSS v2
    default_cve_v2 = {
        'access_vector': {'NETWORK': 1.2, 'ADJACENT_NETWORK': 1.1, 'LOCAL': 1.0},
        'access_complexity': {'LOW': 1.2, 'MEDIUM': 1.1, 'HIGH': 1.0},
        'authentication': {'NONE': 1.2, 'SINGLE': 1.1, 'MULTIPLE': 1.0}
    }
    
    # Объединяем настройки
    cve_v3_settings = cve_settings.get('cvss_v3', default_cve_v3)
    cve_v2_settings = cve_settings.get('cvss_v2', default_cve_v2)
    
    # Проверяем CVSS v3 метрики
    if cve_data.get('cvss_v3_attack_vector'):
        attack_vector = cve_data['cvss_v3_attack_vector']
        privileges_required = cve_data.get('cvss_v3_privileges_required', 'NONE')
        user_interaction = cve_data.get('cvss_v3_user_interaction', 'NONE')
        
        attack_mult = cve_v3_settings['attack_vector'].get(attack_vector, 1.0)
        priv_mult = cve_v3_settings['privileges_required'].get(privileges_required, 1.0)
        user_mult = cve_v3_settings['user_interaction'].get(user_interaction, 1.0)
        
        return attack_mult * priv_mult * user_mult
    
    # Проверяем CVSS v2 метрики
    elif cve_data.get('cvss_v2_access_vector'):
        access_vector = cve_data['cvss_v2_access_vector']
        access_complexity = cve_data.get('cvss_v2_access_complexity', 'LOW')
        authentication = cve_data.get('cvss_v2_authentication', 'NONE')
        
        vector_mult = cve_v2_settings['access_vector'].get(access_vector, 1.0)
        complexity_mult = cve_v2_settings['access_complexity'].get(access_complexity, 1.0)
        auth_mult = cve_v2_settings['authentication'].get(authentication, 1.0)
        
        return vector_mult * complexity_mult * auth_mult
    
    return 1.0


def _calculate_exdb_param(cve_data: dict = None, settings: dict = None) -> float:
    """Расчет ExDB_param на основе типа эксплойта ExploitDB"""
    if not cve_data or not cve_data.get('exploitdb_type'):
        return 1.0
    
    exploit_type = cve_data['exploitdb_type']
    
    # Получаем настройки ExploitDB параметров
    if not settings:
        settings = {}
    
    # Настройки по умолчанию
    default_exdb = {
        'remote': 0.8,
        'webapps': 0.85,
        'dos': 0.8,
        'local': 0.9,
        'hardware': 0.7
    }
    
    # Читаем настройки из базы данных
    exdb_settings = {}
    for key in default_exdb.keys():
        setting_key = f'exploitdb_{key}'
        if setting_key in settings:
            exdb_settings[key] = float(settings[setting_key])
        else:
            exdb_settings[key] = default_exdb[key]
    
    # Отладочный вывод для CVE-2017-0144
    if cve_data and cve_data.get('cve_id') == 'CVE-2017-0144':
        print(f"🔍 DEBUG _calculate_exdb_param: exploit_type={exploit_type}")
        print(f"🔍 DEBUG _calculate_exdb_param: exdb_settings={exdb_settings}")
        print(f"🔍 DEBUG _calculate_exdb_param: result={exdb_settings.get(exploit_type, 1.0)}")
    
    return exdb_settings.get(exploit_type, 1.0)


def _calculate_msf_param(cve_data: dict = None, settings: dict = None) -> float:
    """Расчет MSF_param на основе ранга Metasploit"""
    if not cve_data or not cve_data.get('msf_rank'):
        return 1.0
    
    msf_rank = cve_data['msf_rank']
    
    # Получаем настройки Metasploit параметров
    if not settings:
        settings = {}
    
    # Настройки по умолчанию
    default_msf = {
        'excellent': 1.3,
        'good': 1.1,
        'normal': 1.0,
        'average': 0.9,
        'low': 0.8,
        'unknown': 1.0,
        'manual': 0.7
    }
    
    # Читаем настройки из базы данных
    msf_settings = {}
    for key in default_msf.keys():
        setting_key = f'metasploit_{key}'
        if setting_key in settings:
            msf_settings[key] = float(settings[setting_key])
        else:
            msf_settings[key] = default_msf[key]
    
    # Если msf_rank - число, конвертируем в строку
    if isinstance(msf_rank, (int, float)):
        # Маппинг числовых рангов Metasploit в строковые
        if msf_rank >= 1000:
            msf_rank = 'excellent'
        elif msf_rank >= 500:
            msf_rank = 'good'
        elif msf_rank >= 300:
            msf_rank = 'normal'
        elif msf_rank >= 200:
            msf_rank = 'average'
        elif msf_rank >= 100:
            msf_rank = 'low'
        else:
            msf_rank = 'unknown'
    
    return msf_settings.get(msf_rank, 1.0)
