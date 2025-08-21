-- Инициализация единой базы данных STools
-- Создание схем для разных сервисов

-- Схема для аутентификации
CREATE SCHEMA IF NOT EXISTS auth;

-- Схема для LogAnalizer
CREATE SCHEMA IF NOT EXISTS loganalizer;

-- Схема для VulnAnalizer
CREATE SCHEMA IF NOT EXISTS vulnanalizer;

-- Создание единого пользователя для всех сервисов
DO $$
BEGIN
    -- Создаем пользователя stools_user
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'stools_user') THEN
        CREATE USER stools_user WITH PASSWORD 'stools_pass';
    END IF;
END
$$;

-- Предоставление прав доступа ко всем схемам
GRANT USAGE ON SCHEMA auth TO stools_user;
GRANT USAGE ON SCHEMA loganalizer TO stools_user;
GRANT USAGE ON SCHEMA vulnanalizer TO stools_user;

-- Права на создание таблиц во всех схемах
GRANT CREATE ON SCHEMA auth TO stools_user;
GRANT CREATE ON SCHEMA loganalizer TO stools_user;
GRANT CREATE ON SCHEMA vulnanalizer TO stools_user;

-- Права на все будущие таблицы во всех схемах
ALTER DEFAULT PRIVILEGES IN SCHEMA auth GRANT ALL ON TABLES TO stools_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA loganalizer GRANT ALL ON TABLES TO stools_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA vulnanalizer GRANT ALL ON TABLES TO stools_user;

-- Права на последовательности
ALTER DEFAULT PRIVILEGES IN SCHEMA auth GRANT ALL ON SEQUENCES TO stools_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA loganalizer GRANT ALL ON SEQUENCES TO stools_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA vulnanalizer GRANT ALL ON SEQUENCES TO stools_user;