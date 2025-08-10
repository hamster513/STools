#!/bin/bash

# Скрипт для генерации SSL сертификата
# Автоматически определяет имя сервера и генерирует сертификат

set -e

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔐 Генерация SSL сертификата для STools${NC}"

# Создаем директорию для SSL сертификатов
mkdir -p nginx/ssl

# Определяем имя сервера
SERVER_NAME=""
if command -v hostname &> /dev/null; then
    SERVER_NAME=$(hostname)
elif [ -f /etc/hostname ]; then
    SERVER_NAME=$(cat /etc/hostname)
else
    SERVER_NAME="localhost"
fi

# Убираем доменную часть, если есть
SERVER_NAME=$(echo $SERVER_NAME | cut -d'.' -f1)

# Если имя сервера пустое или localhost, используем IP
if [ -z "$SERVER_NAME" ] || [ "$SERVER_NAME" = "localhost" ]; then
    if command -v ip &> /dev/null; then
        SERVER_NAME=$(ip route get 1.1.1.1 | awk '{print $7; exit}' 2>/dev/null || echo "localhost")
    elif command -v hostname &> /dev/null; then
        SERVER_NAME=$(hostname -I | awk '{print $1}' 2>/dev/null || echo "localhost")
    else
        SERVER_NAME="localhost"
    fi
fi

echo -e "${YELLOW}📋 Информация о сертификате:${NC}"
echo -e "   Сервер: ${GREEN}$SERVER_NAME${NC}"
echo -e "   Организация: ${GREEN}STools${NC}"
echo -e "   Срок действия: ${GREEN}365 дней${NC}"
echo -e "   Алгоритм: ${GREEN}RSA 2048 bit${NC}"

# Проверяем, существует ли уже сертификат
if [ -f "nginx/ssl/certificate.crt" ] && [ -f "nginx/ssl/private.key" ]; then
    echo -e "${YELLOW}⚠️  SSL сертификат уже существует${NC}"
    echo -e "   Сертификат: ${GREEN}nginx/ssl/certificate.crt${NC}"
    echo -e "   Приватный ключ: ${GREEN}nginx/ssl/private.key${NC}"
    
    # Показываем информацию о существующем сертификате
    echo -e "${YELLOW}📋 Информация о существующем сертификате:${NC}"
    if command -v openssl &> /dev/null; then
        echo -e "   CN: ${GREEN}$(openssl x509 -in nginx/ssl/certificate.crt -noout -subject 2>/dev/null | sed 's/.*CN = //' | sed 's/,.*//' || echo "неизвестно")${NC}"
        echo -e "   Действителен до: ${GREEN}$(openssl x509 -in nginx/ssl/certificate.crt -noout -enddate 2>/dev/null | sed 's/.*=//' || echo "неизвестно")${NC}"
    fi
    
    read -p "Хотите пересоздать сертификат? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${GREEN}✅ Сертификат оставлен без изменений${NC}"
        exit 0
    fi
    
    # Создаем резервную копию
    echo -e "${YELLOW}💾 Создание резервной копии...${NC}"
    cp nginx/ssl/certificate.crt nginx/ssl/certificate.crt.backup.$(date +%Y%m%d_%H%M%S)
    cp nginx/ssl/private.key nginx/ssl/private.key.backup.$(date +%Y%m%d_%H%M%S)
fi

# Генерируем новый сертификат
echo -e "${YELLOW}🔧 Генерация нового SSL сертификата...${NC}"

# Проверяем наличие OpenSSL
if ! command -v openssl &> /dev/null; then
    echo -e "${RED}❌ OpenSSL не установлен${NC}"
    echo -e "Установите OpenSSL:"
    echo -e "  Ubuntu/Debian: sudo apt install openssl"
    echo -e "  CentOS/RHEL: sudo yum install openssl"
    echo -e "  macOS: brew install openssl"
    exit 1
fi

# Генерируем сертификат
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout nginx/ssl/private.key \
    -out nginx/ssl/certificate.crt \
    -subj "/C=RU/ST=Moscow/L=Moscow/O=STools/OU=IT/CN=$SERVER_NAME" \
    -addext "subjectAltName=DNS:$SERVER_NAME,DNS:localhost,IP:127.0.0.1"

# Проверяем успешность генерации
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ SSL сертификат успешно создан!${NC}"
    
    # Показываем информацию о созданном сертификате
    echo -e "${YELLOW}📋 Детали сертификата:${NC}"
    echo -e "   Файл сертификата: ${GREEN}nginx/ssl/certificate.crt${NC}"
    echo -e "   Приватный ключ: ${GREEN}nginx/ssl/private.key${NC}"
    echo -e "   Common Name: ${GREEN}$SERVER_NAME${NC}"
    echo -e "   Действителен до: ${GREEN}$(openssl x509 -in nginx/ssl/certificate.crt -noout -enddate | sed 's/.*=//')${NC}"
    
    # Устанавливаем правильные права доступа
    chmod 644 nginx/ssl/certificate.crt
    chmod 600 nginx/ssl/private.key
    
    echo -e "${GREEN}🔒 Права доступа установлены${NC}"
    echo -e "${YELLOW}💡 Для применения сертификата перезапустите nginx:${NC}"
    echo -e "   docker-compose -f docker-compose.prod.yml restart nginx"
    
else
    echo -e "${RED}❌ Ошибка при создании SSL сертификата${NC}"
    exit 1
fi

echo -e "${GREEN}🎉 Генерация SSL сертификата завершена!${NC}"
