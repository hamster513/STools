# LogAnalizer

Сервис анализа логов с поддержкой загрузки файлов, распаковки архивов и анализа важных строк в логах.

## Возможности

- **Загрузка файлов**: Поддержка различных форматов (.log, .txt, .csv, .json, .xml)
- **Распаковка архивов**: Автоматическая распаковка .zip, .tar, .gz, .bz2, .xz
- **Рекурсивная распаковка**: Поддержка вложенных архивов с настраиваемой глубиной
- **Анализ логов**: Фильтрация важных строк (ERROR, WARN, CRITICAL, FATAL)
- **Пресеты анализа**: Настраиваемые шаблоны для анализа
- **Предварительный просмотр**: Просмотр первых 100 строк файла
- **Управление файлами**: Удаление отдельных файлов или очистка всех
- **Настройки**: Гибкая настройка параметров загрузки и анализа

## Архитектура

- **Backend**: FastAPI (Python)
- **Frontend**: HTML, CSS, JavaScript
- **База данных**: PostgreSQL
- **Веб-сервер**: Nginx
- **Контейнеризация**: Docker & Docker Compose

## Быстрый старт

LogAnalizer является частью проекта STools и развертывается вместе с ним.

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
```
http://localhost/loganalizer/
```

## Структура проекта

```
loganalizer/
├── app/                    # FastAPI приложение
│   ├── main.py            # Основной файл приложения
│   ├── database.py        # Модуль базы данных
│   ├── models.py          # Модели данных
│   ├── requirements.txt   # Зависимости Python
│   ├── Dockerfile         # Docker образ
│   ├── static/            # Статические файлы
│   │   ├── css/          # Стили
│   │   ├── js/           # JavaScript
│   │   └── favicon.svg   # Иконка
│   └── templates/        # HTML шаблоны
├── init-db/              # Инициализация БД
└── README.md            # Документация
```

## API Endpoints

### Файлы
- `POST /api/logs/upload` - Загрузка файлов
- `GET /api/logs/files` - Список файлов
- `GET /api/logs/files/{id}/preview` - Предварительный просмотр
- `DELETE /api/logs/files/{id}` - Удаление файла
- `POST /api/logs/files/clear` - Очистка всех файлов

### Анализ
- `POST /api/logs/analyze` - Анализ файлов
- `GET /api/presets` - Список пресетов
- `POST /api/presets` - Создание пресета

### Настройки
- `GET /api/settings` - Получение настроек
- `POST /api/settings` - Обновление настроек

## Настройки

### Загрузка файлов
- `max_file_size_mb` - Максимальный размер файла (МБ)
- `supported_formats` - Поддерживаемые форматы файлов

### Распаковка архивов
- `extract_nested_archives` - Распаковка вложенных архивов
- `max_extraction_depth` - Максимальная глубина вложенности

### Анализ логов
- `important_log_levels` - Важные уровни логов для фильтрации

## Безопасность

- Защита от zip-bomb атак
- Ограничение размера файлов
- Валидация типов файлов
- Изоляция в Docker контейнерах

## Разработка

### Локальная разработка
```bash
# Установка зависимостей
pip install -r app/requirements.txt

# Запуск базы данных
docker-compose up postgres -d

# Запуск приложения
cd app
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Тестирование
```bash
# Проверка здоровья сервиса
curl http://localhost/loganalizer/api/health
```

## Лицензия

MIT License 