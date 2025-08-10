# 🚀 Руководство по развертыванию STools

## 📋 Требования к системе

### Минимальные требования:
- **ОС:** Linux (Ubuntu 20.04+, CentOS 8+, RHEL 8+) или macOS 10.15+
- **RAM:** 4 GB (рекомендуется 8 GB)
- **Диск:** 20 GB свободного места
- **Docker:** 20.10+
- **Docker Compose:** 2.0+

### Рекомендуемые требования:
- **ОС:** Ubuntu 22.04 LTS
- **RAM:** 16 GB
- **Диск:** 50 GB SSD
- **Docker:** 24.0+
- **Docker Compose:** 2.20+

## 🔧 Установка зависимостей

### 1. Установка Docker

#### Ubuntu/Debian:
```bash
# Обновляем пакеты
sudo apt update

# Устанавливаем необходимые пакеты
sudo apt install -y apt-transport-https ca-certificates curl gnupg lsb-release

# Добавляем GPG ключ Docker
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

# Добавляем репозиторий Docker
echo "deb [arch=amd64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Устанавливаем Docker
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Добавляем пользователя в группу docker
sudo usermod -aG docker $USER

# Запускаем Docker
sudo systemctl start docker
sudo systemctl enable docker
```

#### CentOS/RHEL:
```bash
# Устанавливаем необходимые пакеты
sudo yum install -y yum-utils

# Добавляем репозиторий Docker
sudo yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo

# Устанавливаем Docker
sudo yum install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Запускаем Docker
sudo systemctl start docker
sudo systemctl enable docker

# Добавляем пользователя в группу docker
sudo usermod -aG docker $USER
```

#### macOS:
```bash
# Устанавливаем Homebrew (если не установлен)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Устанавливаем Docker Desktop
brew install --cask docker
```

### 2. Установка Git

#### Ubuntu/Debian:
```bash
sudo apt install -y git
```

#### CentOS/RHEL:
```bash
sudo yum install -y git
```

#### macOS:
```bash
brew install git
```

## 📥 Клонирование проекта

```bash
# Клонируем репозиторий
git clone https://github.com/hamster513/STools.git
cd STools
```
```

# Проверяем структуру проекта
ls -la
```

## 🐳 Сборка Docker образов (опционально)

Если вы хотите собрать образы локально или опубликовать их в Docker Hub:

```bash
# Делаем скрипт исполняемым
chmod +x build_images.sh

# Сборка образов локально
./build_images.sh

# Сборка и публикация в Docker Hub
./build_images.sh push
```

**Примечание:** Готовые образы уже доступны в Docker Hub под тегом `hamster5133/stools-*:latest`

## ⚙️ Настройка окружения

### 1. Автоматическая инициализация (рекомендуется)

```bash
# Запускаем автоматическую инициализацию
./init_project.sh
```

Этот скрипт автоматически:
- Создает файл `.env` из `env.example`
- Генерирует SSL сертификат с именем текущего сервера
- Проверяет наличие Docker и Docker Compose
- Опционально запускает проект

### 2. Ручная настройка

#### 2.1. Создание файла конфигурации

```bash
# Копируем пример конфигурации
cp env.example .env

# Редактируем конфигурацию
nano .env
```

#### 2.2. Генерация SSL сертификата

```bash
# Генерируем SSL сертификат с именем текущего сервера
./generate_ssl_cert.sh
```

### 2. Основные параметры конфигурации

```env
# Основные настройки
COMPOSE_PROJECT_NAME=stools
DOMAIN=localhost

# Настройки PostgreSQL
POSTGRES_PASSWORD=your_secure_password
VULNANALIZER_DB_PASSWORD=your_vulnanalizer_password
LOGANALIZER_DB_PASSWORD=your_loganalizer_password
AUTH_DB_PASSWORD=your_auth_password

# Настройки Redis
REDIS_PASSWORD=your_redis_password

# Настройки безопасности
SECRET_KEY=your_secret_key_here
```

### 3. Настройка домена (опционально)

Если у вас есть домен, обновите `DOMAIN` в `.env`:
```env
DOMAIN=your-domain.com
```

