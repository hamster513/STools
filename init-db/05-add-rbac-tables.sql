-- Создание таблиц для ролевой модели RBAC
CREATE SCHEMA IF NOT EXISTS auth;

-- Таблица ролей
CREATE TABLE IF NOT EXISTS auth.roles (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE,
    description TEXT,
    is_system BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Таблица прав (permissions)
CREATE TABLE IF NOT EXISTS auth.permissions (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    resource VARCHAR(50) NOT NULL, -- vulnanalizer, loganalizer, auth, system
    action VARCHAR(50) NOT NULL,   -- read, write, delete, admin
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Связь ролей и прав (many-to-many)
CREATE TABLE IF NOT EXISTS auth.role_permissions (
    role_id INT NOT NULL,
    permission_id INT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (role_id, permission_id),
    FOREIGN KEY (role_id) REFERENCES auth.roles (id) ON DELETE CASCADE,
    FOREIGN KEY (permission_id) REFERENCES auth.permissions (id) ON DELETE CASCADE
);

-- Связь пользователей и ролей (many-to-many)
CREATE TABLE IF NOT EXISTS auth.user_roles (
    user_id INT NOT NULL,
    role_id INT NOT NULL,
    assigned_by INT,
    assigned_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP WITH TIME ZONE,
    PRIMARY KEY (user_id, role_id),
    FOREIGN KEY (user_id) REFERENCES auth.users (id) ON DELETE CASCADE,
    FOREIGN KEY (role_id) REFERENCES auth.roles (id) ON DELETE CASCADE,
    FOREIGN KEY (assigned_by) REFERENCES auth.users (id) ON DELETE SET NULL
);

-- Индексы для производительности
CREATE INDEX IF NOT EXISTS idx_roles_name ON auth.roles (name);
CREATE INDEX IF NOT EXISTS idx_permissions_resource_action ON auth.permissions (resource, action);
CREATE INDEX IF NOT EXISTS idx_user_roles_user_id ON auth.user_roles (user_id);
CREATE INDEX IF NOT EXISTS idx_user_roles_role_id ON auth.user_roles (role_id);
CREATE INDEX IF NOT EXISTS idx_role_permissions_role_id ON auth.role_permissions (role_id);
CREATE INDEX IF NOT EXISTS idx_role_permissions_permission_id ON auth.role_permissions (permission_id);

-- Комментарии к таблицам
COMMENT ON TABLE auth.roles IS 'Таблица ролей пользователей';
COMMENT ON TABLE auth.permissions IS 'Таблица прав доступа';
COMMENT ON TABLE auth.role_permissions IS 'Связь ролей и прав (many-to-many)';
COMMENT ON TABLE auth.user_roles IS 'Связь пользователей и ролей (many-to-many)';

-- Комментарии к полям
COMMENT ON COLUMN auth.roles.name IS 'Название роли';
COMMENT ON COLUMN auth.roles.description IS 'Описание роли';
COMMENT ON COLUMN auth.roles.is_system IS 'Системная роль (нельзя удалить)';

COMMENT ON COLUMN auth.permissions.name IS 'Название права';
COMMENT ON COLUMN auth.permissions.resource IS 'Ресурс (vulnanalizer, loganalizer, auth, system)';
COMMENT ON COLUMN auth.permissions.action IS 'Действие (read, write, delete, admin)';

COMMENT ON COLUMN auth.user_roles.assigned_by IS 'Кто назначил роль';
COMMENT ON COLUMN auth.user_roles.expires_at IS 'Срок действия роли (NULL = бессрочно)';
