-- Миграция для добавления недостающих колонок в таблицу background_tasks
-- Выполняется только если колонки еще не существуют

-- Добавление колонки total_items (INTEGER)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'background_tasks' 
        AND column_name = 'total_items'
    ) THEN
        ALTER TABLE background_tasks ADD COLUMN total_items INTEGER DEFAULT 0;
    END IF;
END $$;

-- Добавление колонки processed_items (INTEGER)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'background_tasks' 
        AND column_name = 'processed_items'
    ) THEN
        ALTER TABLE background_tasks ADD COLUMN processed_items INTEGER DEFAULT 0;
    END IF;
END $$;

-- Добавление колонки total_records (INTEGER)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'background_tasks' 
        AND column_name = 'total_records'
    ) THEN
        ALTER TABLE background_tasks ADD COLUMN total_records INTEGER DEFAULT 0;
    END IF;
END $$;

-- Добавление колонки updated_records (INTEGER)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'background_tasks' 
        AND column_name = 'updated_records'
    ) THEN
        ALTER TABLE background_tasks ADD COLUMN updated_records INTEGER DEFAULT 0;
    END IF;
END $$;

-- Добавление колонки current_step (TEXT)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'background_tasks' 
        AND column_name = 'current_step'
    ) THEN
        ALTER TABLE background_tasks ADD COLUMN current_step TEXT;
    END IF;
END $$;