## 🚀 Запуск проекта

### 1. Первоначальный запуск (с готовыми образами)

```bash
# Создаем и запускаем контейнеры с готовыми образами
docker-compose -f docker-compose.prod.yml up -d

# Проверяем статус контейнеров
docker-compose -f docker-compose.prod.yml ps

# Просматриваем логи
docker-compose -f docker-compose.prod.yml logs -f
```

### 2. Альтернативный запуск (сборка из исходников)

```bash
# Создаем и запускаем контейнеры с локальной сборкой
docker-compose up -d

# Проверяем статус контейнеров
docker-compose ps

# Просматриваем логи
docker-compose logs -f
```

### 2. Проверка работоспособности

```bash
# Проверяем доступность сервисов
curl http://localhost/vulnanalizer
curl http://localhost/loganalizer
curl http://localhost/auth
```

### 3. Проверка инициализации баз данных

```bash
# Базы данных инициализируются автоматически при первом запуске
# Проверяем состояние баз данных
docker-compose exec vulnanalizer_postgres psql -U vulnanalizer -d vulnanalizer -c "SELECT COUNT(*) FROM hosts;"
docker-compose exec vulnanalizer_postgres psql -U vulnanalizer -d vulnanalizer -c "SELECT COUNT(*) FROM settings;"
```

## 🔐 Настройка безопасности

### 1. Изменение паролей по умолчанию

```bash
# Генерируем новые пароли
openssl rand -base64 32
openssl rand -base64 32
openssl rand -base64 32

# Обновляем .env файл с новыми паролями
nano .env
```

### 2. Настройка SSL (для продакшена)

```bash
# Создаем директорию для SSL сертификатов
mkdir -p nginx/ssl

# Копируем ваши сертификаты
cp your-certificate.crt nginx/ssl/
cp your-private-key.key nginx/ssl/

# Обновляем nginx конфигурацию
nano nginx/nginx.conf
```

### 3. Настройка файрвола

```bash
# Открываем только необходимые порты
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw enable
```

## 📊 Мониторинг и логи

### 1. Просмотр логов

```bash
# Все сервисы
docker-compose logs -f

# Конкретный сервис
docker-compose logs -f vulnanalizer_web
docker-compose logs -f loganalizer_web
docker-compose logs -f nginx
```

### 2. Мониторинг ресурсов

```bash
# Использование ресурсов контейнерами
docker stats

# Использование диска
df -h

# Использование памяти
free -h
```

### 3. Проверка состояния баз данных

```bash
# VulnAnalizer
docker-compose exec vulnanalizer_postgres psql -U vulnanalizer -d vulnanalizer -c "SELECT COUNT(*) FROM hosts;"
docker-compose exec vulnanalizer_postgres psql -U vulnanalizer -d vulnanalizer -c "SELECT COUNT(*) FROM epss;"
docker-compose exec vulnanalizer_postgres psql -U vulnanalizer -d vulnanalizer -c "SELECT COUNT(*) FROM exploitdb;"

# LogAnalizer
docker-compose exec loganalizer_postgres psql -U loganalizer_user -d loganalizer_db -c "SELECT COUNT(*) FROM log_files;"
```

## 🔄 Управление проектом

### 1. Остановка сервисов

```bash
# Остановка всех сервисов
docker-compose down

# Остановка с удалением volumes (ОСТОРОЖНО!)
docker-compose down -v
```

### 2. Перезапуск сервисов

```bash
# Перезапуск всех сервисов
docker-compose restart

# Перезапуск конкретного сервиса
docker-compose restart vulnanalizer_web
```

### 3. Обновление проекта

```bash
# Останавливаем сервисы
docker-compose down

# Получаем обновления
git pull origin main

# Пересобираем и запускаем
docker-compose up -d --build
```

## 💾 Резервное копирование

### 1. Создание резервной копии

