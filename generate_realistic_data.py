#!/usr/bin/env python3
"""
Генератор реалистичных тестовых данных для STools
Создает CSV файл с 100k записей хостов, используя реальные CVE из базы данных
- 90k записей с CVE из NVD (случайно выбранные)
- 10k записей с CVE из ExploitDB (случайно выбранные)
"""

import csv
import random
import string
import subprocess
import tempfile
import os
from datetime import datetime, timedelta
from typing import List, Dict, Set

class RealisticDataGenerator:
    def __init__(self):
        self.nvd_cves = []
        self.exploitdb_cves = []
        
    def get_cves_from_database(self):
        """Получает CVE из базы данных через docker exec"""
        print("📥 Получение CVE из базы данных...")
        
        try:
            # Получаем CVE из таблицы cve (NVD)
            print("🔍 Загрузка CVE из NVD...")
            nvd_query = """
                SELECT cve_id, description, cvss_v3_base_score, cvss_v2_base_score, 
                       cvss_v3_base_severity, cvss_v2_base_severity
                FROM vulnanalizer.cve 
                WHERE cve_id IS NOT NULL 
                ORDER BY RANDOM() 
                LIMIT 90000;
            """
            
            # Выполняем запрос через docker exec
            result = subprocess.run([
                'docker', 'exec', 'stools_postgres', 'psql', 
                '-U', 'stools_user', '-d', 'stools_db', 
                '-c', nvd_query, '--csv', '--no-align', '--tuples-only'
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                for line in lines:
                    if line and '|' in line:
                        parts = line.split('|')
                        if len(parts) >= 6:
                            self.nvd_cves.append({
                                'cve_id': parts[0].strip(),
                                'description': parts[1].strip() if parts[1] else '',
                                'cvss_v3_base_score': float(parts[2]) if parts[2] and parts[2] != 'NULL' else None,
                                'cvss_v2_base_score': float(parts[3]) if parts[3] and parts[3] != 'NULL' else None,
                                'cvss_v3_base_severity': parts[4].strip() if parts[4] and parts[4] != 'NULL' else None,
                                'cvss_v2_base_severity': parts[5].strip() if parts[5] and parts[5] != 'NULL' else None
                            })
                
                print(f"📊 Загружено {len(self.nvd_cves)} CVE из NVD")
            else:
                print(f"❌ Ошибка получения CVE из NVD: {result.stderr}")
                self.nvd_cves = self.generate_fake_nvd_cves(90000)
            
            # Получаем CVE из ExploitDB
            print("🔍 Загрузка CVE из ExploitDB...")
            exploitdb_query = """
                SELECT DISTINCT unnest(cves) as cve_id
                FROM vulnanalizer.exploitdb 
                WHERE cves IS NOT NULL AND array_length(cves, 1) > 0
                ORDER BY RANDOM() 
                LIMIT 10000;
            """
            
            result = subprocess.run([
                'docker', 'exec', 'stools_postgres', 'psql', 
                '-U', 'stools_user', '-d', 'stools_db', 
                '-c', exploitdb_query, '--csv', '--no-align', '--tuples-only'
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                exploitdb_cve_ids = [line.strip() for line in result.stdout.strip().split('\n') if line.strip()]
                
                # Получаем информацию о каждом CVE из ExploitDB
                for cve_id in exploitdb_cve_ids:
                    cve_info_query = f"""
                        SELECT cve_id, description, cvss_v3_base_score, cvss_v2_base_score, 
                               cvss_v3_base_severity, cvss_v2_base_severity
                        FROM vulnanalizer.cve 
                        WHERE cve_id = '{cve_id}';
                    """
                    
                    result = subprocess.run([
                        'docker', 'exec', 'stools_postgres', 'psql', 
                        '-U', 'stools_user', '-d', 'stools_db', 
                        '-c', cve_info_query, '--csv', '--no-align', '--tuples-only'
                    ], capture_output=True, text=True)
                    
                    if result.returncode == 0 and result.stdout.strip():
                        line = result.stdout.strip()
                        if '|' in line:
                            parts = line.split('|')
                            if len(parts) >= 6:
                                self.exploitdb_cves.append({
                                    'cve_id': parts[0].strip(),
                                    'description': parts[1].strip() if parts[1] else '',
                                    'cvss_v3_base_score': float(parts[2]) if parts[2] and parts[2] != 'NULL' else None,
                                    'cvss_v2_base_score': float(parts[3]) if parts[3] and parts[3] != 'NULL' else None,
                                    'cvss_v3_base_severity': parts[4].strip() if parts[4] and parts[4] != 'NULL' else None,
                                    'cvss_v2_base_severity': parts[5].strip() if parts[5] and parts[5] != 'NULL' else None
                                })
                
                print(f"🔧 Загружено {len(self.exploitdb_cves)} CVE из ExploitDB")
            else:
                print(f"❌ Ошибка получения CVE из ExploitDB: {result.stderr}")
                self.exploitdb_cves = self.generate_fake_exploitdb_cves(10000)
                
        except Exception as e:
            print(f"❌ Ошибка получения данных из базы: {e}")
            # Создаем фиктивные данные если не удалось получить из БД
            self.nvd_cves = self.generate_fake_nvd_cves(90000)
            self.exploitdb_cves = self.generate_fake_exploitdb_cves(10000)
    
    def generate_fake_nvd_cves(self, count: int) -> List[Dict]:
        """Генерирует фиктивные CVE для NVD если база данных пуста"""
        cves = []
        for i in range(count):
            year = random.randint(1999, 2024)
            number = random.randint(1, 99999)
            cve_id = f"CVE-{year}-{number:05d}"
            
            # Генерируем реалистичные описания
            descriptions = [
                "Buffer overflow vulnerability in the processing of malformed network packets",
                "Cross-site scripting (XSS) vulnerability in web interface",
                "SQL injection vulnerability in database query processing",
                "Privilege escalation vulnerability in system service",
                "Denial of service vulnerability in network protocol implementation",
                "Information disclosure vulnerability in error handling",
                "Authentication bypass vulnerability in login mechanism",
                "Code execution vulnerability in file parser",
                "Memory corruption vulnerability in image processing",
                "Path traversal vulnerability in file upload functionality"
            ]
            
            cvss_v3_score = random.choice([None, round(random.uniform(0.1, 10.0), 1)])
            cvss_v2_score = random.choice([None, round(random.uniform(0.1, 10.0), 1)])
            
            cves.append({
                'cve_id': cve_id,
                'description': random.choice(descriptions),
                'cvss_v3_base_score': cvss_v3_score,
                'cvss_v2_base_score': cvss_v2_score,
                'cvss_v3_base_severity': self.get_severity_v3(cvss_v3_score) if cvss_v3_score else None,
                'cvss_v2_base_severity': self.get_severity_v2(cvss_v2_score) if cvss_v2_score else None
            })
        
        return cves
    
    def generate_fake_exploitdb_cves(self, count: int) -> List[Dict]:
        """Генерирует фиктивные CVE для ExploitDB если база данных пуста"""
        cves = []
        for i in range(count):
            year = random.randint(2010, 2024)  # Более новые CVE для эксплойтов
            number = random.randint(1, 99999)
            cve_id = f"CVE-{year}-{number:05d}"
            
            # Более серьезные уязвимости для ExploitDB
            descriptions = [
                "Remote code execution vulnerability in web application",
                "Privilege escalation vulnerability in kernel driver",
                "Authentication bypass vulnerability in admin panel",
                "SQL injection vulnerability in user input processing",
                "Buffer overflow vulnerability in network service",
                "Cross-site scripting vulnerability in user interface",
                "File upload vulnerability leading to code execution",
                "Memory corruption vulnerability in media player",
                "Command injection vulnerability in system utility",
                "Path traversal vulnerability in file manager"
            ]
            
            # Более высокие CVSS scores для эксплойтов
            cvss_v3_score = round(random.uniform(5.0, 10.0), 1)
            cvss_v2_score = round(random.uniform(5.0, 10.0), 1)
            
            cves.append({
                'cve_id': cve_id,
                'description': random.choice(descriptions),
                'cvss_v3_base_score': cvss_v3_score,
                'cvss_v2_base_score': cvss_v2_score,
                'cvss_v3_base_severity': self.get_severity_v3(cvss_v3_score),
                'cvss_v2_base_severity': self.get_severity_v2(cvss_v2_score)
            })
        
        return cves
    
    def get_severity_v3(self, score: float) -> str:
        """Определяет уровень серьезности для CVSS v3"""
        if score is None:
            return None
        if score >= 9.0:
            return "Critical"
        elif score >= 7.0:
            return "High"
        elif score >= 4.0:
            return "Medium"
        elif score >= 0.1:
            return "Low"
        else:
            return "None"
    
    def get_severity_v2(self, score: float) -> str:
        """Определяет уровень серьезности для CVSS v2"""
        if score is None:
            return None
        if score >= 7.0:
            return "High"
        elif score >= 4.0:
            return "Medium"
        elif score >= 0.1:
            return "Low"
        else:
            return "None"
    
    def generate_ip(self) -> str:
        """Генерирует случайный IP адрес"""
        return f"{random.randint(1, 254)}.{random.randint(1, 254)}.{random.randint(1, 254)}.{random.randint(1, 254)}"
    
    def generate_hostname(self) -> str:
        """Генерирует случайное имя хоста"""
        prefixes = ['server', 'host', 'node', 'vm', 'container', 'instance', 'machine', 'workstation', 'laptop', 'desktop']
        suffixes = ['prod', 'dev', 'test', 'staging', 'backup', 'db', 'web', 'app', 'api', 'mail', 'dns', 'proxy']
        environments = ['corp', 'office', 'branch', 'remote', 'cloud', 'onprem']
        
        prefix = random.choice(prefixes)
        suffix = random.choice(suffixes)
        env = random.choice(environments)
        number = random.randint(1, 999)
        
        return f"{prefix}-{suffix}-{env}-{number:03d}"
    
    def generate_realistic_data(self, num_hosts: int = 100000, num_with_exploits: int = 10000) -> List[Dict]:
        """Генерирует реалистичные данные хостов"""
        
        # Убеждаемся, что у нас достаточно CVE
        if len(self.nvd_cves) < num_hosts - num_with_exploits:
            print(f"⚠️  Недостаточно CVE из NVD. Создаем дополнительные...")
            additional_needed = num_hosts - num_with_exploits - len(self.nvd_cves)
            self.nvd_cves.extend(self.generate_fake_nvd_cves(additional_needed))
        
        if len(self.exploitdb_cves) < num_with_exploits:
            print(f"⚠️  Недостаточно CVE из ExploitDB. Создаем дополнительные...")
            additional_needed = num_with_exploits - len(self.exploitdb_cves)
            self.exploitdb_cves.extend(self.generate_fake_exploitdb_cves(additional_needed))
        
        # Перемешиваем CVE для случайности
        random.shuffle(self.nvd_cves)
        random.shuffle(self.exploitdb_cves)
        
        hosts = []
        criticality_levels = ['Critical', 'High', 'Medium', 'Low', 'None']
        zones = ['DMZ', 'Internal', 'External', 'Management', 'Backup', 'Development', 'Production', 'Testing']
        os_names = ['Linux', 'Windows', 'macOS', 'FreeBSD', 'Ubuntu', 'CentOS', 'Debian', 'Red Hat', 'SUSE', 'Windows Server']
        
        nvd_index = 0
        exploitdb_index = 0
        
        for i in range(num_hosts):
            hostname = self.generate_hostname()
            ip = self.generate_ip()
            os_name = random.choice(os_names)
            zone = random.choice(zones)
            
            # Выбираем CVE для хоста
            if i < num_with_exploits:
                # Первые записи получают CVE с эксплойтами
                if exploitdb_index < len(self.exploitdb_cves):
                    cve_data = self.exploitdb_cves[exploitdb_index]
                    exploitdb_index += 1
                else:
                    # Если закончились CVE с эксплойтами, берем из NVD
                    cve_data = self.nvd_cves[nvd_index % len(self.nvd_cves)]
                    nvd_index += 1
            else:
                # Остальные получают CVE из NVD
                cve_data = self.nvd_cves[nvd_index % len(self.nvd_cves)]
                nvd_index += 1
            
            # Определяем критичность на основе CVSS
            cvss_score = cve_data.get('cvss_v3_base_score') or cve_data.get('cvss_v2_base_score')
            if cvss_score:
                if cvss_score >= 9.0:
                    criticality = 'Critical'
                elif cvss_score >= 7.0:
                    criticality = 'High'
                elif cvss_score >= 4.0:
                    criticality = 'Medium'
                else:
                    criticality = 'Low'
            else:
                criticality = random.choice(criticality_levels)
            
            # Создаем запись с одним CVE
            host = {
                '@Host': f'{hostname} ({ip})',
                'Host.OsName': os_name,
                'Host.@Vulners.CVEs': cve_data['cve_id'],
                'host.UF_Criticality': criticality,
                'Host.UF_Zone': zone
            }
            
            hosts.append(host)
            
            # Добавляем дополнительные CVE (0-3 штуки) как отдельные записи
            num_additional = random.randint(0, 3)
            
            for _ in range(num_additional):
                if random.random() < 0.3:  # 30% шанс взять CVE с эксплойтами
                    if exploitdb_index < len(self.exploitdb_cves):
                        additional_cve_data = self.exploitdb_cves[exploitdb_index]
                        exploitdb_index += 1
                    else:
                        additional_cve_data = self.nvd_cves[nvd_index % len(self.nvd_cves)]
                        nvd_index += 1
                else:
                    additional_cve_data = self.nvd_cves[nvd_index % len(self.nvd_cves)]
                    nvd_index += 1
                
                if additional_cve_data['cve_id'] != cve_data['cve_id']:
                    # Определяем критичность для дополнительного CVE
                    additional_cvss_score = additional_cve_data.get('cvss_v3_base_score') or additional_cve_data.get('cvss_v2_base_score')
                    if additional_cvss_score:
                        if additional_cvss_score >= 9.0:
                            additional_criticality = 'Critical'
                        elif additional_cvss_score >= 7.0:
                            additional_criticality = 'High'
                        elif additional_cvss_score >= 4.0:
                            additional_criticality = 'Medium'
                        else:
                            additional_criticality = 'Low'
                    else:
                        additional_criticality = random.choice(criticality_levels)
                    
                    # Создаем отдельную запись для дополнительного CVE
                    additional_host = {
                        '@Host': f'{hostname} ({ip})',
                        'Host.OsName': os_name,
                        'Host.@Vulners.CVEs': additional_cve_data['cve_id'],
                        'host.UF_Criticality': additional_criticality,
                        'Host.UF_Zone': zone
                    }
                    
                    hosts.append(additional_host)
        
        return hosts
    
    def save_to_csv(self, hosts: List[Dict], filename: str = 'realistic_test_data_100k.csv'):
        """Сохраняет данные в CSV файл"""
        
        fieldnames = ['@Host', 'Host.OsName', 'Host.@Vulners.CVEs', 'host.UF_Criticality', 'Host.UF_Zone']
        
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames, delimiter=';', quoting=csv.QUOTE_ALL)
            writer.writeheader()
            writer.writerows(hosts)
        
        # Получаем размер файла после закрытия
        import os
        file_size = os.path.getsize(filename) / (1024*1024)
        
        print(f"✅ Создан файл {filename}")
        print(f"📊 Количество записей: {len(hosts):,}")
        print(f"🎯 Размер файла: {file_size:.2f} МБ")
        
        # Статистика по CVE
        nvd_count = len(self.nvd_cves)
        exploitdb_count = len(self.exploitdb_cves)
        print(f"📋 Использовано CVE из NVD: {nvd_count:,}")
        print(f"🔧 Использовано CVE из ExploitDB: {exploitdb_count:,}")

def main():
    print("🚀 Генерация реалистичных тестовых данных...")
    print("📋 Параметры:")
    print("   - Общее количество хостов: 100,000")
    print("   - Хостов с эксплойтами: 10,000")
    print("   - CVE на хост: 1-5")
    print("   - Источник данных: База данных NVD и ExploitDB через docker exec")
    
    generator = RealisticDataGenerator()
    
    try:
        # Получаем данные из базы
        print("\n📥 Загрузка данных из базы данных...")
        generator.get_cves_from_database()
        
        # Генерируем данные
        print("\n🔄 Генерация данных хостов...")
        hosts = generator.generate_realistic_data(100000, 10000)
        
        # Сохраняем в файл
        print("\n💾 Сохранение в файл...")
        generator.save_to_csv(hosts, 'realistic_test_data_100k.csv')
        
        print("\n✅ Генерация завершена!")
        
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        raise

if __name__ == "__main__":
    main()
