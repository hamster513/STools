"""
Утилиты для валидации данных
"""
import re
from datetime import datetime
from typing import Optional


def parse_date(date_str: Optional[str]) -> Optional[datetime]:
    """Парсинг даты из строки"""
    if not date_str or date_str.strip() == '':
        return None
    
    try:
        # Пробуем разные форматы даты
        formats = [
            '%Y-%m-%d',
            '%Y-%m-%d %H:%M:%S',
            '%d.%m.%Y',
            '%d/%m/%Y',
            '%Y/%m/%d'
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str.strip(), fmt)
            except ValueError:
                continue
        
        # Если ни один формат не подошел, возвращаем None
        return None
    except Exception:
        return None


def is_valid_ip(ip_str: str) -> bool:
    """Проверка валидности IP адреса"""
    if not ip_str:
        return False
    
    # Простая проверка IPv4
    ip_pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
    if not re.match(ip_pattern, ip_str):
        return False
    
    # Проверяем, что каждый октет в диапазоне 0-255
    try:
        octets = ip_str.split('.')
        for octet in octets:
            if not 0 <= int(octet) <= 255:
                return False
        return True
    except (ValueError, AttributeError):
        return False
