#!/usr/bin/env python3
"""
Генератор реалистичных данных с реальными CVE из базы данных
"""

import csv
import random
import subprocess
from datetime import datetime

class RealisticDataGeneratorWithRealCVEs:
    def __init__(self):
        self.os_names = [
            "Windows 10", "Windows 11", "Windows Server 2019", "Windows Server 2022",
            "Ubuntu 20.04", "Ubuntu 22.04", "CentOS 7", "CentOS 8", "RHEL 8", "RHEL 9",
            "Debian 11", "Debian 12", "Alpine Linux", "macOS 12", "macOS 13"
        ]
        
        self.zones = ["Internal", "DMZ", "External", "Management", "Production", "Development"]
        self.criticality_levels = ["Critical", "High", "Medium", "Low"]
        
    def get_real_cves_from_database(self):
        """Получает реальные CVE из базы данных"""
        print("📥 Получение реальных CVE из базы данных...")
        
        try:
            # Получаем CVE из таблицы cve (NVD) с CVSS
            print("🔍 Загрузка CVE из NVD...")
            nvd_query = """
                SELECT cve_id, description, cvss_v3_base_score, cvss_v2_base_score, 
                       cvss_v3_base_severity, cvss_v2_base_severity
                FROM vulnanalizer.cve 
                WHERE cve_id IS NOT NULL 
                AND (cvss_v3_base_score IS NOT NULL OR cvss_v2_base_score IS NOT NULL)
                ORDER BY RANDOM() 
                LIMIT 90000;
            """
            result = subprocess.run([
                'docker', 'exec', 'stools_postgres', 'psql', 
                '-U', 'stools_user', '-d', 'stools_db', 
                '-c', nvd_query, '--csv', '--no-align', '--tuples-only'
            ], capture_output=True, text=True)
            
            if result.returncode != 0:
                print(f"❌ Ошибка при получении NVD CVE: {result.stderr}")
                return []
            
            nvd_cves = []
            for line in result.stdout.strip().split('\n'):
                if line and ',' in line:
                    parts = line.split(',')
                    if len(parts) >= 6:
                        try:
                            cvss_v3 = parts[2].strip('"')
                            cvss_v2 = parts[3].strip('"')
                            
                            # Проверяем, что это числа
                            cvss_v3_score = None
                            cvss_v2_score = None
                            
                            if cvss_v3 and cvss_v3.replace('.', '').isdigit():
                                cvss_v3_score = cvss_v3
                            if cvss_v2 and cvss_v2.replace('.', '').isdigit():
                                cvss_v2_score = cvss_v2
                            
                            cve_data = {
                                'cve_id': parts[0].strip('"'),
                                'description': parts[1].strip('"'),
                                'cvss_v3_base_score': cvss_v3_score,
                                'cvss_v2_base_score': cvss_v2_score,
                                'cvss_v3_base_severity': parts[4].strip('"'),
                                'cvss_v2_base_severity': parts[5].strip('"'),
                                'source': 'NVD'
                            }
                            nvd_cves.append(cve_data)
                        except Exception as e:
                            print(f"⚠️ Пропускаем некорректную строку: {line[:100]}...")
                            continue
            
            print(f"✅ Загружено {len(nvd_cves)} CVE из NVD")
            
            # Получаем CVE из ExploitDB
            print("🔍 Загрузка CVE из ExploitDB...")
            exploitdb_query = """
                SELECT DISTINCT split_part(codes, ';', 1) as cve_id
                FROM vulnanalizer.exploitdb 
                WHERE codes IS NOT NULL AND codes LIKE 'CVE-%'
                ORDER BY split_part(codes, ';', 1)
                LIMIT 10000;
            """
            result = subprocess.run([
                'docker', 'exec', 'stools_postgres', 'psql', 
                '-U', 'stools_user', '-d', 'stools_db', 
                '-c', exploitdb_query, '--csv', '--no-align', '--tuples-only'
            ], capture_output=True, text=True)
            
            if result.returncode != 0:
                print(f"❌ Ошибка при получении ExploitDB CVE: {result.stderr}")
                exploitdb_cves = []
            else:
                exploitdb_cves = []
                for line in result.stdout.strip().split('\n'):
                    if line and line.strip():
                        cve_id = line.strip('"')
                        # Проверяем, есть ли этот CVE в NVD
                        if not any(cve['cve_id'] == cve_id for cve in nvd_cves):
                            cve_data = {
                                'cve_id': cve_id,
                                'description': f'Exploit available for {cve_id}',
                                'cvss_v3_base_score': None,
                                'cvss_v2_base_score': None,
                                'cvss_v3_base_severity': None,
                                'cvss_v2_base_severity': None,
                                'source': 'ExploitDB'
                            }
                            exploitdb_cves.append(cve_data)
                
                print(f"✅ Загружено {len(exploitdb_cves)} уникальных CVE из ExploitDB")
            
            # Объединяем CVE
            all_cves = nvd_cves + exploitdb_cves
            print(f"✅ Всего загружено {len(all_cves)} уникальных CVE")
            
            return all_cves
            
        except Exception as e:
            print(f"❌ Ошибка при получении CVE: {e}")
            return []
    
    def generate_hostname(self):
        """Генерирует реалистичное имя хоста"""
        prefixes = ['web', 'app', 'db', 'api', 'auth', 'cache', 'load', 'proxy', 'mail', 'dns']
        suffixes = ['prod', 'dev', 'test', 'staging', 'backup', 'monitor', 'log', 'admin']
        
        prefix = random.choice(prefixes)
        suffix = random.choice(suffixes)
        number = random.randint(1, 999)
        
        return f"{prefix}-{suffix}-{number:03d}"
    
    def generate_ip(self):
        """Генерирует реалистичный IP адрес"""
        # Генерируем IP из разных диапазонов
        ranges = [
            (10, 10, 0, 255, 0, 255),      # 10.0.0.0/8
            (172, 172, 16, 31, 0, 255),    # 172.16.0.0/12
            (192, 192, 168, 168, 0, 255)   # 192.168.0.0/16
        ]
        
        range_choice = random.choice(ranges)
        
        # Первый октет
        first = range_choice[0]
        # Второй октет
        second = random.randint(range_choice[2], range_choice[3])
        # Третий октет
        third = random.randint(range_choice[4], range_choice[5])
        # Четвертый октет
        fourth = random.randint(1, 254)
        
        return f"{first}.{second}.{third}.{fourth}"
    
    def generate_realistic_data(self, num_hosts=100000):
        """Генерирует реалистичные данные с реальными CVE"""
        print(f"🚀 Начинаем генерацию {num_hosts} записей хостов...")
        
        # Получаем реальные CVE
        cves = self.get_real_cves_from_database()
        if not cves:
            print("❌ Не удалось получить CVE из базы данных")
            return
        
        hosts = []
        
        for i in range(num_hosts):
            if i % 10000 == 0:
                print(f"📊 Обработано {i}/{num_hosts} записей...")
            
            hostname = self.generate_hostname()
            ip = self.generate_ip()
            os_name = random.choice(self.os_names)
            zone = random.choice(self.zones)
            
            # Выбираем случайный CVE
            cve_data = random.choice(cves)
            
            # Определяем критичность на основе CVSS
            try:
                if cve_data['cvss_v3_base_score'] and cve_data['cvss_v3_base_score'].replace('.', '').isdigit():
                    score = float(cve_data['cvss_v3_base_score'])
                    if score >= 9.0:
                        criticality = "Critical"
                    elif score >= 7.0:
                        criticality = "High"
                    elif score >= 4.0:
                        criticality = "Medium"
                    else:
                        criticality = "Low"
                elif cve_data['cvss_v2_base_score'] and cve_data['cvss_v2_base_score'].replace('.', '').isdigit():
                    score = float(cve_data['cvss_v2_base_score'])
                    if score >= 7.0:
                        criticality = "Critical"
                    elif score >= 5.0:
                        criticality = "High"
                    elif score >= 3.0:
                        criticality = "Medium"
                    else:
                        criticality = "Low"
                else:
                    # Для CVE без CVSS используем случайную критичность
                    criticality = random.choice(self.criticality_levels)
            except (ValueError, TypeError):
                # Для CVE без CVSS используем случайную критичность
                criticality = random.choice(self.criticality_levels)
            
            # Создаем запись с одним CVE
            host = {
                '@Host': f'{hostname} ({ip})',
                'Host.OsName': os_name,
                'Host.@Vulners.CVEs': cve_data['cve_id'],
                'host.UF_Criticality': criticality,
                'Host.UF_Zone': zone
            }
            hosts.append(host)
            
            # Добавляем дополнительные CVE (0-2) как отдельные записи
            num_additional = random.randint(0, 2)
            for _ in range(num_additional):
                additional_cve_data = random.choice(cves)
                
                # Определяем критичность для дополнительного CVE
                try:
                    if additional_cve_data['cvss_v3_base_score'] and additional_cve_data['cvss_v3_base_score'].replace('.', '').isdigit():
                        score = float(additional_cve_data['cvss_v3_base_score'])
                        if score >= 9.0:
                            additional_criticality = "Critical"
                        elif score >= 7.0:
                            additional_criticality = "High"
                        elif score >= 4.0:
                            additional_criticality = "Medium"
                        else:
                            additional_criticality = "Low"
                    elif additional_cve_data['cvss_v2_base_score'] and additional_cve_data['cvss_v2_base_score'].replace('.', '').isdigit():
                        score = float(additional_cve_data['cvss_v2_base_score'])
                        if score >= 7.0:
                            additional_criticality = "Critical"
                        elif score >= 5.0:
                            additional_criticality = "High"
                        elif score >= 3.0:
                            additional_criticality = "Medium"
                        else:
                            additional_criticality = "Low"
                    else:
                        additional_criticality = random.choice(self.criticality_levels)
                except (ValueError, TypeError):
                    additional_criticality = random.choice(self.criticality_levels)
                
                additional_host = {
                    '@Host': f'{hostname} ({ip})',
                    'Host.OsName': os_name,
                    'Host.@Vulners.CVEs': additional_cve_data['cve_id'],
                    'host.UF_Criticality': additional_criticality,
                    'Host.UF_Zone': zone
                }
                hosts.append(additional_host)
        
        print(f"✅ Сгенерировано {len(hosts)} записей хостов")
        return hosts
    
    def save_to_csv(self, hosts, filename='realistic_test_data_with_real_cves.csv'):
        """Сохраняет данные в CSV файл"""
        print(f"💾 Сохранение данных в файл {filename}...")
        
        fieldnames = ['@Host', 'Host.OsName', 'Host.@Vulners.CVEs', 'host.UF_Criticality', 'Host.UF_Zone']
        
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames, delimiter=';', quoting=csv.QUOTE_ALL)
            writer.writeheader()
            writer.writerows(hosts)
        
        print(f"✅ Данные сохранены в файл {filename}")
        print(f"📊 Всего записей: {len(hosts)}")

def main():
    print("🎯 Генератор реалистичных данных с реальными CVE")
    print("=" * 50)
    
    generator = RealisticDataGeneratorWithRealCVEs()
    
    # Генерируем 100,000 записей
    hosts = generator.generate_realistic_data(100000)
    
    if hosts:
        # Сохраняем в CSV
        generator.save_to_csv(hosts)
        
        print("\n🎉 Генерация завершена успешно!")
        print("📁 Файл: realistic_test_data_with_real_cves.csv")
        print("📊 Записей: {len(hosts)}")
        print("\n💡 Теперь можете импортировать этот файл в систему!")
    else:
        print("❌ Ошибка при генерации данных")

if __name__ == "__main__":
    main()
