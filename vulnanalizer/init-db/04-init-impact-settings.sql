-- Инициализация настроек Impact для расчета риска
-- Эти настройки необходимы для корректного расчета риска

INSERT INTO settings (key, value) VALUES 
    ('impact_resource_criticality', 'Medium'),
    ('impact_confidential_data', 'Отсутствуют'),
    ('impact_internet_access', 'Недоступен')
ON CONFLICT (key) DO UPDATE SET 
    value = EXCLUDED.value,
    updated_at = CURRENT_TIMESTAMP;
