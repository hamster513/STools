-- =====================================================
-- Единый скрипт инициализации базы данных STools
-- Версия: 2025-09-05
-- Описание: Создание всех схем, таблиц, индексов и настроек
-- =====================================================

-- Создание схем
CREATE SCHEMA IF NOT EXISTS auth;
CREATE SCHEMA IF NOT EXISTS loganalizer;
CREATE SCHEMA IF NOT EXISTS vulnanalizer;

-- =====================================================
-- ФУНКЦИИ
-- =====================================================

-- Функция обновления updated_at
CREATE OR REPLACE FUNCTION vulnanalizer.update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Функция обновления updated_at для Metasploit
CREATE OR REPLACE FUNCTION update_metasploit_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- =====================================================
-- СХЕМА VULNANALIZER
-- =====================================================

-- Таблица хостов
CREATE TABLE IF NOT EXISTS vulnanalizer.hosts (
    id SERIAL PRIMARY KEY,
    hostname VARCHAR(255),
    ip_address INET,
    os_info TEXT,
    criticality VARCHAR(50) DEFAULT 'Medium',
    confidential_data BOOLEAN DEFAULT FALSE,
    internet_access BOOLEAN DEFAULT FALSE,
    cve TEXT,
    cvss NUMERIC(3,1),
    status VARCHAR(50) DEFAULT 'Active',
    os_name TEXT,
    zone VARCHAR(100),
    epss_score NUMERIC(10,9),
    exploits_count INTEGER DEFAULT 0,
    risk_score NUMERIC(5,2),
    epss_updated_at TIMESTAMP,
    exploits_updated_at TIMESTAMP,
    risk_updated_at TIMESTAMP,
    cvss_source VARCHAR(50),
    epss_percentile NUMERIC(5,2),
    risk_raw NUMERIC(10,6),
    impact_score NUMERIC(5,2),
    verified_exploits_count INTEGER DEFAULT 0,
    has_exploits BOOLEAN DEFAULT FALSE,
    last_exploit_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metasploit_rank INTEGER
);

-- Таблица CVE
CREATE TABLE IF NOT EXISTS vulnanalizer.cve (
    id SERIAL PRIMARY KEY,
    cve_id VARCHAR(20) NOT NULL UNIQUE,
    description TEXT,
    cvss_v3_base_score NUMERIC(3,1),
    cvss_v3_base_severity VARCHAR(20),
    cvss_v2_base_score NUMERIC(3,1),
    cvss_v2_base_severity VARCHAR(20),
    exploitability_score NUMERIC(3,1),
    impact_score NUMERIC(3,1),
    published_date DATE,
    last_modified_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    -- CVSS v3 метрики
    cvss_v3_attack_vector VARCHAR(20),
    cvss_v3_privileges_required VARCHAR(20),
    cvss_v3_user_interaction VARCHAR(20),
    cvss_v3_confidentiality_impact VARCHAR(20),
    cvss_v3_integrity_impact VARCHAR(20),
    cvss_v3_availability_impact VARCHAR(20),
    -- CVSS v2 метрики
    cvss_v2_access_vector VARCHAR(20),
    cvss_v2_access_complexity VARCHAR(20),
    cvss_v2_authentication VARCHAR(20),
    cvss_v2_confidentiality_impact VARCHAR(20),
    cvss_v2_integrity_impact VARCHAR(20),
    cvss_v2_availability_impact VARCHAR(20)
);

