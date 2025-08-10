#!/bin/bash

# Скрипт для сборки и публикации Docker образов STools
# Использование: ./build_images.sh [push]

set -e  # Остановка при ошибке

# Конфигурация
DOCKER_USERNAME="hamster5133"
VERSION="latest"

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🐳 Сборка Docker образов STools${NC}"
echo "=========================================="

# Проверяем, что Docker запущен
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}❌ Ошибка: Docker не запущен${NC}"
    exit 1
fi

# Функция для сборки образа
build_image() {
    local service_name=$1
    local dockerfile_path=$2
    local image_name="${DOCKER_USERNAME}/stools-${service_name}:${VERSION}"
    
    echo -e "${YELLOW}🔨 Сборка образа ${service_name}...${NC}"
    echo "Путь: ${dockerfile_path}"
    echo "Образ: ${image_name}"
    
    docker build -t "${image_name}" "${dockerfile_path}"
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Образ ${service_name} успешно собран${NC}"
        
        # Если передан аргумент push, публикуем образ
        if [ "$1" = "push" ] || [ "$2" = "push" ]; then
            echo -e "${YELLOW}📤 Публикация образа ${service_name}...${NC}"
            docker push "${image_name}"
            
            if [ $? -eq 0 ]; then
                echo -e "${GREEN}✅ Образ ${service_name} успешно опубликован${NC}"
            else
                echo -e "${RED}❌ Ошибка при публикации образа ${service_name}${NC}"
            fi
        fi
    else
        echo -e "${RED}❌ Ошибка при сборке образа ${service_name}${NC}"
        exit 1
    fi
    
    echo ""
}

# Сборка всех образов
echo -e "${BLUE}📦 Начинаем сборку образов...${NC}"
echo ""

# 1. Auth сервис
build_image "auth" "./auth"

# 2. VulnAnalizer
build_image "vulnanalizer" "./vulnanalizer/app"

# 3. LogAnalizer
build_image "loganalizer" "./loganalizer/app"

echo -e "${GREEN}🎉 Все образы успешно собраны!${NC}"
echo ""
echo -e "${BLUE}📋 Список созданных образов:${NC}"
echo "  - ${DOCKER_USERNAME}/stools-auth:${VERSION}"
echo "  - ${DOCKER_USERNAME}/stools-vulnanalizer:${VERSION}"
echo "  - ${DOCKER_USERNAME}/stools-loganalizer:${VERSION}"
echo ""

# Если нужно опубликовать
if [ "$1" = "push" ]; then
    echo -e "${YELLOW}📤 Публикация образов в Docker Hub...${NC}"
    echo "Убедитесь, что вы авторизованы в Docker Hub:"
    echo "  docker login"
    echo ""
    
    read -p "Продолжить публикацию? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        docker push "${DOCKER_USERNAME}/stools-auth:${VERSION}"
        docker push "${DOCKER_USERNAME}/stools-vulnanalizer:${VERSION}"
        docker push "${DOCKER_USERNAME}/stools-loganalizer:${VERSION}"
        
        echo -e "${GREEN}🎉 Все образы опубликованы в Docker Hub!${NC}"
    else
        echo -e "${YELLOW}⏭️ Публикация пропущена${NC}"
    fi
fi

echo ""
echo -e "${BLUE}📝 Следующие шаги:${NC}"
echo "  1. Обновите docker-compose.yml для использования готовых образов"
echo "  2. Протестируйте развертывание с готовыми образами"
echo "  3. Обновите документацию"
