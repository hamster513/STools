-- ===== METASPLOIT SCHEMA =====

-- Создание таблицы для хранения данных Metasploit
CREATE TABLE IF NOT EXISTS metasploit_modules (
    id SERIAL PRIMARY KEY,
    module_name VARCHAR(500) NOT NULL UNIQUE,
    name TEXT NOT NULL,
    rank INTEGER NOT NULL,
    rank_text VARCHAR(20) GENERATED ALWAYS AS (
        CASE 
            WHEN rank = 0 THEN 'manual'
            WHEN rank = 200 THEN 'low'
            WHEN rank = 300 THEN 'average'
            WHEN rank = 400 THEN 'normal'
            WHEN rank = 500 THEN 'good'
            WHEN rank = 600 THEN 'excellent'
            ELSE 'unknown'
        END
    ) STORED,
    disclosure_date DATE,
    type VARCHAR(50) NOT NULL,
    description TEXT,
    "references" TEXT, -- Corrected: "references" is a reserved keyword
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Создание индексов для оптимизации поиска
CREATE INDEX IF NOT EXISTS idx_metasploit_module_name ON metasploit_modules(module_name);
CREATE INDEX IF NOT EXISTS idx_metasploit_rank ON metasploit_modules(rank);
CREATE INDEX IF NOT EXISTS idx_metasploit_type ON metasploit_modules(type);
CREATE INDEX IF NOT EXISTS idx_metasploit_disclosure_date ON metasploit_modules(disclosure_date);

-- Создание триггера для автоматического обновления updated_at
CREATE OR REPLACE FUNCTION update_metasploit_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER trigger_metasploit_updated_at
    BEFORE UPDATE ON metasploit_modules 
    FOR EACH ROW 
    EXECUTE FUNCTION update_metasploit_updated_at();

-- Предоставление прав доступа
GRANT ALL PRIVILEGES ON TABLE metasploit_modules TO stools_user;
GRANT USAGE, SELECT ON SEQUENCE metasploit_modules_id_seq TO stools_user;
