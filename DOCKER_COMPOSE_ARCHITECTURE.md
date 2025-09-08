# Docker Compose для разных архитектур

Проект поддерживает две архитектуры: ARM64 (для macOS) и x86_64 (для Linux серверов).

## Файлы конфигурации

- `docker-compose.arm.yml` - для macOS с ARM64 архитектурой
- `docker-compose.x86.yml` - для Linux серверов с x86_64 архитектурой

## Использование

### На macOS (ARM64):
```bash
docker-compose -f docker-compose.arm.yml up -d
```

### На Linux сервере (x86_64):
```bash
docker-compose -f docker-compose.x86.yml up -d
```

## Основные отличия

Оба файла идентичны, за исключением параметра `platform`:

- **ARM версия**: `platform: linux/arm64`
- **x86 версия**: `platform: linux/amd64`

## Автоматическое определение архитектуры

Можно создать скрипт для автоматического выбора нужного файла:

```bash
#!/bin/bash
ARCH=$(uname -m)
if [[ "$ARCH" == "arm64" ]]; then
    COMPOSE_FILE="docker-compose.arm.yml"
else
    COMPOSE_FILE="docker-compose.x86.yml"
fi

echo "Используется архитектура: $ARCH"
echo "Файл конфигурации: $COMPOSE_FILE"

docker-compose -f $COMPOSE_FILE up -d
```

## Сборка образов

### Для ARM64 (macOS):
```bash
docker build --platform linux/arm64 -t hamster5133/stools-auth_web:v0.6.03 ./auth/
docker build --platform linux/arm64 -t hamster5133/stools-loganalizer_web:v0.6.03 ./loganalizer/app/
docker build --platform linux/arm64 -t hamster5133/stools-vulnanalizer_web:v0.6.03 ./vulnanalizer/app/
docker build --platform linux/arm64 -t hamster5133/stools-main_web:v0.6.03 ./
```

### Для x86_64 (Linux):
```bash
docker build --platform linux/amd64 -t hamster5133/stools-auth_web:v0.6.03 ./auth/
docker build --platform linux/amd64 -t hamster5133/stools-loganalizer_web:v0.6.03 ./loganalizer/app/
docker build --platform linux/amd64 -t hamster5133/stools-vulnanalizer_web:v0.6.03 ./vulnanalizer/app/
docker build --platform linux/amd64 -t hamster5133/stools-main_web:v0.6.03 ./
```

## Решение проблем

Если возникает ошибка "exec format error", это означает несоответствие архитектуры образа и системы. Используйте соответствующий docker-compose файл для вашей архитектуры.
