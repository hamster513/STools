#!/usr/bin/env python3
"""
Мониторинг логов контейнеров для поиска багов
"""

import subprocess
import time
import re
from datetime import datetime

class LogMonitor:
    def __init__(self):
        self.errors = []
        self.warnings = []
        self.containers = ['nginx', 'auth_web', 'vulnanalizer_web', 'loganalizer_web']
        
    def get_container_logs(self, container, lines=50):
        """Получение логов контейнера"""
        try:
            result = subprocess.run(
                ['docker-compose', 'logs', '--tail', str(lines), container],
                capture_output=True, text=True, timeout=30
            )
            return result.stdout
        except Exception as e:
            return f"Ошибка получения логов {container}: {str(e)}"
    
    def analyze_logs(self, container):
        """Анализ логов на наличие ошибок"""
        logs = self.get_container_logs(container)
        
        # Паттерны для поиска ошибок
        error_patterns = [
            r'ERROR',
            r'Exception',
            r'Traceback',
            r'Failed',
            r'Connection refused',
            r'404 Not Found',
            r'500 Internal Server Error',
            r'502 Bad Gateway',
            r'503 Service Unavailable',
            r'nginx.*error',
            r'python.*error',
            r'fastapi.*error'
        ]
        
        warning_patterns = [
            r'WARNING',
            r'Warning',
            r'deprecated',
            r'DeprecationWarning'
        ]
        
        lines = logs.split('\n')
        for i, line in enumerate(lines):
            # Ищем ошибки
            for pattern in error_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    self.errors.append(f"❌ {container}: {line.strip()}")
                    break
            
            # Ищем предупреждения
            for pattern in warning_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    self.warnings.append(f"⚠️ {container}: {line.strip()}")
                    break
    
    def check_container_status(self):
        """Проверка статуса контейнеров"""
        try:
            result = subprocess.run(
                ['docker-compose', 'ps'],
                capture_output=True, text=True, timeout=10
            )
            
            lines = result.stdout.split('\n')
            for line in lines:
                if any(container in line for container in self.containers):
                    if 'Up' not in line:
                        self.errors.append(f"❌ Контейнер не запущен: {line.strip()}")
                    else:
                        print(f"✅ Контейнер работает: {line.split()[0]}")
                        
        except Exception as e:
            self.errors.append(f"❌ Ошибка проверки статуса: {str(e)}")
    
    def check_ports(self):
        """Проверка доступности портов"""
        import socket
        
        ports = {
            80: "HTTP (Nginx)",
            8000: "Auth API",
            8001: "VulnAnalizer API", 
            8002: "LogAnalizer API"
        }
        
        for port, service in ports.items():
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(2)
                result = sock.connect_ex(('localhost', port))
                sock.close()
                
                if result == 0:
                    print(f"✅ Порт {port} ({service}): доступен")
                else:
                    self.errors.append(f"❌ Порт {port} ({service}): недоступен")
                    
            except Exception as e:
                self.errors.append(f"❌ Ошибка проверки порта {port}: {str(e)}")
    
    def run_monitoring(self):
        """Запуск мониторинга"""
        print("🔍 Запуск мониторинга логов и состояния...")
        
        # Проверяем статус контейнеров
        print("\n📊 Статус контейнеров:")
        self.check_container_status()
        
        # Проверяем порты
        print("\n🌐 Проверка портов:")
        self.check_ports()
        
        # Анализируем логи
        print("\n📝 Анализ логов:")
        for container in self.containers:
            print(f"\n🔍 Анализ логов {container}:")
            self.analyze_logs(container)
        
        # Выводим результаты
        print("\n📊 РЕЗУЛЬТАТЫ МОНИТОРИНГА:")
        
        if self.errors:
            print(f"\n❌ Найдено {len(self.errors)} ошибок:")
            for error in self.errors:
                print(f"  {error}")
        
        if self.warnings:
            print(f"\n⚠️ Найдено {len(self.warnings)} предупреждений:")
            for warning in self.warnings:
                print(f"  {warning}")
        
        if not self.errors and not self.warnings:
            print("✅ Проблем не обнаружено!")
        
        return len(self.errors) == 0

if __name__ == "__main__":
    monitor = LogMonitor()
    success = monitor.run_monitoring()
    exit(0 if success else 1)
