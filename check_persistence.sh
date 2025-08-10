#!/bin/bash

echo "🔍 Проверка персистентности данных в Docker volumes"

echo ""
echo "📊 Текущие volumes:"
docker volume ls | grep stools

echo ""
echo "📈 Данные в VulnAnalizer до перезапуска:"
docker-compose exec vulnanalizer_postgres psql -U vulnanalizer -d vulnanalizer -c "SELECT COUNT(*) as hosts_count FROM hosts;"
docker-compose exec vulnanalizer_postgres psql -U vulnanalizer -d vulnanalizer -c "SELECT COUNT(*) as epss_count FROM epss;"
docker-compose exec vulnanalizer_postgres psql -U vulnanalizer -d vulnanalizer -c "SELECT COUNT(*) as exploitdb_count FROM exploitdb;"

echo ""
echo "📈 Данные в LogAnalizer до перезапуска:"
docker-compose exec loganalizer_postgres psql -U loganalizer_user -d loganalizer_db -c "SELECT COUNT(*) as logs_count FROM logs;" 2>/dev/null || echo "Таблица logs не существует"

echo ""
echo "🔄 Перезапуск PostgreSQL контейнеров..."
docker-compose restart vulnanalizer_postgres loganalizer_postgres

echo ""
echo "⏳ Ожидание запуска баз данных..."
sleep 10

echo ""
echo "📈 Данные в VulnAnalizer после перезапуска:"
docker-compose exec vulnanalizer_postgres psql -U vulnanalizer -d vulnanalizer -c "SELECT COUNT(*) as hosts_count FROM hosts;"
docker-compose exec vulnanalizer_postgres psql -U vulnanalizer -d vulnanalizer -c "SELECT COUNT(*) as epss_count FROM epss;"
docker-compose exec vulnanalizer_postgres psql -U vulnanalizer -d vulnanalizer -c "SELECT COUNT(*) as exploitdb_count FROM exploitdb;"

echo ""
echo "📈 Данные в LogAnalizer после перезапуска:"
docker-compose exec loganalizer_postgres psql -U loganalizer_user -d loganalizer_db -c "SELECT COUNT(*) as logs_count FROM logs;" 2>/dev/null || echo "Таблица logs не существует"

echo ""
echo "✅ Проверка завершена!"
