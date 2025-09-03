-- Инициализация схемы VulnAnalizer
SET search_path TO vulnanalizer;

-- Создание функции для обновления updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Таблица хостов
CREATE TABLE IF NOT EXISTS hosts (
    id SERIAL PRIMARY KEY,
    hostname VARCHAR(255),
    ip_address INET,
    os_info TEXT,
    criticality VARCHAR(50) DEFAULT 'Medium',
    confidential_data BOOLEAN DEFAULT FALSE,
    internet_access BOOLEAN DEFAULT FALSE,
    cve TEXT,
    cvss DECIMAL(3,1),
    status VARCHAR(50) DEFAULT 'Active',
    os_name TEXT,
    zone VARCHAR(100),
    epss_score DECIMAL(10,9),
    exploits_count INTEGER DEFAULT 0,
    risk_score DECIMAL(5,2),
    epss_updated_at TIMESTAMP,
    exploits_updated_at TIMESTAMP,
    risk_updated_at TIMESTAMP,
    cvss_source VARCHAR(50),
    epss_percentile DECIMAL(5,2),
    risk_raw DECIMAL(10,6),
    impact_score DECIMAL(5,2),
    verified_exploits_count INTEGER DEFAULT 0,
    has_exploits BOOLEAN DEFAULT FALSE,
    last_exploit_date DATE,
    metasploit_rank INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Таблица CVE
CREATE TABLE IF NOT EXISTS cve_data (
    id SERIAL PRIMARY KEY,
    cve_id VARCHAR(20) UNIQUE NOT NULL,
    description TEXT,
    cvss_score DECIMAL(3,1),
    cvss_vector VARCHAR(100),
    published_date DATE,
    last_modified_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Таблица уязвимостей хостов
CREATE TABLE IF NOT EXISTS host_vulnerabilities (
    id SERIAL PRIMARY KEY,
    host_id INTEGER REFERENCES hosts(id) ON DELETE CASCADE,
    cve_id VARCHAR(20) REFERENCES cve_data(cve_id) ON DELETE CASCADE,
    status VARCHAR(50) DEFAULT 'open',
    risk_score DECIMAL(5,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Таблица EPSS данных
CREATE TABLE IF NOT EXISTS epss_data (
    id SERIAL PRIMARY KEY,
    cve_id VARCHAR(20) UNIQUE NOT NULL,
    epss_score DECIMAL(10,9),
    percentile DECIMAL(5,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Таблица ExploitDB данных
CREATE TABLE IF NOT EXISTS exploitdb_data (
    id SERIAL PRIMARY KEY,
    cve_id VARCHAR(20),
    exploit_id INTEGER,
    description TEXT,
    file_path VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Таблица фоновых задач
CREATE TABLE IF NOT EXISTS background_tasks (
    id SERIAL PRIMARY KEY,
    task_type VARCHAR(100) NOT NULL,
    status VARCHAR(50) DEFAULT 'idle',
    current_step TEXT,
    total_items INTEGER DEFAULT 0,
    processed_items INTEGER DEFAULT 0,
    total_records INTEGER DEFAULT 0,
    processed_records INTEGER DEFAULT 0,
    updated_records INTEGER DEFAULT 0,
    progress_percent INTEGER DEFAULT 0,
    start_time TIMESTAMP,
    end_time TIMESTAMP,
    error_message TEXT,
    cancelled BOOLEAN DEFAULT FALSE,
    parameters JSONB,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Таблица настроек системы
CREATE TABLE IF NOT EXISTS system_settings (
    id SERIAL PRIMARY KEY,
    setting_name VARCHAR(100) UNIQUE NOT NULL,
    setting_value TEXT,
    description TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Индексы для оптимизации
CREATE INDEX IF NOT EXISTS idx_hosts_hostname ON hosts(hostname);
CREATE INDEX IF NOT EXISTS idx_hosts_ip_address ON hosts(ip_address);
CREATE INDEX IF NOT EXISTS idx_hosts_cve ON hosts(cve);
CREATE INDEX IF NOT EXISTS idx_hosts_status ON hosts(status);
CREATE INDEX IF NOT EXISTS idx_hosts_zone ON hosts(zone);
CREATE INDEX IF NOT EXISTS idx_hosts_epss_score ON hosts(epss_score);
CREATE INDEX IF NOT EXISTS idx_hosts_risk_score ON hosts(risk_score);

-- Уникальный индекс для предотвращения дубликатов хостов с одинаковым CVE
CREATE UNIQUE INDEX IF NOT EXISTS idx_hosts_hostname_cve_unique ON hosts(hostname, cve);

CREATE INDEX IF NOT EXISTS idx_cve_data_cve_id ON cve_data(cve_id);
CREATE INDEX IF NOT EXISTS idx_cve_data_cvss_score ON cve_data(cvss_score);
CREATE INDEX IF NOT EXISTS idx_host_vulnerabilities_host_id ON host_vulnerabilities(host_id);
CREATE INDEX IF NOT EXISTS idx_host_vulnerabilities_cve_id ON host_vulnerabilities(cve_id);
CREATE INDEX IF NOT EXISTS idx_epss_data_cve_id ON epss_data(cve_id);
CREATE INDEX IF NOT EXISTS idx_exploitdb_data_cve_id ON exploitdb_data(cve_id);
CREATE INDEX IF NOT EXISTS idx_background_tasks_task_type ON background_tasks(task_type);
CREATE INDEX IF NOT EXISTS idx_background_tasks_status ON background_tasks(status);
CREATE INDEX IF NOT EXISTS idx_system_settings_setting_name ON system_settings(setting_name);

-- Создание триггеров для обновления updated_at
CREATE TRIGGER update_hosts_updated_at 
    BEFORE UPDATE ON hosts 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_background_tasks_updated_at 
    BEFORE UPDATE ON background_tasks 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_system_settings_updated_at 
    BEFORE UPDATE ON system_settings 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();
