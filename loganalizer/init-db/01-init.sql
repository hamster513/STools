-- Инициализация базы данных LogAnalizer
-- База данных loganalizer_db уже создана через переменные окружения

-- Создание таблицы настроек
CREATE TABLE IF NOT EXISTS settings (
    id SERIAL PRIMARY KEY,
    key VARCHAR(255) UNIQUE NOT NULL,
    value TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Создание таблицы файлов логов
CREATE TABLE IF NOT EXISTS log_files (
    id VARCHAR(255) PRIMARY KEY,
    original_name VARCHAR(500) NOT NULL,
    file_path TEXT NOT NULL,
    file_type VARCHAR(50),
    file_size BIGINT,
    upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    parent_file_id VARCHAR(255),
    FOREIGN KEY (parent_file_id) REFERENCES log_files(id) ON DELETE CASCADE
);

-- Создание таблицы пресетов анализа
CREATE TABLE IF NOT EXISTS analysis_presets (
    id VARCHAR(255) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    system_context TEXT,
    questions JSONB,
    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_default BOOLEAN DEFAULT FALSE
);

-- Создание таблицы пользовательских настроек анализа
CREATE TABLE IF NOT EXISTS custom_analysis_settings (
    id VARCHAR(255) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    pattern TEXT NOT NULL,
    description TEXT,
    enabled BOOLEAN DEFAULT TRUE,
    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Создание таблицы отфильтрованных файлов
CREATE TABLE IF NOT EXISTS filtered_files (
    id VARCHAR(255) PRIMARY KEY,
    original_file_id VARCHAR(255) NOT NULL,
    filtered_file_path TEXT NOT NULL,
    filter_settings JSONB,
    lines_count INTEGER,
    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (original_file_id) REFERENCES log_files(id) ON DELETE CASCADE
);
