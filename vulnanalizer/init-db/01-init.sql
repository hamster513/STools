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

-- Создание таблицы настроек
CREATE TABLE IF NOT EXISTS settings (
    key VARCHAR(100) PRIMARY KEY,
    value TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

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

-- Создание таблицы ExploitDB
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

-- Создание таблицы хостов
CREATE TABLE IF NOT EXISTS hosts (
    id SERIAL PRIMARY KEY,
    hostname VARCHAR(255),
    ip_address INET,
    cve VARCHAR(20),
    cvss DECIMAL(3,1),
    criticality VARCHAR(20),
    status VARCHAR(50) DEFAULT 'Active',
    os_name VARCHAR(100),
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
