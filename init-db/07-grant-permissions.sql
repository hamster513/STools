-- Выдача прав на существующие таблицы в схемах для единого пользователя

-- Права для stools_user на все таблицы во всех схемах
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA auth TO stools_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA auth TO stools_user;

GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA loganalizer TO stools_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA loganalizer TO stools_user;

GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA vulnanalizer TO stools_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA vulnanalizer TO stools_user;
