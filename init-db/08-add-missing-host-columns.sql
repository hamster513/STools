-- Добавление недостающих колонок в таблицу hosts
SET search_path TO vulnanalizer;

-- Добавляем недостающие колонки
ALTER TABLE hosts ADD COLUMN IF NOT EXISTS cve TEXT;
ALTER TABLE hosts ADD COLUMN IF NOT EXISTS cvss DECIMAL(3,1);
ALTER TABLE hosts ADD COLUMN IF NOT EXISTS status VARCHAR(50) DEFAULT 'Active';
ALTER TABLE hosts ADD COLUMN IF NOT EXISTS os_name TEXT;
ALTER TABLE hosts ADD COLUMN IF NOT EXISTS zone VARCHAR(100);
ALTER TABLE hosts ADD COLUMN IF NOT EXISTS epss_score DECIMAL(10,9);
ALTER TABLE hosts ADD COLUMN IF NOT EXISTS exploits_count INTEGER DEFAULT 0;
ALTER TABLE hosts ADD COLUMN IF NOT EXISTS risk_score DECIMAL(5,2);
ALTER TABLE hosts ADD COLUMN IF NOT EXISTS epss_updated_at TIMESTAMP;
ALTER TABLE hosts ADD COLUMN IF NOT EXISTS exploits_updated_at TIMESTAMP;
ALTER TABLE hosts ADD COLUMN IF NOT EXISTS risk_updated_at TIMESTAMP;
ALTER TABLE hosts ADD COLUMN IF NOT EXISTS cvss_source VARCHAR(50);
ALTER TABLE hosts ADD COLUMN IF NOT EXISTS epss_percentile DECIMAL(5,2);
ALTER TABLE hosts ADD COLUMN IF NOT EXISTS risk_raw DECIMAL(10,6);
ALTER TABLE hosts ADD COLUMN IF NOT EXISTS impact_score DECIMAL(5,2);
ALTER TABLE hosts ADD COLUMN IF NOT EXISTS verified_exploits_count INTEGER DEFAULT 0;
ALTER TABLE hosts ADD COLUMN IF NOT EXISTS has_exploits BOOLEAN DEFAULT FALSE;
ALTER TABLE hosts ADD COLUMN IF NOT EXISTS last_exploit_date DATE;

-- Создаем индексы для новых колонок
CREATE INDEX IF NOT EXISTS idx_hosts_cve ON hosts(cve);
CREATE INDEX IF NOT EXISTS idx_hosts_status ON hosts(status);
CREATE INDEX IF NOT EXISTS idx_hosts_zone ON hosts(zone);
CREATE INDEX IF NOT EXISTS idx_hosts_epss_score ON hosts(epss_score);
CREATE INDEX IF NOT EXISTS idx_hosts_risk_score ON hosts(risk_score);
