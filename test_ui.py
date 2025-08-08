#!/usr/bin/env python3
"""
Автоматический тест веб-интерфейса для поиска багов
"""

import requests
import time
import json
from bs4 import BeautifulSoup
from urllib.parse import urljoin

class WebUITester:
    def __init__(self, base_url="http://localhost"):
        self.base_url = base_url
        self.session = requests.Session()
        self.bugs = []
        
    def test_page_loading(self, path):
        """Тест загрузки страницы"""
        try:
            url = urljoin(self.base_url, path)
            response = self.session.get(url, timeout=10)
            
            if response.status_code != 200:
                self.bugs.append(f"❌ {path}: HTTP {response.status_code}")
                return False
                
            # Проверяем наличие критических элементов
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Проверяем CSS
            css_links = soup.find_all('link', rel='stylesheet')
            for css in css_links:
                css_url = css.get('href')
                if css_url:
                    css_response = self.session.get(urljoin(url, css_url))
                    if css_response.status_code != 200:
                        self.bugs.append(f"❌ CSS не загружается: {css_url}")
            
            # Проверяем JavaScript
            js_scripts = soup.find_all('script', src=True)
            for script in js_scripts:
                js_url = script.get('src')
                if js_url:
                    js_response = self.session.get(urljoin(url, js_url))
                    if js_response.status_code != 200:
                        self.bugs.append(f"❌ JS не загружается: {js_url}")
            
            print(f"✅ {path}: OK")
            return True
            
        except Exception as e:
            self.bugs.append(f"❌ {path}: {str(e)}")
            return False
    
    def test_api_endpoints(self):
        """Тест API эндпоинтов"""
        endpoints = [
            "/auth/api/login",
            "/vulnanalizer/api/hosts/search",
            "/loganalizer/api/logs/files"
        ]
        
        for endpoint in endpoints:
            try:
                url = urljoin(self.base_url, endpoint)
                response = self.session.get(url, timeout=5)
                
                # API должен возвращать JSON или определенный статус
                if response.status_code not in [200, 401, 405]:
                    self.bugs.append(f"❌ API {endpoint}: неожиданный статус {response.status_code}")
                else:
                    print(f"✅ API {endpoint}: OK")
                    
            except Exception as e:
                self.bugs.append(f"❌ API {endpoint}: {str(e)}")
    
    def test_static_files(self):
        """Тест статических файлов"""
        static_files = [
            "/static/css/style.css",
            "/auth/static/css/style.css",
            "/auth/static/js/login.js"
        ]
        
        for file_path in static_files:
            try:
                url = urljoin(self.base_url, file_path)
                response = self.session.get(url, timeout=5)
                
                if response.status_code != 200:
                    self.bugs.append(f"❌ Статический файл не найден: {file_path}")
                else:
                    print(f"✅ Статический файл: {file_path}")
                    
            except Exception as e:
                self.bugs.append(f"❌ Статический файл {file_path}: {str(e)}")
    
    def test_redirects(self):
        """Тест редиректов"""
        redirects = [
            ("/", "/vulnanalizer/"),
            ("/loganalizer/", "/loganalizer/"),
            ("/vulnanalizer/", "/vulnanalizer/")
        ]
        
        for from_path, expected_to in redirects:
            try:
                url = urljoin(self.base_url, from_path)
                response = self.session.get(url, allow_redirects=False, timeout=5)
                
                if response.status_code in [301, 302]:
                    location = response.headers.get('Location', '')
                    if expected_to not in location:
                        self.bugs.append(f"❌ Неправильный редирект {from_path} -> {location}")
                    else:
                        print(f"✅ Редирект {from_path} -> {location}")
                else:
                    print(f"✅ {from_path}: прямой доступ")
                    
            except Exception as e:
                self.bugs.append(f"❌ Редирект {from_path}: {str(e)}")
    
    def run_all_tests(self):
        """Запуск всех тестов"""
        print("🔍 Запуск автоматических тестов...")
        
        # Тестируем основные страницы
        pages = [
            "/",
            "/vulnanalizer/",
            "/loganalizer/",
            "/auth/"
        ]
        
        for page in pages:
            self.test_page_loading(page)
        
        # Тестируем API
        self.test_api_endpoints()
        
        # Тестируем статические файлы
        self.test_static_files()
        
        # Тестируем редиректы
        self.test_redirects()
        
        # Выводим результаты
        print("\n📊 РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ:")
        if self.bugs:
            print(f"❌ Найдено {len(self.bugs)} проблем:")
            for bug in self.bugs:
                print(f"  {bug}")
        else:
            print("✅ Все тесты прошли успешно!")
        
        return len(self.bugs) == 0

if __name__ == "__main__":
    tester = WebUITester()
    success = tester.run_all_tests()
    exit(0 if success else 1)
