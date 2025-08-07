# 🚀 VulnAnalizer - Быстрый старт

## 📦 Что нужно сделать товарищу:

### 1. Установите Docker
- **macOS/Windows**: Скачайте [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- **Linux**: `curl -fsSL https://get.docker.com -o get-docker.sh && sudo sh get-docker.sh`

### 2. Распакуйте архив
```bash
tar -xzf vulnanalizer_for_deployment_*.tar.gz
cd VulnAnalizer
```

### 3. Запустите одним командой
```bash
./deploy.sh
```

### 4. Откройте в браузере
```
http://localhost
```

## 🎯 Готово!

Приложение автоматически:
- ✅ Создаст все необходимые файлы
- ✅ Запустит контейнеры
- ✅ Инициализирует базу данных
- ✅ Запустит веб-сервер

## 📋 Полезные команды:
```bash
# Остановить приложение
docker-compose down

# Запустить заново
docker-compose up -d

# Посмотреть логи
docker-compose logs -f
```

## 📖 Подробная инструкция
Смотрите `README_DEPLOY.md` для детального описания всех возможностей и решения проблем.

---
**Размер архива**: 35 KB  
**Время развертывания**: ~2-3 минуты  
**Требования**: Docker + Docker Compose 