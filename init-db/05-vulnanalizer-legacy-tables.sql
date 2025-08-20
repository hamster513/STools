-- Создание legacy таблиц для совместимости с vulnanalizer
SET search_path TO vulnanalizer;

-- Таблица epss (legacy)
CREATE TABLE IF NOT EXISTS epss (
    id SERIAL PRIMARY KEY,
    cve VARCHAR(20) NOT NULL,
    epss DECIMAL(10,9),
    percentile DECIMAL(5,2),
    cvss DECIMAL(3,1),
    date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Таблица exploitdb (legacy)
CREATE TABLE IF NOT EXISTS exploitdb (
    exploit_id INTEGER PRIMARY KEY,
    file_path VARCHAR(500),
    description TEXT,
    date_published DATE,
    author VARCHAR(255),
    type VARCHAR(100),
    platform VARCHAR(100),
    port VARCHAR(50),
    date_added DATE,
    date_updated DATE,
    verified BOOLEAN DEFAULT FALSE,
    codes TEXT,
    tags TEXT,
    aliases TEXT,
    screenshot_url VARCHAR(500),
    application_url VARCHAR(500),
    source_url VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Таблица cve (legacy)
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
    published_date DATE,
    last_modified_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Таблица settings (legacy)
CREATE TABLE IF NOT EXISTS settings (
    id SERIAL PRIMARY KEY,
    key VARCHAR(255) UNIQUE NOT NULL,
    value TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Индексы для оптимизации
CREATE INDEX IF NOT EXISTS idx_epss_cve ON epss(cve);
CREATE INDEX IF NOT EXISTS idx_exploitdb_exploit_id ON exploitdb(exploit_id);
CREATE INDEX IF NOT EXISTS idx_cve_cve_id ON cve(cve_id);
CREATE INDEX IF NOT EXISTS idx_settings_key ON settings(key);

-- Создание триггеров для обновления updated_at
CREATE TRIGGER update_settings_updated_at 
    BEFORE UPDATE ON settings 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

