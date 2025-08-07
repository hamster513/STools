# VulnAnalizer - Инструкция по развертыванию

## 🚀 Быстрый старт (рекомендуется)

### 1. Установите Docker и Docker Compose
- **macOS**: Скачайте Docker Desktop с [официального сайта](https://www.docker.com/products/docker-desktop/)
- **Windows**: Скачайте Docker Desktop с [официального сайта](https://www.docker.com/products/docker-desktop/)
- **Linux**: Выполните команды:
  ```bash
  curl -fsSL https://get.docker.com -o get-docker.sh
  sudo sh get-docker.sh
  sudo usermod -aG docker $USER
  ```

### 2. Распакуйте проект
```bash
# Если у вас есть архив
tar -xzf vulnanalizer_complete_backup_*.tar.gz

# Или склонируйте из git
git clone <repository-url>
cd VulnAnalizer
```

### 3. Запустите автоматическое развертывание
```bash
./deploy.sh
```

### 4. Откройте в браузере
```
http://localhost
```

## 📋 Ручное развертывание

### 1. Создайте .env файл
```bash
cat > .env << EOF
POSTGRES_DB=vulnanalizer
POSTGRES_USER=vulnanalizer
POSTGRES_PASSWORD=vulnanalizer
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
EOF
```

### 2. Запустите контейнеры
```bash
docker-compose up -d --build
```

### 3. Проверьте статус
```bash
docker-compose ps
```

## 🔧 Полезные команды

### Управление контейнерами
```bash
# Запуск
docker-compose up -d

# Остановка
docker-compose down

# Перезапуск
docker-compose restart

# Просмотр логов
docker-compose logs -f

# Просмотр логов конкретного сервиса
docker-compose logs -f web
docker-compose logs -f postgres
```

### Работа с базой данных
```bash
# Подключение к базе данных
docker-compose exec postgres psql -U vulnanalizer -d vulnanalizer

# Бэкап базы данных
docker-compose exec postgres pg_dump -U vulnanalizer vulnanalizer > backup.sql

# Восстановление базы данных
docker-compose exec postgres psql -U vulnanalizer -d vulnanalizer < backup.sql
```

### Обновление приложения
```bash
# Остановить контейнеры
docker-compose down

# Пересобрать образы
docker-compose build --no-cache

# Запустить заново
docker-compose up -d
```

## 🐛 Решение проблем

### Проблема: Порт 80 занят
```bash
# Измените порт в docker-compose.yml
ports:
  - "8080:80"  # Вместо "80:80"
```

### Проблема: База данных не запускается
```bash
# Проверьте логи
docker-compose logs postgres

# Пересоздайте контейнер
docker-compose down
docker volume rm vulnanalizer_postgres_data
docker-compose up -d
```

### Проблема: Приложение не отвечает
```bash
# Проверьте логи веб-приложения
docker-compose logs web

# Проверьте статус контейнеров
docker-compose ps
```

## 📊 Структура проекта

```
VulnAnalizer/
├── app/                    # Основное приложение
│   ├── main.py            # FastAPI приложение
│   ├── database.py        # Работа с БД
│   ├── static/            # CSS, JS файлы
│   └── templates/         # HTML шаблоны
├── init-db/               # Инициализация БД
├── nginx/                 # Конфигурация Nginx
├── static/                # Дополнительные статические файлы
├── docker-compose.yml     # Конфигурация контейнеров
├── deploy.sh              # Скрипт автоматического развертывания
└── README_DEPLOY.md       # Эта инструкция
```

## 🌟 Возможности приложения

### Основные функции:
- ✅ **Поиск CVE** с отображением EPSS и ExploitDB данных
- ✅ **Расчет риска** с настраиваемым Impact
- ✅ **Цветовая градация** Risk Score
- ✅ **Импорт хостов** из CSV файлов
- ✅ **Поиск хостов** по различным критериям
- ✅ **Автоматический расчет риска** для хостов
- ✅ **Группировка хостов** по hostname, IP, CVE
- ✅ **Настройки приложения**
- ✅ **Загрузка EPSS и ExploitDB данных**

### Технический стек:
- **Backend**: FastAPI (Python)
- **Database**: PostgreSQL
- **Frontend**: HTML, CSS, JavaScript
- **Containerization**: Docker & Docker Compose
- **Web Server**: Nginx

## 📞 Поддержка

Если возникли проблемы:
1. Проверьте логи: `docker-compose logs -f`
2. Убедитесь, что Docker и Docker Compose установлены
3. Проверьте, что порты 80 и 5432 свободны
4. Попробуйте пересобрать контейнеры: `docker-compose build --no-cache`

## 🎉 Готово!

После успешного развертывания вы получите полнофункциональное веб-приложение для анализа уязвимостей с современным интерфейсом и всеми необходимыми функциями. 