FROM python:3.11-slim

WORKDIR /app

# Устанавливаем системные зависимости
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Копируем и устанавливаем зависимости Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем код приложения
COPY . .



# Создаем директорию для данных
RUN mkdir -p /app/data

# Открываем порт
EXPOSE 8000

# Оптимизированные настройки uvicorn для производительности
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--loop", "uvloop", "--http", "httptools", "--timeout-keep-alive", "3600", "--access-log", "--log-level", "info"] 