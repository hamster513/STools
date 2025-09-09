/**
 * Админ-панель Dashboard
 */
class AdminDashboard {
    constructor() {
        this.init();
    }

    init() {
        this.loadStatistics();
        this.loadRecentActivity();
        this.updateSystemInfo();
        
        // Обновляем статистику каждые 30 секунд
        setInterval(() => {
            this.loadStatistics();
        }, 30000);
    }

    async loadStatistics() {
        try {
            // Загружаем статистику пользователей
            const usersResponse = await fetch('/auth/api/users');
            if (usersResponse.ok) {
                const users = await usersResponse.json();
                
                document.getElementById('total-users').textContent = users.length;
                document.getElementById('active-users').textContent = users.filter(u => u.is_active).length;
                document.getElementById('admin-users').textContent = users.filter(u => u.is_admin).length;
            }
            
            // Загружаем статистику входов (заглушка)
            document.getElementById('recent-logins').textContent = '12';
            
        } catch (error) {
            console.error('Ошибка загрузки статистики:', error);
            this.showNotification('Ошибка загрузки статистики', 'error');
        }
    }

    async loadRecentActivity() {
        try {
            // Заглушка для последних действий
            const activities = [
                {
                    user: 'admin',
                    action: 'Создал пользователя',
                    target: 'user123',
                    time: '2 минуты назад',
                    icon: 'fas fa-user-plus',
                    type: 'success'
                },
                {
                    user: 'user123',
                    action: 'Вход в систему',
                    target: '',
                    time: '5 минут назад',
                    icon: 'fas fa-sign-in-alt',
                    type: 'info'
                },
                {
                    user: 'admin',
                    action: 'Изменил права',
                    target: 'user456',
                    time: '10 минут назад',
                    icon: 'fas fa-user-shield',
                    type: 'warning'
                },
                {
                    user: 'user456',
                    action: 'Выход из системы',
                    target: '',
                    time: '15 минут назад',
                    icon: 'fas fa-sign-out-alt',
                    type: 'info'
                }
            ];

            this.renderRecentActivity(activities);
            
        } catch (error) {
            console.error('Ошибка загрузки активности:', error);
            document.getElementById('recent-activity-list').innerHTML = 
                '<div class="error">Ошибка загрузки последних действий</div>';
        }
    }

    renderRecentActivity(activities) {
        const container = document.getElementById('recent-activity-list');
        
        if (activities.length === 0) {
            container.innerHTML = '<div class="no-activity">Нет недавних действий</div>';
            return;
        }

        const html = activities.map(activity => `
            <div class="activity-item ${activity.type}">
                <div class="activity-icon">
                    <i class="${activity.icon}"></i>
                </div>
                <div class="activity-content">
                    <div class="activity-text">
                        <strong>${activity.user}</strong> ${activity.action}
                        ${activity.target ? `<span class="activity-target">${activity.target}</span>` : ''}
                    </div>
                    <div class="activity-time">${activity.time}</div>
                </div>
            </div>
        `).join('');

        container.innerHTML = html;
    }

    async updateSystemInfo() {
        try {
            // Проверяем статус БД
            const healthResponse = await fetch('/auth/health');
            if (healthResponse.ok) {
                document.getElementById('db-status').textContent = 'Подключено';
                document.getElementById('db-status').className = 'info-value status-success';
            } else {
                document.getElementById('db-status').textContent = 'Ошибка';
                document.getElementById('db-status').className = 'info-value status-error';
            }
            
            // Время работы (заглушка)
            document.getElementById('uptime').textContent = '2 дня 14 часов';
            
            // Последний бэкап (заглушка)
            document.getElementById('last-backup').textContent = 'Сегодня 10:30';
            
        } catch (error) {
            console.error('Ошибка обновления системной информации:', error);
            document.getElementById('db-status').textContent = 'Неизвестно';
            document.getElementById('db-status').className = 'info-value status-unknown';
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

        // Автоматически убираем уведомление через 5 секунд
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
    window.adminDashboard = new AdminDashboard();
});
