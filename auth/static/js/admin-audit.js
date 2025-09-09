/**
 * Управление аудитом и логированием
 */
class AdminAudit {
    constructor() {
        this.currentTab = 'logs';
        this.logs = [];
        this.loginAttempts = [];
        this.sessions = [];
        this.stats = {};
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.loadStats();
        this.loadData();
    }

    setupEventListeners() {
        // Переключение вкладок
        document.querySelectorAll('.audit-tab').forEach(tab => {
            tab.addEventListener('click', (e) => {
                e.preventDefault();
                const tabName = e.target.dataset.tab;
                this.switchTab(tabName);
            });
        });

        // Кнопка обновления
        document.getElementById('refresh-audit-btn').addEventListener('click', () => {
            this.loadData();
        });

        // Фильтры для логов
        document.getElementById('log-user-filter').addEventListener('change', () => {
            this.loadLogs();
        });

        document.getElementById('log-action-filter').addEventListener('change', () => {
            this.loadLogs();
        });

        document.getElementById('log-resource-filter').addEventListener('change', () => {
            this.loadLogs();
        });

        // Фильтры для попыток входа
        document.getElementById('login-username-filter').addEventListener('change', () => {
            this.loadLoginAttempts();
        });

        document.getElementById('login-success-filter').addEventListener('change', () => {
            this.loadLoginAttempts();
        });
    }

    switchTab(tabName) {
        // Обновляем активную вкладку
        document.querySelectorAll('.audit-tab').forEach(tab => {
            tab.classList.remove('active');
        });
        document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');

        // Показываем соответствующий контент
        document.querySelectorAll('.audit-content').forEach(content => {
            content.style.display = 'none';
        });
        document.getElementById(`${tabName}-content`).style.display = 'block';

        this.currentTab = tabName;
        this.loadData();
    }

    async loadStats() {
        try {
            const token = localStorage.getItem('auth_token');
            if (!token) {
                window.location.href = '/auth/';
                return;
            }

            const response = await fetch('/auth/api/audit/stats', {
                headers: { 'Authorization': `Bearer ${token}` }
            });

            if (response.ok) {
                this.stats = await response.json();
                this.renderStats();
            } else if (response.status === 401) {
                localStorage.removeItem('auth_token');
                window.location.href = '/auth/';
            }
        } catch (error) {
            console.error('Ошибка загрузки статистики:', error);
        }
    }

    renderStats() {
        const statsContainer = document.getElementById('audit-stats');
        if (!statsContainer) return;

        statsContainer.innerHTML = `
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-icon">
                        <i class="fas fa-list"></i>
                    </div>
                    <div class="stat-content">
                        <h3>${this.stats.total_events || 0}</h3>
                        <p>Всего событий</p>
                    </div>
                </div>
                <div class="stat-card">
                    <div class="stat-icon">
                        <i class="fas fa-clock"></i>
                    </div>
                    <div class="stat-content">
                        <h3>${this.stats.events_24h || 0}</h3>
                        <p>За 24 часа</p>
                    </div>
                </div>
                <div class="stat-card">
                    <div class="stat-icon">
                        <i class="fas fa-check-circle"></i>
                    </div>
                    <div class="stat-content">
                        <h3>${this.stats.successful_events || 0}</h3>
                        <p>Успешных</p>
                    </div>
                </div>
                <div class="stat-card">
                    <div class="stat-icon">
                        <i class="fas fa-exclamation-circle"></i>
                    </div>
                    <div class="stat-content">
                        <h3>${this.stats.failed_events || 0}</h3>
                        <p>Ошибок</p>
                    </div>
                </div>
                <div class="stat-card">
                    <div class="stat-icon">
                        <i class="fas fa-users"></i>
                    </div>
                    <div class="stat-content">
                        <h3>${this.stats.active_sessions || 0}</h3>
                        <p>Активных сессий</p>
                    </div>
                </div>
                <div class="stat-card">
                    <div class="stat-icon">
                        <i class="fas fa-sign-in-alt"></i>
                    </div>
                    <div class="stat-content">
                        <h3>${this.stats.login_attempts_24h || 0}</h3>
                        <p>Попыток входа (24ч)</p>
                    </div>
                </div>
            </div>
        `;
    }

