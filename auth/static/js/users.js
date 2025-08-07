class UsersManager {
    constructor() {
        this.currentUser = null;
        this.editingUserId = null;
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

        // Проверяем токен
        fetch('/auth/api/me', {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        }).then(response => {
            if (!response.ok) {
                localStorage.removeItem('auth_token');
                window.location.href = '/auth/';
            } else {
                return response.json();
            }
        }).then(user => {
            if (user && !user.is_admin) {
                alert('Доступ запрещен. Требуются права администратора.');
                window.close();
            }
        }).catch(() => {
            localStorage.removeItem('auth_token');
            window.location.href = '/auth/';
        });
    }

    setupEventListeners() {
        // Кнопка добавления пользователя
        document.getElementById('add-user-btn').addEventListener('click', () => {
            this.openUserModal();
        });

        // Модальное окно пользователя
        document.getElementById('close-modal').addEventListener('click', () => {
            this.closeUserModal();
        });

        document.getElementById('cancel-btn').addEventListener('click', () => {
            this.closeUserModal();
        });

        document.getElementById('save-btn').addEventListener('click', () => {
            this.saveUser();
        });

        // Модальное окно пароля
        document.getElementById('close-password-modal').addEventListener('click', () => {
            this.closePasswordModal();
        });

        document.getElementById('cancel-password-btn').addEventListener('click', () => {
            this.closePasswordModal();
        });

        document.getElementById('save-password-btn').addEventListener('click', () => {
            this.savePassword();
        });

        // Закрытие модальных окон при клике вне их
        window.addEventListener('click', (e) => {
            if (e.target.classList.contains('modal')) {
                e.target.classList.remove('show');
            }
        });
    }

    async loadUsers() {
        try {
            const token = localStorage.getItem('auth_token');
            const response = await fetch('/auth/api/users', {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });

            if (response.ok) {
                const data = await response.json();
                this.renderUsers(data.users);
            } else {
                this.showError('Ошибка загрузки пользователей');
            }
        } catch (error) {
            console.error('Error loading users:', error);
            this.showError('Ошибка соединения с сервером');
        }
    }

    renderUsers(users) {
        const usersList = document.getElementById('users-list');
        usersList.innerHTML = '';

        users.forEach(user => {
            const userCard = this.createUserCard(user);
            usersList.appendChild(userCard);
        });
    }

    createUserCard(user) {
        const card = document.createElement('div');
        card.className = 'user-card';
        
        const badges = [];
        if (user.is_admin) badges.push('<span class="user-badge admin">Админ</span>');
        if (user.is_active) {
            badges.push('<span class="user-badge active">Активен</span>');
        } else {
            badges.push('<span class="user-badge inactive">Неактивен</span>');
        }

        card.innerHTML = `
            <div class="user-header">
                <div class="user-info">
                    <h3>${user.username}</h3>
                    <div class="user-email">${user.email || 'Email не указан'}</div>
                </div>
                <div class="user-badges">
                    ${badges.join('')}
                </div>
            </div>
            <div class="user-actions">
                <button class="btn btn-secondary edit-user" data-user-id="${user.id}">
                    <i class="fas fa-edit"></i> Редактировать
                </button>
                <button class="btn btn-secondary change-password" data-user-id="${user.id}">
                    <i class="fas fa-key"></i> Сменить пароль
                </button>
                ${user.id !== 1 ? `<button class="btn btn-danger delete-user" data-user-id="${user.id}">
                    <i class="fas fa-trash"></i> Удалить
                </button>` : ''}
            </div>
        `;

        // Добавляем обработчики событий
        card.querySelector('.edit-user').addEventListener('click', () => {
            this.editUser(user);
        });

        card.querySelector('.change-password').addEventListener('click', () => {
            this.changePassword(user.id);
        });

        const deleteBtn = card.querySelector('.delete-user');
        if (deleteBtn) {
            deleteBtn.addEventListener('click', () => {
                this.deleteUser(user.id);
            });
        }

        return card;
    }

    openUserModal(user = null) {
        this.editingUserId = user ? user.id : null;
        const modal = document.getElementById('user-modal');
        const title = document.getElementById('modal-title');
        const form = document.getElementById('user-form');

        if (user) {
            title.textContent = 'Редактировать пользователя';
            form.username.value = user.username;
            form.email.value = user.email || '';
            form['is-admin'].checked = user.is_admin;
            form['is-active'].checked = user.is_active;
            form.password.required = false;
            form['confirm-password'].required = false;
        } else {
            title.textContent = 'Добавить пользователя';
            form.reset();
            form.password.required = true;
            form['confirm-password'].required = true;
        }

        modal.classList.add('show');
    }

    closeUserModal() {
        const modal = document.getElementById('user-modal');
        modal.classList.remove('show');
        this.editingUserId = null;
    }

    async saveUser() {
        const form = document.getElementById('user-form');
        const formData = new FormData(form);

        const userData = {
            username: formData.get('username'),
            email: formData.get('email'),
            password: formData.get('password'),
            confirm_password: formData.get('confirm-password'),
            is_admin: formData.get('is-admin') === 'on',
            is_active: formData.get('is-active') === 'on'
        };

        // Валидация
        if (!userData.username) {
            this.showError('Имя пользователя обязательно');
            return;
        }

        if (!this.editingUserId && (!userData.password || userData.password !== userData.confirm_password)) {
            this.showError('Пароли не совпадают');
            return;
        }

        try {
            const token = localStorage.getItem('auth_token');
            const url = this.editingUserId 
                ? `/auth/api/users/${this.editingUserId}`
                : '/auth/api/users';
            
            const method = this.editingUserId ? 'PUT' : 'POST';
            const body = this.editingUserId 
                ? JSON.stringify({
                    username: userData.username,
                    email: userData.email,
                    is_admin: userData.is_admin,
                    is_active: userData.is_active
                })
                : JSON.stringify({
                    username: userData.username,
                    email: userData.email,
                    password: userData.password,
                    is_admin: userData.is_admin
                });

            const response = await fetch(url, {
                method: method,
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                },
                body: body
            });

            if (response.ok) {
                this.showSuccess(this.editingUserId ? 'Пользователь обновлен' : 'Пользователь создан');
                this.closeUserModal();
                this.loadUsers();
            } else {
                const error = await response.json();
                this.showError(error.detail || 'Ошибка сохранения');
            }
        } catch (error) {
            console.error('Error saving user:', error);
            this.showError('Ошибка соединения с сервером');
        }
    }

    editUser(user) {
        this.openUserModal(user);
    }

    changePassword(userId) {
        this.editingUserId = userId;
        const modal = document.getElementById('password-modal');
        modal.classList.add('show');
    }

    closePasswordModal() {
        const modal = document.getElementById('password-modal');
        modal.classList.remove('show');
        this.editingUserId = null;
    }

    async savePassword() {
        const form = document.getElementById('password-form');
        const formData = new FormData(form);

        const passwordData = {
            password: formData.get('new-password'),
            confirm_password: formData.get('confirm-new-password')
        };

        if (!passwordData.password || passwordData.password !== passwordData.confirm_password) {
            this.showError('Пароли не совпадают');
            return;
        }

        try {
            const token = localStorage.getItem('auth_token');
            const response = await fetch(`/auth/api/users/${this.editingUserId}/password`, {
                method: 'PUT',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    password: passwordData.password
                })
            });

            if (response.ok) {
                this.showSuccess('Пароль изменен');
                this.closePasswordModal();
            } else {
                const error = await response.json();
                this.showError(error.detail || 'Ошибка изменения пароля');
            }
        } catch (error) {
            console.error('Error changing password:', error);
            this.showError('Ошибка соединения с сервером');
        }
    }

    async deleteUser(userId) {
        if (!confirm('Вы уверены, что хотите удалить этого пользователя?')) {
            return;
        }

        try {
            const token = localStorage.getItem('auth_token');
            const response = await fetch(`/auth/api/users/${userId}`, {
                method: 'DELETE',
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });

            if (response.ok) {
                this.showSuccess('Пользователь удален');
                this.loadUsers();
            } else {
                const error = await response.json();
                this.showError(error.detail || 'Ошибка удаления');
            }
        } catch (error) {
            console.error('Error deleting user:', error);
            this.showError('Ошибка соединения с сервером');
        }
    }

    showSuccess(message) {
        alert(message); // В будущем можно заменить на красивые уведомления
    }

    showError(message) {
        alert('Ошибка: ' + message); // В будущем можно заменить на красивые уведомления
    }
}

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', () => {
    new UsersManager();
});
