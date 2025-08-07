"""
Универсальная система распознавания форматов логов
Поддерживает различные форматы логов от разных систем и приложений
"""

import re
from typing import List, Optional, Dict, Tuple
from dataclasses import dataclass
from enum import Enum

class LogFormat(Enum):
    """Типы форматов логов"""
    STANDARD = "standard"
    JSON = "json"
    XML = "xml"
    CSV = "csv"
    CUSTOM = "custom"

@dataclass
class LogPattern:
    """Паттерн для распознавания логов"""
    name: str
    pattern: str
    level_group: int = 1
    description: str = ""
    examples: List[str] = None
    
    def __post_init__(self):
        if self.examples is None:
            self.examples = []

class LogFormatDetector:
    """Детектор форматов логов с поддержкой множественных паттернов"""
    
    def __init__(self):
        # Базовые паттерны для различных форматов
        self.patterns = {
            LogFormat.STANDARD: [
                # Стандартные форматы
                LogPattern(
                    name="ISO Timestamp with Level",
                    pattern=r'\[(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:[+-]\d{2}:\d{2})?)\]\s+(\w+)\s+',
                    level_group=2,
                    description="ISO timestamp в квадратных скобках с уровнем",
                    examples=[
                        "[2025-07-17T17:31:35.904+0300] INFO Service started",
                        "[2025-07-17T17:31:35.904+0300] ERROR Connection failed"
                    ]
                ),
                LogPattern(
                    name="Node.js Format",
                    pattern=r'\[(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:[+-]\d{2}:\d{2})?)\]\s+\d+:\d+\s+(\w+)\s+',
                    level_group=2,
                    description="Node.js формат с PID:THREAD",
                    examples=[
                        "[2025-07-17T17:31:35.904+0300] 10239:10370 INFO Service started",
                        "[2025-07-17T17:31:35.904+0300] 10239:10370 ERROR Connection failed"
                    ]
                ),
                LogPattern(
                    name="Simple Timestamp",
                    pattern=r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}(?:\.\d+)?)\s+(\w+)\s+',
                    level_group=2,
                    description="Простой timestamp с уровнем",
                    examples=[
                        "2025-07-17 17:31:35 INFO Service started",
                        "2025-07-17 17:31:35 ERROR Connection failed"
                    ]
                ),
                LogPattern(
                    name="Unix Timestamp",
                    pattern=r'(\d{10,13})\s+(\w+)\s+',
                    level_group=2,
                    description="Unix timestamp с уровнем",
                    examples=[
                        "1647523895 INFO Service started",
                        "1647523895 ERROR Connection failed"
                    ]
                ),
                LogPattern(
                    name="Level in Parentheses",
                    pattern=r'\((\w+)\)',
                    level_group=1,
                    description="Уровень в скобках",
                    examples=[
                        "Some message (ERROR) details",
                        "Another message (INFO) details"
                    ]
                ),
                LogPattern(
                    name="Level after Colon",
                    pattern=r':\s*(\w+)\s*:',
                    level_group=1,
                    description="Уровень после двоеточия",
                    examples=[
                        "timestamp: ERROR: message",
                        "timestamp: INFO: message"
                    ]
                ),
                LogPattern(
                    name="Level at Start",
                    pattern=r'^(\w+)\s+',
                    level_group=1,
                    description="Уровень в начале строки",
                    examples=[
                        "ERROR Service failed",
                        "INFO Service started"
                    ]
                ),
                LogPattern(
                    name="Level in Brackets",
                    pattern=r'\[(\w+)\]',
                    level_group=1,
                    description="Уровень в квадратных скобках",
                    examples=[
                        "[ERROR] Service failed",
                        "[INFO] Service started"
                    ]
                ),
                LogPattern(
                    name="Java Log Format",
                    pattern=r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2},\d{3})\s+(\w+)\s+',
                    level_group=2,
                    description="Java формат с миллисекундами",
                    examples=[
                        "2025-07-17 17:31:35,123 INFO Service started",
                        "2025-07-17 17:31:35,123 ERROR Service failed"
                    ]
                ),
                LogPattern(
                    name="Python Log Format",
                    pattern=r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2},\d{3})\s+(\w+)\s+',
                    level_group=2,
                    description="Python формат с миллисекундами",
                    examples=[
                        "2025-07-17 17:31:35,123 INFO Service started",
                        "2025-07-17 17:31:35,123 ERROR Service failed"
                    ]
                ),
                LogPattern(
                    name="Docker Log Format",
                    pattern=r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z?)\s+(\w+)\s+',
                    level_group=2,
                    description="Docker формат с UTC",
                    examples=[
                        "2025-07-17T17:31:35.904Z INFO Service started",
                        "2025-07-17T17:31:35.904Z ERROR Service failed"
                    ]
                ),
                LogPattern(
                    name="Syslog Format",
                    pattern=r'(\w+\s+\d+\s+\d{2}:\d{2}:\d{2})\s+\w+\s+(\w+):',
                    level_group=2,
                    description="Syslog формат",
                    examples=[
                        "Jul 17 17:31:35 hostname service: ERROR message",
                        "Jul 17 17:31:35 hostname service: INFO message"
                    ]
                ),
            ],
            
            LogFormat.JSON: [
                LogPattern(
                    name="JSON with level field",
                    pattern=r'"level"\s*:\s*"(\w+)"',
                    level_group=1,
                    description="JSON с полем level",
                    examples=[
                        '{"timestamp": "2025-07-17T17:31:35", "level": "ERROR", "message": "Service failed"}',
                        '{"timestamp": "2025-07-17T17:31:35", "level": "INFO", "message": "Service started"}'
                    ]
                ),
                LogPattern(
                    name="JSON with severity field",
                    pattern=r'"severity"\s*:\s*"(\w+)"',
                    level_group=1,
                    description="JSON с полем severity",
                    examples=[
                        '{"timestamp": "2025-07-17T17:31:35", "severity": "ERROR", "message": "Service failed"}',
                        '{"timestamp": "2025-07-17T17:31:35", "severity": "INFO", "message": "Service started"}'
                    ]
                ),
            ],
            
            LogFormat.XML: [
                LogPattern(
                    name="XML with level attribute",
                    pattern=r'<log\s+level="(\w+)"',
                    level_group=1,
                    description="XML с атрибутом level",
                    examples=[
                        '<log level="ERROR" timestamp="2025-07-17T17:31:35">Service failed</log>',
                        '<log level="INFO" timestamp="2025-07-17T17:31:35">Service started</log>'
                    ]
                ),
            ],
        }
    
    def detect_log_level(self, line: str, important_levels: List[str], debug: bool = False) -> Optional[str]:
        """
        Универсальное определение уровня лога
        """
        line_upper = line.upper()
        
        # Проверяем все форматы
        for format_type, patterns in self.patterns.items():
            for pattern in patterns:
                try:
                    match = re.search(pattern.pattern, line_upper)
                    if match:
                        detected_level = match.group(pattern.level_group)
                        if detected_level in important_levels:
                            if debug:
                                print(f"🔍 {format_type.value} - {pattern.name} matched: {detected_level}")
                            return detected_level
                except Exception as e:
                    if debug:
                        print(f"❌ Error in pattern {pattern.name}: {e}")
                    continue
        
        # Fallback: ищем уровни как отдельные слова
        for level in important_levels:
            level_pattern = r'\b' + re.escape(level) + r'\b'
            if re.search(level_pattern, line_upper):
                if debug:
                    print(f"🔍 Word pattern matched: {level}")
                return level
        
        if debug:
            print(f"❌ No level detected for: {line.strip()[:100]}...")
        return None
    
    def detect_format(self, lines: List[str]) -> Dict[str, float]:
        """
        Автоматическое определение формата логов на основе анализа строк
        """
        format_scores = {format_type: 0.0 for format_type in LogFormat}
        
        for line in lines[:100]:  # Анализируем первые 100 строк
            line_upper = line.upper()
            
            # Проверяем каждый формат
            for format_type, patterns in self.patterns.items():
                for pattern in patterns:
                    try:
                        if re.search(pattern.pattern, line_upper):
                            format_scores[format_type] += 1.0
                            break
                    except:
                        continue
            
            # Дополнительные эвристики
            if '{' in line and '}' in line:
                format_scores[LogFormat.JSON] += 0.5
            if '<' in line and '>' in line:
                format_scores[LogFormat.XML] += 0.5
        
        # Нормализуем scores
        total_lines = min(len(lines), 100)
        if total_lines > 0:
            for format_type in format_scores:
                format_scores[format_type] /= total_lines
        
        return format_scores
    
    def get_supported_formats(self) -> List[Dict]:
        """
        Возвращает список поддерживаемых форматов для UI
        """
        formats = []
        for format_type, patterns in self.patterns.items():
            for pattern in patterns:
                formats.append({
                    'name': pattern.name,
                    'description': pattern.description,
                    'format_type': format_type.value,
                    'examples': pattern.examples
                })
        return formats

# Глобальный экземпляр детектора
log_detector = LogFormatDetector()

def detect_log_level(line: str, important_levels: List[str], debug: bool = False) -> Optional[str]:
    """
    Универсальная функция для определения уровня лога
    """
    return log_detector.detect_log_level(line, important_levels, debug) 