# Многоэтапная сборка для оптимизации
FROM python:3.11-slim as builder

# Устанавливаем зависимости для сборки
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Создаем виртуальное окружение
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Копируем и устанавливаем зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Финальный образ
FROM python:3.11-slim

# Устанавливаем только необходимые пакеты
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Копируем виртуальное окружение
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Создаем пользователя для безопасности
RUN useradd --create-home --shell /bin/bash app
USER app

# Рабочая директория
WORKDIR /app

# Копируем код приложения
COPY --chown=app:app . .

# Копируем файл версии
COPY --chown=app:app VERSION /app/VERSION
RUN echo "Version: $(cat /app/VERSION)"

# Порт
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

# Запуск приложения с оптимизацией для больших файлов
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--loop", "uvloop", "--http", "httptools", "--timeout-keep-alive", "3600"] 