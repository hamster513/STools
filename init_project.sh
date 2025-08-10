#!/bin/bash

# Скрипт для инициализации проекта STools
# Автоматически настраивает окружение и генерирует SSL сертификат

set -e

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Инициализация проекта STools${NC}"

# Проверяем, что мы в корневой директории проекта
if [ ! -f "docker-compose.yml" ] || [ ! -f "docker-compose.prod.yml" ]; then
    echo -e "${RED}❌ Ошибка: запустите скрипт из корневой директории проекта STools${NC}"
    exit 1
fi

# 1. Создаем .env файл, если его нет
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}📝 Создание файла .env из примера...${NC}"
    if [ -f "env.example" ]; then
        cp env.example .env
        echo -e "${GREEN}✅ Файл .env создан${NC}"
    else
        echo -e "${RED}❌ Файл env.example не найден${NC}"
        exit 1
    fi
else
    echo -e "${GREEN}✅ Файл .env уже существует${NC}"
fi

# 2. Генерируем SSL сертификат
echo -e "${YELLOW}🔐 Генерация SSL сертификата...${NC}"
if [ -f "generate_ssl_cert.sh" ]; then
    ./generate_ssl_cert.sh
else
    echo -e "${RED}❌ Скрипт generate_ssl_cert.sh не найден${NC}"
    exit 1
fi

# 3. Проверяем наличие Docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker не установлен${NC}"
    echo -e "Установите Docker:"
    echo -e "  https://docs.docker.com/get-docker/"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}❌ Docker Compose не установлен${NC}"
    echo -e "Установите Docker Compose:"
    echo -e "  https://docs.docker.com/compose/install/"
    exit 1
fi

echo -e "${GREEN}✅ Docker и Docker Compose доступны${NC}"

# 4. Показываем информацию о настройках
echo -e "${YELLOW}📋 Текущие настройки:${NC}"
if [ -f ".env" ]; then
    echo -e "   HTTP порт: ${GREEN}$(grep NGINX_HTTP_PORT .env | cut -d'=' -f2)${NC}"
    echo -e "   HTTPS порт: ${GREEN}$(grep NGINX_HTTPS_PORT .env | cut -d'=' -f2)${NC}"
    echo -e "   Домен: ${GREEN}$(grep DOMAIN .env | cut -d'=' -f2)${NC}"
fi

# 5. Спрашиваем, хочет ли пользователь запустить проект
echo -e "${YELLOW}🤔 Хотите запустить проект сейчас?${NC}"
echo -e "   Это займет несколько минут для скачивания образов"
read -p "Запустить проект? (y/N): " -n 1 -r
echo

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}🚀 Запуск проекта...${NC}"
    
    # Останавливаем существующие контейнеры, если есть
    echo -e "${YELLOW}🛑 Остановка существующих контейнеров...${NC}"
    docker-compose -f docker-compose.prod.yml down 2>/dev/null || true
    
    # Запускаем проект
    echo -e "${YELLOW}📦 Запуск контейнеров...${NC}"
    docker-compose -f docker-compose.prod.yml up -d
    
    # Ждем немного и проверяем статус
    echo -e "${YELLOW}⏳ Ожидание запуска сервисов...${NC}"
    sleep 10
    
    echo -e "${YELLOW}📊 Статус контейнеров:${NC}"
    docker-compose -f docker-compose.prod.yml ps
    
    echo -e "${GREEN}🎉 Проект запущен!${NC}"
    echo -e "${YELLOW}🌐 Доступные URL:${NC}"
    HTTP_PORT=$(grep NGINX_HTTP_PORT .env | cut -d'=' -f2)
    HTTPS_PORT=$(grep NGINX_HTTPS_PORT .env | cut -d'=' -f2)
    DOMAIN=$(grep DOMAIN .env | cut -d'=' -f2)
    
    echo -e "   HTTP: ${GREEN}http://$DOMAIN:$HTTP_PORT${NC}"
    echo -e "   HTTPS: ${GREEN}https://$DOMAIN:$HTTPS_PORT${NC}"
    echo -e "   VulnAnalizer: ${GREEN}https://$DOMAIN:$HTTPS_PORT/vulnanalizer/${NC}"
    echo -e "   LogAnalizer: ${GREEN}https://$DOMAIN:$HTTPS_PORT/loganalizer/${NC}"
    echo -e "   Auth: ${GREEN}https://$DOMAIN:$HTTPS_PORT/auth/${NC}"
    
    echo -e "${YELLOW}💡 Полезные команды:${NC}"
    echo -e "   Просмотр логов: ${GREEN}docker-compose -f docker-compose.prod.yml logs -f${NC}"
    echo -e "   Остановка: ${GREEN}docker-compose -f docker-compose.prod.yml down${NC}"
    echo -e "   Перезапуск: ${GREEN}docker-compose -f docker-compose.prod.yml restart${NC}"
    
else
    echo -e "${GREEN}✅ Инициализация завершена!${NC}"
    echo -e "${YELLOW}💡 Для запуска проекта выполните:${NC}"
    echo -e "   docker-compose -f docker-compose.prod.yml up -d"
fi

echo -e "${GREEN}🎉 Инициализация проекта STools завершена!${NC}"
