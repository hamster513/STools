-- Оптимизация индексов для VulnAnalizer
-- Выполняется для улучшения производительности запросов

-- 1. Составные индексы для часто используемых комбинаций полей
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_hosts_cve_risk_score 
ON hosts(cve, risk_score DESC NULLS LAST);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_hosts_cve_cvss 
ON hosts(cve, cvss DESC NULLS LAST);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_hosts_criticality_risk_score 
ON hosts(criticality, risk_score DESC NULLS LAST);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_hosts_has_exploits_risk_score 
ON hosts(has_exploits, risk_score DESC NULLS LAST);

-- 2. Индексы для поиска по частичному совпадению
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_hosts_hostname_gin 
ON hosts USING gin(hostname gin_trgm_ops);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_hosts_cve_gin 
ON hosts USING gin(cve gin_trgm_ops);

-- 3. Индексы для временных полей (для сортировки и фильтрации)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_hosts_epss_updated_at 
ON hosts(epss_updated_at DESC NULLS LAST);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_hosts_exploits_updated_at 
ON hosts(exploits_updated_at DESC NULLS LAST);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_hosts_risk_updated_at 
ON hosts(risk_updated_at DESC NULLS LAST);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_hosts_imported_at 
ON hosts(imported_at DESC NULLS LAST);

-- 4. Индексы для числовых полей с NULL значениями
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_hosts_epss_score 
ON hosts(epss_score DESC NULLS LAST);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_hosts_epss_percentile 
ON hosts(epss_percentile DESC NULLS LAST);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_hosts_exploits_count 
ON hosts(exploits_count DESC NULLS LAST);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_hosts_verified_exploits_count 
ON hosts(verified_exploits_count DESC NULLS LAST);

-- 5. Индексы для таблицы CVE
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_cve_cvss_v3_severity 
ON cve(cvss_v3_base_severity);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_cve_cvss_v2_severity 
ON cve(cvss_v2_base_severity);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_cve_exploitability_score 
ON cve(exploitability_score DESC NULLS LAST);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_cve_impact_score 
ON cve(impact_score DESC NULLS LAST);

-- 6. Индексы для таблицы EPSS
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_epss_cve_id 
ON epss(cve_id);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_epss_epss_score 
ON epss(epss DESC NULLS LAST);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_epss_percentile 
ON epss(percentile DESC NULLS LAST);

-- 7. Индексы для таблицы ExploitDB
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_exploitdb_cve_id 
ON exploitdb(cve_id);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_exploitdb_verified 
ON exploitdb(verified);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_exploitdb_date 
ON exploitdb(date DESC NULLS LAST);

-- 8. Индексы для фоновых задач
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_background_tasks_type_status 
ON background_tasks(task_type, status);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_background_tasks_created_at 
ON background_tasks(created_at DESC);

-- 9. Индексы для настроек
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_settings_key 
ON settings(key);

-- 10. Частичные индексы для оптимизации
-- Индекс только для хостов с высоким риском
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_hosts_high_risk 
ON hosts(hostname, cve, risk_score) 
WHERE risk_score > 50;

-- Индекс только для хостов с эксплойтами
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_hosts_with_exploits 
ON hosts(hostname, cve, exploits_count) 
WHERE has_exploits = TRUE;

-- Индекс только для критических хостов
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_hosts_critical 
ON hosts(hostname, cve, risk_score) 
WHERE criticality = 'Critical';

-- 11. Индексы для полнотекстового поиска (если нужно)
-- CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_hosts_hostname_fulltext 
-- ON hosts USING gin(to_tsvector('english', hostname));

-- 12. Статистика для оптимизатора запросов
ANALYZE hosts;
ANALYZE cve;
ANALYZE epss;
ANALYZE exploitdb;
ANALYZE background_tasks;
ANALYZE settings;

-- 13. Проверка размера индексов
SELECT 
    schemaname,
    tablename,
    indexname,
    pg_size_pretty(pg_relation_size(indexrelid)) as index_size
FROM pg_indexes 
WHERE schemaname = 'public' 
ORDER BY pg_relation_size(indexrelid) DESC;
