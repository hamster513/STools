FROM python:3.11-slim

WORKDIR /app

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Копирование зависимостей
COPY requirements.txt .

# Установка Python зависимостей
RUN pip install --no-cache-dir -r requirements.txt

# Копируем файл версии
COPY VERSION /app/VERSION
RUN echo "Version: $(cat /app/VERSION)"

# Копирование кода приложения
COPY . .

# Создание директории для данных
RUN mkdir -p /app/data

# Открытие порта
EXPOSE 8000

# Запуск приложения с оптимизацией
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--timeout-keep-alive", "3600"]
