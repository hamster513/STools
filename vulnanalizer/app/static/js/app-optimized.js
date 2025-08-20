/**
 * Оптимизированное приложение VulnAnalizer
 * Модульная архитектура для улучшения поддерживаемости и производительности
 */
class VulnAnalizer {
    constructor() {
        this.modules = {};
        this.operationStatus = {};
        this.init();
    }

    /**
     * Инициализация приложения
     */
    async init() {
        try {
            console.log('Starting VulnAnalizer initialization...');
            
            // Инициализируем модули
            this.initModules();
            console.log('Modules initialized successfully');
            
            // Инициализируем UI
            this.initUI();
            console.log('UI initialized successfully');
            
            // Загружаем начальные данные
            await this.loadInitialData();
            console.log('Initial data loaded successfully');
            
            console.log('VulnAnalizer initialized successfully');
        } catch (error) {
            console.error('Error initializing VulnAnalizer:', error);
            console.error('Error stack:', error.stack);
        }
    }

    /**
     * Инициализация модулей
     */
    initModules() {
        try {
            // Проверяем доступность всех модулей
            const requiredModules = [
                'NotificationsModule',
                'ApiModule', 
                'AuthModule',
                'HostsModule',
                'EPSSModule',
                'ExploitDBModule',
                'CVEModule',
                'SettingsModule',
                'VMModule',
                'NavigationModule',
                'UtilsModule'
            ];

            for (const moduleName of requiredModules) {
                if (typeof window[moduleName] === 'undefined') {
                    throw new Error(`Module ${moduleName} is not loaded`);
                }
            }

            // Модуль уведомлений (должен быть первым)
            this.modules.notifications = new NotificationsModule();
            
            // Модуль API
            this.modules.api = new ApiModule(this);
            
            // Модуль аутентификации
            this.modules.auth = new AuthModule(this);
            
            // Модуль хостов
            this.modules.hosts = new HostsModule(this);
            
            // Модуль EPSS
            this.modules.epss = new EPSSModule(this);
            
            // Модуль ExploitDB
            this.modules.exploitdb = new ExploitDBModule(this);
            
            // Модуль CVE
            this.modules.cve = new CVEModule(this);
            
            // Модуль настроек
            this.modules.settings = new SettingsModule(this);
            
            // Модуль VM
            this.modules.vm = new VMModule(this);
            
            // Модуль навигации
            this.modules.navigation = new NavigationModule(this);
            
            // Модуль утилит
            this.modules.utils = new UtilsModule(this);

            console.log('All modules initialized successfully');
        } catch (error) {
            console.error('Error initializing modules:', error);
            throw error;
        }
    }

    /**
     * Инициализация UI
     */
    initUI() {
        try {
            // Инициализируем UIManager для управления боковой панелью и темами
            if (typeof UIManager !== 'undefined') {
                this.uiManager = new UIManager();
            }
            
            // Инициализируем активную страницу
            if (this.modules.navigation && typeof this.modules.navigation.initializeActivePage === 'function') {
                this.modules.navigation.initializeActivePage();
            } else {
                console.warn('Navigation module or initializeActivePage method not available');
            }
        } catch (error) {
            console.error('Error initializing UI:', error);
        }
    }

    /**
     * Загрузка начальных данных
     */
    async loadInitialData() {
        try {
            console.log('Loading initial data...');
            
            // Загружаем статусы всех модулей
            const statusPromises = [];
            
            if (this.modules.hosts && typeof this.modules.hosts.updateStatus === 'function') {
                statusPromises.push(this.modules.hosts.updateStatus());
            }
            
            if (this.modules.epss && typeof this.modules.epss.updateStatus === 'function') {
                statusPromises.push(this.modules.epss.updateStatus());
            }
            
            if (this.modules.exploitdb && typeof this.modules.exploitdb.updateStatus === 'function') {
                statusPromises.push(this.modules.exploitdb.updateStatus());
            }
            
            if (this.modules.cve && typeof this.modules.cve.updateStatus === 'function') {
                statusPromises.push(this.modules.cve.updateStatus());
            }
            
            if (this.modules.vm && typeof this.modules.vm.updateStatus === 'function') {
                statusPromises.push(this.modules.vm.updateStatus());
            }
            
            if (statusPromises.length > 0) {
                await Promise.all(statusPromises);
            }
            
            // Проверяем статус фонового обновления
            if (this.modules.hosts && typeof this.modules.hosts.checkBackgroundUpdateStatus === 'function') {
                await this.modules.hosts.checkBackgroundUpdateStatus();
            }
            
            // Загружаем настройки базы данных
            if (this.modules.settings && typeof this.modules.settings.loadDatabaseSettings === 'function') {
                await this.modules.settings.loadDatabaseSettings();
            }
            
            console.log('Initial data loaded successfully');
            
        } catch (error) {
            console.error('Error loading initial data:', error);
            if (this.modules.notifications) {
                this.modules.notifications.show('Ошибка загрузки данных', 'error');
            }
        }
    }

    /**
     * Получение модуля по имени
     */
    getModule(name) {
        return this.modules[name];
    }

    /**
     * Глобальные методы для совместимости
     */
    showNotification(message, type = 'info') {
        return this.modules.notifications.show(message, type);
    }

    getApiBasePath() {
        return this.modules.api.getApiBasePath();
    }

    // Делегирование методов к соответствующим модулям
    get hosts() { return this.modules.hosts; }
    get auth() { return this.modules.auth; }
    get api() { return this.modules.api; }
    get notifications() { return this.modules.notifications; }
    get settings() { return this.modules.settings; }
    get epss() { return this.modules.epss; }
    get exploitdb() { return this.modules.exploitdb; }
    get cve() { return this.modules.cve; }
    get vm() { return this.modules.vm; }
    get navigation() { return this.modules.navigation; }
    get utils() { return this.modules.utils; }
}

// Инициализация приложения при загрузке страницы
document.addEventListener('DOMContentLoaded', () => {
    window.vulnAnalizer = new VulnAnalizer();
});

// Экспорт для использования в модулях
if (typeof module !== 'undefined' && module.exports) {
    module.exports = VulnAnalizer;
} else {
    window.VulnAnalizer = VulnAnalizer;
}
