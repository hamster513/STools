# VulnAnalizer - Информация о бэкапе

## Дата создания
31 июля 2025, 00:20

## Файлы бэкапа

### 1. Полный бэкап проекта
- **Файл**: `vulnanalizer_backup_20250731_002017.tar.gz`
- **Размер**: 32.4 KB
- **Содержимое**: Весь проект без временных файлов

### 2. Бэкап базы данных
- **Файл**: `vulnanalizer_db_backup_20250731_002034.sql`
- **Размер**: 26.7 MB
- **Содержимое**: Полная структура и данные PostgreSQL

## Восстановление

### Восстановление проекта
```bash
# Распаковать бэкап
tar -xzf vulnanalizer_backup_20250731_002017.tar.gz

# Перейти в директорию проекта
cd VulnAnalizer

# Запустить контейнеры
docker-compose up -d
```

### Восстановление базы данных
```bash
# Остановить контейнеры
docker-compose down

# Запустить только PostgreSQL
docker-compose up -d postgres

# Восстановить базу данных
docker-compose exec postgres psql -U vulnanalizer -d vulnanalizer < vulnanalizer_db_backup_20250731_002034.sql

# Запустить все контейнеры
docker-compose up -d
```

## Состояние проекта на момент бэкапа

### Реализованные функции:
- ✅ Поиск CVE с отображением EPSS и ExploitDB данных
- ✅ Расчет риска с настраиваемым Impact
- ✅ Цветовая градация Risk Score
- ✅ Импорт хостов из CSV
- ✅ Поиск хостов по различным критериям
- ✅ Автоматический расчет риска для хостов
- ✅ Группировка хостов по hostname, IP, CVE
- ✅ Настройки приложения
- ✅ Загрузка EPSS и ExploitDB данных

### Технический стек:
- **Backend**: FastAPI (Python)
- **Database**: PostgreSQL
- **Frontend**: HTML, CSS, JavaScript (Vanilla)
- **Containerization**: Docker & Docker Compose
- **Web Server**: Nginx

### Структура проекта:
```
VulnAnalizer/
├── app/                    # Основное приложение
│   ├── main.py            # FastAPI приложение
│   ├── database.py        # Работа с БД
│   ├── static/            # Статические файлы
│   └── templates/         # HTML шаблоны
├── init-db/               # Инициализация БД
├── nginx/                 # Конфигурация Nginx
├── static/                # Дополнительные статические файлы
├── docker-compose.yml     # Docker Compose конфигурация
└── README.md              # Документация
```

## Примечания
- Бэкап создан с исключением временных файлов (.git, __pycache__, *.pyc)
- База данных содержит все таблицы: settings, epss, exploitdb, hosts
- Все настройки и данные сохранены 