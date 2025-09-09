/**
 * Управление ролями и правами
 */
class AdminRoles {
    constructor() {
        this.roles = [];
        this.permissions = [];
        this.filteredRoles = [];
        this.currentRoleId = null;
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.loadData();
    }

    setupEventListeners() {
        // Кнопка создания роли
        document.getElementById('create-role-btn').addEventListener('click', () => {
            this.openRoleModal();
        });

        // Кнопка обновления
        document.getElementById('refresh-roles-btn').addEventListener('click', () => {
            this.loadData();
        });

        // Поиск
        document.getElementById('role-search').addEventListener('input', (e) => {
            this.filterRoles();
        });

        // Фильтры
        document.getElementById('system-filter').addEventListener('change', () => {
            this.filterRoles();
        });
    }

    async loadData() {
        try {
            const token = localStorage.getItem('auth_token');
            if (!token) {
                window.location.href = '/auth/';
                return;
            }

            // Загружаем роли и права параллельно
            const [rolesResponse, permissionsResponse] = await Promise.all([
                fetch('/auth/api/roles', {
                    headers: { 'Authorization': `Bearer ${token}` }
                }),
                fetch('/auth/api/permissions', {
                    headers: { 'Authorization': `Bearer ${token}` }
                })
            ]);

            if (rolesResponse.ok && permissionsResponse.ok) {
                const rolesData = await rolesResponse.json();
                const permissionsData = await permissionsResponse.json();
                
                this.roles = rolesData.roles || [];
                this.permissions = permissionsData.permissions || [];
                
                this.filterRoles();
            } else if (rolesResponse.status === 401 || permissionsResponse.status === 401) {
                localStorage.removeItem('auth_token');
                window.location.href = '/auth/';
            } else {
                throw new Error('Ошибка загрузки данных');
            }
        } catch (error) {
            console.error('Ошибка загрузки данных:', error);
            this.showNotification('Ошибка загрузки данных', 'error');
            this.renderRoles([]);
        }
    }

    filterRoles() {
        const searchTerm = document.getElementById('role-search').value.toLowerCase();
        const systemFilter = document.getElementById('system-filter').value;

        this.filteredRoles = this.roles.filter(role => {
            // Поиск по названию и описанию
            const matchesSearch = !searchTerm || 
                role.name.toLowerCase().includes(searchTerm) ||
                (role.description && role.description.toLowerCase().includes(searchTerm));

            // Фильтр по типу роли
            const matchesSystem = !systemFilter || 
                (systemFilter === 'system' && role.is_system) ||
                (systemFilter === 'custom' && !role.is_system);

            return matchesSearch && matchesSystem;
        });

        this.renderRoles(this.filteredRoles);
    }

    renderRoles(roles) {
        const container = document.getElementById('roles-list');
        
        if (roles.length === 0) {
            container.innerHTML = '<div class="no-roles">Роли не найдены</div>';
            return;
        }

        const html = roles.map(role => `
            <div class="role-item" data-role-id="${role.id}">
                <div class="role-info">
                    <div class="role-header">
                        <h4>${role.name}</h4>
                        <div class="role-badges">
                            ${role.is_system ? '<span class="badge system">Системная</span>' : '<span class="badge custom">Пользовательская</span>'}
                            <span class="badge users">${role.user_count} пользователей</span>
                        </div>
                    </div>
                    <p class="role-description">${role.description || 'Описание отсутствует'}</p>
                    <div class="role-meta">
                        <small>Создана: ${new Date(role.created_at).toLocaleDateString('ru-RU')}</small>
                    </div>
                </div>
                <div class="role-actions">
                    <button class="btn btn-sm btn-primary" onclick="adminRoles.editRole(${role.id})">
                        <i class="fas fa-edit"></i> Редактировать
                    </button>
                    <button class="btn btn-sm btn-info" onclick="adminRoles.managePermissions(${role.id})">
                        <i class="fas fa-key"></i> Права
                    </button>
                    ${!role.is_system ? `
                        <button class="btn btn-sm btn-danger" onclick="adminRoles.deleteRole(${role.id})">
                            <i class="fas fa-trash"></i> Удалить
                        </button>
                    ` : ''}
                </div>
            </div>
        `).join('');

        container.innerHTML = html;
    }

    openRoleModal(roleId = null) {
        const modal = document.getElementById('role-modal');
        const title = document.getElementById('modal-title');
        const form = document.getElementById('role-form');
        
        if (roleId) {
            // Редактирование
            const role = this.roles.find(r => r.id === roleId);
            if (role) {
                title.textContent = 'Редактировать роль';
                document.getElementById('role-id').value = role.id;
                document.getElementById('role-name').value = role.name;
                document.getElementById('role-description').value = role.description || '';
            }
        } else {
            // Создание
            title.textContent = 'Создать роль';
            form.reset();
        }
        
        modal.style.display = 'flex';
    }

    closeRoleModal() {
        document.getElementById('role-modal').style.display = 'none';
        document.getElementById('role-form').reset();
    }

