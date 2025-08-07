#!/bin/bash

echo "=== Проверка сетевого взаимодействия между контейнерами ==="
echo

# Проверяем, что контейнеры запущены
echo "1. Проверка статуса контейнеров:"
docker-compose ps
echo

# Проверяем сеть
echo "2. Информация о сети:"
docker network ls | grep vulnanalizer
docker network inspect vulnanalizer_vulnanalizer_network
echo

# Проверяем IP-адреса контейнеров
echo "3. IP-адреса контейнеров:"
echo "PostgreSQL: $(docker inspect vulnanalizer_postgres | grep IPAddress | grep -v null | head -1 | cut -d'"' -f4)"
echo "Web (FastAPI): $(docker inspect vulnanalizer_web | grep IPAddress | grep -v null | head -1 | cut -d'"' -f4)"
echo "Nginx: $(docker inspect vulnanalizer_nginx | grep IPAddress | grep -v null | head -1 | cut -d'"' -f4)"
echo

# Проверяем доступность PostgreSQL из web-контейнера
echo "4. Проверка подключения к PostgreSQL из web-контейнера:"
docker exec vulnanalizer_web ping -c 2 172.20.0.10
echo

# Проверяем доступность web-контейнера из nginx
echo "5. Проверка подключения к web-контейнеру из nginx:"
docker exec vulnanalizer_nginx ping -c 2 172.20.0.20
echo

# Проверяем доступность PostgreSQL из nginx
echo "6. Проверка подключения к PostgreSQL из nginx:"
docker exec vulnanalizer_nginx ping -c 2 172.20.0.10
echo

echo "=== Проверка завершена ===" 