-- Таблица EPSS данных
CREATE TABLE IF NOT EXISTS vulnanalizer.epss (
    cve VARCHAR(20) PRIMARY KEY,
    epss NUMERIC(10,9) NOT NULL,
    percentile NUMERIC(5,2) NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Таблица ExploitDB
CREATE TABLE IF NOT EXISTS vulnanalizer.exploitdb (
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

-- Таблица Metasploit модулей
CREATE TABLE IF NOT EXISTS vulnanalizer.metasploit_modules (
    id SERIAL PRIMARY KEY,
    module_name VARCHAR(500) NOT NULL UNIQUE,
    name TEXT NOT NULL,
    fullname VARCHAR(500) NOT NULL,
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
    "references" TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Таблица настроек
CREATE TABLE IF NOT EXISTS vulnanalizer.settings (
    id SERIAL PRIMARY KEY,
    key VARCHAR(255) NOT NULL UNIQUE,
    value TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Таблица фоновых задач
CREATE TABLE IF NOT EXISTS vulnanalizer.background_tasks (
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

-- Таблица связей хостов и уязвимостей
CREATE TABLE IF NOT EXISTS vulnanalizer.host_vulnerabilities (
    id SERIAL PRIMARY KEY,
    host_id INTEGER NOT NULL REFERENCES vulnanalizer.hosts(id) ON DELETE CASCADE,
    vulnerability_id VARCHAR(50) NOT NULL,
    severity VARCHAR(20),
    status VARCHAR(50) DEFAULT 'Open',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =====================================================
-- ИНДЕКСЫ
-- =====================================================

-- Индексы для таблицы hosts
CREATE INDEX IF NOT EXISTS idx_hosts_cve ON vulnanalizer.hosts(cve);
CREATE INDEX IF NOT EXISTS idx_hosts_epss_score ON vulnanalizer.hosts(epss_score);
CREATE INDEX IF NOT EXISTS idx_hosts_hostname ON vulnanalizer.hosts(hostname);
CREATE INDEX IF NOT EXISTS idx_hosts_hostname_cve_unique ON vulnanalizer.hosts(hostname, cve);
CREATE INDEX IF NOT EXISTS idx_hosts_ip_address ON vulnanalizer.hosts(ip_address);
CREATE INDEX IF NOT EXISTS idx_hosts_risk_score ON vulnanalizer.hosts(risk_score);
CREATE INDEX IF NOT EXISTS idx_hosts_status ON vulnanalizer.hosts(status);
CREATE INDEX IF NOT EXISTS idx_hosts_zone ON vulnanalizer.hosts(zone);

-- Индексы для таблицы cve
CREATE INDEX IF NOT EXISTS idx_cve_cve_id ON vulnanalizer.cve(cve_id);
CREATE INDEX IF NOT EXISTS idx_cve_cvss_v2_access_complexity ON vulnanalizer.cve(cvss_v2_access_complexity);
CREATE INDEX IF NOT EXISTS idx_cve_cvss_v2_access_vector ON vulnanalizer.cve(cvss_v2_access_vector);
CREATE INDEX IF NOT EXISTS idx_cve_cvss_v2_authentication ON vulnanalizer.cve(cvss_v2_authentication);
CREATE INDEX IF NOT EXISTS idx_cve_cvss_v3_attack_vector ON vulnanalizer.cve(cvss_v3_attack_vector);
CREATE INDEX IF NOT EXISTS idx_cve_cvss_v3_privileges_required ON vulnanalizer.cve(cvss_v3_privileges_required);
CREATE INDEX IF NOT EXISTS idx_cve_cvss_v3_user_interaction ON vulnanalizer.cve(cvss_v3_user_interaction);

-- Индексы для таблицы epss
CREATE INDEX IF NOT EXISTS idx_epss_cve ON vulnanalizer.epss(cve);
CREATE INDEX IF NOT EXISTS idx_epss_score ON vulnanalizer.epss(epss);

-- Индексы для таблицы exploitdb
CREATE INDEX IF NOT EXISTS idx_exploitdb_exploit_id ON vulnanalizer.exploitdb(exploit_id);

-- Индексы для таблицы metasploit_modules
CREATE INDEX IF NOT EXISTS idx_metasploit_disclosure_date ON vulnanalizer.metasploit_modules(disclosure_date);
CREATE INDEX IF NOT EXISTS idx_metasploit_module_name ON vulnanalizer.metasploit_modules(module_name);
CREATE INDEX IF NOT EXISTS idx_metasploit_rank ON vulnanalizer.metasploit_modules(rank);
CREATE INDEX IF NOT EXISTS idx_metasploit_type ON vulnanalizer.metasploit_modules(type);

-- Индексы для таблицы settings
CREATE INDEX IF NOT EXISTS idx_settings_key ON vulnanalizer.settings(key);

-- Индексы для таблицы background_tasks
CREATE INDEX IF NOT EXISTS idx_background_tasks_status ON vulnanalizer.background_tasks(status);
CREATE INDEX IF NOT EXISTS idx_background_tasks_task_type ON vulnanalizer.background_tasks(task_type);

-- =====================================================
-- ТРИГГЕРЫ
-- =====================================================

-- Триггер для обновления updated_at в таблице hosts
DROP TRIGGER IF EXISTS update_hosts_updated_at ON vulnanalizer.hosts;
CREATE TRIGGER update_hosts_updated_at
    BEFORE UPDATE ON vulnanalizer.hosts
    FOR EACH ROW
    EXECUTE FUNCTION vulnanalizer.update_updated_at_column();

-- Триггер для обновления updated_at в таблице metasploit_modules
DROP TRIGGER IF EXISTS trigger_metasploit_updated_at ON vulnanalizer.metasploit_modules;
CREATE TRIGGER trigger_metasploit_updated_at
    BEFORE UPDATE ON vulnanalizer.metasploit_modules
    FOR EACH ROW
    EXECUTE FUNCTION update_metasploit_updated_at();

-- Триггер для обновления updated_at в таблице settings
DROP TRIGGER IF EXISTS update_settings_updated_at ON vulnanalizer.settings;
CREATE TRIGGER update_settings_updated_at
    BEFORE UPDATE ON vulnanalizer.settings
    FOR EACH ROW
    EXECUTE FUNCTION vulnanalizer.update_updated_at_column();

-- Триггер для обновления updated_at в таблице background_tasks
DROP TRIGGER IF EXISTS update_background_tasks_updated_at ON vulnanalizer.background_tasks;
CREATE TRIGGER update_background_tasks_updated_at
    BEFORE UPDATE ON vulnanalizer.background_tasks
    FOR EACH ROW
    EXECUTE FUNCTION vulnanalizer.update_updated_at_column();

-- Триггер для обновления updated_at в таблице epss
DROP TRIGGER IF EXISTS update_epss_updated_at ON vulnanalizer.epss;
CREATE TRIGGER update_epss_updated_at
    BEFORE UPDATE ON vulnanalizer.epss
    FOR EACH ROW
    EXECUTE FUNCTION vulnanalizer.update_updated_at_column();


-- =====================================================
-- НАСТРОЙКИ ПО УМОЛЧАНИЮ
-- =====================================================

-- Вставляем настройки ExploitDB
INSERT INTO vulnanalizer.settings (key, value) VALUES
    ('exdb_remote', '1.3'),
    ('exdb_webapps', '1.2'),
    ('exdb_dos', '0.85'),
    ('exdb_local', '1.05'),
    ('exdb_hardware', '1.0')
ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value;

-- Вставляем настройки Metasploit
INSERT INTO vulnanalizer.settings (key, value) VALUES
    ('msf_excellent', '1.3'),
    ('msf_good', '1.25'),
    ('msf_normal', '1.2'),
    ('msf_average', '1.1'),
    ('msf_low', '0.8'),
    ('msf_unknown', '1.0'),
    ('msf_manual', '1.0')
ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value;

-- Вставляем настройки Impact
INSERT INTO vulnanalizer.settings (key, value) VALUES
    ('impact_resource_criticality_critical', '0.33'),
    ('impact_resource_criticality_high', '0.25'),
    ('impact_resource_criticality_medium', '0.2'),
    ('impact_resource_criticality_none', '0.2'),
    ('impact_confidential_data_yes', '0.33'),
    ('impact_confidential_data_no', '0.2'),
    ('impact_internet_access_yes', '0.33'),
    ('impact_internet_access_no', '0.2')
ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value;

-- Вставляем настройки CVSS v3
INSERT INTO vulnanalizer.settings (key, value) VALUES
    ('cvss_v3_attack_vector_network', '1.2'),
    ('cvss_v3_attack_vector_adjacent', '1.1'),
    ('cvss_v3_attack_vector_local', '1.0'),
    ('cvss_v3_attack_vector_physical', '0.9'),
    ('cvss_v3_privileges_required_none', '1.2'),
    ('cvss_v3_privileges_required_low', '1.1'),
    ('cvss_v3_privileges_required_high', '1.0'),
    ('cvss_v3_user_interaction_none', '1.2'),
    ('cvss_v3_user_interaction_required', '1.0')
ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value;

-- Вставляем настройки CVSS v2
INSERT INTO vulnanalizer.settings (key, value) VALUES
    ('cvss_v2_access_vector_network', '1.2'),
    ('cvss_v2_access_vector_adjacent_network', '1.1'),
    ('cvss_v2_access_vector_local', '1.0'),
    ('cvss_v2_access_complexity_low', '1.2'),
    ('cvss_v2_access_complexity_medium', '1.1'),
    ('cvss_v2_access_complexity_high', '1.0'),
    ('cvss_v2_authentication_none', '1.2'),
    ('cvss_v2_authentication_single', '1.1'),
    ('cvss_v2_authentication_multiple', '1.0')
ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value;

-- Вставляем общие настройки
INSERT INTO vulnanalizer.settings (key, value) VALUES
    ('risk_threshold', '55'),
    ('max_concurrent_requests', '10')
ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value;

-- =====================================================
-- СХЕМА AUTH
-- =====================================================

-- Таблица пользователей
CREATE TABLE IF NOT EXISTS auth.users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    email VARCHAR(100),
    is_active BOOLEAN DEFAULT TRUE,
    is_admin BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Триггер для обновления updated_at в таблице users
DROP TRIGGER IF EXISTS update_users_updated_at ON auth.users;
CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON auth.users
    FOR EACH ROW
    EXECUTE FUNCTION vulnanalizer.update_updated_at_column();

-- =====================================================
-- СХЕМА LOGANALIZER
-- =====================================================

-- Таблица логов
CREATE TABLE IF NOT EXISTS loganalizer.logs (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    level VARCHAR(20) NOT NULL,
    message TEXT NOT NULL,
    source VARCHAR(100),
    hostname VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Таблица настроек loganalizer
CREATE TABLE IF NOT EXISTS loganalizer.settings (
    id SERIAL PRIMARY KEY,
    key VARCHAR(255) UNIQUE NOT NULL,
    value TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Таблица файлов логов
CREATE TABLE IF NOT EXISTS loganalizer.log_files (
    id VARCHAR(255) PRIMARY KEY,
    original_name VARCHAR(500) NOT NULL,
    file_path TEXT NOT NULL,
    file_type VARCHAR(50),
    file_size BIGINT,
    upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    parent_file_id VARCHAR(255),
    FOREIGN KEY (parent_file_id) REFERENCES loganalizer.log_files(id) ON DELETE CASCADE
);

-- Таблица пресетов анализа
CREATE TABLE IF NOT EXISTS loganalizer.analysis_presets (
    id VARCHAR(255) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    system_context TEXT,
    questions JSONB,
    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_default BOOLEAN DEFAULT FALSE
);

-- Таблица пользовательских настроек анализа
CREATE TABLE IF NOT EXISTS loganalizer.custom_analysis_settings (
    id VARCHAR(255) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    pattern TEXT NOT NULL,
    description TEXT,
    enabled BOOLEAN DEFAULT TRUE,
    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Таблица отфильтрованных файлов
CREATE TABLE IF NOT EXISTS loganalizer.filtered_files (
    id VARCHAR(255) PRIMARY KEY,
    original_file_id VARCHAR(255) NOT NULL,
    filtered_file_path TEXT NOT NULL,
    filter_settings JSONB,
    lines_count INTEGER,
    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (original_file_id) REFERENCES loganalizer.log_files(id) ON DELETE CASCADE
);

-- Индексы для таблицы logs
CREATE INDEX IF NOT EXISTS idx_logs_timestamp ON loganalizer.logs(timestamp);
CREATE INDEX IF NOT EXISTS idx_logs_level ON loganalizer.logs(level);
CREATE INDEX IF NOT EXISTS idx_logs_hostname ON loganalizer.logs(hostname);

-- Индексы для таблицы settings
CREATE INDEX IF NOT EXISTS idx_loganalizer_settings_key ON loganalizer.settings(key);

-- Индексы для таблицы log_files
CREATE INDEX IF NOT EXISTS idx_log_files_upload_date ON loganalizer.log_files(upload_date);
CREATE INDEX IF NOT EXISTS idx_log_files_file_type ON loganalizer.log_files(file_type);

-- Индексы для таблицы analysis_presets
CREATE INDEX IF NOT EXISTS idx_analysis_presets_name ON loganalizer.analysis_presets(name);
CREATE INDEX IF NOT EXISTS idx_analysis_presets_is_default ON loganalizer.analysis_presets(is_default);

-- Индексы для таблицы custom_analysis_settings
CREATE INDEX IF NOT EXISTS idx_custom_analysis_settings_name ON loganalizer.custom_analysis_settings(name);
CREATE INDEX IF NOT EXISTS idx_custom_analysis_settings_enabled ON loganalizer.custom_analysis_settings(enabled);

-- Индексы для таблицы filtered_files
CREATE INDEX IF NOT EXISTS idx_filtered_files_original_file_id ON loganalizer.filtered_files(original_file_id);
CREATE INDEX IF NOT EXISTS idx_filtered_files_created_date ON loganalizer.filtered_files(created_date);

-- Триггер для обновления updated_at в таблице loganalizer.settings
DROP TRIGGER IF EXISTS update_loganalizer_settings_updated_at ON loganalizer.settings;
CREATE TRIGGER update_loganalizer_settings_updated_at
    BEFORE UPDATE ON loganalizer.settings
    FOR EACH ROW
    EXECUTE FUNCTION vulnanalizer.update_updated_at_column();

-- =====================================================
-- ПРАВА ДОСТУПА
-- =====================================================

-- Предоставляем права пользователю stools_user
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA vulnanalizer TO stools_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA vulnanalizer TO stools_user;
GRANT ALL PRIVILEGES ON ALL FUNCTIONS IN SCHEMA vulnanalizer TO stools_user;

GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA auth TO stools_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA auth TO stools_user;

GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA loganalizer TO stools_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA loganalizer TO stools_user;

-- =====================================================
-- ЗАВЕРШЕНИЕ
-- =====================================================

-- Обновляем статистику
ANALYZE;

-- Выводим информацию о созданных объектах
SELECT 
    schemaname,
    tablename,
    tableowner
FROM pg_tables 
WHERE schemaname IN ('vulnanalizer', 'auth', 'loganalizer')
ORDER BY schemaname, tablename;

-- Выводим количество настроек
SELECT COUNT(*) as settings_count FROM vulnanalizer.settings;

-- Сообщение об успешном завершении
DO $$
BEGIN
    RAISE NOTICE '✅ Единый скрипт инициализации базы данных выполнен успешно!';
    RAISE NOTICE '📊 Созданы схемы: vulnanalizer, auth, loganalizer';
    RAISE NOTICE '🗃️ Созданы все необходимые таблицы, индексы и триггеры';
    RAISE NOTICE '⚙️ Вставлены настройки по умолчанию';
    RAISE NOTICE '🔐 Настроены права доступа';
END $$;
