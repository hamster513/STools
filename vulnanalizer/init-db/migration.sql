-- Миграция для добавления недостающих колонок в таблицу hosts
-- Выполняется для существующих баз данных

-- Добавляем колонку status
ALTER TABLE hosts ADD COLUMN IF NOT EXISTS status VARCHAR(50) DEFAULT 'Active';

-- Добавляем колонку os_name
ALTER TABLE hosts ADD COLUMN IF NOT EXISTS os_name VARCHAR(100);

-- Добавляем колонку epss_percentile
ALTER TABLE hosts ADD COLUMN IF NOT EXISTS epss_percentile DECIMAL(5,2);

-- Добавляем колонку risk_raw
ALTER TABLE hosts ADD COLUMN IF NOT EXISTS risk_raw DECIMAL(5,2);

-- Добавляем колонку exploits_count (переименовываем exploit_count)
ALTER TABLE hosts ADD COLUMN IF NOT EXISTS exploits_count INTEGER DEFAULT 0;
UPDATE hosts SET exploits_count = exploit_count WHERE exploit_count IS NOT NULL;
ALTER TABLE hosts DROP COLUMN IF EXISTS exploit_count;

-- Добавляем колонку verified_exploits_count (переименовываем verified_exploits)
ALTER TABLE hosts ADD COLUMN IF NOT EXISTS verified_exploits_count INTEGER DEFAULT 0;
UPDATE hosts SET verified_exploits_count = verified_exploits WHERE verified_exploits IS NOT NULL;
ALTER TABLE hosts DROP COLUMN IF EXISTS verified_exploits;

-- Добавляем колонку has_exploits
ALTER TABLE hosts ADD COLUMN IF NOT EXISTS has_exploits BOOLEAN DEFAULT FALSE;

-- Добавляем колонку last_exploit_date
ALTER TABLE hosts ADD COLUMN IF NOT EXISTS last_exploit_date DATE;

-- Добавляем колонки для отслеживания обновлений
ALTER TABLE hosts ADD COLUMN IF NOT EXISTS epss_updated_at TIMESTAMP;
ALTER TABLE hosts ADD COLUMN IF NOT EXISTS exploits_updated_at TIMESTAMP;
ALTER TABLE hosts ADD COLUMN IF NOT EXISTS risk_updated_at TIMESTAMP;
ALTER TABLE hosts ADD COLUMN IF NOT EXISTS imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;

-- Создаем индексы для новых колонок
CREATE INDEX IF NOT EXISTS idx_hosts_status ON hosts(status);
CREATE INDEX IF NOT EXISTS idx_hosts_os_name ON hosts(os_name);
CREATE INDEX IF NOT EXISTS idx_hosts_has_exploits ON hosts(has_exploits);
CREATE INDEX IF NOT EXISTS idx_hosts_last_exploit_date ON hosts(last_exploit_date);
