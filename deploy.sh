#!/bin/bash

# Скрипт для развертывания STools v0.7.00 на удаленном сервере

set -e

echo "🚀 Развертывание STools v0.7.00"

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
docker-compose -f $COMPOSE_FILE down || true

# Удаляем старые образы
echo "🗑️  Удаление старых образов..."
docker image prune -f || true

# Создаем необходимые директории
echo "📁 Создание директорий..."
mkdir -p backups
mkdir -p nginx/ssl

# Загружаем новые образы
echo "⬇️  Загрузка образов v0.7.00..."
docker pull hamster5133/stools-auth_web:v0.7.00
docker pull hamster5133/stools-loganalizer_web:v0.7.00
docker pull hamster5133/stools-vulnanalizer_web:v0.7.00
docker pull hamster5133/stools-main_web:v0.7.00

# Запускаем контейнеры
echo "🚀 Запуск контейнеров..."
docker-compose -f $COMPOSE_FILE up -d

# Ждем запуска
echo "⏳ Ожидание запуска сервисов..."
sleep 30

# Проверяем статус
echo "📊 Статус контейнеров:"
docker-compose -f $COMPOSE_FILE ps

echo "✅ Развертывание завершено!"
echo "🌐 Приложение доступно по адресу: http://localhost"
echo "📊 VulnAnalizer: http://localhost/vulnanalizer"
echo "📋 LogAnalizer: http://localhost/loganalizer"
