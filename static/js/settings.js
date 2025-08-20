/**
 * Управление общими настройками системы
 */
class SettingsManager {
    constructor() {
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.loadSettings();
        this.updateSystemInfo();
    }

    setupEventListeners() {
        // Настройки базы данных
        const dbForm = document.getElementById('database-settings-form');
        if (dbForm) {
            dbForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.saveDatabaseSettings();
            });
        }

        // Тест подключения к БД
        const testBtn = document.getElementById('test-connection');
        if (testBtn) {
            testBtn.addEventListener('click', () => {
                this.testDatabaseConnection();
            });
        }

        // Общие настройки
        const generalForm = document.getElementById('general-settings-form');
        if (generalForm) {
            generalForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.saveGeneralSettings();
            });
        }

        // Настройки безопасности
        const securityForm = document.getElementById('security-settings-form');
        if (securityForm) {
            securityForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.saveSecuritySettings();
            });
        }

        // Обновление информации о системе
        const refreshBtn = document.getElementById('refresh-info');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => {
                this.updateSystemInfo();
            });
        }
    }

    async loadSettings() {
        try {
            // Загружаем настройки БД (заглушка - в реальности должны быть из конфига)
            document.getElementById('db-host').value = 'postgres';
            document.getElementById('db-port').value = '5432';
            document.getElementById('db-name').value = 'stools_db';
            document.getElementById('db-user').value = 'stools_user';
            // Пароль не загружаем из соображений безопасности

            this.showNotification('Настройки загружены', 'success');
        } catch (error) {
            console.error('Error loading settings:', error);
            this.showNotification('Ошибка загрузки настроек', 'error');
        }
    }

    async saveDatabaseSettings() {
        const formData = new FormData(document.getElementById('database-settings-form'));
        const settings = Object.fromEntries(formData.entries());

        try {
            // В реальной реализации здесь должен быть API вызов
            console.log('Saving database settings:', settings);
            this.showNotification('Настройки базы данных сохранены', 'success');
        } catch (error) {
            console.error('Error saving database settings:', error);
            this.showNotification('Ошибка сохранения настроек БД', 'error');
        }
    }

    async testDatabaseConnection() {
        const testBtn = document.getElementById('test-connection');
        const originalText = testBtn.innerHTML;
        
        testBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Проверка...';
        testBtn.disabled = true;

        try {
            // В реальной реализации здесь должен быть API вызов
            await new Promise(resolve => setTimeout(resolve, 2000)); // Имитация запроса
            
            this.showNotification('Подключение к базе данных успешно', 'success');
            document.getElementById('db-status').textContent = 'Подключено';
            document.getElementById('db-status').className = 'info-value status-success';
        } catch (error) {
            console.error('Database connection test failed:', error);
            this.showNotification('Ошибка подключения к базе данных', 'error');
            document.getElementById('db-status').textContent = 'Ошибка подключения';
            document.getElementById('db-status').className = 'info-value status-error';
        } finally {
            testBtn.innerHTML = originalText;
            testBtn.disabled = false;
        }
    }

    async saveGeneralSettings() {
        const formData = new FormData(document.getElementById('general-settings-form'));
        const settings = Object.fromEntries(formData.entries());

        try {
            // В реальной реализации здесь должен быть API вызов
            console.log('Saving general settings:', settings);
            this.showNotification('Общие настройки сохранены', 'success');
        } catch (error) {
            console.error('Error saving general settings:', error);
            this.showNotification('Ошибка сохранения общих настроек', 'error');
        }
    }

    async saveSecuritySettings() {
        const formData = new FormData(document.getElementById('security-settings-form'));
        const settings = Object.fromEntries(formData.entries());

        try {
            // В реальной реализации здесь должен быть API вызов
            console.log('Saving security settings:', settings);
            this.showNotification('Настройки безопасности сохранены', 'success');
        } catch (error) {
            console.error('Error saving security settings:', error);
            this.showNotification('Ошибка сохранения настроек безопасности', 'error');
        }
    }

    async updateSystemInfo() {
        try {
            // В реальной реализации здесь должны быть API вызовы к различным сервисам
            document.getElementById('system-version').textContent = '1.0.0';
            document.getElementById('active-users').textContent = '1';
            document.getElementById('system-uptime').textContent = 'Менее часа';
            
            // Проверяем статус БД
            document.getElementById('db-status').textContent = 'Проверка...';
            document.getElementById('db-status').className = 'info-value status-checking';
            
            // Имитация проверки БД
            setTimeout(() => {
                document.getElementById('db-status').textContent = 'Подключено';
                document.getElementById('db-status').className = 'info-value status-success';
            }, 1000);
            
        } catch (error) {
            console.error('Error updating system info:', error);
            this.showNotification('Ошибка обновления информации о системе', 'error');
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
    window.settingsManager = new SettingsManager();
});


