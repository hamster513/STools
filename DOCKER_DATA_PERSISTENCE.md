# 🐳 Персистентность данных в Docker

## 📋 Обзор

В проекте STools используется Docker с именованными volumes для обеспечения персистентности данных. Все базы данных и файлы приложений сохраняются между перезапусками контейнеров.

## 🗄️ Структура Volumes

### Именованные Volumes
```bash
# Список всех volumes проекта
docker volume ls | grep stools

# Результат:
local     stools_app_data
local     stools_auth_data
local     stools_auth_postgres_data
local     stools_loganalizer_data
local     stools_loganalizer_postgres_data
local     stools_postgres_data
local     stools_redis_data
local     stools_vulnanalizer_data
local     stools_vulnanalizer_postgres_data
```

### Назначение Volumes

| Volume | Назначение | Контейнер |
|--------|------------|-----------|
| `stools_vulnanalizer_postgres_data` | База данных VulnAnalizer | `vulnanalizer_postgres` |
| `stools_loganalizer_postgres_data` | База данных LogAnalizer | `loganalizer_postgres` |
| `stools_auth_postgres_data` | База данных Auth | `auth_postgres` |
| `stools_redis_data` | Кэш Redis | `stools_redis` |
| `stools_vulnanalizer_data` | Файлы VulnAnalizer | `vulnanalizer_web` |
| `stools_loganalizer_data` | Файлы LogAnalizer | `loganalizer_web` |
| `stools_auth_data` | Файлы Auth | `auth_web` |

## 🔧 Управление данными

### Проверка персистентности
```bash
# Запуск автоматической проверки
./check_persistence.sh
```

### Ручная проверка данных
```bash
# VulnAnalizer
docker-compose exec vulnanalizer_postgres psql -U vulnanalizer -d vulnanalizer -c "SELECT COUNT(*) FROM hosts;"

# LogAnalizer
docker-compose exec loganalizer_postgres psql -U loganalizer_user -d loganalizer_db -c "SELECT COUNT(*) FROM log_files;"

# Auth
docker-compose exec auth_postgres psql -U auth_user -d auth_db -c "SELECT COUNT(*) FROM users;"
```

### Резервное копирование
```bash
# Создание резервной копии VulnAnalizer
docker-compose exec vulnanalizer_postgres pg_dump -U vulnanalizer vulnanalizer > backup_vulnanalizer.sql

# Создание резервной копии LogAnalizer
docker-compose exec loganalizer_postgres pg_dump -U loganalizer_user loganalizer_db > backup_loganalizer.sql

# Создание резервной копии Auth
docker-compose exec auth_postgres pg_dump -U auth_user auth_db > backup_auth.sql
```

### Восстановление из резервной копии
```bash
# Восстановление VulnAnalizer
docker-compose exec -T vulnanalizer_postgres psql -U vulnanalizer vulnanalizer < backup_vulnanalizer.sql

# Восстановление LogAnalizer
docker-compose exec -T loganalizer_postgres psql -U loganalizer_user loganalizer_db < backup_loganalizer.sql

# Восстановление Auth
docker-compose exec -T auth_postgres psql -U auth_user auth_db < backup_auth.sql
```

## 🚨 Важные моменты

### 1. Инициализация базы данных
- **VulnAnalizer**: Использует SQL файлы в `vulnanalizer/init-db/`
- **LogAnalizer**: Использует код Python в `loganalizer/app/database.py`
- **Auth**: Использует код Python в `auth/database.py`

### 2. Перезапуск контейнеров
```bash
# Безопасный перезапуск (данные сохраняются)
docker-compose restart vulnanalizer_postgres
docker-compose restart loganalizer_postgres
docker-compose restart auth_postgres

# Полная остановка и запуск (данные сохраняются)
docker-compose down
docker-compose up -d
```

### 3. Очистка данных
```bash
# ⚠️ ОСТОРОЖНО! Удаляет все данные
docker-compose down -v  # Удаляет volumes
docker volume rm stools_vulnanalizer_postgres_data
docker volume rm stools_loganalizer_postgres_data
docker volume rm stools_auth_postgres_data
```

## 🔍 Диагностика проблем

### Проверка состояния volumes
```bash
# Информация о volume
docker volume inspect stools_vulnanalizer_postgres_data

# Размер данных
docker system df -v
```

### Проверка логов
```bash
# Логи PostgreSQL
docker-compose logs vulnanalizer_postgres
docker-compose logs loganalizer_postgres
docker-compose logs auth_postgres

# Логи приложений
docker-compose logs vulnanalizer_web
docker-compose logs loganalizer_web
docker-compose logs auth_web
```

### Проверка подключения к базе
```bash
# Тест подключения VulnAnalizer
docker-compose exec vulnanalizer_postgres psql -U vulnanalizer -d vulnanalizer -c "SELECT version();"

# Тест подключения LogAnalizer
docker-compose exec loganalizer_postgres psql -U loganalizer_user -d loganalizer_db -c "SELECT version();"

# Тест подключения Auth
docker-compose exec auth_postgres psql -U auth_user -d auth_db -c "SELECT version();"
```

## 📊 Мониторинг

### Автоматическая проверка
```bash
# Создание cron задачи для ежедневной проверки
echo "0 2 * * * cd /path/to/STools && ./check_persistence.sh >> /var/log/stools_persistence.log 2>&1" | crontab -
```

### Алерты
- Если данные не сохраняются при перезапуске
- Если размер volume неожиданно изменился
- Если контейнеры не могут подключиться к базе данных

## 🛠️ Устранение неполадок

### Проблема: Данные не сохраняются
1. Проверьте, что volumes созданы: `docker volume ls | grep stools`
2. Проверьте права доступа к volumes
3. Убедитесь, что контейнеры используют правильные volumes

### Проблема: База данных не инициализируется
1. Проверьте файлы инициализации в `init-db/`
2. Проверьте логи PostgreSQL
3. Убедитесь, что переменные окружения корректны

### Проблема: Контейнеры не запускаются
1. Проверьте, что порты не заняты
2. Проверьте логи контейнеров
3. Убедитесь, что все зависимости доступны

## 📝 Заключение

При правильной настройке Docker volumes данные сохраняются между перезапусками. Используйте предоставленные скрипты для проверки и управления данными.
