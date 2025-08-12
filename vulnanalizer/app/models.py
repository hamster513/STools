from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime

class Settings(BaseModel):
    database_host: str
    database_port: str
    database_name: str
    database_user: str
    database_password: str
    theme: str = "light"

class EPSSRecord(BaseModel):
    cve: str
    epss: float
    percentile: float
    date: Optional[datetime] = None

class ExploitDBRecord(BaseModel):
    exploit_id: int
    file_path: Optional[str] = None
    description: Optional[str] = None
    date_published: Optional[datetime] = None
    author: Optional[str] = None
    type: Optional[str] = None
    platform: Optional[str] = None
    port: Optional[int] = None
    date_added: Optional[datetime] = None
    date_updated: Optional[datetime] = None
    verified: bool = False
    codes: Optional[str] = None
    tags: Optional[str] = None
    aliases: Optional[str] = None
    screenshot_url: Optional[str] = None
    application_url: Optional[str] = None
    source_url: Optional[str] = None

class CVERecord(BaseModel):
    cve_id: str
    description: Optional[str] = None
    cvss_v3_base_score: Optional[float] = None
    cvss_v3_base_severity: Optional[str] = None
    cvss_v2_base_score: Optional[float] = None
    cvss_v2_base_severity: Optional[str] = None
    exploitability_score: Optional[float] = None
    impact_score: Optional[float] = None
    published_date: Optional[datetime] = None
    last_modified_date: Optional[datetime] = None

class HostRecord(BaseModel):
    id: Optional[int] = None
    hostname: str
    ip_address: Optional[str] = None
    cve: str
    cvss: Optional[float] = None
    criticality: str
    status: str
    # Новые поля для EPSS и риска
    epss_score: Optional[float] = None
    epss_percentile: Optional[float] = None
    risk_score: Optional[float] = None
    risk_raw: Optional[float] = None
    impact_score: Optional[float] = None
    # Поля для эксплойтов
    exploits_count: int = 0
    verified_exploits_count: int = 0
    has_exploits: bool = False
    last_exploit_date: Optional[datetime] = None
    # Поля для обновления данных
    epss_updated_at: Optional[datetime] = None
    exploits_updated_at: Optional[datetime] = None
    risk_updated_at: Optional[datetime] = None
    imported_at: Optional[datetime] = None

class HostRiskData(BaseModel):
    host_id: int
    epss_data: Optional[dict] = None
    exploit_data: Optional[list] = None
    risk_calculation: Optional[dict] = None
    last_updated: Optional[datetime] = None 

class AlertRule(BaseModel):
    """Правило для создания алертов"""
    id: Optional[int] = None
    name: str
    description: Optional[str] = None
    conditions: Dict[str, Any]  # Условия срабатывания
    severity: str = "medium"  # low, medium, high, critical
    enabled: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class Alert(BaseModel):
    """Алерт"""
    id: Optional[int] = None
    rule_id: int
    title: str
    message: str
    severity: str
    host_count: int = 0
    cve_count: int = 0
    status: str = "new"  # new, acknowledged, resolved
    created_at: Optional[datetime] = None
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None

class DashboardStats(BaseModel):
    """Статистика для дашборда"""
    total_hosts: int
    total_cves: int
    high_risk_hosts: int
    critical_hosts: int
    hosts_with_exploits: int
    avg_risk_score: float
    recent_alerts: int
    last_update: Optional[datetime] = None 