/**
 * Управление пользователями
 */
class AdminUsers {
    constructor() {
        this.users = [];
        this.filteredUsers = [];
        this.currentUserId = null;
        this.roles = [];
        this.init();
    }

    init() {
        this.checkAuth();
        this.setupEventListeners();
        this.loadRoles();
        this.loadUsers();
    }

    checkAuth() {
        // Ищем единый токен stools_auth_token для всех сервисов STools
        const token = localStorage.getItem('stools_auth_token');
        if (!token) {
            window.location.href = '/auth/';
            return;
        }

        // Проверяем токен
        fetch('/auth/api/me-simple', {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        }).then(response => {
            if (!response.ok) {
                localStorage.removeItem('stools_auth_token');
                localStorage.removeItem('stools_user_info');
                window.location.href = '/auth/';
            } else {
                return response.json();
            }
        }).then(user => {
            if (user && !user.is_admin) {
                // Если пользователь не админ, перенаправляем
                window.location.href = '/auth/';
            }
        }).catch(() => {
            localStorage.removeItem('auth_token');
            window.location.href = '/auth/';
        });
    }

    setupEventListeners() {
        // Кнопка создания пользователя
        const createBtn = document.getElementById('create-user-btn');
        if (createBtn) {
            createBtn.addEventListener('click', () => {
                this.openUserModal();
            });
        }

        // Кнопка обновления
        const refreshBtn = document.getElementById('refresh-users-btn');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => {
                this.loadUsers();
            });
        }

        // Поиск
        document.getElementById('user-search').addEventListener('input', (e) => {
            this.filterUsers();
        });

        // Фильтры
        document.getElementById('status-filter').addEventListener('change', () => {
            this.filterUsers();
        });

        document.getElementById('role-filter').addEventListener('change', () => {
            this.filterUsers();
        });
    }

    async loadUsers() {
        try {
            const token = localStorage.getItem('stools_auth_token');
            if (!token) {
                window.location.href = '/auth/';
                return;
            }

            const response = await fetch('/auth/api/users', {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });
            
            if (response.ok) {
                const data = await response.json();
                this.users = (data.users || []).map(user => {
                    // Если roles - строка, парсим её
                    if (typeof user.roles === 'string') {
                        try {
                            user.roles = JSON.parse(user.roles);
                        } catch (e) {
                            console.error('Ошибка парсинга ролей:', e);
                            user.roles = [];
                        }
                    }
                    return user;
                });
                this.filterUsers();
            } else if (response.status === 401) {
                localStorage.removeItem('stools_auth_token');
                localStorage.removeItem('stools_user_info');
                window.location.href = '/auth/';
            } else {
                throw new Error('Ошибка загрузки пользователей');
            }
        } catch (error) {
            console.error('Ошибка загрузки пользователей:', error);
            this.showNotification('Ошибка загрузки пользователей', 'error');
            this.renderUsers([]);
        }
    }

    async loadRoles() {
        try {
            const token = localStorage.getItem('stools_auth_token');
            if (!token) return;

            const response = await fetch('/auth/api/roles', {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });
            
            if (response.ok) {
                const data = await response.json();
                this.roles = data.roles || [];
            }
        } catch (error) {
            console.error('Ошибка загрузки ролей:', error);
        }
    }

    filterUsers() {
        const searchTerm = document.getElementById('user-search').value.toLowerCase();
        const statusFilter = document.getElementById('status-filter').value;
        const roleFilter = document.getElementById('role-filter').value;

        this.filteredUsers = this.users.filter(user => {
            // Поиск по имени и email
            const matchesSearch = !searchTerm || 
                user.username.toLowerCase().includes(searchTerm) ||
                (user.email && user.email.toLowerCase().includes(searchTerm));

            // Фильтр по статусу
            const matchesStatus = !statusFilter || 
                (statusFilter === 'active' && user.is_active) ||
                (statusFilter === 'inactive' && !user.is_active);

            // Фильтр по роли
            const matchesRole = !roleFilter ||
                (roleFilter === 'admin' && user.is_admin) ||
                (roleFilter === 'user' && !user.is_admin);

            return matchesSearch && matchesStatus && matchesRole;
        });

        this.renderUsers(this.filteredUsers);
    }

    renderUsers(users) {
        const container = document.getElementById('users-list');
        
        if (users.length === 0) {
            container.innerHTML = '<div class="no-users">Пользователи не найдены</div>';
            return;
        }

        const html = users.map(user => {
            // Формируем отображение ролей
            let rolesHtml = '';
            if (user.roles && Array.isArray(user.roles) && user.roles.length > 0) {
                rolesHtml = user.roles.map(role => 
                    `<span class="badge role">${role.description || role.name}</span>`
                ).join('');
            }
            
            return `
            <div class="user-item" data-user-id="${user.id}">
                <div class="user-info">
                    <div class="user-avatar">
                        <i class="fas fa-user"></i>
                    </div>
                    <div class="user-details">
                        <h4>${user.username}</h4>
                        <p>${user.email || 'Email не указан'}</p>
                        <div class="user-badges">
                            ${rolesHtml || '<span class="badge">Нет ролей</span>'}
                            ${user.is_active ? '<span class="badge active">Активный</span>' : '<span class="badge inactive">Неактивный</span>'}
                        </div>
                    </div>
                </div>
                <div class="user-actions">
                    <button class="btn btn-sm btn-primary" onclick="adminUsers.editUser(${user.id})">
                        <i class="fas fa-edit"></i> Редактировать
                    </button>
                    <button class="btn btn-sm btn-warning" onclick="adminUsers.resetPassword(${user.id})">
                        <i class="fas fa-key"></i> Сбросить пароль
                    </button>
                    <button class="btn btn-sm btn-danger" onclick="adminUsers.deleteUser(${user.id})">
                        <i class="fas fa-trash"></i> Удалить
                    </button>
                </div>
            </div>
        `}).join('');

        container.innerHTML = html;
    }

    openUserModal(userId = null) {
        const modal = document.getElementById('user-modal');
        const title = document.getElementById('modal-title');
        const form = document.getElementById('user-form');
        const rolesSelect = document.getElementById('user-roles');
        
        if (!modal) {
            console.error('Модальное окно user-modal не найдено!');
            return;
        }
        
        // Заполняем список ролей
        rolesSelect.innerHTML = this.roles.map(role => 
            `<option value="${role.id}">${role.description || role.name}</option>`
        ).join('');
        
        if (userId) {
            // Редактирование
            const user = this.users.find(u => u.id === userId);
            if (user) {
                title.textContent = 'Редактировать пользователя';
                document.getElementById('user-id').value = user.id;
                document.getElementById('username').value = user.username;
                document.getElementById('email').value = user.email || '';
                document.getElementById('is-admin').checked = user.is_admin;
                document.getElementById('is-active').checked = user.is_active;
                document.getElementById('password').required = false;
                document.getElementById('password').placeholder = 'Оставьте пустым, чтобы не изменять';
                
                // Выбираем роли пользователя
                if (user.roles && Array.isArray(user.roles)) {
                    const userRoleIds = user.roles.map(r => r.id);
                    Array.from(rolesSelect.options).forEach(option => {
                        option.selected = userRoleIds.includes(parseInt(option.value));
                    });
                }
            }
        } else {
            // Создание
            title.textContent = 'Создать пользователя';
            form.reset();
            document.getElementById('password').required = true;
            document.getElementById('password').placeholder = '';
            
            // Перезаполняем роли после reset
            rolesSelect.innerHTML = this.roles.map(role => 
                `<option value="${role.id}">${role.description || role.name}</option>`
            ).join('');
        }
        
        modal.style.display = 'flex';
    }

    closeUserModal() {
        document.getElementById('user-modal').style.display = 'none';
        document.getElementById('user-form').reset();
    }

    async saveUser() {
        const form = document.getElementById('user-form');
        const formData = new FormData(form);
        const userData = Object.fromEntries(formData.entries());
        
        // Обрабатываем чекбоксы
        userData.is_admin = formData.has('is_admin');
        userData.is_active = formData.has('is_active');
        
        // Получаем выбранные роли
        const rolesSelect = document.getElementById('user-roles');
        const selectedRoles = Array.from(rolesSelect.selectedOptions).map(opt => parseInt(opt.value));
        userData.role_ids = selectedRoles;
        
        try {
            const userId = userData.id;
            const url = userId ? `/auth/api/users/${userId}` : '/auth/api/users';
            const method = userId ? 'PUT' : 'POST';
            
            // Убираем пустой пароль при редактировании
            if (userId && !userData.password) {
                delete userData.password;
            }
            
            const token = localStorage.getItem('stools_auth_token');
            const response = await fetch(url, {
                method: method,
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify(userData)
            });

            if (response.ok) {
                this.showNotification(
                    userId ? 'Пользователь обновлен' : 'Пользователь создан', 
                    'success'
                );
                this.closeUserModal();
                this.loadUsers();
            } else {
                const error = await response.json();
                throw new Error(error.detail || 'Ошибка сохранения пользователя');
            }
        } catch (error) {
            console.error('Ошибка сохранения пользователя:', error);
            this.showNotification('Ошибка сохранения пользователя: ' + error.message, 'error');
        }
    }

    editUser(userId) {
        this.openUserModal(userId);
    }

    async resetPassword(userId) {
        const user = this.users.find(u => u.id === userId);
        if (!user) return;

        const newPassword = prompt(`Введите новый пароль для пользователя ${user.username}:`);
        if (!newPassword) return;

        try {
            const token = localStorage.getItem('stools_auth_token');
            const response = await fetch(`/auth/api/users/${userId}/password`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({ password: newPassword })
            });

            if (response.ok) {
                this.showNotification('Пароль обновлен', 'success');
            } else {
                const error = await response.json();
                throw new Error(error.detail || 'Ошибка обновления пароля');
            }
        } catch (error) {
            console.error('Ошибка обновления пароля:', error);
            this.showNotification('Ошибка обновления пароля: ' + error.message, 'error');
        }
    }

    deleteUser(userId) {
        const user = this.users.find(u => u.id === userId);
        if (!user) return;

        document.getElementById('delete-username').textContent = user.username;
        document.getElementById('delete-modal').style.display = 'flex';
        this.currentUserId = userId;
    }

    closeDeleteModal() {
        document.getElementById('delete-modal').style.display = 'none';
        this.currentUserId = null;
    }

    async confirmDelete() {
        if (!this.currentUserId) return;

        try {
            const token = localStorage.getItem('stools_auth_token');
            const response = await fetch(`/auth/api/users/${this.currentUserId}`, {
                method: 'DELETE',
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });

            if (response.ok) {
                this.showNotification('Пользователь удален', 'success');
                this.closeDeleteModal();
                this.loadUsers();
            } else {
                const error = await response.json();
                throw new Error(error.detail || 'Ошибка удаления пользователя');
            }
        } catch (error) {
            console.error('Ошибка удаления пользователя:', error);
            this.showNotification('Ошибка удаления пользователя: ' + error.message, 'error');
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
function closeUserModal() {
    window.adminUsers.closeUserModal();
}

function saveUser() {
    window.adminUsers.saveUser();
}

function closeDeleteModal() {
    window.adminUsers.closeDeleteModal();
}

function confirmDelete() {
    window.adminUsers.confirmDelete();
}

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', () => {
    window.adminUsers = new AdminUsers();
});
