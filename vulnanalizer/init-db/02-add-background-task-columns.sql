-- Миграция для добавления колонок parameters и description в таблицу background_tasks
-- Выполняется только если колонки еще не существуют

-- Добавление колонки parameters (JSONB)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'background_tasks' 
        AND column_name = 'parameters'
    ) THEN
        ALTER TABLE background_tasks ADD COLUMN parameters JSONB;
    END IF;
END $$;

-- Добавление колонки description (TEXT)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'background_tasks' 
        AND column_name = 'description'
    ) THEN
        ALTER TABLE background_tasks ADD COLUMN description TEXT;
    END IF;
END $$;
