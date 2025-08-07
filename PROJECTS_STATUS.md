# Статус проектов STools

## 🚀 Активные проекты

### 1. LogAnalizer
- **Статус**: ✅ Работает
- **URL**: http://localhost/loganalizer/
- **API**: http://localhost/loganalizer/api/
- **База данных**: PostgreSQL (внутренняя сеть)
- **Папка**: `loganalizer/`

### 2. VulnAnalizer
- **Статус**: ✅ Работает
- **URL**: http://localhost/vulnanalizer/
- **API**: http://localhost/vulnanalizer/api/
- **База данных**: PostgreSQL (внутренняя сеть)
- **Папка**: `vulnanalizer/`

## 🏗️ Архитектура

### Единая система
- **Единый Nginx**: Проксирование на порту 80
- **Общая сеть**: `stools_network` для всех контейнеров
- **Именованные сервисы**: Контейнеры общаются по именам, а не по IP
- **Чистые URL**: Пользователь не видит порты

### Структура
```
STools/
├── docker-compose.yml          # Единая конфигурация
├── nginx/                      # Единый веб-сервер
│   └── nginx.conf
├── loganalizer/                # Анализатор логов
│   ├── app/                   # Приложение
│   ├── init-db/               # Инициализация БД
│   └── README.md
├── vulnanalizer/               # Анализатор уязвимостей
│   ├── app/                   # Приложение
│   ├── init-db/               # Инициализация БД
│   └── README.md
└── PROJECTS_STATUS.md         # Этот файл
```

## 🔧 Управление проектами

### Запуск всей системы
```bash
docker-compose up -d --build
```

### Остановка
```bash
docker-compose down
```

### Просмотр логов
```bash
# Все сервисы
docker-compose logs -f

# Конкретный сервис
docker-compose logs -f loganalizer_web
docker-compose logs -f vulnanalizer_web
docker-compose logs -f stools_nginx
```

## 🌐 Доступ

| Сервис | URL | Описание |
|--------|-----|----------|
| LogAnalizer | http://localhost/loganalizer/ | Анализатор логов |
| VulnAnalizer | http://localhost/vulnanalizer/ | Анализатор уязвимостей |
| Главная страница | http://localhost/ | Редирект на LogAnalizer |

## ✅ Улучшения реализованы

1. **Убрана жесткая привязка к IP** - контейнеры общаются по именам
2. **Единый Nginx** - проксирование на порту 80
3. **Убраны лишние nginx** - удалены из отдельных проектов
4. **Чистые URL** - пользователь не видит порты
5. **Обновлены ссылки** - в верхних панелях приложений
6. **Обновлен JavaScript** - API вызовы работают с новыми путями
7. **Исправлены статические файлы** - JavaScript и CSS загружаются корректно
8. **Исправлен порядок location блоков** - более специфичные блоки идут первыми

## 🎯 Следующие шаги

1. Добавить SSL сертификаты для HTTPS
2. Создать общий скрипт для управления всеми проектами
3. Добавить мониторинг и логирование
4. Настроить резервное копирование баз данных
