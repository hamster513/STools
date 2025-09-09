-- Вставка базовых ролей и прав

-- Базовые роли
INSERT INTO auth.roles (name, description, is_system) VALUES
('super_admin', 'Супер администратор - полный доступ ко всем функциям', true),
('admin', 'Администратор - управление пользователями и настройками', true),
('analyst', 'Аналитик - просмотр и анализ данных', false),
('viewer', 'Наблюдатель - только просмотр данных', false),
('guest', 'Гость - ограниченный доступ', false)
ON CONFLICT (name) DO NOTHING;

-- Базовые права
INSERT INTO auth.permissions (name, description, resource, action) VALUES
-- Системные права
('system.admin', 'Администрирование системы', 'system', 'admin'),
('system.settings', 'Управление настройками системы', 'system', 'write'),
('system.read', 'Просмотр системной информации', 'system', 'read'),

-- Права аутентификации
('auth.admin', 'Администрирование пользователей', 'auth', 'admin'),
('auth.users', 'Управление пользователями', 'auth', 'write'),
('auth.roles', 'Управление ролями', 'auth', 'write'),
('auth.read', 'Просмотр информации о пользователях', 'auth', 'read'),

-- Права анализатора уязвимостей
('vulnanalizer.admin', 'Администрирование анализатора уязвимостей', 'vulnanalizer', 'admin'),
('vulnanalizer.write', 'Загрузка и изменение данных', 'vulnanalizer', 'write'),
('vulnanalizer.read', 'Просмотр данных анализатора', 'vulnanalizer', 'read'),
('vulnanalizer.delete', 'Удаление данных', 'vulnanalizer', 'delete'),

-- Права анализатора логов
('loganalizer.admin', 'Администрирование анализатора логов', 'loganalizer', 'admin'),
('loganalizer.write', 'Загрузка и изменение логов', 'loganalizer', 'write'),
('loganalizer.read', 'Просмотр логов', 'loganalizer', 'read'),
('loganalizer.delete', 'Удаление логов', 'loganalizer', 'delete')
ON CONFLICT (name) DO NOTHING;

-- Назначение прав ролям
-- Супер администратор - все права
INSERT INTO auth.role_permissions (role_id, permission_id)
SELECT r.id, p.id
FROM auth.roles r, auth.permissions p
WHERE r.name = 'super_admin'
ON CONFLICT DO NOTHING;

-- Администратор - все права кроме системного администрирования
INSERT INTO auth.role_permissions (role_id, permission_id)
SELECT r.id, p.id
FROM auth.roles r, auth.permissions p
WHERE r.name = 'admin' 
  AND p.name != 'system.admin'
ON CONFLICT DO NOTHING;

-- Аналитик - чтение и запись данных
INSERT INTO auth.role_permissions (role_id, permission_id)
SELECT r.id, p.id
FROM auth.roles r, auth.permissions p
WHERE r.name = 'analyst' 
  AND (p.action = 'read' OR p.action = 'write')
  AND p.resource IN ('vulnanalizer', 'loganalizer')
ON CONFLICT DO NOTHING;

-- Наблюдатель - только чтение
INSERT INTO auth.role_permissions (role_id, permission_id)
SELECT r.id, p.id
FROM auth.roles r, auth.permissions p
WHERE r.name = 'viewer' 
  AND p.action = 'read'
  AND p.resource IN ('vulnanalizer', 'loganalizer', 'system')
ON CONFLICT DO NOTHING;

-- Гость - только базовое чтение
INSERT INTO auth.role_permissions (role_id, permission_id)
SELECT r.id, p.id
FROM auth.roles r, auth.permissions p
WHERE r.name = 'guest' 
  AND p.name IN ('system.read', 'vulnanalizer.read', 'loganalizer.read')
ON CONFLICT DO NOTHING;

-- Назначение роли супер администратора пользователю admin
INSERT INTO auth.user_roles (user_id, role_id, assigned_by)
SELECT u.id, r.id, u.id
FROM auth.users u, auth.roles r
WHERE u.username = 'admin' AND r.name = 'super_admin'
ON CONFLICT DO NOTHING;
