#!/usr/bin/env python3
"""
Тестовый скрипт для загрузки CVE данных
"""
import requests
import json
import os
from pathlib import Path

def test_cve_upload():
    """Тестирование загрузки CVE данных"""
    
    # URL для загрузки
    upload_url = "https://localhost/vulnanalizer/api/cve/upload"
    status_url = "https://localhost/vulnanalizer/api/cve/status"
    
    # Путь к тестовому файлу
    test_file = Path("/Users/hom/Downloads/test_cve_small.json")
    
    if not test_file.exists():
        print("❌ Тестовый файл не найден")
        return
    
    print(f"📁 Тестовый файл: {test_file}")
    print(f"📊 Размер файла: {test_file.stat().st_size} байт")
    
    # Проверяем статус до загрузки
    print("\n🔍 Проверяем статус до загрузки...")
    try:
        response = requests.get(status_url, verify=False)
        if response.status_code == 200:
            data = response.json()
            print(f"📊 Записей в базе: {data.get('count', 0)}")
        else:
            print(f"❌ Ошибка получения статуса: {response.status_code}")
            return
    except Exception as e:
        print(f"❌ Ошибка подключения: {e}")
        return
    
    # Загружаем файл
    print("\n📤 Загружаем CVE данные...")
    try:
        with open(test_file, 'rb') as f:
            files = {'file': (test_file.name, f, 'application/json')}
            response = requests.post(upload_url, files=files, verify=False)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Загрузка успешна!")
            print(f"📊 Загружено записей: {data.get('count', 0)}")
            print(f"💬 Сообщение: {data.get('message', '')}")
        else:
            print(f"❌ Ошибка загрузки: {response.status_code}")
            print(f"📄 Ответ: {response.text}")
            return
            
    except Exception as e:
        print(f"❌ Ошибка загрузки: {e}")
        return
    
    # Проверяем статус после загрузки
    print("\n🔍 Проверяем статус после загрузки...")
    try:
        response = requests.get(status_url, verify=False)
        if response.status_code == 200:
            data = response.json()
            print(f"📊 Записей в базе: {data.get('count', 0)}")
        else:
            print(f"❌ Ошибка получения статуса: {response.status_code}")
    except Exception as e:
        print(f"❌ Ошибка подключения: {e}")

if __name__ == "__main__":
    print("🚀 Тестирование загрузки CVE данных")
    print("=" * 50)
    test_cve_upload()
