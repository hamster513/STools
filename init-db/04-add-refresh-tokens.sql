-- Создание таблицы для refresh токенов
-- Этот скрипт добавляет поддержку JWT refresh токенов

-- Создаем схему auth если её нет
CREATE SCHEMA IF NOT EXISTS auth;

-- Создаем таблицу для refresh токенов
CREATE TABLE IF NOT EXISTS auth.refresh_tokens (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    token TEXT NOT NULL UNIQUE,
    expires_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Создаем индекс для быстрого поиска по user_id
CREATE INDEX IF NOT EXISTS idx_refresh_tokens_user_id ON auth.refresh_tokens(user_id);

-- Создаем индекс для быстрого поиска по токену
CREATE INDEX IF NOT EXISTS idx_refresh_tokens_token ON auth.refresh_tokens(token);

-- Добавляем комментарии
COMMENT ON TABLE auth.refresh_tokens IS 'Таблица для хранения JWT refresh токенов';
COMMENT ON COLUMN auth.refresh_tokens.user_id IS 'ID пользователя';
COMMENT ON COLUMN auth.refresh_tokens.token IS 'Refresh токен';
COMMENT ON COLUMN auth.refresh_tokens.expires_at IS 'Время истечения токена';
COMMENT ON COLUMN auth.refresh_tokens.created_at IS 'Время создания токена';
COMMENT ON COLUMN auth.refresh_tokens.updated_at IS 'Время последнего обновления токена';
