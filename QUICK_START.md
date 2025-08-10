# 🚀 Быстрый старт STools

## 📋 Требования

- Docker и Docker Compose
- Git
- OpenSSL (для генерации сертификатов)

## ⚡ Быстрая установка

### 1. Клонирование проекта
```bash
git clone https://github.com/hamster513/STools.git
cd STools
```

### 2. Автоматическая инициализация
```bash
./init_project.sh
```

Этот скрипт автоматически:
- ✅ Создает файл `.env` из `env.example`
- ✅ Генерирует SSL сертификат с именем вашего сервера
- ✅ Проверяет наличие Docker
- ✅ Опционально запускает проект

### 3. Ручная настройка (если нужно)

#### Создание .env файла:
```bash
cp env.example .env
```

#### Генерация SSL сертификата:
```bash
./generate_ssl_cert.sh
```

#### Запуск проекта:
```bash
docker-compose -f docker-compose.prod.yml up -d
```

## 🌐 Доступ к сервисам

После запуска доступны:

- **VulnAnalizer**: `https://localhost/vulnanalizer/`
- **LogAnalizer**: `https://localhost/loganalizer/`
- **Auth**: `https://localhost/auth/`

## 🔧 Полезные команды

```bash
# Просмотр статуса
docker-compose -f docker-compose.prod.yml ps

# Просмотр логов
docker-compose -f docker-compose.prod.yml logs -f

# Остановка
docker-compose -f docker-compose.prod.yml down

# Перезапуск
docker-compose -f docker-compose.prod.yml restart

# Обновление SSL сертификата
./generate_ssl_cert.sh
```

## 🔐 SSL сертификат

- **Автоматическая генерация**: при первом запуске `init_project.sh`
- **Ручная генерация**: `./generate_ssl_cert.sh`
- **Местоположение**: `nginx/ssl/certificate.crt` и `nginx/ssl/private.key`
- **Срок действия**: 365 дней
- **Common Name**: автоматически определяется как имя сервера

## 📝 Настройка портов

По умолчанию используются стандартные порты:
- **HTTP**: 80
- **HTTPS**: 443

Для изменения портов отредактируйте `.env`:
```env
NGINX_HTTP_PORT=8080
NGINX_HTTPS_PORT=8443
```

## 🆘 Устранение проблем

### SSL сертификат не работает
```bash
# Пересоздать сертификат
./generate_ssl_cert.sh

# Перезапустить nginx
docker-compose -f docker-compose.prod.yml restart nginx
```

### Порт занят
```bash
# Проверить, что использует порт
lsof -i :80
lsof -i :443

# Изменить порты в .env и перезапустить
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml up -d
```

### Образы не скачиваются
```bash
# Проверить подключение к интернету
ping docker.io

# Попробовать локальную сборку
docker-compose build
docker-compose up -d
```

## 📚 Дополнительная документация

- [Полное руководство по развертыванию](DEPLOYMENT_GUIDE.md)
- [Статус проектов](PROJECTS_STATUS.md)
- [Оптимизация производительности](PERFORMANCE_OPTIMIZATION.md) 