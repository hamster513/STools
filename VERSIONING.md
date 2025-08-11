# Система версионирования STools

## Обзор

STools использует простую систему версионирования с одним центральным файлом `VERSION` в корне проекта.

## Структура версионирования

```
STools/
├── VERSION                    # Единственная версия проекта
└── ...
```

## Формат версии

Версии следуют формату: `MAJOR.MINOR.PATCH` (например: `0.2.0001`)

- **MAJOR**: Крупные изменения, несовместимые с предыдущими версиями
- **MINOR**: Новые функции, совместимые с предыдущими версиями  
- **PATCH**: Исправления ошибок

## API Endpoints

Все сервисы предоставляют endpoint для получения версии:

- **VulnAnalizer**: `GET /vulnanalizer/api/version`
- **LogAnalizer**: `GET /loganalizer/api/version`
- **Auth**: `GET /auth/api/version`

Пример ответа:
```json
{
    "version": "0.2.0001"
}
```

## Обновление версии

### Автоматическое обновление

Используйте скрипт `update_version.sh`:

```bash
./update_version.sh 0.2.0002
```

### Ручное обновление

1. Обновите файл `VERSION` в корне проекта
2. Пересоберите контейнеры для применения изменений

## Проверка версий

### Через API

```bash
# Проверка версии VulnAnalizer
curl -k https://localhost/vulnanalizer/api/version

# Проверка версии LogAnalizer  
curl -k https://localhost/loganalizer/api/version

# Проверка версии Auth
curl -k https://localhost/auth/api/version
```

### Через файл

```bash
cat VERSION
```

## Применение изменений

После обновления версии пересоберите контейнеры:

```bash
docker-compose down
docker-compose up -d --build
```
