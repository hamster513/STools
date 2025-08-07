#!/usr/bin/env python3
"""
Тестовый скрипт для проверки новой системы распознавания уровней логов
"""

import sys
import os

# Добавляем путь к модулям приложения
sys.path.append('/app')

from log_formats import detect_log_level

def test_log_levels():
    """Тестирует распознавание различных уровней логов"""
    
    # Новые уровни логов
    important_levels = ['ERROR', 'WARN', 'CRITICAL', 'FATAL', 'ALERT', 'EMERGENCY', 'INFO', 'DEBUG']
    
    # Тестовые строки логов
    test_lines = [
        "[2025-07-17T17:31:35.904+0300] 10239:10370 INFO Node: Service 'router' precommit is triggered",
        "[2025-07-17T17:31:41.006+0300] 10239:10725 WARN Node.Transport.Publisher: <1 times>: Confirmation failed",
        "[2025-07-17T17:35:25.265+0300] 10239:10721 ERROR Node.Transport.Consumer: Consume failed",
        "[2025-07-17T17:36:30.123+0300] 10239:10539 DEBUG Node.Transport.Consumer: Debug message for testing",
        "2025-07-17 17:31:35 INFO Service started",
        "2025-07-17 17:31:35 ERROR Service failed",
        "2025-07-17 17:31:35 DEBUG Debug info",
        "Some message (ERROR) details",
        "Another message (INFO) details",
        "timestamp: DEBUG: debug message",
        "ERROR Service failed",
        "INFO Service started",
        "DEBUG Debug info",
        "[ERROR] Service failed",
        "[INFO] Service started",
        "[DEBUG] Debug info"
    ]
    
    print("🧪 Testing new log level detection system...")
    print("=" * 60)
    
    for i, line in enumerate(test_lines, 1):
        detected_level = detect_log_level(line, important_levels, debug=False)
        status = "✅" if detected_level else "❌"
        print(f"{status} Line {i:2d}: {detected_level or 'NOT DETECTED'} - {line[:80]}...")
    
    print("=" * 60)
    print("📊 Test completed!")

if __name__ == "__main__":
    test_log_levels() 