/**
 * StorageManager - Централизованное управление локальным хранилищем
 * v=8.0 - Унифицированная система токенов для всех сервисов STools
 */
class StorageManager {
    constructor() {
        this.storage = localStorage;
        this.prefix = 'stools_';  // Единый префикс для всех сервисов STools
    }

    // Безопасное получение данных
    get(key, defaultValue = null) {
        try {
            const fullKey = this.prefix + key;
            const item = this.storage.getItem(fullKey);
            
            if (item === null) {
                return defaultValue;
            }
            
            // Пытаемся распарсить JSON
            try {
                return JSON.parse(item);
            } catch (e) {
                // Если не JSON, возвращаем как строку
                return item;
            }
        } catch (error) {
            console.warn(`Storage get error for key '${key}':`, error);
            return defaultValue;
        }
    }

    // Безопасное сохранение данных
    set(key, value) {
        try {
            const fullKey = this.prefix + key;
            const serializedValue = typeof value === 'string' ? value : JSON.stringify(value);
            this.storage.setItem(fullKey, serializedValue);
            return true;
        } catch (error) {
            console.error(`Storage set error for key '${key}':`, error);
            return false;
        }
    }

    // Удаление данных
    remove(key) {
        try {
            const fullKey = this.prefix + key;
            this.storage.removeItem(fullKey);
            return true;
        } catch (error) {
            console.error(`Storage remove error for key '${key}':`, error);
            return false;
        }
    }

    // Проверка существования ключа
    has(key) {
        const fullKey = this.prefix + key;
        return this.storage.getItem(fullKey) !== null;
    }

    // Очистка всех данных с префиксом
    clear() {
        try {
            const keysToRemove = [];
            for (let i = 0; i < this.storage.length; i++) {
                const key = this.storage.key(i);
                if (key && key.startsWith(this.prefix)) {
                    keysToRemove.push(key);
                }
            }
            
            keysToRemove.forEach(key => this.storage.removeItem(key));
            return true;
        } catch (error) {
            console.error('Storage clear error:', error);
            return false;
        }
    }

    // Получение всех ключей с префиксом
    keys() {
        const keys = [];
        for (let i = 0; i < this.storage.length; i++) {
            const key = this.storage.key(i);
            if (key && key.startsWith(this.prefix)) {
                keys.push(key.substring(this.prefix.length));
            }
        }
        return keys;
    }

    // Специализированные методы для работы с пользователем
    setUser(user) {
        return this.set('user', user);
    }

    getUser() {
        return this.get('user', null);
    }

    setAuthToken(token) {
        return this.set('auth_token', token);
    }

    getAuthToken() {
        return this.get('auth_token', null);
    }

    clearAuth() {
        this.remove('auth_token');
        this.remove('user');
        return true;
    }

    // Специализированные методы для настроек
    setSettings(settings) {
        return this.set('settings', settings);
    }

    getSettings() {
        return this.get('settings', {});
    }

    // Специализированные методы для темы
    setTheme(theme) {
        return this.set('theme', theme);
    }

    getTheme() {
        return this.get('theme', 'light');
    }

    // Специализированные методы для пагинации
    setPaginationState(state) {
        return this.set('pagination', state);
    }

    getPaginationState() {
        return this.get('pagination', {
            currentPage: 1,
            totalPages: 1,
            totalCount: 0,
            limit: 100
        });
    }

    // Метод для миграции старых ключей (без префикса)
    migrateOldKeys() {
        const oldKeys = ['auth_token', 'user_info', 'theme'];
        
        oldKeys.forEach(oldKey => {
            const oldValue = this.storage.getItem(oldKey);
            if (oldValue !== null) {
                this.set(oldKey, oldValue);
                this.storage.removeItem(oldKey);
            }
        });
    }
}

// Экспорт для использования в других модулях
if (typeof module !== 'undefined' && module.exports) {
    module.exports = StorageManager;
} else {
    window.StorageManager = StorageManager;
}
