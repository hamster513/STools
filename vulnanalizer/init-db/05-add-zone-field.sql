-- Миграция для добавления поля zone в таблицу hosts
-- Добавляем поле для хранения зоны из VM MaxPatrol

ALTER TABLE hosts ADD COLUMN IF NOT EXISTS zone VARCHAR(100);

-- Создаем индекс для поля zone
CREATE INDEX IF NOT EXISTS idx_hosts_zone ON hosts(zone);
