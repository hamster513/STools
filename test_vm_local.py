#!/usr/bin/env python3
"""
Тестовый скрипт для локального тестирования VM импорта с реальным файлом
"""
import csv
import io
import os

def _group_vm_data_by_hosts(vm_data):
    """Преобразует данные VM в формат для hosts_repository (один CVE = одна запись)"""
    result = []
    
    print(f"🔄 Начинаем преобразование {len(vm_data)} записей (один CVE = одна запись)")
    
    for record in vm_data:
        host_info = record['host']
        
        # Парсим hostname и IP
        if ' (' in host_info:
            hostname = host_info.split(' (')[0]
            ip_address = host_info.split('(')[1].split(')')[0]
        else:
            hostname = host_info
            ip_address = ''
        
        # Получаем CVE
        cve = record['cve']
        if not cve or not cve.strip():
            continue
        
        # Создаем запись для каждого CVE
        result.append({
            'hostname': hostname,
            'ip_address': ip_address,
            'cve': cve,
            'cvss': 0.0,  # По умолчанию CVSS = 0
            'criticality': record.get('criticality', 'Medium'),  # Из Host.UF_Criticality
            'zone': record.get('zone', ''),  # Из Host.UF_Zone
            'status': 'Active'
        })
    
    print(f"✅ Преобразовано {len(result)} записей из {len(vm_data)} исходных (один CVE = одна запись)")
    return result

def test_vm_import():
    """Тестируем импорт VM с реальным файлом"""
    
    print("🚀 Начинаем тестирование VM импорта с реальным файлом")
    
    # Читаем реальный файл
    csv_file = '/Users/hom/Downloads/out.csv'
    if not os.path.exists(csv_file):
        print(f"❌ Файл {csv_file} не найден!")
        return
    
    with open(csv_file, 'r', encoding='utf-8') as f:
        csv_content = f.read()
    
    print(f"📊 Размер CSV файла: {len(csv_content)} символов")
    
    # Парсим CSV (как в vm_worker.py)
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
    
    # Преобразуем данные
    hosts = _group_vm_data_by_hosts(vm_data)
    
    print(f"📊 После преобразования: {len(hosts)} записей")
    if len(hosts) > 0:
        print(f"📋 Пример первой записи: {hosts[0]}")
    
    # Тестируем сохранение в базу (без реального сохранения)
    print(f"\n🔍 Анализ данных для сохранения:")
    
    # Подсчитываем только записи с CVE (как в insert_hosts_records_with_progress)
    valid_records = [rec for rec in hosts if rec.get('cve', '').strip()]
    total_records = len(valid_records)
    skipped_records = len(hosts) - total_records
    
    print(f"📊 Всего записей получено: {len(hosts)}")
    print(f"✅ Записей с CVE: {total_records}")
    print(f"❌ Записей без CVE (пропущено): {skipped_records}")
    
    if len(hosts) > 0:
        print(f"📋 Пример первой записи: {hosts[0]}")
    if len(valid_records) > 0:
        print(f"✅ Пример первой валидной записи: {valid_records[0]}")
    
    # Проверяем структуру данных
    if valid_records:
        first_record = valid_records[0]
        required_fields = ['hostname', 'ip_address', 'cve', 'cvss', 'criticality', 'status']
        missing_fields = [field for field in required_fields if field not in first_record]
        
        if missing_fields:
            print(f"❌ Отсутствуют поля: {missing_fields}")
        else:
            print(f"✅ Все необходимые поля присутствуют")
        
        # Проверяем типы данных
        print(f"\n🔍 Проверка типов данных:")
        print(f"  hostname: {type(first_record['hostname'])} = '{first_record['hostname']}'")
        print(f"  ip_address: {type(first_record['ip_address'])} = '{first_record['ip_address']}'")
        print(f"  cve: {type(first_record['cve'])} = '{first_record['cve']}'")
        print(f"  cvss: {type(first_record['cvss'])} = {first_record['cvss']}")
        print(f"  criticality: {type(first_record['criticality'])} = '{first_record['criticality']}'")
        print(f"  zone: {type(first_record['zone'])} = '{first_record['zone']}'")
        print(f"  status: {type(first_record['status'])} = '{first_record['status']}'")
    
    print(f"\n🎯 Результат: {total_records} записей готовы к сохранению в базу данных")
    
    # Симулируем SQL запрос
    if valid_records:
        print(f"\n🔍 Симуляция SQL запроса:")
        first_record = valid_records[0]
        print(f"INSERT INTO vulnanalizer.hosts (hostname, ip_address, cve, cvss, criticality, status, os_name, zone)")
        print(f"VALUES (")
        print(f"  '{first_record['hostname']}',")
        print(f"  '{first_record['ip_address']}',")
        print(f"  '{first_record['cve']}',")
        print(f"  {first_record['cvss']},")
        print(f"  '{first_record['criticality']}',")
        print(f"  '{first_record['status']}',")
        print(f"  '',")  # os_name
        print(f"  '{first_record['zone']}'")
        print(f")")

if __name__ == "__main__":
    test_vm_import()