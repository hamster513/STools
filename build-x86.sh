#!/bin/bash

# Скрипт для сборки и загрузки образов для x86_64 архитектуры

echo "🔨 Сборка и загрузка образов для x86_64 архитектуры"
echo "===================================================="

# Читаем версию из файла VERSION
VERSION=$(cat VERSION 2>/dev/null || echo "0.8.0")
echo "📋 Версия: $VERSION"

echo "🚀 Начинаем сборку образов для linux/amd64..."

# Сборка auth_web
echo "📦 Сборка auth_web для x86_64..."
docker build --platform linux/amd64 -t hamster5133/stools-auth_web:v$VERSION ./auth/
if [ $? -eq 0 ]; then
    echo "✅ auth_web собран успешно"
else
    echo "❌ Ошибка при сборке auth_web"
    exit 1
fi

# Сборка loganalizer_web
echo "📦 Сборка loganalizer_web для x86_64..."
docker build --platform linux/amd64 -t hamster5133/stools-loganalizer_web:v$VERSION ./loganalizer/app/
if [ $? -eq 0 ]; then
    echo "✅ loganalizer_web собран успешно"
else
    echo "❌ Ошибка при сборке loganalizer_web"
    exit 1
fi

# Сборка vulnanalizer_web
echo "📦 Сборка vulnanalizer_web для x86_64..."
docker build --platform linux/amd64 -t hamster5133/stools-vulnanalizer_web:v$VERSION ./vulnanalizer/app/
if [ $? -eq 0 ]; then
    echo "✅ vulnanalizer_web собран успешно"
else
    echo "❌ Ошибка при сборке vulnanalizer_web"
    exit 1
fi

# Сборка main_web
echo "📦 Сборка main_web для x86_64..."
docker build --platform linux/amd64 -t hamster5133/stools-main_web:v$VERSION ./
if [ $? -eq 0 ]; then
    echo "✅ main_web собран успешно"
else
    echo "❌ Ошибка при сборке main_web"
    exit 1
fi

echo ""
echo "📤 Загружаем образы в Docker Hub..."

# Загрузка в Docker Hub
echo "📤 Загрузка auth_web..."
docker push hamster5133/stools-auth_web:v$VERSION

echo "📤 Загрузка loganalizer_web..."
docker push hamster5133/stools-loganalizer_web:v$VERSION

echo "📤 Загрузка vulnanalizer_web..."
docker push hamster5133/stools-vulnanalizer_web:v$VERSION

echo "📤 Загрузка main_web..."
docker push hamster5133/stools-main_web:v$VERSION

echo ""
echo "🎉 Все образы успешно собраны и загружены для x86_64 архитектуры!"
echo "📋 Загруженные образы:"
echo "   - hamster5133/stools-auth_web:v$VERSION (x86_64)"
echo "   - hamster5133/stools-loganalizer_web:v$VERSION (x86_64)"
echo "   - hamster5133/stools-vulnanalizer_web:v$VERSION (x86_64)"
echo "   - hamster5133/stools-main_web:v$VERSION (x86_64)"

echo ""
echo "🚀 Теперь на удаленном хосте можно запустить:"
echo "   ./start.sh"
echo ""
echo "Docker автоматически скачает образы для x86_64 архитектуры!"
