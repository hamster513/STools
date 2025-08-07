-- Обновление уровней логов в базе данных
UPDATE settings 
SET value = '["ERROR", "WARN", "CRITICAL", "FATAL", "ALERT", "EMERGENCY", "INFO", "DEBUG"]'::jsonb
WHERE key = 'important_log_levels'; 