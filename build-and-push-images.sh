#!/bin/bash

# Скрипт для сборки и публикации Docker образов STools для linux/amd64
set -e

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Читаем версию
VERSION=$(cat VERSION 2>/dev/null || echo "0.7.10")
DOCKER_USERNAME="hamster5133"
PLATFORM="linux/amd64"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Сборка Docker образов STools${NC}"
echo -e "${BLUE}  Версия: ${VERSION}${NC}"
echo -e "${BLUE}  Платформа: ${PLATFORM}${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Проверяем авторизацию в Docker Hub
echo -e "${YELLOW}→${NC} Проверка авторизации в Docker Hub..."
if ! grep -q "index.docker.io" ~/.docker/config.json 2>/dev/null; then
    echo -e "${YELLOW}⚠${NC}  Требуется авторизация в Docker Hub"
    echo -e "${YELLOW}→${NC} Выполните: docker login"
    exit 1
fi
echo -e "${GREEN}✓${NC} Авторизация подтверждена"
echo ""

# Функция для сборки и публикации образа
build_and_push() {
    local service=$1
    local dockerfile=$2
    local context=$3
    local image_name="${DOCKER_USERNAME}/stools-${service}:v${VERSION}"
    
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}  Сборка: ${service}${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${YELLOW}→${NC} Dockerfile: ${dockerfile}"
    echo -e "${YELLOW}→${NC} Context: ${context}"
    echo -e "${YELLOW}→${NC} Image: ${image_name}"
    echo ""
    
    # Сборка образа для linux/amd64
    echo -e "${YELLOW}→${NC} Сборка образа..."
    if docker buildx build \
        --platform ${PLATFORM} \
        -f ${dockerfile} \
        -t ${image_name} \
        --load \
        ${context}; then
        echo -e "${GREEN}✓${NC} Образ собран успешно"
    else
        echo -e "${RED}✗${NC} Ошибка сборки образа ${service}"
        return 1
    fi
    
    # Публикация образа
    echo -e "${YELLOW}→${NC} Публикация образа в Docker Hub..."
    if docker push ${image_name}; then
        echo -e "${GREEN}✓${NC} Образ опубликован: ${image_name}"
    else
        echo -e "${RED}✗${NC} Ошибка публикации образа ${service}"
        return 1
    fi
    
    echo ""
}

# Проверяем наличие buildx
if ! docker buildx version &> /dev/null; then
    echo -e "${RED}✗${NC} Docker buildx не установлен"
    echo -e "${YELLOW}→${NC} Установите buildx: https://docs.docker.com/buildx/working-with-buildx/"
    exit 1
fi

# Создаем builder для мультиплатформенной сборки
echo -e "${YELLOW}→${NC} Настройка buildx..."
docker buildx create --name multiplatform --use 2>/dev/null || docker buildx use multiplatform
docker buildx inspect --bootstrap
echo ""

# 1. Auth Service
build_and_push "auth_web" "auth/Dockerfile" "auth"

# 2. VulnAnalizer Web
build_and_push "vulnanalizer_web" "vulnanalizer/app/Dockerfile" "vulnanalizer/app"

# 3. VulnAnalizer Worker
build_and_push "vulnanalizer_worker" "vulnanalizer/app/Dockerfile.worker" "vulnanalizer/app"

# 4. Main Web
build_and_push "main_web" "Dockerfile" "."

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Все образы успешно собраны и опубликованы!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${BLUE}Опубликованные образы:${NC}"
echo -e "  • ${DOCKER_USERNAME}/stools-auth_web:v${VERSION}"
echo -e "  • ${DOCKER_USERNAME}/stools-vulnanalizer_web:v${VERSION}"
echo -e "  • ${DOCKER_USERNAME}/stools-vulnanalizer_worker:v${VERSION}"
echo -e "  • ${DOCKER_USERNAME}/stools-main_web:v${VERSION}"
echo ""
echo -e "${YELLOW}Для использования обновите версии в docker-compose.yml${NC}"
echo ""


