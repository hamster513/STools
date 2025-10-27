/**
 * AuthManager - Менеджер аутентификации
 * v=8.0 - Унифицированная система токенов
 */
class AuthManager {
    constructor(app) {
        this.app = app;
        this.storage = app.storage;
        this.api = app.api;
        this.eventManager = app.eventManager;
    }

    // Проверка авторизации
    async checkAuth() {
        const token = this.storage.get('auth_token');
        
        if (!token) {
            console.log('❌ AuthManager.checkAuth: токен не найден, перенаправляем на /auth/');
            window.location.href = '/auth/';
            return;
        }

        try {
            const response = await fetch('/auth/api/verify', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                }
            });

            if (response.ok) {
                const userData = await response.json();
                await this.handleAuthSuccess(userData);
            } else {
                this.handleAuthError();
            }
        } catch (error) {
            console.error('Ошибка проверки токена:', error);
            this.handleAuthError();
        }
    }

    // Обработка успешной авторизации
    async handleAuthSuccess(userData) {
        if (userData.user) {
            this.storage.set('user_info', userData.user);
            
            // Проверяем права администратора
            const isAdmin = userData.user.is_admin === true;
            
            // Обновляем UI в зависимости от прав
            this.app.updateSidebarVisibility(isAdmin);
            this.app.updateMenuVisibility(isAdmin);
            
            // Загружаем настройки пользователя
            await this.loadUserSettings();
        }
    }

    // Обработка ошибки авторизации
    handleAuthError() {
        this.storage.remove('auth_token');
        this.storage.remove('user_info');
        window.location.href = '/auth/';
    }

    // Загрузка настроек пользователя
    async loadUserSettings() {
        try {
            const response = await fetch('/auth/user-settings', {
                headers: {
                    'Authorization': `Bearer ${this.storage.get('auth_token')}`
                }
            });

            if (response.ok) {
                const settings = await response.json();
                this.applyUserSettings(settings);
            }
        } catch (error) {
            console.error('Ошибка загрузки настроек пользователя:', error);
        }
    }

    // Применение настроек пользователя
    applyUserSettings(settings) {
        if (settings.theme) {
            document.documentElement.setAttribute('data-theme', settings.theme);
            this.app.updateThemeText(settings.theme);
        }
    }

    // Проверка прав пользователя
    checkUserPermissions() {
        const userInfo = this.storage.get('user_info');
        if (userInfo) {
            try {
                const user = typeof userInfo === 'string' ? JSON.parse(userInfo) : userInfo;
                const isAdmin = user.is_admin === true;
                
                this.app.updateSidebarVisibility(isAdmin);
                this.app.updateMenuVisibility(isAdmin);
            } catch (e) {
                console.warn('Ошибка парсинга пользователя:', e);
            }
        }
    }

    // Выход из системы
    logout() {
        // Очищаем данные пользователя
        this.storage.remove('auth_token');
        this.storage.remove('user_info');
        
        // Эмитируем событие выхода
        if (this.eventManager) {
            this.eventManager.emit('userLogout');
        }
        
        // Перенаправляем на страницу входа
        window.location.href = '/auth/';
    }

    // Получение информации о пользователе
    getCurrentUser() {
        const userInfo = this.storage.get('user_info');
        if (userInfo) {
            try {
                return typeof userInfo === 'string' ? JSON.parse(userInfo) : userInfo;
            } catch (e) {
                console.warn('Ошибка парсинга пользователя:', e);
                return null;
            }
        }
        return null;
    }

    // Проверка роли пользователя
    hasRole(role) {
        const user = this.getCurrentUser();
        if (role === 'admin') {
            return user && user.is_admin === true;
        }
        return user && user.role === role;
    }

    // Проверка прав администратора
    isAdmin() {
        return this.hasRole('admin');
    }

    // Открытие страницы управления пользователями
    openUsersPage() {
        // Перенаправляем на админ-панель auth сервиса
        window.location.href = '/auth/admin/users/';
    }
}

// Экспорт для использования в других модулях
if (typeof module !== 'undefined' && module.exports) {
    module.exports = AuthManager;
} else {
    window.AuthManager = AuthManager;
}
