# VulnAnalizer

Система анализа уязвимостей и безопасности.

## Описание

VulnAnalizer - это веб-приложение для анализа уязвимостей, сканирования безопасности и управления данными о безопасности.

## Структура проекта

```
vulnanalizer/
├── app/                    # Основное приложение
│   ├── main.py            # Главный файл приложения
│   ├── database.py        # Работа с базой данных
│   ├── models.py          # Модели данных
│   ├── requirements.txt   # Зависимости Python
│   ├── Dockerfile         # Конфигурация Docker
│   ├── static/            # Статические файлы (CSS, JS)
│   ├── templates/         # HTML шаблоны
│   └── data/              # Данные приложения
├── init-db/               # Инициализация базы данных
│   └── init.sql
└── README.md              # Документация
```

## Быстрый запуск

VulnAnalizer является частью проекта STools и развертывается вместе с ним.

1. **Клонирование репозитория**:
   ```bash
   git clone https://github.com/hamster513/STools.git
   cd STools
   ```

2. **Запуск всех сервисов**:
   ```bash
   docker-compose up -d --build
   ```

3. **Открытие в браузере**:
   - VulnAnalizer: http://localhost/vulnanalizer/
   - LogAnalizer: http://localhost/loganalizer/

## Полезные команды

- Просмотр логов: `docker-compose logs -f`
- Остановка: `docker-compose down`
- Перезапуск: `docker-compose restart`
- Обновление: `docker-compose up -d --build`
- Просмотр логов конкретного сервиса: `docker-compose logs -f vulnanalizer_web`

## Доступ

- **http://localhost/loganalizer/** - LogAnalizer
- **http://localhost/vulnanalizer/** - VulnAnalizer
- **http://localhost/** - Редирект на LogAnalizer

## Разработка

Для разработки можно использовать:
```bash
# Запуск в режиме разработки
docker-compose up -d

# Просмотр логов VulnAnalizer
docker-compose logs -f vulnanalizer_web

# Перезапуск только VulnAnalizer
docker-compose restart vulnanalizer_web

# Перезапуск только LogAnalizer
docker-compose restart loganalizer_web
```