    async saveRole() {
        const form = document.getElementById('role-form');
        const formData = new FormData(form);
        const roleData = Object.fromEntries(formData.entries());
        
        try {
            const token = localStorage.getItem('auth_token');
            const roleId = roleData.id;
            const url = roleId ? `/auth/api/roles/${roleId}` : '/auth/api/roles';
            const method = roleId ? 'PUT' : 'POST';
            
            const response = await fetch(url, {
                method: method,
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'Authorization': `Bearer ${token}`
                },
                body: new URLSearchParams(roleData)
            });

            if (response.ok) {
                this.showNotification(
                    roleId ? 'Роль обновлена' : 'Роль создана', 
                    'success'
                );
                this.closeRoleModal();
                this.loadData();
            } else {
                const error = await response.json();
                throw new Error(error.detail || 'Ошибка сохранения роли');
            }
        } catch (error) {
            console.error('Ошибка сохранения роли:', error);
            this.showNotification('Ошибка сохранения роли: ' + error.message, 'error');
        }
    }

    editRole(roleId) {
        this.openRoleModal(roleId);
    }

    managePermissions(roleId) {
        this.currentRoleId = roleId;
        this.openPermissionsModal();
    }

    openPermissionsModal() {
        const modal = document.getElementById('permissions-modal');
        const role = this.roles.find(r => r.id === this.currentRoleId);
        
        if (role) {
            document.getElementById('permissions-modal-title').textContent = `Права роли: ${role.name}`;
        }
        
        this.renderPermissions();
        modal.style.display = 'flex';
    }

    closePermissionsModal() {
        document.getElementById('permissions-modal').style.display = 'none';
        this.currentRoleId = null;
    }

    renderPermissions() {
        const container = document.getElementById('permissions-list');
        
        // Группируем права по ресурсам
        const groupedPermissions = this.permissions.reduce((groups, permission) => {
            if (!groups[permission.resource]) {
                groups[permission.resource] = [];
            }
            groups[permission.resource].push(permission);
            return groups;
        }, {});

        const html = Object.entries(groupedPermissions).map(([resource, permissions]) => `
            <div class="permission-group">
                <h5>${this.getResourceName(resource)}</h5>
                <div class="permission-items">
                    ${permissions.map(permission => `
                        <label class="permission-item">
                            <input type="checkbox" 
                                   value="${permission.id}" 
                                   data-resource="${permission.resource}"
                                   data-action="${permission.action}">
                            <span class="permission-name">${permission.name}</span>
                            <span class="permission-description">${permission.description}</span>
                        </label>
                    `).join('')}
                </div>
            </div>
        `).join('');

        container.innerHTML = html;
    }

    getResourceName(resource) {
        const names = {
            'system': 'Система',
            'auth': 'Аутентификация',
            'vulnanalizer': 'Анализатор уязвимостей',
            'loganalizer': 'Анализатор логов'
        };
        return names[resource] || resource;
    }

    deleteRole(roleId) {
        const role = this.roles.find(r => r.id === roleId);
        if (!role) return;

        document.getElementById('delete-role-name').textContent = role.name;
        document.getElementById('delete-modal').style.display = 'flex';
        this.currentRoleId = roleId;
    }

    closeDeleteModal() {
        document.getElementById('delete-modal').style.display = 'none';
        this.currentRoleId = null;
    }

    async confirmDelete() {
        if (!this.currentRoleId) return;

        try {
            const token = localStorage.getItem('auth_token');
            const response = await fetch(`/auth/api/roles/${this.currentRoleId}`, {
                method: 'DELETE',
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });

            if (response.ok) {
                this.showNotification('Роль удалена', 'success');
                this.closeDeleteModal();
                this.loadData();
            } else {
                const error = await response.json();
                throw new Error(error.detail || 'Ошибка удаления роли');
            }
        } catch (error) {
            console.error('Ошибка удаления роли:', error);
            this.showNotification('Ошибка удаления роли: ' + error.message, 'error');
        }
    }

    showNotification(message, type = 'info') {
        const container = document.getElementById('notifications');
        if (!container) return;

        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.innerHTML = `
            <div class="notification-content">
                <i class="fas fa-${this.getNotificationIcon(type)}"></i>
                <span>${message}</span>
            </div>
            <button class="notification-close" onclick="this.parentElement.remove()">
                <i class="fas fa-times"></i>
            </button>
        `;

        container.appendChild(notification);

        setTimeout(() => {
            if (notification.parentElement) {
                notification.remove();
            }
        }, 5000);
    }

    getNotificationIcon(type) {
        const icons = {
            'success': 'check-circle',
            'error': 'exclamation-circle',
            'warning': 'exclamation-triangle',
            'info': 'info-circle'
        };
        return icons[type] || 'info-circle';
    }
}

// Глобальные функции для вызова из HTML
function closeRoleModal() {
    window.adminRoles.closeRoleModal();
}

function saveRole() {
    window.adminRoles.saveRole();
}

function closePermissionsModal() {
    window.adminRoles.closePermissionsModal();
}

function closeDeleteModal() {
    window.adminRoles.closeDeleteModal();
}

function confirmDelete() {
    window.adminRoles.confirmDelete();
}

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', () => {
    window.adminRoles = new AdminRoles();
});
