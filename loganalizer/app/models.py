from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime

class LogFile(BaseModel):
    id: str
    original_name: str
    file_path: str
    file_type: str
    file_size: int
    upload_date: datetime
    parent_file_id: Optional[str] = None

class LogSettings(BaseModel):
    # Настройки загрузки файлов
    max_file_size_mb: int = 100
    supported_formats: List[str] = ['.log', '.txt', '.csv', '.json', '.xml', '.zip', '.tar', '.gz', '.bz2', '.xz']
    
    # Настройки распаковки
    extract_nested_archives: bool = True
    max_extraction_depth: int = 5
    
    # Настройки фильтрации
    max_filtering_file_size_mb: int = 50  # Максимальный размер файла для автоматической фильтрации
    
    # Настройки анализа
    important_log_levels: List[str] = ['ERROR', 'WARN', 'CRITICAL', 'FATAL', 'ALERT', 'EMERGENCY', 'INFO', 'DEBUG']
    
    # Настройки ML анализа
    enable_ml_analysis: bool = True
    ml_model_path: Optional[str] = None

class AnalysisPreset(BaseModel):
    id: Optional[str] = None
    name: str
    description: str
    system_context: str
    questions: List[str]
    created_date: Optional[datetime] = None
    is_default: bool = False

class LogAnalysisRequest(BaseModel):
    file_ids: List[str]
    system_name: str
    preset_id: Optional[str] = None
    custom_questions: Optional[List[str]] = None

class LogAnalysisResult(BaseModel):
    file_id: str
    original_name: str
    important_lines: List[Dict[str, Any]]
    total_lines: int
    analysis_summary: Optional[str] = None

class CustomAnalysisSetting(BaseModel):
    id: Optional[str] = None
    name: str
    pattern: str
    description: Optional[str] = None
    enabled: bool = True
    created_date: Optional[datetime] = None 