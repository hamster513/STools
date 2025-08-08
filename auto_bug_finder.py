#!/usr/bin/env python3
"""
Автоматический поиск багов в проекте
"""

import subprocess
import sys
import time
from datetime import datetime

def run_command(cmd, description):
    """Выполнение команды с выводом результата"""
    print(f"\n🔍 {description}...")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60)
        if result.returncode == 0:
            print(f"✅ {description}: успешно")
            return True, result.stdout
        else:
            print(f"❌ {description}: ошибка")
            print(f"STDOUT: {result.stdout}")
            print(f"STDERR: {result.stderr}")
            return False, result.stderr
    except subprocess.TimeoutExpired:
        print(f"⏰ {description}: таймаут")
        return False, "Timeout"
    except Exception as e:
        print(f"💥 {description}: исключение - {str(e)}")
        return False, str(e)

def check_docker_health():
    """Проверка здоровья Docker контейнеров"""
    print("\n🐳 Проверка Docker контейнеров:")
    
    # Проверяем статус контейнеров
    success, output = run_command("docker-compose ps", "Статус контейнеров")
    if success:
        print(output)
    
    # Проверяем логи nginx
    success, output = run_command("docker-compose logs --tail=10 nginx", "Логи Nginx")
    if success:
        print(output)
    
    # Проверяем логи auth
    success, output = run_command("docker-compose logs --tail=10 auth_web", "Логи Auth")
    if success:
        print(output)

def check_web_responses():
    """Проверка HTTP ответов"""
    print("\n🌐 Проверка HTTP ответов:")
    
    urls = [
        "http://localhost/",
        "http://localhost/vulnanalizer/",
        "http://localhost/loganalizer/",
        "http://localhost/auth/",
        "http://localhost/static/css/style.css"
    ]
    
    for url in urls:
        success, output = run_command(f"curl -s -o /dev/null -w '%{{http_code}}' {url}", f"Проверка {url}")
        if success:
            status_code = output.strip()
            if status_code == "200":
                print(f"✅ {url}: OK (200)")
            else:
                print(f"❌ {url}: {status_code}")

def check_file_integrity():
    """Проверка целостности файлов"""
    print("\n📁 Проверка целостности файлов:")
    
    critical_files = [
        "docker-compose.yml",
        "nginx/nginx.conf",
        "static/css/style.css",
        "vulnanalizer/app/main.py",
        "loganalizer/app/main.py",
        "auth/main.py"
    ]
    
    for file_path in critical_files:
        success, output = run_command(f"test -f {file_path} && echo 'exists'", f"Проверка {file_path}")
        if success and "exists" in output:
            print(f"✅ {file_path}: существует")
        else:
            print(f"❌ {file_path}: отсутствует")

def check_syntax():
    """Проверка синтаксиса конфигурационных файлов"""
    print("\n🔧 Проверка синтаксиса:")
    
    # Проверяем nginx конфигурацию
    success, output = run_command("docker-compose exec nginx nginx -t", "Проверка nginx.conf")
    if success:
        print("✅ nginx.conf: синтаксис корректен")
    else:
        print(f"❌ nginx.conf: ошибка синтаксиса")
        print(output)
    
    # Проверяем docker-compose
    success, output = run_command("docker-compose config", "Проверка docker-compose.yml")
    if success:
        print("✅ docker-compose.yml: синтаксис корректен")
    else:
        print(f"❌ docker-compose.yml: ошибка синтаксиса")
        print(output)

def check_database_connections():
    """Проверка подключений к базе данных"""
    print("\n🗄️ Проверка баз данных:")
    
    # Проверяем подключение к auth_postgres
    success, output = run_command(
        "docker-compose exec auth_postgres psql -U postgres -d auth_db -c 'SELECT 1;'",
        "Проверка auth_postgres"
    )
    if success:
        print("✅ auth_postgres: подключение работает")
    else:
        print("❌ auth_postgres: ошибка подключения")
    
    # Проверяем подключение к vulnanalizer_postgres
    success, output = run_command(
        "docker-compose exec vulnanalizer_postgres psql -U postgres -d vulnanalizer_db -c 'SELECT 1;'",
        "Проверка vulnanalizer_postgres"
    )
    if success:
        print("✅ vulnanalizer_postgres: подключение работает")
    else:
        print("❌ vulnanalizer_postgres: ошибка подключения")

def run_automated_tests():
    """Запуск автоматических тестов"""
    print("\n🧪 Запуск автоматических тестов:")
    
    # Запускаем тест веб-интерфейса
    success, output = run_command("python3 test_ui.py", "Тест веб-интерфейса")
    if success:
        print("✅ Тест веб-интерфейса: пройден")
    else:
        print("❌ Тест веб-интерфейса: провален")
        print(output)
    
    # Запускаем мониторинг логов
    success, output = run_command("python3 monitor_logs.py", "Мониторинг логов")
    if success:
        print("✅ Мониторинг логов: пройден")
    else:
        print("❌ Мониторинг логов: провален")
        print(output)

def generate_report():
    """Генерация отчета о проверке"""
    print("\n📊 ГЕНЕРАЦИЯ ОТЧЕТА:")
    print("=" * 50)
    print(f"Время проверки: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)
    
    # Запускаем все проверки
    check_docker_health()
    check_web_responses()
    check_file_integrity()
    check_syntax()
    check_database_connections()
    run_automated_tests()
    
    print("\n🎯 РЕКОМЕНДАЦИИ:")
    print("1. Если найдены ошибки - исправьте их")
    print("2. Если контейнеры не запущены - выполните docker-compose up -d")
    print("3. Если порты недоступны - проверьте конфигурацию")
    print("4. Если файлы отсутствуют - восстановите их из git")

if __name__ == "__main__":
    print("🚀 АВТОМАТИЧЕСКИЙ ПОИСК БАГОВ")
    print("=" * 50)
    
    generate_report()
    
    print("\n✅ Проверка завершена!")
    print("Используйте результаты выше для диагностики проблем.")
