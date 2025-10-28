#!/bin/bash

# Скрипт для развертывания STools v0.8.1 на удаленном сервере

set -e

echo "🚀 Развертывание STools v0.8.1"

# Устанавливаем переменные окружения
export COMPOSE_PROJECT_NAME=stools
export STOOLS_VERSION=0.8.1

# Проверяем архитектуру
ARCH=$(uname -m)
if [[ "$ARCH" == "arm64" ]]; then
    COMPOSE_FILE="docker-compose.arm.yml"
    echo "🍎 Обнаружена архитектура ARM64"
elif [[ "$ARCH" == "x86_64" ]]; then
    COMPOSE_FILE="docker-compose.x86.yml"
    echo "🐧 Обнаружена архитектура x86_64"
else
    echo "❌ Неподдерживаемая архитектура: $ARCH"
    exit 1
fi

echo "📁 Используется файл конфигурации: $COMPOSE_FILE"

# Останавливаем старые контейнеры
echo "🛑 Остановка старых контейнеров..."
docker-compose -f $COMPOSE_FILE -p stools down || true

# Удаляем все контейнеры проекта
echo "🗑️  Удаление всех контейнеров проекта..."
docker container prune -f || true

# Удаляем старые образы
echo "🗑️  Удаление старых образов..."
docker image prune -a -f || true


# Создаем необходимые директории
echo "📁 Создание директорий..."
mkdir -p backups
mkdir -p nginx/ssl
mkdir -p data/logs
mkdir -p data/vm_imports

# Устанавливаем правильные права доступа
echo "🔐 Установка прав доступа..."
chmod -R 777 data/ backups/

# Загружаем новые образы
echo "⬇️  Загрузка образов v0.8.1..."
docker pull hamster5133/stools-auth_web:v0.8.1
docker pull hamster5133/stools-vulnanalizer_web:v0.8.1
docker pull hamster5133/stools-main_web:v0.8.1

# Запускаем контейнеры
echo "🚀 Запуск контейнеров..."
docker-compose -f $COMPOSE_FILE -p stools up -d

# Ждем запуска
echo "⏳ Ожидание запуска сервисов..."
sleep 30

# Применяем миграции базы данных
echo "🗄️  Применение миграций базы данных..."
if [ -f "./apply_migrations.sh" ]; then
    chmod +x ./apply_migrations.sh
    ./apply_migrations.sh
else
    echo "⚠️  Скрипт apply_migrations.sh не найден, пропускаем миграции"
fi

# Проверяем статус
echo "📊 Статус контейнеров:"
docker-compose -f $COMPOSE_FILE -p stools ps

echo "✅ Развертывание завершено!"
echo "🌐 Приложение доступно по адресу: http://localhost"
echo "📊 VulnAnalizer: http://localhost/vulnanalizer"
