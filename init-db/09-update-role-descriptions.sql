-- Обновление описаний ролей (убираем подробности, оставляем только название)
UPDATE auth.roles SET description = 'Суперадминистратор' WHERE name = 'super_admin';
UPDATE auth.roles SET description = 'Администратор' WHERE name = 'admin';
UPDATE auth.roles SET description = 'Аналитик' WHERE name = 'analyst';
UPDATE auth.roles SET description = 'Наблюдатель' WHERE name = 'viewer';
UPDATE auth.roles SET description = 'Гость' WHERE name = 'guest';

-- Добавляем поле для сортировки, если его нет
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'auth' 
        AND table_name = 'roles' 
        AND column_name = 'sort_order'
    ) THEN
        ALTER TABLE auth.roles ADD COLUMN sort_order INTEGER DEFAULT 999;
    END IF;
END $$;

-- Устанавливаем порядок сортировки
UPDATE auth.roles SET sort_order = 1 WHERE name = 'super_admin';
UPDATE auth.roles SET sort_order = 2 WHERE name = 'admin';
UPDATE auth.roles SET sort_order = 3 WHERE name = 'analyst';
UPDATE auth.roles SET sort_order = 4 WHERE name = 'viewer';
UPDATE auth.roles SET sort_order = 5 WHERE name = 'guest';

-- Создаем индекс для быстрой сортировки
CREATE INDEX IF NOT EXISTS idx_roles_sort_order ON auth.roles (sort_order);

