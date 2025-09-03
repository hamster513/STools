#!/bin/bash

# Скрипт для загрузки всех образов STools в Docker Hub

set -e

# Конфигурация
DOCKER_USERNAME="hamster5133"
VERSION="0.6.03"
LATEST_TAG="latest"
VERSION_TAG="v${VERSION}"

echo "🚀 Начинаем загрузку всех образов STools в Docker Hub"
echo "👤 Пользователь: ${DOCKER_USERNAME}"
echo "📦 Версия: ${VERSION}"
echo "🏷️  Теги: ${VERSION_TAG}, ${LATEST_TAG}"

# Массив образов для загрузки
IMAGES=(
    "stools-auth_web:${VERSION_TAG}"
    "stools-loganalizer_web:${VERSION_TAG}"
    "stools-vulnanalizer_web:${VERSION_TAG}"
    "stools-main_web:${VERSION_TAG}"
)

# Переименовываем и загружаем каждый образ
for local_image in "${IMAGES[@]}"; do
    # Извлекаем имя образа без тега
    image_name=$(echo $local_image | cut -d':' -f1)
    
    # Создаем полное имя для Docker Hub
    hub_image="${DOCKER_USERNAME}/${image_name}"
    
    echo "📤 Загружаем ${local_image} как ${hub_image}:${VERSION_TAG}"
    
    # Переименовываем образ
    docker tag ${local_image} ${hub_image}:${VERSION_TAG}
    docker tag ${local_image} ${hub_image}:${LATEST_TAG}
    
    # Загружаем образ
    docker push ${hub_image}:${VERSION_TAG}
    docker push ${hub_image}:${LATEST_TAG}
    
    echo "✅ ${image_name} загружен успешно!"
done

echo "🎉 Все образы загружены в Docker Hub!"
echo "🔗 Доступны по адресу: https://hub.docker.com/r/${DOCKER_USERNAME}"
echo "📋 Команды для запуска:"
for local_image in "${IMAGES[@]}"; do
    image_name=$(echo $local_image | cut -d':' -f1)
    hub_image="${DOCKER_USERNAME}/${image_name}"
    echo "   docker run -p 8000:8000 ${hub_image}:${VERSION_TAG}"
done
