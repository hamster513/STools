-- Инициализация базы данных VulnAnalizer
-- База данных vulnanalizer уже создана через переменные окружения

-- Создание таблицы пользователей
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    email VARCHAR(100),
    is_admin BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Создание индексов для пользователей
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_is_admin ON users(is_admin);
CREATE INDEX IF NOT EXISTS idx_users_is_active ON users(is_active);

-- Создание пользователя-администратора по умолчанию
-- Пароль: admin123 (хеш bcrypt)
INSERT INTO users (username, password, email, is_admin, is_active) VALUES 
    ('admin', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj/RK.s5uO.G', 'admin@example.com', TRUE, TRUE)
ON CONFLICT (username) DO UPDATE SET 
    password = EXCLUDED.password,
    email = EXCLUDED.email,
    is_admin = EXCLUDED.is_admin,
    is_active = EXCLUDED.is_active,
    updated_at = CURRENT_TIMESTAMP;

-- Создание таблицы настроек
CREATE TABLE IF NOT EXISTS settings (
    key VARCHAR(100) PRIMARY KEY,
    value TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Инициализация настроек Impact для расчета риска
INSERT INTO settings (key, value) VALUES 
    ('impact_resource_criticality', 'Medium'),
    ('impact_confidential_data', 'Отсутствуют'),
    ('impact_internet_access', 'Недоступен')
ON CONFLICT (key) DO UPDATE SET 
    value = EXCLUDED.value,
    updated_at = CURRENT_TIMESTAMP;

-- Инициализация настроек базы данных
INSERT INTO settings (key, value) VALUES 
    ('database_host', 'localhost'),
    ('database_port', '5432'),
    ('database_name', 'vulnanalizer'),
    ('database_user', 'postgres'),
    ('database_password', '')
ON CONFLICT (key) DO UPDATE SET 
    value = EXCLUDED.value,
    updated_at = CURRENT_TIMESTAMP;

-- Создание таблицы EPSS
CREATE TABLE IF NOT EXISTS epss (
    id SERIAL PRIMARY KEY,
    cve VARCHAR(20) UNIQUE NOT NULL,
    epss DECIMAL(5,4),
    percentile DECIMAL(5,2),
    cvss DECIMAL(3,1),
    date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Создание индексов для EPSS
CREATE INDEX IF NOT EXISTS idx_epss_cve ON epss(cve);
CREATE INDEX IF NOT EXISTS idx_epss_date ON epss(date);
CREATE INDEX IF NOT EXISTS idx_epss_epss ON epss(epss);

-- Создание таблицы ExploitDB (исправленная структура)
CREATE TABLE IF NOT EXISTS exploitdb (
    id SERIAL PRIMARY KEY,
    exploit_id INTEGER UNIQUE NOT NULL,
    file_path TEXT,
    description TEXT,
    date_published DATE,
    author VARCHAR(100),
    type VARCHAR(50),
    platform VARCHAR(50),
    port VARCHAR(10),
    date_added DATE,
    date_updated DATE,
    verified BOOLEAN DEFAULT FALSE,
    codes TEXT,
    tags TEXT,
    aliases TEXT,
    screenshot_url TEXT,
    application_url TEXT,
    source_url TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Создание индексов для ExploitDB
CREATE INDEX IF NOT EXISTS idx_exploitdb_exploit_id ON exploitdb(exploit_id);
CREATE INDEX IF NOT EXISTS idx_exploitdb_date_published ON exploitdb(date_published);
CREATE INDEX IF NOT EXISTS idx_exploitdb_verified ON exploitdb(verified);
CREATE INDEX IF NOT EXISTS idx_exploitdb_type ON exploitdb(type);
CREATE INDEX IF NOT EXISTS idx_exploitdb_platform ON exploitdb(platform);

-- Создание таблицы хостов (с полем zone)
CREATE TABLE IF NOT EXISTS hosts (
    id SERIAL PRIMARY KEY,
    hostname VARCHAR(255),
    ip_address INET,
    cve VARCHAR(20),
    cvss DECIMAL(3,1),
    cvss_source VARCHAR(20),
    criticality VARCHAR(20),
    status VARCHAR(50) DEFAULT 'Active',
    os_name VARCHAR(100),
    zone VARCHAR(100),
    epss_score DECIMAL(5,4),
    epss_percentile DECIMAL(5,2),
    exploits_count INTEGER DEFAULT 0,
    verified_exploits_count INTEGER DEFAULT 0,
    has_exploits BOOLEAN DEFAULT FALSE,
    last_exploit_date DATE,
    risk_score DECIMAL(5,2),
    risk_raw DECIMAL(5,2),
    impact_score DECIMAL(5,2),
    epss_updated_at TIMESTAMP,
    exploits_updated_at TIMESTAMP,
    risk_updated_at TIMESTAMP,
    imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Создание индексов для хостов
CREATE INDEX IF NOT EXISTS idx_hosts_hostname ON hosts(hostname);
CREATE INDEX IF NOT EXISTS idx_hosts_ip_address ON hosts(ip_address);
CREATE INDEX IF NOT EXISTS idx_hosts_cve ON hosts(cve);
CREATE INDEX IF NOT EXISTS idx_hosts_criticality ON hosts(criticality);
CREATE INDEX IF NOT EXISTS idx_hosts_status ON hosts(status);
CREATE INDEX IF NOT EXISTS idx_hosts_os_name ON hosts(os_name);
CREATE INDEX IF NOT EXISTS idx_hosts_zone ON hosts(zone);
CREATE INDEX IF NOT EXISTS idx_hosts_risk_score ON hosts(risk_score);
CREATE INDEX IF NOT EXISTS idx_hosts_has_exploits ON hosts(has_exploits);
CREATE INDEX IF NOT EXISTS idx_hosts_last_exploit_date ON hosts(last_exploit_date);

-- Создание таблицы VM импорта
CREATE TABLE IF NOT EXISTS vm_import_status (
    id SERIAL PRIMARY KEY,
    last_import TIMESTAMP,
    import_count INTEGER DEFAULT 0,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Создание таблицы статуса фоновых задач
CREATE TABLE IF NOT EXISTS background_tasks (
    id SERIAL PRIMARY KEY,
    task_type VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'idle', -- idle, running, completed, error, cancelled
    current_step TEXT,
    total_items INTEGER DEFAULT 0,
    processed_items INTEGER DEFAULT 0,
    total_records INTEGER DEFAULT 0,
    updated_records INTEGER DEFAULT 0,
    start_time TIMESTAMP,
    end_time TIMESTAMP,
    error_message TEXT,
    cancelled BOOLEAN DEFAULT FALSE,
    parameters JSONB,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Создание индексов для фоновых задач
CREATE INDEX IF NOT EXISTS idx_background_tasks_task_type ON background_tasks(task_type);
CREATE INDEX IF NOT EXISTS idx_background_tasks_status ON background_tasks(status);
CREATE INDEX IF NOT EXISTS idx_background_tasks_created_at ON background_tasks(created_at);

-- Создание таблицы CVE
CREATE TABLE IF NOT EXISTS cve (
    id SERIAL PRIMARY KEY,
    cve_id VARCHAR(20) UNIQUE NOT NULL,
    description TEXT,
    cvss_v3_base_score DECIMAL(3,1),
    cvss_v3_base_severity VARCHAR(20),
    cvss_v2_base_score DECIMAL(3,1),
    cvss_v2_base_severity VARCHAR(20),
    exploitability_score DECIMAL(3,1),
    impact_score DECIMAL(3,1),
    published_date TIMESTAMP,
    last_modified_date TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Создание индексов для CVE
CREATE INDEX IF NOT EXISTS idx_cve_cve_id ON cve(cve_id);
CREATE INDEX IF NOT EXISTS idx_cve_cvss_v3_base_score ON cve(cvss_v3_base_score);
CREATE INDEX IF NOT EXISTS idx_cve_cvss_v2_base_score ON cve(cvss_v2_base_score);
CREATE INDEX IF NOT EXISTS idx_cve_published_date ON cve(published_date);
CREATE INDEX IF NOT EXISTS idx_cve_last_modified_date ON cve(last_modified_date);
