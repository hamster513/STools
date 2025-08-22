#!/usr/bin/env python3
"""
Генератор тестовых данных для STools
Создает CSV файл с 100k записей хостов, включая 10k с эксплойтами
"""

import csv
import random
import string
from datetime import datetime, timedelta

def generate_cve_id():
    """Генерирует случайный CVE ID"""
    year = random.randint(1999, 2024)
    number = random.randint(1, 99999)
    return f"CVE-{year}-{number:05d}"

def generate_ip():
    """Генерирует случайный IP адрес"""
    return f"{random.randint(1, 254)}.{random.randint(1, 254)}.{random.randint(1, 254)}.{random.randint(1, 254)}"

def generate_hostname():
    """Генерирует случайное имя хоста"""
    prefixes = ['server', 'host', 'node', 'vm', 'container', 'instance', 'machine']
    suffixes = ['prod', 'dev', 'test', 'staging', 'backup', 'db', 'web', 'app']
    
    prefix = random.choice(prefixes)
    suffix = random.choice(suffixes)
    number = random.randint(1, 999)
    
    return f"{prefix}-{suffix}-{number:03d}"

def generate_test_data(num_hosts=100000, num_with_exploits=10000):
    """Генерирует тестовые данные"""
    
    # Создаем пул CVE с эксплойтами (10k записей с эксплойтами)
    exploit_cves = set()
    for _ in range(num_with_exploits):
        exploit_cves.add(generate_cve_id())
    
    # Создаем общий пул CVE
    all_cves = set()
    for _ in range(num_hosts * 3):  # Больше CVE чем хостов
        all_cves.add(generate_cve_id())
    
    # Добавляем CVE с эксплойтами в общий пул
    all_cves.update(exploit_cves)
    
    # Конвертируем в список для выборки
    all_cves_list = list(all_cves)
    exploit_cves_list = list(exploit_cves)
    
    # Генерируем хосты
    hosts = []
    criticality_levels = ['Critical', 'High', 'Medium', 'Low', 'None']
    zones = ['DMZ', 'Internal', 'External', 'Management', 'Backup']
    os_names = ['Linux', 'Windows', 'macOS', 'FreeBSD', 'Ubuntu', 'CentOS', 'Debian']
    
    for i in range(num_hosts):
        hostname = generate_hostname()
        ip = generate_ip()
        
        # Выбираем CVE для хоста
        if i < num_with_exploits:
            # Первые 10k хостов получают CVE с эксплойтами
            cve = random.choice(exploit_cves_list)
        else:
            # Остальные получают случайные CVE
            cve = random.choice(all_cves_list)
        
        # Добавляем дополнительные CVE (1-3 штуки)
        additional_cves = []
        for _ in range(random.randint(0, 3)):
            additional_cve = random.choice(all_cves_list)
            if additional_cve != cve and additional_cve not in additional_cves:
                additional_cves.append(additional_cve)
        
        # Объединяем CVE
        all_cves_for_host = [cve] + additional_cves
        cve_string = ','.join(all_cves_for_host)
        
        host = {
            '@Host': f'{hostname} ({ip})',
            'Host.@Vulners.CVEs': cve_string,
            'host.UF_Criticality': random.choice(criticality_levels),
            'Host.UF_Zone': random.choice(zones),
            'Host.OsName': random.choice(os_names)
        }
        
        hosts.append(host)
    
    return hosts

def save_to_csv(hosts, filename='test_data_100k.csv'):
    """Сохраняет данные в CSV файл"""
    
    fieldnames = ['@Host', 'Host.@Vulners.CVEs', 'host.UF_Criticality', 'Host.UF_Zone', 'Host.OsName']
    
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames, delimiter=';')
        writer.writeheader()
        writer.writerows(hosts)
    
    # Получаем размер файла после закрытия
    import os
    file_size = os.path.getsize(filename) / (1024*1024)
    
    print(f"✅ Создан файл {filename}")
    print(f"📊 Количество записей: {len(hosts):,}")
    print(f"🎯 Размер файла: {file_size:.2f} МБ")

def main():
    print("🚀 Генерация тестовых данных...")
    print("📋 Параметры:")
    print("   - Общее количество хостов: 100,000")
    print("   - Хостов с эксплойтами: 10,000")
    print("   - CVE на хост: 1-5")
    
    # Генерируем данные
    hosts = generate_test_data(100000, 10000)
    
    # Сохраняем в файл
    save_to_csv(hosts, 'test_data_100k.csv')
    
    print("✅ Генерация завершена!")

if __name__ == "__main__":
    main()
