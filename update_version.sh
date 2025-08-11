#!/bin/bash

# Скрипт для обновления версии проекта
# Использование: ./update_version.sh <новая_версия>
# Пример: ./update_version.sh 0.1.0002

set -e

# Проверяем, что передана версия
if [ $# -eq 0 ]; then
    echo "❌ Ошибка: Не указана новая версия"
    echo "Использование: $0 <новая_версия>"
    echo "Пример: $0 0.1.0002"
    exit 1
fi

NEW_VERSION=$1

echo "🔄 Обновление версии до $NEW_VERSION..."

# Обновляем основную версию проекта
echo "$NEW_VERSION" > VERSION
echo "✅ Обновлена версия проекта: $NEW_VERSION"

# Копируем версию в директории приложений
cp VERSION auth/VERSION
cp VERSION loganalizer/app/VERSION
cp VERSION vulnanalizer/app/VERSION
echo "✅ Скопирована версия в директории приложений"

echo ""
echo "🎉 Версия успешно обновлена до $NEW_VERSION"
echo "📝 Файл VERSION обновлен в корне проекта и скопирован в приложения"
