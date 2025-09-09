-- Создание таблиц для аудита и логирования действий пользователей
CREATE SCHEMA IF NOT EXISTS auth;

-- Таблица аудита действий пользователей
CREATE TABLE IF NOT EXISTS auth.audit_logs (
    id SERIAL PRIMARY KEY,
    user_id INT,
    username VARCHAR(50),
    action VARCHAR(100) NOT NULL,
    resource VARCHAR(50) NOT NULL,
    resource_id VARCHAR(100),
    details JSONB,
    ip_address INET,
    user_agent TEXT,
    session_id VARCHAR(255),
    success BOOLEAN DEFAULT TRUE,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Таблица сессий пользователей
CREATE TABLE IF NOT EXISTS auth.user_sessions (
    id SERIAL PRIMARY KEY,
    user_id INT NOT NULL,
    session_id VARCHAR(255) NOT NULL UNIQUE,
    ip_address INET,
    user_agent TEXT,
    login_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_activity TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    logout_at TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN DEFAULT TRUE,
    FOREIGN KEY (user_id) REFERENCES auth.users (id) ON DELETE CASCADE
);

-- Таблица попыток входа
CREATE TABLE IF NOT EXISTS auth.login_attempts (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50),
    ip_address INET,
    user_agent TEXT,
    success BOOLEAN NOT NULL,
    failure_reason VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Индексы для производительности
CREATE INDEX IF NOT EXISTS idx_audit_logs_user_id ON auth.audit_logs (user_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_action ON auth.audit_logs (action);
CREATE INDEX IF NOT EXISTS idx_audit_logs_resource ON auth.audit_logs (resource);
CREATE INDEX IF NOT EXISTS idx_audit_logs_created_at ON auth.audit_logs (created_at);
CREATE INDEX IF NOT EXISTS idx_audit_logs_ip_address ON auth.audit_logs (ip_address);

CREATE INDEX IF NOT EXISTS idx_user_sessions_user_id ON auth.user_sessions (user_id);
CREATE INDEX IF NOT EXISTS idx_user_sessions_session_id ON auth.user_sessions (session_id);
CREATE INDEX IF NOT EXISTS idx_user_sessions_is_active ON auth.user_sessions (is_active);
CREATE INDEX IF NOT EXISTS idx_user_sessions_last_activity ON auth.user_sessions (last_activity);

CREATE INDEX IF NOT EXISTS idx_login_attempts_username ON auth.login_attempts (username);
CREATE INDEX IF NOT EXISTS idx_login_attempts_ip_address ON auth.login_attempts (ip_address);
CREATE INDEX IF NOT EXISTS idx_login_attempts_created_at ON auth.login_attempts (created_at);
CREATE INDEX IF NOT EXISTS idx_login_attempts_success ON auth.login_attempts (success);

-- Комментарии к таблицам
COMMENT ON TABLE auth.audit_logs IS 'Таблица аудита действий пользователей';
COMMENT ON TABLE auth.user_sessions IS 'Таблица активных сессий пользователей';
COMMENT ON TABLE auth.login_attempts IS 'Таблица попыток входа в систему';

-- Комментарии к полям
COMMENT ON COLUMN auth.audit_logs.user_id IS 'ID пользователя (может быть NULL для системных действий)';
COMMENT ON COLUMN auth.audit_logs.username IS 'Имя пользователя (для быстрого поиска)';
COMMENT ON COLUMN auth.audit_logs.action IS 'Действие (login, logout, create, update, delete, etc.)';
COMMENT ON COLUMN auth.audit_logs.resource IS 'Ресурс (users, roles, permissions, etc.)';
COMMENT ON COLUMN auth.audit_logs.resource_id IS 'ID ресурса (может быть NULL)';
COMMENT ON COLUMN auth.audit_logs.details IS 'Дополнительные детали в JSON формате';
COMMENT ON COLUMN auth.audit_logs.ip_address IS 'IP адрес пользователя';
COMMENT ON COLUMN auth.audit_logs.user_agent IS 'User Agent браузера';
COMMENT ON COLUMN auth.audit_logs.session_id IS 'ID сессии';
COMMENT ON COLUMN auth.audit_logs.success IS 'Успешность операции';
COMMENT ON COLUMN auth.audit_logs.error_message IS 'Сообщение об ошибке (если операция неуспешна)';

COMMENT ON COLUMN auth.user_sessions.session_id IS 'Уникальный идентификатор сессии';
COMMENT ON COLUMN auth.user_sessions.ip_address IS 'IP адрес пользователя';
COMMENT ON COLUMN auth.user_sessions.user_agent IS 'User Agent браузера';
COMMENT ON COLUMN auth.user_sessions.login_at IS 'Время входа';
COMMENT ON COLUMN auth.user_sessions.last_activity IS 'Время последней активности';
COMMENT ON COLUMN auth.user_sessions.logout_at IS 'Время выхода (NULL если сессия активна)';
COMMENT ON COLUMN auth.user_sessions.is_active IS 'Активна ли сессия';

COMMENT ON COLUMN auth.login_attempts.username IS 'Имя пользователя (может быть NULL)';
COMMENT ON COLUMN auth.login_attempts.ip_address IS 'IP адрес';
COMMENT ON COLUMN auth.login_attempts.user_agent IS 'User Agent браузера';
COMMENT ON COLUMN auth.login_attempts.success IS 'Успешность попытки входа';
COMMENT ON COLUMN auth.login_attempts.failure_reason IS 'Причина неудачи (invalid_credentials, user_disabled, etc.)';