    async loadData() {
        switch (this.currentTab) {
            case 'logs':
                await this.loadLogs();
                break;
            case 'login-attempts':
                await this.loadLoginAttempts();
                break;
            case 'sessions':
                await this.loadSessions();
                break;
        }
    }

    async loadLogs() {
        try {
            const token = localStorage.getItem('auth_token');
            if (!token) {
                window.location.href = '/auth/';
                return;
            }

            const userFilter = document.getElementById('log-user-filter').value;
            const actionFilter = document.getElementById('log-action-filter').value;
            const resourceFilter = document.getElementById('log-resource-filter').value;

            const params = new URLSearchParams();
            if (userFilter) params.append('user_id', userFilter);
            if (actionFilter) params.append('action', actionFilter);
            if (resourceFilter) params.append('resource', resourceFilter);
            params.append('limit', '100');

            const response = await fetch(`/auth/api/audit/logs?${params}`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });

            if (response.ok) {
                const data = await response.json();
                this.logs = data.logs || [];
                this.renderLogs();
            } else if (response.status === 401) {
                localStorage.removeItem('auth_token');
                window.location.href = '/auth/';
            }
        } catch (error) {
            console.error('Ошибка загрузки логов:', error);
            this.showNotification('Ошибка загрузки логов', 'error');
        }
    }

    renderLogs() {
        const container = document.getElementById('logs-list');
        if (!container) return;

        if (this.logs.length === 0) {
            container.innerHTML = '<div class="no-data">Логи не найдены</div>';
            return;
        }

        const html = this.logs.map(log => `
            <div class="log-item ${log.success ? 'success' : 'error'}">
                <div class="log-row">
                    <div class="log-icon">
                        <i class="fas fa-${this.getActionIcon(log.action)}"></i>
                    </div>
                    <div class="log-time">
                        ${new Date(log.created_at).toLocaleString('ru-RU')}
                    </div>
                    <div class="log-user">
                        ${log.username || 'Система'}
                    </div>
                    <div class="log-ip">
                        ${log.ip_address || 'Неизвестно'}
                    </div>
                    <div class="log-action">
                        ${this.getActionName(log.action)}
                    </div>
                    <div class="log-resource">
                        ${this.getResourceName(log.resource)}
                    </div>
                    ${log.error_message ? `
                        <div class="log-error">
                            <i class="fas fa-exclamation-triangle"></i>
                            ${log.error_message}
                        </div>
                    ` : ''}
                </div>
            </div>
        `).join('');

        container.innerHTML = html;
    }

    async loadLoginAttempts() {
        try {
            const token = localStorage.getItem('auth_token');
            if (!token) {
                window.location.href = '/auth/';
                return;
            }

            const usernameFilter = document.getElementById('login-username-filter').value;
            const successFilter = document.getElementById('login-success-filter').value;

            const params = new URLSearchParams();
            if (usernameFilter) params.append('username', usernameFilter);
            if (successFilter) params.append('success', successFilter);
            params.append('limit', '100');

            const response = await fetch(`/auth/api/audit/login-attempts?${params}`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });

            if (response.ok) {
                const data = await response.json();
                this.loginAttempts = data.attempts || [];
                this.renderLoginAttempts();
            } else if (response.status === 401) {
                localStorage.removeItem('auth_token');
                window.location.href = '/auth/';
            }
        } catch (error) {
            console.error('Ошибка загрузки попыток входа:', error);
            this.showNotification('Ошибка загрузки попыток входа', 'error');
        }
    }

    renderLoginAttempts() {
        const container = document.getElementById('login-attempts-list');
        if (!container) return;

        if (this.loginAttempts.length === 0) {
            container.innerHTML = '<div class="no-data">Попытки входа не найдены</div>';
            return;
        }

        const html = this.loginAttempts.map(attempt => `
            <div class="attempt-item ${attempt.success ? 'success' : 'failed'}">
                <div class="attempt-header">
                    <div class="attempt-status">
                        <i class="fas fa-${attempt.success ? 'check-circle' : 'times-circle'}"></i>
                        <span>${attempt.success ? 'Успешно' : 'Неудачно'}</span>
                    </div>
                    <div class="attempt-time">
                        ${new Date(attempt.created_at).toLocaleString('ru-RU')}
                    </div>
                </div>
                <div class="attempt-details">
                    <div class="attempt-user">
                        <i class="fas fa-user"></i>
                        <span>${attempt.username || 'Неизвестно'}</span>
                    </div>
                    <div class="attempt-ip">
                        <i class="fas fa-globe"></i>
                        <span>${attempt.ip_address || 'Неизвестно'}</span>
                    </div>
                    ${attempt.failure_reason ? `
                        <div class="attempt-reason">
                            <i class="fas fa-exclamation-triangle"></i>
                            <span>${this.getFailureReason(attempt.failure_reason)}</span>
                        </div>
                    ` : ''}
                </div>
            </div>
        `).join('');

        container.innerHTML = html;
    }

    async loadSessions() {
        try {
            const token = localStorage.getItem('auth_token');
            if (!token) {
                window.location.href = '/auth/';
                return;
            }

            const response = await fetch('/auth/api/audit/sessions?limit=100', {
                headers: { 'Authorization': `Bearer ${token}` }
            });

            if (response.ok) {
                const data = await response.json();
                this.sessions = data.sessions || [];
                this.renderSessions();
            } else if (response.status === 401) {
                localStorage.removeItem('auth_token');
                window.location.href = '/auth/';
            }
        } catch (error) {
            console.error('Ошибка загрузки сессий:', error);
            this.showNotification('Ошибка загрузки сессий', 'error');
        }
    }

    renderSessions() {
        const container = document.getElementById('sessions-list');
        if (!container) return;

        if (this.sessions.length === 0) {
            container.innerHTML = '<div class="no-data">Активные сессии не найдены</div>';
            return;
        }

        const html = this.sessions.map(session => `
            <div class="session-item">
                <div class="session-header">
                    <div class="session-user">
                        <i class="fas fa-user"></i>
                        <span>${session.username}</span>
                    </div>
                    <div class="session-status">
                        <span class="status-badge active">Активна</span>
                    </div>
                </div>
                <div class="session-details">
                    <div class="session-ip">
                        <i class="fas fa-globe"></i>
                        <span>${session.ip_address || 'Неизвестно'}</span>
                    </div>
                    <div class="session-login">
                        <i class="fas fa-sign-in-alt"></i>
                        <span>Вход: ${new Date(session.login_at).toLocaleString('ru-RU')}</span>
                    </div>
                    <div class="session-activity">
                        <i class="fas fa-clock"></i>
                        <span>Активность: ${new Date(session.last_activity).toLocaleString('ru-RU')}</span>
                    </div>
                </div>
            </div>
        `).join('');

        container.innerHTML = html;
    }

    getActionIcon(action) {
        const icons = {
            'login': 'sign-in-alt',
            'logout': 'sign-out-alt',
            'create': 'plus',
            'update': 'edit',
            'delete': 'trash',
            'read': 'eye',
            'admin': 'cog'
        };
        return icons[action] || 'circle';
    }

    getActionName(action) {
        const names = {
            'login': 'Вход',
            'logout': 'Выход',
            'create': 'Создание',
            'update': 'Обновление',
            'delete': 'Удаление',
            'read': 'Просмотр',
            'admin': 'Администрирование'
        };
        return names[action] || action;
    }

    getResourceName(resource) {
        const names = {
            'auth': 'Аутентификация',
            'users': 'Пользователи',
            'roles': 'Роли',
            'permissions': 'Права',
            'system': 'Система',
            'vulnanalizer': 'Анализатор уязвимостей',
            'loganalizer': 'Анализатор логов'
        };
        return names[resource] || resource;
    }

    getFailureReason(reason) {
        const reasons = {
            'invalid_credentials': 'Неверные учетные данные',
            'user_disabled': 'Пользователь отключен',
            'account_locked': 'Аккаунт заблокирован',
            'too_many_attempts': 'Слишком много попыток'
        };
        return reasons[reason] || reason;
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

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', () => {
    window.adminAudit = new AdminAudit();
});
