#!/bin/bash

# Скрипт для сборки и загрузки Docker образа VulnAnalizer

set -e

# Конфигурация
IMAGE_NAME="hamster513/vulnanalizer"
VERSION=$(cat vulnanalizer/app/VERSION)
LATEST_TAG="latest"
VERSION_TAG="v${VERSION}"

echo "🚀 Начинаем сборку и загрузку VulnAnalizer"
echo "📦 Версия: ${VERSION}"
echo "🏷️  Теги: ${VERSION_TAG}, ${LATEST_TAG}"

# Переходим в директорию приложения
cd vulnanalizer/app

# Сборка образа
echo "🔨 Сборка Docker образа..."
docker build -t ${IMAGE_NAME}:${VERSION_TAG} .
docker tag ${IMAGE_NAME}:${VERSION_TAG} ${IMAGE_NAME}:${LATEST_TAG}

echo "✅ Образ собран успешно"

# Проверяем, авторизованы ли мы в Docker Hub
if ! docker info | grep -q "Username"; then
    echo "⚠️  Не авторизованы в Docker Hub. Выполните: docker login"
    echo "📤 Пропускаем загрузку образа"
    exit 0
fi

# Загрузка образа
echo "📤 Загрузка образа в Docker Hub..."
docker push ${IMAGE_NAME}:${VERSION_TAG}
docker push ${IMAGE_NAME}:${LATEST_TAG}

echo "✅ Образ загружен успешно!"
echo "🔗 Доступен по адресу: https://hub.docker.com/r/${IMAGE_NAME}"
echo "📋 Команда для запуска:"
echo "   docker run -p 8000:8000 ${IMAGE_NAME}:${VERSION_TAG}"