```bash
# Создаем директорию для бэкапов
mkdir -p backups/$(date +%Y%m%d)

# Бэкап VulnAnalizer
docker-compose exec vulnanalizer_postgres pg_dump -U vulnanalizer vulnanalizer > backups/$(date +%Y%m%d)/vulnanalizer_backup.sql

# Бэкап LogAnalizer
docker-compose exec loganalizer_postgres pg_dump -U loganalizer_user loganalizer_db > backups/$(date +%Y%m%d)/loganalizer_backup.sql

# Бэкап Auth
docker-compose exec auth_postgres pg_dump -U auth_user auth_db > backups/$(date +%Y%m%d)/auth_backup.sql

# Бэкап Docker volumes
docker run --rm -v stools_vulnanalizer_postgres_data:/data -v $(pwd)/backups/$(date +%Y%m%d):/backup alpine tar czf /backup/vulnanalizer_data.tar.gz -C /data .
docker run --rm -v stools_loganalizer_postgres_data:/data -v $(pwd)/backups/$(date +%Y%m%d):/backup alpine tar czf /backup/loganalizer_data.tar.gz -C /data .
```

### 2. Восстановление из резервной копии

```bash
# Останавливаем сервисы
docker-compose down

# Восстанавливаем VulnAnalizer
docker-compose exec vulnanalizer_postgres psql -U vulnanalizer -d vulnanalizer < backups/20241201/vulnanalizer_backup.sql

# Восстанавливаем LogAnalizer
docker-compose exec loganalizer_postgres psql -U loganalizer_user -d loganalizer_db < backups/20241201/loganalizer_backup.sql

# Восстанавливаем Auth
docker-compose exec auth_postgres psql -U auth_user -d auth_db < backups/20241201/auth_backup.sql

# Запускаем сервисы
docker-compose up -d
```

## 🛠️ Устранение неполадок

### 1. Проблемы с подключением к базам данных

```bash
# Проверяем статус PostgreSQL контейнеров
docker-compose ps | grep postgres

# Проверяем логи PostgreSQL
docker-compose logs vulnanalizer_postgres
docker-compose logs loganalizer_postgres
docker-compose logs auth_postgres

# Проверяем подключение к базе
docker-compose exec vulnanalizer_postgres psql -U vulnanalizer -d vulnanalizer -c "SELECT 1;"
```

### 2. Проблемы с веб-сервисами

```bash
# Проверяем статус веб-контейнеров
docker-compose ps | grep web

# Проверяем логи веб-сервисов
docker-compose logs vulnanalizer_web
docker-compose logs loganalizer_web
docker-compose logs nginx

# Проверяем доступность портов
netstat -tlnp | grep :80
netstat -tlnp | grep :443
```

### 3. Проблемы с памятью

```bash
# Проверяем использование памяти
docker stats --no-stream

# Очищаем неиспользуемые ресурсы
docker system prune -f
docker volume prune -f
```

### 4. Проблемы с дисковым пространством

```bash
# Проверяем использование диска
df -h
docker system df

# Очищаем неиспользуемые образы и контейнеры
docker system prune -a -f
```

## 📞 Поддержка

### Полезные команды для диагностики:

```bash
# Информация о системе
docker version
docker-compose version
docker info

# Статус всех сервисов
docker-compose ps

# Использование ресурсов
docker stats

# Проверка сетевых подключений
docker network ls
docker network inspect stools_default
```

### Логи и отладка:

```bash
# Подробные логи
docker-compose logs --tail=100 -f

# Логи конкретного сервиса
docker-compose logs vulnanalizer_web --tail=50

# Проверка конфигурации
docker-compose config
```

## 🎯 Быстрый старт (для опытных пользователей)

```bash
# 1. Клонирование
git clone https://github.com/hamster513/STools.git
cd STools

# 2. Настройка
cp env.example .env
nano .env  # Настройте пароли и домен

# 3. Запуск (с готовыми образами)
docker-compose -f docker-compose.prod.yml up -d

# 4. Проверка
curl http://localhost/vulnanalizer
curl http://localhost/loganalizer
curl http://localhost/auth

# 5. Проверка работоспособности
curl http://localhost/vulnanalizer
curl http://localhost/loganalizer
```

---

**Примечание:** Замените `your-domain.com` на ваш домен, если используете собственный домен.
