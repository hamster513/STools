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
├── nginx/                 # Конфигурация веб-сервера
│   └── nginx.conf
├── init-db/               # Инициализация базы данных
│   └── init.sql
└── docker-compose.yml     # Конфигурация контейнеров
```

## Быстрый запуск

1. Перейдите в папку vulnanalizer:
   ```bash
   cd vulnanalizer
   ```

2. Запустите проект из корневой папки:
   ```bash
   cd ..
   docker-compose up -d --build
   ```

3. Откройте в браузере:
   - Основной URL: http://localhost/vulnanalizer/
   - Прямой доступ к API: http://localhost/vulnanalizer/api/

## Полезные команды

- Просмотр логов: `docker-compose logs -f`
- Остановка: `docker-compose down`
- Перезапуск: `docker-compose restart`
- Обновление: `docker-compose up -d --build`

## Доступ

- **http://localhost/loganalizer/** - LogAnalizer
- **http://localhost/vulnanalizer/** - VulnAnalizer
- **http://localhost/** - Редирект на LogAnalizer

## Разработка

Для разработки можно использовать:
```bash
# Запуск в режиме разработки
docker-compose up -d

# Просмотр логов
docker-compose logs -f web

# Перезапуск только веб-приложения
docker-compose restart web
```
