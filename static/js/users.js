class UsersManager {
    constructor() {
        this.currentUser = null;
        this.init();
    }

    init() {
        this.checkAuth();
        this.setupEventListeners();
        this.loadUsers();
    }

    checkAuth() {
        const token = localStorage.getItem('auth_token');
        if (!token) {
            window.location.href = '/auth/';
            return;
        }

        // Проверяем права администратора
        const userInfo = localStorage.getItem('user_info');
        if (userInfo) {
            try {
                const user = JSON.parse(userInfo);
                if (!user.is_admin) {
                    this.showNotification('Доступ запрещен: требуются права администратора', 'error');
                    window.history.back();
                    return;
                }
            } catch (e) {
                console.error('Error parsing user info:', e);
            }
        }
    }

    setupEventListeners() {
        // Кнопка добавления пользователя
        const addUserBtn = document.getElementById('add-user-btn');
        if (addUserBtn) {
            addUserBtn.addEventListener('click', () => this.openUserModal());
        }

        // Кнопка обновления списка
        const refreshUsersBtn = document.getElementById('refresh-users-btn');
        if (refreshUsersBtn) {
            refreshUsersBtn.addEventListener('click', () => this.loadUsers());
        }
    }

    async loadUsers() {
        try {
            const response = await fetch('/auth/api/users', {
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('auth_token')}`
                }
            });

            if (response.ok) {
                const data = await response.json();
                this.renderUsers(data.users || data);
            } else {
                this.showNotification('Ошибка загрузки пользователей', 'error');
            }
        } catch (error) {
            console.error('Error loading users:', error);
            this.showNotification('Ошибка загрузки пользователей', 'error');
        }
    }

    renderUsers(users) {
        const usersList = document.getElementById('users-list');
        if (!usersList) return;

        if (users.length === 0) {
            usersList.innerHTML = '<p class="no-users">Нет пользователей</p>';
            return;
        }

        usersList.innerHTML = users.map(user => `
            <div class="user-item">
                <div class="user-info">
                    <div class="user-avatar">
                        <i class="fas fa-user"></i>
                    </div>
                    <div class="user-details">
                        <h4>${user.username}</h4>
                        <p>${user.email || 'Email не указан'}</p>
                        <div class="user-badges">
                            ${user.is_admin ? '<span class="badge admin">Администратор</span>' : ''}
                            ${user.is_active ? '<span class="badge active">Активен</span>' : '<span class="badge inactive">Неактивен</span>'}
                        </div>
                    </div>
                </div>
                <div class="user-actions">
                    <button class="btn btn-sm btn-primary" onclick="usersManager.editUser(${user.id})">
                        <i class="fas fa-edit"></i> Редактировать
                    </button>
                    ${user.id !== 1 ? `<button class="btn btn-sm btn-danger" onclick="usersManager.deleteUser(${user.id})">
                        <i class="fas fa-trash"></i> Удалить
                    </button>` : ''}
                </div>
            </div>
        `).join('');
    }

    openUserModal(userId = null) {
        const modal = document.getElementById('user-modal');
        const title = document.getElementById('user-modal-title');
        const form = document.getElementById('user-form');

        if (userId) {
            title.textContent = 'Редактировать пользователя';
            this.loadUserData(userId);
        } else {
            title.textContent = 'Добавить пользователя';
            form.reset();
        }

        modal.style.display = 'block';
        this.currentUser = userId;
    }

    async loadUserData(userId) {
        try {
            const response = await fetch(`/auth/api/users/${userId}`, {
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('auth_token')}`
                }
            });

            if (response.ok) {
                const user = await response.json();
                document.getElementById('username').value = user.username;
                document.getElementById('email').value = user.email || '';
                document.getElementById('is_admin').checked = user.is_admin;
                document.getElementById('is_active').checked = user.is_active;
            }
        } catch (error) {
            console.error('Error loading user data:', error);
            this.showNotification('Ошибка загрузки данных пользователя', 'error');
        }
    }

    async saveUser() {
        const form = document.getElementById('user-form');
        const formData = new FormData(form);
        
        const userData = {
            username: formData.get('username'),
            email: formData.get('email'),
            password: formData.get('password'),
            is_admin: formData.get('is_admin') === 'on',
            is_active: formData.get('is_active') === 'on'
        };

        try {
            const url = this.currentUser 
                ? `/auth/api/users/${this.currentUser}`
                : '/auth/api/users';
            
            const method = this.currentUser ? 'PUT' : 'POST';

            const response = await fetch(url, {
                method: method,
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${localStorage.getItem('auth_token')}`
                },
                body: JSON.stringify(userData)
            });

            if (response.ok) {
                this.showNotification(
                    this.currentUser ? 'Пользователь обновлен' : 'Пользователь создан', 
                    'success'
                );
                this.closeUserModal();
                this.loadUsers();
            } else {
                const error = await response.json();
                this.showNotification(error.detail || 'Ошибка сохранения', 'error');
            }
        } catch (error) {
            console.error('Error saving user:', error);
            this.showNotification('Ошибка сохранения пользователя', 'error');
        }
    }

    async deleteUser(userId) {
        if (!confirm('Вы уверены, что хотите удалить этого пользователя?')) {
            return;
        }

        try {
            const response = await fetch(`/auth/api/users/${userId}`, {
                method: 'DELETE',
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('auth_token')}`
                }
            });

            if (response.ok) {
                this.showNotification('Пользователь удален', 'success');
                this.loadUsers();
            } else {
                this.showNotification('Ошибка удаления пользователя', 'error');
            }
        } catch (error) {
            console.error('Error deleting user:', error);
            this.showNotification('Ошибка удаления пользователя', 'error');
        }
    }

    closeUserModal() {
        const modal = document.getElementById('user-modal');
        modal.style.display = 'none';
        this.currentUser = null;
    }

    showNotification(message, type = 'info') {
        if (window.uiManager && window.uiManager.showNotification) {
            window.uiManager.showNotification(message, type);
        } else {
            alert(message);
        }
    }
}

// Глобальные функции для модального окна
function closeUserModal() {
    if (window.usersManager) {
        window.usersManager.closeUserModal();
    }
}

function saveUser() {
    if (window.usersManager) {
        window.usersManager.saveUser();
    }
}

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', () => {
    window.usersManager = new UsersManager();
});
