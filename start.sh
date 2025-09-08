#!/bin/bash

# Скрипт для автоматического запуска Docker Compose с правильной архитектурой

ARCH=$(uname -m)

if [[ "$ARCH" == "arm64" ]]; then
    COMPOSE_FILE="docker-compose.arm.yml"
    echo "🍎 Обнаружена архитектура ARM64 (macOS)"
elif [[ "$ARCH" == "x86_64" ]]; then
    COMPOSE_FILE="docker-compose.x86.yml"
    echo "🐧 Обнаружена архитектура x86_64 (Linux)"
else
    echo "❌ Неподдерживаемая архитектура: $ARCH"
    echo "Поддерживаемые архитектуры: arm64, x86_64"
    exit 1
fi

echo "📁 Используется файл конфигурации: $COMPOSE_FILE"
echo "🚀 Запуск контейнеров..."

docker-compose -f $COMPOSE_FILE up -d

if [ $? -eq 0 ]; then
    echo "✅ Контейнеры успешно запущены!"
    echo "📊 Статус контейнеров:"
    docker-compose -f $COMPOSE_FILE ps
else
    echo "❌ Ошибка при запуске контейнеров"
    exit 1
fi
