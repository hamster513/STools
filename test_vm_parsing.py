#!/usr/bin/env python3
"""
Тестовый скрипт для проверки парсинга VM CSV файла
"""
import csv
import io

def test_vm_csv_parsing():
    """Тестируем парсинг VM CSV файла"""
    
    # Читаем реальный файл
    with open('/Users/hom/Downloads/out.csv', 'r', encoding='utf-8') as f:
        csv_content = f.read()
    
    print(f"📊 Размер CSV файла: {len(csv_content)} символов")
    
    # Парсим CSV
    csv_reader = csv.DictReader(io.StringIO(csv_content), delimiter=';')
    
    vm_data = []
    row_count = 0
    
    for row in csv_reader:
        row_count += 1
        if row_count <= 5:  # Показываем первые 5 строк
            print(f"📋 Строка {row_count}: {dict(row)}")
        
        vm_data.append({
            'host': row['@Host'].strip('"'),
            'os_name': row['Host.OsName'].strip('"'),
            'groups': row['Host.@Groups'].strip('"'),
            'cve': row['Host.@Vulners.CVEs'].strip('"'),
            'criticality': row['Host.UF_Criticality'].strip('"'),
            'zone': row['Host.UF_Zone'].strip('"')
        })
    
    print(f"✅ Обработано {row_count} строк CSV, создано {len(vm_data)} записей")
    
    # Показываем примеры данных
    print(f"\n📋 Пример первой записи:")
    print(f"  Host: {vm_data[0]['host']}")
    print(f"  CVE: {vm_data[0]['cve']}")
    print(f"  Criticality: {vm_data[0]['criticality']}")
    print(f"  Zone: {vm_data[0]['zone']}")
    
    # Проверяем уникальные хосты
    unique_hosts = set()
    for record in vm_data:
        host_info = record['host']
        if ' (' in host_info:
            hostname = host_info.split(' (')[0]
        else:
            hostname = host_info
        unique_hosts.add(hostname)
    
    print(f"\n📊 Статистика:")
    print(f"  Всего записей: {len(vm_data)}")
    print(f"  Уникальных хостов: {len(unique_hosts)}")
    print(f"  Записей на хост: {len(vm_data) / len(unique_hosts):.1f}")
    
    # Проверяем валидность CVE
    valid_cves = [rec for rec in vm_data if rec['cve'].strip()]
    invalid_cves = [rec for rec in vm_data if not rec['cve'].strip()]
    print(f"  Записей с CVE: {len(valid_cves)}")
    print(f"  Записей без CVE: {len(invalid_cves)}")
    
    # Показываем примеры записей без CVE
    if invalid_cves:
        print(f"\n❌ Примеры записей без CVE:")
        for i, rec in enumerate(invalid_cves[:3]):
            print(f"  {i+1}. Host: {rec['host']}, CVE: '{rec['cve']}', Criticality: {rec['criticality']}")
    
    return vm_data

if __name__ == "__main__":
    test_vm_csv_parsing()