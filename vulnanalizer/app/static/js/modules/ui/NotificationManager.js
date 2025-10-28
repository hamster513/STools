/**
 * NotificationManager - Централизованное управление уведомлениями
 * v=7.2
 */
class NotificationManager {
    constructor(app) {
        this.app = app;
        this.notifications = [];
        this.maxNotifications = 5;
        this.defaultTimeout = 5000;
        this.container = null;
        this.init();
    }

    init() {
        this.createContainer();
        this.setupStyles();
    }

    createContainer() {
        this.container = document.createElement('div');
        this.container.id = 'notification-container';
        this.container.className = 'notification-container';
        document.body.appendChild(this.container);
    }

    setupStyles() {
        if (document.getElementById('notification-styles')) return;

        const style = document.createElement('style');
        style.id = 'notification-styles';
        style.textContent = `
            .notification-container {
                position: fixed;
                top: 20px;
                right: 20px;
                z-index: var(--z-notification, 99999);
                max-width: 400px;
                pointer-events: none;
            }

            .notification {
                background: var(--card-bg, #ffffff);
                border: 1px solid var(--border-color, #e0e0e0);
                border-radius: 8px;
                padding: 16px;
                margin-bottom: 10px;
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
                pointer-events: auto;
                transform: translateX(100%);
                transition: transform 0.3s ease-in-out, opacity 0.3s ease-in-out;
                opacity: 0;
                position: static;
                overflow: hidden;
            }

            .notification.show {
                transform: translateX(0);
                opacity: 1;
            }

            .notification.hide {
                transform: translateX(100%);
                opacity: 0;
            }

            .notification.success {
                border-left: 4px solid #4caf50;
            }

            .notification.error {
                border-left: 4px solid #f44336;
            }

            .notification.warning {
                border-left: 4px solid #ff9800;
            }

            .notification.info {
                border-left: 4px solid #2196f3;
            }

            .notification-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 8px;
            }

            .notification-title {
                font-weight: 600;
                font-size: 14px;
                margin: 0;
            }

            .notification-close {
                background: none;
                border: none;
                font-size: 18px;
                cursor: pointer;
                padding: 0;
                width: 20px;
                height: 20px;
                display: flex;
                align-items: center;
                justify-content: center;
                color: var(--text-secondary, #666);
            }

            .notification-close:hover {
                color: var(--text-primary, #333);
            }

            .notification-message {
                font-size: 14px;
                line-height: 1.4;
                margin: 0;
                color: var(--text-primary, #333);
            }

            .notification-progress {
                position: absolute;
                bottom: 0;
                left: 0;
                height: 3px;
                background: var(--primary-color, #2196f3);
                transition: width linear;
            }

            .dark-theme .notification {
                background: var(--card-bg, #2d2d2d);
                border-color: var(--border-color, #404040);
                color: var(--text-primary, #ffffff);
            }

            .dark-theme .notification-close {
                color: var(--text-secondary, #ccc);
            }

            .dark-theme .notification-close:hover {
                color: var(--text-primary, #ffffff);
            }
        `;
        document.head.appendChild(style);
    }

    show(message, type = 'info', options = {}) {
        const notification = {
            id: Date.now() + Math.random(),
            message,
            type,
            timeout: options.timeout || this.defaultTimeout,
            persistent: options.persistent || false,
            actions: options.actions || [],
            onClose: options.onClose || null
        };

        this.notifications.push(notification);
        this.renderNotification(notification);
        this.cleanup();

        return notification.id;
    }

    renderNotification(notification) {
        const element = document.createElement('div');
        element.className = `notification ${notification.type}`;
        element.dataset.id = notification.id;

        const title = this.getTypeTitle(notification.type);
        
        element.innerHTML = `
            <div class="notification-header">
                <h4 class="notification-title">${title}</h4>
                <button class="notification-close" onclick="window.vulnAnalizer.notificationManager.close('${notification.id}')">
                    ×
                </button>
            </div>
            <p class="notification-message">${notification.message}</p>
            ${notification.actions.length > 0 ? this.renderActions(notification.actions) : ''}
            ${!notification.persistent ? '<div class="notification-progress"></div>' : ''}
        `;

        this.container.appendChild(element);

        // Анимация появления
        requestAnimationFrame(() => {
            element.classList.add('show');
        });

        // Автоматическое закрытие
        if (!notification.persistent && notification.timeout > 0) {
            this.scheduleClose(notification.id, notification.timeout);
        }

        // Эмитируем событие
        if (this.app && this.app.eventManager) {
            this.app.eventManager.emitNotification(notification.message, notification.type);
        }
    }

    renderActions(actions) {
        return `
            <div class="notification-actions" style="margin-top: 12px; display: flex; gap: 8px;">
                ${actions.map(action => `
                    <button 
                        class="notification-action-btn" 
                        onclick="${action.handler}"
                        style="padding: 6px 12px; border: 1px solid var(--border-color); background: var(--card-bg); border-radius: 4px; cursor: pointer; font-size: 12px;"
                    >
                        ${action.text}
                    </button>
                `).join('')}
            </div>
        `;
    }

    getTypeTitle(type) {
        const titles = {
            success: 'Успех',
            error: 'Ошибка',
            warning: 'Предупреждение',
            info: 'Информация'
        };
        return titles[type] || 'Уведомление';
    }

    scheduleClose(id, timeout) {
        const element = this.container.querySelector(`[data-id="${id}"]`);
        if (!element) return;

        const progressBar = element.querySelector('.notification-progress');
        if (progressBar) {
            progressBar.style.width = '100%';
            progressBar.style.transitionDuration = `${timeout}ms`;
        }

        setTimeout(() => {
            this.close(id);
        }, timeout);
    }

    close(id) {
        const element = this.container.querySelector(`[data-id="${id}"]`);
        if (!element) return;

        const notification = this.notifications.find(n => n.id == id);
        if (notification && notification.onClose) {
            notification.onClose();
        }

        element.classList.add('hide');
        
        setTimeout(() => {
            if (element.parentNode) {
                element.parentNode.removeChild(element);
            }
        }, 300);

        this.notifications = this.notifications.filter(n => n.id != id);
    }

    closeAll() {
        this.notifications.forEach(notification => {
            this.close(notification.id);
        });
    }

    cleanup() {
        if (this.notifications.length > this.maxNotifications) {
            const toRemove = this.notifications.slice(0, this.notifications.length - this.maxNotifications);
            toRemove.forEach(notification => {
                this.close(notification.id);
            });
        }
    }

    // Специализированные методы
    success(message, options = {}) {
        return this.show(message, 'success', options);
    }

    error(message, options = {}) {
        return this.show(message, 'error', options);
    }

    warning(message, options = {}) {
        return this.show(message, 'warning', options);
    }

    info(message, options = {}) {
        return this.show(message, 'info', options);
    }

    // Метод для совместимости со старым API
    showNotification(message, type = 'info') {
        return this.show(message, type);
    }
}

// Экспорт для использования в других модулях
if (typeof module !== 'undefined' && module.exports) {
    module.exports = NotificationManager;
} else {
    window.NotificationManager = NotificationManager;
}
