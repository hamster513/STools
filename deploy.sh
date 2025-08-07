#!/bin/bash

echo "🚀 VulnAnalizer - Автоматическое развертывание"
echo "================================================"

# Проверяем наличие Docker и Docker Compose
if ! command -v docker &> /dev/null; then
    echo "❌ Docker не установлен. Установите Docker: https://docs.docker.com/get-docker/"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose не установлен. Установите Docker Compose: https://docs.docker.com/compose/install/"
    exit 1
fi

echo "✅ Docker и Docker Compose найдены"

# Создаем .env файл если его нет
if [ ! -f .env ]; then
    echo "📝 Создаем файл .env..."
    cat > .env << EOF
POSTGRES_DB=vulnanalizer
POSTGRES_USER=vulnanalizer
POSTGRES_PASSWORD=vulnanalizer
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
EOF
    echo "✅ Файл .env создан"
fi

# Останавливаем контейнеры если они запущены
echo "🛑 Останавливаем существующие контейнеры..."
docker-compose down

# Собираем и запускаем контейнеры
echo "🔨 Собираем и запускаем контейнеры..."
docker-compose up -d --build

# Ждем запуска базы данных
echo "⏳ Ждем запуска базы данных..."
sleep 10

# Проверяем статус контейнеров
echo "📊 Статус контейнеров:"
docker-compose ps

echo ""
echo "🎉 VulnAnalizer успешно развернут!"
echo "🌐 Откройте в браузере: http://localhost"
echo ""
echo "📋 Полезные команды:"
echo "  • Просмотр логов: docker-compose logs -f"
echo "  • Остановка: docker-compose down"
echo "  • Перезапуск: docker-compose restart"
echo "  • Обновление: ./deploy.sh"
echo ""
echo "📁 Структура проекта:"
echo "  • app/ - Основное приложение"
echo "  • init-db/ - Инициализация базы данных"
echo "  • nginx/ - Конфигурация веб-сервера"
echo "  • docker-compose.yml - Конфигурация контейнеров" 