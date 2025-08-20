-- Инициализация схемы LogAnalizer
SET search_path TO loganalizer;

-- Создание функции для обновления updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Таблица файлов логов
CREATE TABLE IF NOT EXISTS log_files (
    id VARCHAR(255) PRIMARY KEY,
    filename VARCHAR(255) NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    file_size BIGINT,
    upload_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(50) DEFAULT 'uploaded',
    extracted_count INTEGER DEFAULT 0,
    error_message TEXT
);

-- Таблица записей логов
CREATE TABLE IF NOT EXISTS log_entries (
    id SERIAL PRIMARY KEY,
    file_id VARCHAR(255) REFERENCES log_files(id) ON DELETE CASCADE,
    timestamp TIMESTAMP,
    level VARCHAR(20),
    message TEXT,
    source VARCHAR(100),
    line_number INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Таблица настроек анализа
CREATE TABLE IF NOT EXISTS analysis_settings (
    id SERIAL PRIMARY KEY,
    setting_name VARCHAR(100) UNIQUE NOT NULL,
    setting_value TEXT,
    description TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Таблица статистики
CREATE TABLE IF NOT EXISTS log_statistics (
    id SERIAL PRIMARY KEY,
    file_id VARCHAR(255) REFERENCES log_files(id) ON DELETE CASCADE,
    total_entries INTEGER DEFAULT 0,
    error_count INTEGER DEFAULT 0,
    warning_count INTEGER DEFAULT 0,
    info_count INTEGER DEFAULT 0,
    debug_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Таблица пресетов анализа
CREATE TABLE IF NOT EXISTS analysis_presets (
    id VARCHAR(255) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    system_context TEXT,
    questions JSONB,
    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_default BOOLEAN DEFAULT FALSE
);

-- Таблица пользовательских настроек анализа
CREATE TABLE IF NOT EXISTS custom_analysis_settings (
    id VARCHAR(255) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    pattern TEXT NOT NULL,
    description TEXT,
    enabled BOOLEAN DEFAULT TRUE,
    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Таблица отфильтрованных файлов
CREATE TABLE IF NOT EXISTS filtered_files (
    id VARCHAR(255) PRIMARY KEY,
    original_file_id VARCHAR(255) NOT NULL,
    filtered_file_path TEXT NOT NULL,
    filter_settings JSONB,
    lines_count INTEGER,
    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (original_file_id) REFERENCES log_files(id) ON DELETE CASCADE
);

-- Таблица настроек
CREATE TABLE IF NOT EXISTS settings (
    id SERIAL PRIMARY KEY,
    key VARCHAR(255) UNIQUE NOT NULL,
    value TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Индексы для оптимизации
CREATE INDEX IF NOT EXISTS idx_log_files_filename ON log_files(filename);
CREATE INDEX IF NOT EXISTS idx_log_files_status ON log_files(status);
CREATE INDEX IF NOT EXISTS idx_log_entries_file_id ON log_entries(file_id);
CREATE INDEX IF NOT EXISTS idx_log_entries_timestamp ON log_entries(timestamp);
CREATE INDEX IF NOT EXISTS idx_log_entries_level ON log_entries(level);
CREATE INDEX IF NOT EXISTS idx_log_statistics_file_id ON log_statistics(file_id);

-- Создание триггера для обновления updated_at
CREATE TRIGGER update_analysis_settings_updated_at 
    BEFORE UPDATE ON analysis_settings 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();
