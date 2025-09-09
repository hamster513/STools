-- Добавляем уникальный индекс для hosts (hostname, cve)
-- Это позволит использовать ON CONFLICT в insert_hosts_records_with_progress

-- Создаем уникальный индекс на hostname и cve
CREATE UNIQUE INDEX IF NOT EXISTS idx_hosts_hostname_cve_unique 
ON vulnanalizer.hosts (hostname, cve);

-- Добавляем комментарий
COMMENT ON INDEX idx_hosts_hostname_cve_unique IS 'Уникальный индекс для предотвращения дублирования записей (hostname, cve)';
