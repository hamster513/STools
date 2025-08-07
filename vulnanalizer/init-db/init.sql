-- Инициализация базы данных VulnAnalizer
-- База данных vulnanalizer уже создана через переменные окружения

-- Создание таблицы для настроек
CREATE TABLE IF NOT EXISTS settings (
    id SERIAL PRIMARY KEY,
    key VARCHAR(255) UNIQUE NOT NULL,
    value TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Создание таблицы для анализа
CREATE TABLE IF NOT EXISTS analysis (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    status VARCHAR(50) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Создание таблицы для EPSS
CREATE TABLE IF NOT EXISTS epss (
    id SERIAL PRIMARY KEY,
    cve VARCHAR(32) NOT NULL UNIQUE,
    epss NUMERIC(10,8),
    percentile NUMERIC(10,8),
    cvss NUMERIC(3,1),
    date DATE
);

-- Создание таблицы для Exploit DB
CREATE TABLE IF NOT EXISTS exploitdb (
    id SERIAL PRIMARY KEY,
    exploit_id INTEGER NOT NULL,
    file_path VARCHAR(500),
    description TEXT,
    date_published DATE,
    author VARCHAR(255),
    type VARCHAR(100),
    platform VARCHAR(100),
    port INTEGER,
    date_added DATE,
    date_updated DATE,
    verified BOOLEAN DEFAULT FALSE,
    codes TEXT,
    tags TEXT,
    aliases TEXT,
    screenshot_url TEXT,
    application_url TEXT,
    source_url TEXT,
    UNIQUE (exploit_id)
);

-- Создание таблицы для хостов с расширенными полями
CREATE TABLE IF NOT EXISTS hosts (
    id SERIAL PRIMARY KEY,
    hostname VARCHAR(255),
    ip_address VARCHAR(45),
    cve VARCHAR(32),
    cvss NUMERIC(3,1),
    criticality VARCHAR(50),
    status VARCHAR(100),
    -- Новые поля для EPSS и риска
    epss_score NUMERIC(10,8),
    epss_percentile NUMERIC(10,8),
    risk_score NUMERIC(5,2),
    risk_raw NUMERIC(10,8),
    impact_score NUMERIC(5,4),
    -- Поля для эксплойтов
    exploits_count INTEGER DEFAULT 0,
    verified_exploits_count INTEGER DEFAULT 0,
    has_exploits BOOLEAN DEFAULT FALSE,
    last_exploit_date DATE,
    -- Поля для обновления данных
    epss_updated_at TIMESTAMP,
    exploits_updated_at TIMESTAMP,
    risk_updated_at TIMESTAMP,
    imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Создание индексов для улучшения производительности
CREATE INDEX IF NOT EXISTS idx_hosts_cve ON hosts(cve);
CREATE INDEX IF NOT EXISTS idx_hosts_risk_score ON hosts(risk_score);
CREATE INDEX IF NOT EXISTS idx_hosts_has_exploits ON hosts(has_exploits);
CREATE INDEX IF NOT EXISTS idx_epss_cve ON epss(cve);
CREATE INDEX IF NOT EXISTS idx_exploitdb_aliases ON exploitdb USING gin(to_tsvector('english', aliases));
CREATE INDEX IF NOT EXISTS idx_exploitdb_tags ON exploitdb USING gin(to_tsvector('english', tags));

-- Вставка начальных настроек
INSERT INTO settings (key, value) VALUES 
    ('database_host', '172.20.0.10'),
    ('database_port', '5432'),
    ('database_name', 'vulnanalizer'),
    ('database_user', 'vulnanalizer'),
    ('database_password', 'vulnanalizer'),
    ('theme', 'light'),
    ('impact_resource_criticality', 'Medium'),
    ('impact_confidential_data', 'Отсутствуют'),
    ('impact_internet_access', 'Недоступен'),
    ('risk_threshold', '75')
ON CONFLICT (key) DO NOTHING; 