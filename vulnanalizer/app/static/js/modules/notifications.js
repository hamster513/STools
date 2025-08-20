/**
 * Модуль управления уведомлениями
 */
class NotificationsModule {
    constructor() {
        this.init();
    }

    init() {
        // Создаем контейнер для уведомлений если его нет
        if (!document.getElementById('notifications')) {
            const notificationsContainer = document.createElement('div');
            notificationsContainer.id = 'notifications';
            notificationsContainer.className = 'notifications-container';
            document.body.appendChild(notificationsContainer);
        }
    }

    /**
     * Показать уведомление
     * @param {string} message - Текст сообщения
     * @param {string} type - Тип уведомления (info, success, error, warning)
     * @param {number} duration - Длительность показа в миллисекундах
     */
    show(message, type = 'info', duration = 5000) {
        const notifications = document.getElementById('notifications');
        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        
        let icon = 'fas fa-info-circle';
        switch (type) {
            case 'success':
                icon = 'fas fa-check-circle';
                break;
            case 'error':
                icon = 'fas fa-exclamation-circle';
                break;
            case 'warning':
                icon = 'fas fa-exclamation-triangle';
                break;
        }

        notification.innerHTML = `
            <i class="${icon}"></i>
            <span>${message}</span>
            <button class="notification-close" onclick="this.parentElement.remove()">
                <i class="fas fa-times"></i>
            </button>
        `;

        notifications.appendChild(notification);

        // Анимация появления
        setTimeout(() => {
            notification.classList.add('show');
        }, 10);

        // Автоматическое удаление
        if (duration > 0) {
            setTimeout(() => {
                this.remove(notification);
            }, duration);
        }

        return notification;
    }

    /**
     * Удалить уведомление
     * @param {HTMLElement} notification - Элемент уведомления
     */
    remove(notification) {
        if (notification && notification.parentElement) {
            notification.classList.remove('show');
            setTimeout(() => {
                notification.remove();
            }, 300);
        }
    }

    /**
     * Очистить все уведомления
     */
    clear() {
        const notifications = document.getElementById('notifications');
        if (notifications) {
            notifications.innerHTML = '';
        }
    }

    /**
     * Показать информационное уведомление
     * @param {string} message - Текст сообщения
     */
    info(message) {
        return this.show(message, 'info');
    }

    /**
     * Показать уведомление об успехе
     * @param {string} message - Текст сообщения
     */
    success(message) {
        return this.show(message, 'success');
    }

    /**
     * Показать уведомление об ошибке
     * @param {string} message - Текст сообщения
     */
    error(message) {
        return this.show(message, 'error');
    }

    /**
     * Показать предупреждение
     * @param {string} message - Текст сообщения
     */
    warning(message) {
        return this.show(message, 'warning');
    }

    /**
     * Показать подтверждение
     * @param {string} message - Текст сообщения
     * @param {Function} onConfirm - Функция при подтверждении
     * @param {Function} onCancel - Функция при отмене
     */
    confirm(message, onConfirm, onCancel) {
        const notification = document.createElement('div');
        notification.className = 'notification confirm';
        
        notification.innerHTML = `
            <i class="fas fa-question-circle"></i>
            <span>${message}</span>
            <div class="notification-actions">
                <button class="btn btn-primary btn-sm" onclick="this.closest('.notification').confirmAction()">
                    Да
                </button>
                <button class="btn btn-secondary btn-sm" onclick="this.closest('.notification').cancelAction()">
                    Нет
                </button>
            </div>
        `;

        // Добавляем методы к элементу
        notification.confirmAction = () => {
            this.remove(notification);
            if (onConfirm) onConfirm();
        };

        notification.cancelAction = () => {
            this.remove(notification);
            if (onCancel) onCancel();
        };

        const notifications = document.getElementById('notifications');
        notifications.appendChild(notification);

        setTimeout(() => {
            notification.classList.add('show');
        }, 10);

        return notification;
    }

    /**
     * Показать прогресс-уведомление
     * @param {string} message - Текст сообщения
     * @param {number} progress - Прогресс в процентах (0-100)
     */
    progress(message, progress = 0) {
        const notification = document.createElement('div');
        notification.className = 'notification progress';
        
        notification.innerHTML = `
            <i class="fas fa-spinner fa-spin"></i>
            <span>${message}</span>
            <div class="progress-bar">
                <div class="progress-fill" style="width: ${progress}%"></div>
            </div>
            <span class="progress-text">${progress.toFixed(1)}%</span>
        `;

        const notifications = document.getElementById('notifications');
        notifications.appendChild(notification);

        setTimeout(() => {
            notification.classList.add('show');
        }, 10);

        return notification;
    }

    /**
     * Обновить прогресс уведомления
     * @param {HTMLElement} notification - Элемент уведомления
     * @param {number} progress - Новый прогресс в процентах
     * @param {string} message - Новый текст сообщения
     */
    updateProgress(notification, progress, message = null) {
        if (notification && notification.classList.contains('progress')) {
            const progressFill = notification.querySelector('.progress-fill');
            const progressText = notification.querySelector('.progress-text');
            const messageSpan = notification.querySelector('span:not(.progress-text)');

            if (progressFill) {
                progressFill.style.width = `${progress}%`;
            }
            if (progressText) {
                progressText.textContent = `${progress.toFixed(1)}%`;
            }
            if (message && messageSpan) {
                messageSpan.textContent = message;
            }
        }
    }
}

// Экспорт модуля
if (typeof module !== 'undefined' && module.exports) {
    module.exports = NotificationsModule;
} else {
    window.NotificationsModule = NotificationsModule;
}
