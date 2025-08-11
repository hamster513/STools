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


def calculate_risk_score(epss: float, cvss: float, settings: dict) -> Dict:
    """Рассчитать риск по формуле: raw_risk = EPSS * (CVSS / 10) * Impact"""
    if epss is None or cvss is None:
        return {
            'raw_risk': None,
            'risk_score': None,
            'calculation_possible': False,
            'impact': None
        }
    
    # Рассчитываем Impact на основе настроек
    impact = calculate_impact(settings)
    
    raw_risk = epss * (cvss / 10) * impact
    risk_score = min(1, raw_risk) * 100
    
    return {
        'raw_risk': raw_risk,
        'risk_score': risk_score,
        'calculation_possible': True,
        'impact': impact
    }
