-- ===== METASPLOIT SCHEMA =====

-- Проверяем, существует ли таблица в схеме public и мигрируем её
DO $$
BEGIN
    -- Если таблица существует в public, переносим её в vulnanalizer
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'metasploit_modules') THEN
        
        -- Создаем таблицу в vulnanalizer, если её там нет
        IF NOT EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'vulnanalizer' AND table_name = 'metasploit_modules') THEN
            
            -- Создаем таблицу в правильной схеме
            CREATE TABLE vulnanalizer.metasploit_modules (
                id SERIAL PRIMARY KEY,
                module_name VARCHAR(500) NOT NULL UNIQUE,
                name TEXT NOT NULL,
                fullname VARCHAR(500) NOT NULL,
                rank INTEGER NOT NULL,
                rank_text VARCHAR(20) GENERATED ALWAYS AS (
                    CASE 
                        WHEN rank = 0 THEN 'manual'
                        WHEN rank = 200 THEN 'low'
                        WHEN rank = 300 THEN 'average'
                        WHEN rank = 400 THEN 'normal'
                        WHEN rank = 500 THEN 'good'
                        WHEN rank = 600 THEN 'excellent'
                        ELSE 'unknown'
                    END
                ) STORED,
                disclosure_date DATE,
                type VARCHAR(50) NOT NULL,
                description TEXT,
                "references" TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            -- Создаем индексы
            CREATE INDEX IF NOT EXISTS idx_metasploit_module_name ON vulnanalizer.metasploit_modules(module_name);
            CREATE INDEX IF NOT EXISTS idx_metasploit_rank ON vulnanalizer.metasploit_modules(rank);
            CREATE INDEX IF NOT EXISTS idx_metasploit_type ON vulnanalizer.metasploit_modules(type);
            CREATE INDEX IF NOT EXISTS idx_metasploit_disclosure_date ON vulnanalizer.metasploit_modules(disclosure_date);
            
            -- Копируем данные из public.metasploit_modules в vulnanalizer.metasploit_modules
            INSERT INTO vulnanalizer.metasploit_modules (
                module_name, name, fullname, rank, disclosure_date, type, description, "references", created_at, updated_at
            )
            SELECT 
                module_name, 
                name, 
                COALESCE(fullname, name) as fullname, 
                rank, 
                disclosure_date, 
                type, 
                description, 
                "references", 
                created_at, 
                updated_at
            FROM public.metasploit_modules;
            
            -- Удаляем таблицу из схемы public
            DROP TABLE public.metasploit_modules;
            
            RAISE NOTICE 'Таблица metasploit_modules успешно перенесена из public в vulnanalizer';
        ELSE
            RAISE NOTICE 'Таблица metasploit_modules уже существует в схеме vulnanalizer';
        END IF;
    ELSE
        -- Если таблицы нет нигде, создаем новую
        IF NOT EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'vulnanalizer' AND table_name = 'metasploit_modules') THEN
            CREATE TABLE vulnanalizer.metasploit_modules (
                id SERIAL PRIMARY KEY,
                module_name VARCHAR(500) NOT NULL UNIQUE,
                name TEXT NOT NULL,
                fullname VARCHAR(500) NOT NULL,
                rank INTEGER NOT NULL,
                rank_text VARCHAR(20) GENERATED ALWAYS AS (
                    CASE 
                        WHEN rank = 0 THEN 'manual'
                        WHEN rank = 200 THEN 'low'
                        WHEN rank = 300 THEN 'average'
                        WHEN rank = 400 THEN 'normal'
                        WHEN rank = 500 THEN 'good'
                        WHEN rank = 600 THEN 'excellent'
                        ELSE 'unknown'
                    END
                ) STORED,
                disclosure_date DATE,
                type VARCHAR(50) NOT NULL,
                description TEXT,
                "references" TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            RAISE NOTICE 'Таблица metasploit_modules создана в схеме vulnanalizer';
        END IF;
    END IF;
END $$;

-- Создание индексов для оптимизации поиска
CREATE INDEX IF NOT EXISTS idx_metasploit_module_name ON vulnanalizer.metasploit_modules(module_name);
CREATE INDEX IF NOT EXISTS idx_metasploit_rank ON vulnanalizer.metasploit_modules(rank);
CREATE INDEX IF NOT EXISTS idx_metasploit_type ON vulnanalizer.metasploit_modules(type);
CREATE INDEX IF NOT EXISTS idx_metasploit_disclosure_date ON vulnanalizer.metasploit_modules(disclosure_date);

-- Создание триггера для автоматического обновления updated_at
CREATE OR REPLACE FUNCTION update_metasploit_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER trigger_metasploit_updated_at
    BEFORE UPDATE ON vulnanalizer.metasploit_modules 
    FOR EACH ROW 
    EXECUTE FUNCTION update_metasploit_updated_at();

-- Предоставление прав доступа
GRANT ALL PRIVILEGES ON TABLE vulnanalizer.metasploit_modules TO stools_user;
GRANT USAGE, SELECT ON SEQUENCE vulnanalizer.metasploit_modules_id_seq TO stools_user;
