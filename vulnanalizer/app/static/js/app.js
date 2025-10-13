/**
 * VulnAnalizer - Основное приложение
 * v=7.2
 */

// Подключение модулей
// Core modules
if (typeof ApiManager !== 'undefined') {
    // ApiManager уже загружен
} else {
    console.warn('ApiManager not loaded');
}

if (typeof StorageManager !== 'undefined') {
    // StorageManager уже загружен
} else {
    console.warn('StorageManager not loaded');
}

if (typeof EventManager !== 'undefined') {
    // EventManager уже загружен
} else {
    console.warn('EventManager not loaded');
}

// UI modules
if (typeof NotificationManager !== 'undefined') {
    // NotificationManager уже загружен
} else {
    console.warn('NotificationManager not loaded');
}

// Utils
if (typeof Helpers !== 'undefined') {
    // Helpers уже загружен
} else {
    console.warn('Helpers not loaded');
}

class VulnAnalizer {
    // Константы
    static DELAYS = {
        SHORT: 300,
        MEDIUM: 500,
        LONG: 800,
        INIT: 100
    };
    
    static API_PATHS = {
        DEFAULT: '/api',
        VULNANALIZER: '/vulnanalizer/api'
    };
    
    static PAGINATION = {
        DEFAULT_LIMIT: 100,
        DEFAULT_PAGE: 1
    };

    constructor() {
        // Инициализируем основные модули
        this.initCoreModules();
        
        // UIManager инициализируется в initCoreModules()
        
        this.operationStatus = {}; // Хранит статус текущих операций
        this.paginationState = {
            currentPage: VulnAnalizer.PAGINATION.DEFAULT_PAGE,
            totalPages: 1,
            totalCount: 0,
            limit: VulnAnalizer.PAGINATION.DEFAULT_LIMIT
        };
        
        // Кэш DOM элементов
        this.domCache = {};
        
        // Инициализируем только после готовности DOM
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => {
                this.init();
            });
        } else {
            this.init();
        }
    }

    // Инициализация основных модулей
    initCoreModules() {
        // Storage Manager
        if (typeof StorageManager !== 'undefined') {
            this.storage = new StorageManager();
            this.storage.migrateOldKeys(); // Миграция старых ключей
        } else {
            console.warn('StorageManager not available, using localStorage directly');
            this.storage = {
                get: (key, defaultValue) => {
                    try {
                        const item = localStorage.getItem(key);
                        return item ? JSON.parse(item) : defaultValue;
                    } catch {
                        return localStorage.getItem(key) || defaultValue;
                    }
                },
                set: (key, value) => {
                    try {
                        localStorage.setItem(key, typeof value === 'string' ? value : JSON.stringify(value));
                        return true;
                    } catch {
                        return false;
                    }
                },
                remove: (key) => {
                    localStorage.removeItem(key);
                    return true;
                }
            };
        }

        // Event Manager
        if (typeof EventManager !== 'undefined') {
            this.eventManager = new EventManager();
        } else {
            console.warn('EventManager not available');
            this.eventManager = {
                on: () => {},
                emit: () => {},
                off: () => {}
            };
        }

        // API Manager
        if (typeof ApiManager !== 'undefined') {
            this.api = new ApiManager(this);
        } else {
            console.warn('ApiManager not available, using fetch directly');
            this.api = {
                get: async (url) => {
                    const response = await fetch(url);
                    return response.json();
                },
                post: async (url, data) => {
                    const response = await fetch(url, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(data)
                    });
                    return response.json();
                }
            };
        }

        // Notification Manager
        if (typeof NotificationManager !== 'undefined') {
            this.notificationManager = new NotificationManager(this);
        } else {
            console.warn('NotificationManager not available');
            this.notificationManager = {
                show: (message, type) => console.log(`[${type}] ${message}`),
                success: (message) => console.log(`[SUCCESS] ${message}`),
                error: (message) => console.error(`[ERROR] ${message}`),
                warning: (message) => console.warn(`[WARNING] ${message}`),
                info: (message) => console.info(`[INFO] ${message}`)
            };
        }

        // Инициализируем сервисы
        this.initServices();

        // Создаем debounced версии часто используемых методов
        if (typeof Helpers !== 'undefined') {
            this.debouncedSearchHosts = Helpers.debounce(this.searchHosts.bind(this), 500);
            this.debouncedUpdateStatus = Helpers.debounce(this.updateHostsStatus.bind(this), 1000);
        } else {
            this.debouncedSearchHosts = this.searchHosts.bind(this);
            this.debouncedUpdateStatus = this.updateHostsStatus.bind(this);
        }
    }

    // Инициализация сервисов
    initServices() {
        // Hosts Service
        if (typeof HostsService !== 'undefined') {
            this.hostsService = new HostsService(this);
        } else {
            console.warn('HostsService not available');
            this.hostsService = {
                searchHosts: () => Promise.resolve({ hosts: [] }),
                updateHostsStatus: () => Promise.resolve({}),
                importHosts: () => Promise.resolve({}),
                exportHosts: () => Promise.resolve({}),
                calculateHostRisk: () => Promise.resolve({}),
                checkActiveImportTasks: () => Promise.resolve({})
            };
        }

        // CVE Service
        if (typeof CVEService !== 'undefined') {
            this.cveService = new CVEService(this);
        } else {
            console.warn('CVEService not available');
            this.cveService = {
                updateCVEStatus: () => Promise.resolve({}),
                uploadCVE: () => Promise.resolve({}),
                searchCVE: () => Promise.resolve({ results: [] }),
                getCVEDetails: () => Promise.resolve({}),
                clearCVEData: () => Promise.resolve({})
            };
        }

        // EPSS Service
        if (typeof EPSSService !== 'undefined') {
            this.epssService = new EPSSService(this);
        } else {
            console.warn('EPSSService not available');
            this.epssService = {
                updateEPSSStatus: () => Promise.resolve({}),
                uploadEPSS: () => Promise.resolve({}),
                clearEPSSData: () => Promise.resolve({})
            };
        }

        // ExploitDB Service
        if (typeof ExploitDBService !== 'undefined') {
            this.exploitdbService = new ExploitDBService(this);
        } else {
            console.warn('ExploitDBService not available');
            this.exploitdbService = {
                updateExploitDBStatus: () => Promise.resolve({}),
                uploadExploitDB: () => Promise.resolve({}),
                clearExploitDBData: () => Promise.resolve({})
            };
        }

        // Metasploit Service
        if (typeof MetasploitService !== 'undefined') {
            this.metasploitService = new MetasploitService(this);
        } else {
            console.warn('MetasploitService not available');
            this.metasploitService = {
                updateMetasploitStatus: () => Promise.resolve({}),
                uploadMetasploit: () => Promise.resolve({}),
                searchMetasploit: () => Promise.resolve({ results: [] }),
                getMetasploitDetails: () => Promise.resolve({}),
                clearMetasploitData: () => Promise.resolve({})
            };
        }

        // Metasploit Manager (для обработки UI событий)
        if (typeof MetasploitManager !== 'undefined') {
            this.metasploitManager = new MetasploitManager(this);
        } else {
            console.warn('MetasploitManager not available');
        }

        // UI Manager
        if (typeof UIManager !== 'undefined') {
            this.uiManager = new UIManager(this);
        } else {
            console.warn('UIManager not available');
            this.uiManager = {
                initTheme: () => {},
                toggleTheme: () => {},
                switchPage: () => {},
                logout: () => {}
            };
        }

        // Hosts UI Manager
        if (typeof HostsUIManager !== 'undefined') {
            this.hostsUIManager = new HostsUIManager(this);
        } else {
            console.warn('HostsUIManager not available');
            this.hostsUIManager = {
                renderHostsResults: () => {},
                showImportProgress: () => {},
                hideImportProgress: () => {}
            };
        }

        // Auth Manager
        if (typeof AuthManager !== 'undefined') {
            this.authManager = new AuthManager(this);
        } else {
            console.warn('AuthManager not available');
            this.authManager = {
                checkAuth: () => Promise.resolve(),
                checkUserPermissions: () => {},
                logout: () => {},
                isAdmin: () => false
            };
        }

        // Setup Manager
        if (typeof SetupManager !== 'undefined') {
            this.setupManager = new SetupManager(this);
        } else {
            console.warn('SetupManager not available');
            this.setupManager = {
                init: () => {}
            };
        }
    }

    // Получение базового пути для API (делегируем в ApiManager)
    getApiBasePath() {
        return this.api ? this.api.getApiBasePath() : '/api';
    }

    // Утилита для задержки (делегируем в Helpers)
    async delay(ms) {
        if (typeof Helpers !== 'undefined') {
            return Helpers.delay(ms);
        }
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    // Утилита для показа уведомлений (делегируем в NotificationManager)
    showNotification(message, type = 'info') {
        if (this.notificationManager) {
            this.notificationManager.show(message, type);
        } else {
            console.log(`[${type.toUpperCase()}] ${message}`);
        }
    }

    // Утилита для кэширования DOM элементов
    getElement(id) {
        if (!this.domCache[id]) {
            this.domCache[id] = document.getElementById(id);
        }
        return this.domCache[id];
    }

    // Безопасная утилита для получения DOM элементов
    getElementSafe(id) {
        const element = this.getElement(id);
        if (!element) {
            console.warn(`Element with id '${id}' not found`);
        }
        return element;
    }

    // Утилита для кэширования querySelector
    getElementBySelector(selector) {
        if (!this.domCache[selector]) {
            this.domCache[selector] = document.querySelector(selector);
        }
        return this.domCache[selector];
    }

    // Централизованная обработка ошибок
    handleError(error, context = 'Unknown', showNotification = true) {
        const errorMessage = error.message || error.toString();
        console.error(`[${context}] Error:`, error);
        
        // Эмитируем событие ошибки
        if (this.eventManager) {
            this.eventManager.emitError(error, context);
        }
        
        if (showNotification) {
            this.showNotification(`Ошибка ${context}: ${errorMessage}`, 'error');
        }
        
        return {
            success: false,
            error: errorMessage,
            context
        };
    }

    // Глобальная обработка ошибок
    setupGlobalErrorHandling() {
        // Обработка необработанных ошибок JavaScript
        window.addEventListener('error', (event) => {
            this.handleError(event.error, 'Global JavaScript Error', true);
        });

        // Обработка необработанных отклонений Promise
        window.addEventListener('unhandledrejection', (event) => {
            this.handleError(event.reason, 'Unhandled Promise Rejection', true);
            event.preventDefault(); // Предотвращаем вывод в консоль браузера
        });

        // Обработка ошибок загрузки ресурсов
        window.addEventListener('error', (event) => {
            if (event.target !== window) {
                this.handleError(
                    new Error(`Failed to load resource: ${event.target.src || event.target.href}`),
                    'Resource Loading Error',
                    false // Не показываем уведомление для ошибок загрузки ресурсов
                );
            }
        }, true);
    }

    initModules() {
        // Инициализируем API модуль первым
        if (typeof ApiModule !== 'undefined') {
            this.api = new ApiModule(this);
        }
        
        // Инициализируем модули если они доступны
        if (typeof CVEModule !== 'undefined') {
            this.cveModule = new CVEModule(this);
        }
        
        if (typeof EPSSModule !== 'undefined') {
            this.epssModule = new EPSSModule(this);
        }
        
        if (typeof ExploitDBModule !== 'undefined') {
            this.exploitdbModule = new ExploitDBModule(this);
        }
        
        if (typeof ArchiveModule !== 'undefined') {
            this.archiveModule = new ArchiveModule(this);
        }
        
        if (typeof HostsModule !== 'undefined') {
            this.hostsModule = new HostsModule(this);
        }
        
        if (typeof SettingsModule !== 'undefined') {
            this.settingsModule = new SettingsModule(this);
        }
        
        if (typeof CVEModalModule !== 'undefined') {
            this.cveModal = new CVEModalModule(this);
        }
        
        // MetasploitModule заменен на MetasploitService
        
        if (typeof MetasploitModalModule !== 'undefined') {
            this.metasploitModal = new MetasploitModalModule(this);
        }
        
        if (typeof EPSSModalModule !== 'undefined') {
            this.epssModal = new EPSSModalModule(this);
        }
        
        if (typeof ExploitDBModalModule !== 'undefined') {
            this.exploitdbModal = new ExploitDBModalModule(this);
        }
        
        if (typeof CVEPreviewModalModule !== 'undefined') {
            this.cvePreviewModal = new CVEPreviewModalModule(this);
        }
        
        if (typeof RiskModalModule !== 'undefined') {
            this.riskModal = new RiskModalModule(this);
        }
        
        if (typeof VMModule !== 'undefined') {
            this.vmModule = new VMModule(this);
        }
    }

    init() {
        // Настраиваем глобальную обработку ошибок
        this.setupGlobalErrorHandling();
        
        // Проверяем авторизацию
        this.authManager.checkAuth();
        
        // Инициализируем тему
        this.uiManager.initTheme();
        
        // Инициализируем боковую панель
        this.setupSidebar();
        
        // Инициализируем все настройки UI через SetupManager
        this.setupManager.init();
        
        // Инициализируем модули после настройки всех компонентов
        this.initModules();
        
        // Инициализируем активную страницу
        this.uiManager.initializeActivePage();
        
        // Проверяем права пользователя и загружаем данные
        this.delay(VulnAnalizer.DELAYS.INIT).then(async () => {
            this.authManager.checkUserPermissions();
            this.updateHostsStatus();
            this.updateEPSSStatus();
            this.updateExploitDBStatus();
            this.updateCVEStatus();
            this.updateMetasploitStatus();
            this.loadBackgroundTasksData();
            this.checkActiveImportTasks(); // Проверяем активные задачи импорта и обновления
            
            // Загружаем настройки базы данных
            await this.loadDatabaseSettings();
        });
    }

    checkAuth() {
        return this.authManager.checkAuth();
    }

    checkUserPermissions() {
        return this.authManager.checkUserPermissions();
    }

    updateSidebarVisibility(isAdmin) {
        return this.uiManager.updateSidebarVisibility(isAdmin);
    }

    updateMenuVisibility(isAdmin) {
        return this.uiManager.updateMenuVisibility(isAdmin);
    }

    initTheme() {
        return this.uiManager.initTheme();
    }

    updateThemeText(theme) {
        return this.uiManager.updateThemeText(theme);
    }

    updateBreadcrumb(page) {
        return this.uiManager.updateBreadcrumb(page);
    }

    toggleTheme() {
        return this.uiManager.toggleTheme();
    }

    initializeActivePage() {
        return this.uiManager.initializeActivePage();
    }

    // setupNavigation перенесен в SetupManager

    // setupSettings перенесен в SetupManager

    // setupUserMenu перенесен в SetupManager

    logout() {
        return this.uiManager.logout();
    }

    switchPage(page) {
        return this.uiManager.switchPage(page);
    }

    // setupForms перенесен в SetupManager

    // setupEPSS перенесен в SetupManager

    // setupExploitDB перенесен в SetupManager

    // setupCVE перенесен в SetupManager

    // setupHosts перенесен в SetupManager

    async updateExploitDBStatus() {
        return this.exploitdbService.updateExploitDBStatus();
    }

    async updateEPSSStatus() {
        return this.epssService.updateEPSSStatus();
    }

    async updateCVEStatus() {
        return this.cveService.updateCVEStatus();
    }

    async updateMetasploitStatus() {
        return this.metasploitService.updateMetasploitStatus();
    }

    async updateHostsStatus() {
        return this.hostsService.updateHostsStatus();
    }

    async searchHosts(page = 1) {
        // Делегируем поиск в HostsService
        return this.hostsService.searchHosts(page);
    }

    renderHostsResults(hosts, groupBy = '', paginationData = null) {
        return this.hostsUIManager.renderHostsResults(hosts, groupBy, paginationData);
    }

    groupHosts(hosts, groupBy) {
        return this.hostsUIManager.groupHosts(hosts, groupBy);
    }

    getGroupTitle(groupBy, groupKey) {
        return this.hostsUIManager.getGroupTitle(groupBy, groupKey);
    }

    getGroupCount(groupBy, hosts) {
        return this.hostsUIManager.getGroupCount(groupBy, hosts);
    }

    renderHostItem(host) {
        return this.hostsUIManager.renderHostItem(host);
    }

    // clearHostsResults перенесен в HostsModule

    renderPagination() {
        return this.hostsUIManager.renderPagination();
    }

    renderPageNumbers() {
        return this.hostsUIManager.renderPageNumbers();
    }

    hidePagination() {
        return this.hostsUIManager.hidePagination();
    }

    async exportHosts() {
        return this.hostsService.exportHosts();
    }

    async calculateHostRisk(hostId) {
        return this.hostsService.calculateHostRisk(hostId);
    }

    renderHostRiskResult(hostId, data) {
        return this.hostsUIManager.renderHostRiskResult(hostId, data);
    }

    async loadInitialData() {
        return this.setupManager.loadInitialData();
    }

    populateSettings(settings) {
        return this.setupManager.populateSettings(settings);
    }

    async saveSettings() {
        return this.setupManager.saveSettings();
    }

    async loadDatabaseSettings() {
        return this.setupManager.loadDatabaseSettings();
    }

    async loadImpactSettings() {
        return this.setupManager.loadImpactSettings();
    }

    async loadExploitDBSettings() {
        return this.setupManager.loadExploitDBSettings();
    }

    async loadMetasploitSettings() {
        return this.setupManager.loadMetasploitSettings();
    }

    async saveImpactSettings() {
        return this.setupManager.saveImpactSettings();
    }

    async searchCVE(query) {
        return this.cveService.searchCVE(query);
    }

    displayCVEResults(data) {
        return this.cveService.displayCVEResults(data);
    }

    // Отображение сообщения о том, что CVE не найдена
    displayCVENotFound(cveId) {
        return this.cveService.displayCVENotFound(cveId);
    }

    getCVSSSeverityClass(score) {
        return this.cveService.getCVSSSeverityClass(score);
    }

    getRiskSeverityClass(score) {
        return this.cveService.getRiskSeverityClass(score);
    }

    updateThresholdSlider(value) {
        return this.setupManager.updateThresholdSlider(value);
    }

    // Проверка подключения к базе данных
    async testConnection() {
        return this.setupManager.testConnection();
    }

    async clearHosts() {
        return this.hostsService.clearHosts();
    }

    async clearEPSS() {
        return this.epssService.clearEPSS();
    }

    async clearExploitDB() {
        return this.exploitdbService.clearExploitDB();
    }

    async clearCVE() {
        return this.cveService.clearCVE();
    }

    async clearMetasploit() {
        return this.metasploitService.clearMetasploitData();
    }

    // Показ уведомлений
    showNotification(message, type = 'info') {
        const notifications = document.getElementById('notifications');
        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        
        let icon = 'fas fa-info-circle';
        if (type === 'success') icon = 'fas fa-check-circle';
        if (type === 'error') icon = 'fas fa-exclamation-circle';
        if (type === 'warning') icon = 'fas fa-exclamation-triangle';

        notification.innerHTML = `
            <i class="${icon}"></i>
            <span>${message}</span>
        `;

        notifications.appendChild(notification);

        // Удаляем уведомление через 5 секунд
        this.delay(5000).then(() => {
            notification.remove();
        });
    }

    // Новые методы для улучшенного статусбара
    showOperationProgress(operationId, message, progress = null) {
        const statusDiv = document.getElementById(`${operationId}-status`);
        if (!statusDiv) return;
        
        let progressHtml = '';
        if (progress !== null) {
            progressHtml = `
                <div class="operation-progress-bar">
                    <div class="operation-progress-fill" style="width: ${progress}%"></div>
                </div>
                <div class="operation-progress-text">${progress.toFixed(1)}%</div>
            `;
        }
        
        statusDiv.innerHTML = `
            <div class="operation-status active">
                <div class="status-header">
                    <i class="fas fa-spinner fa-spin"></i>
                    <span class="status-message">${message}</span>
                </div>
                ${progressHtml}
                <div class="status-details">
                    <small>Операция выполняется...</small>
                </div>
            </div>
        `;
    }

    updateOperationProgress(operationId, message, progress = null, details = null) {
        const statusDiv = document.getElementById(`${operationId}-status`);
        if (!statusDiv) return;
        
        let progressHtml = '';
        if (progress !== null) {
            progressHtml = `
                <div class="operation-progress-bar">
                    <div class="operation-progress-fill" style="width: ${progress}%"></div>
                </div>
                <div class="operation-progress-text">${progress.toFixed(1)}%</div>
            `;
        }
        
        let detailsHtml = '';
        if (details) {
            detailsHtml = `<div class="status-details"><small>${details}</small></div>`;
        }
        
        statusDiv.innerHTML = `
            <div class="operation-status active">
                <div class="status-header">
                    <i class="fas fa-spinner fa-spin"></i>
                    <span class="status-message">${message}</span>
                </div>
                ${progressHtml}
                ${detailsHtml}
            </div>
        `;
    }

    showOperationComplete(operationId, message, details = null) {
        const statusDiv = document.getElementById(`${operationId}-status`);
        if (!statusDiv) return;
        
        let detailsHtml = '';
        if (details) {
            detailsHtml = `<div class="status-details"><small>${details}</small></div>`;
        }
        
        statusDiv.innerHTML = `
            <div class="operation-status success">
                <div class="status-header">
                    <i class="fas fa-check-circle"></i>
                    <span class="status-message">${message}</span>
                </div>
                ${detailsHtml}
            </div>
        `;
    }

    showOperationError(operationId, message, error = null) {
        const statusDiv = document.getElementById(`${operationId}-status`);
        if (!statusDiv) return;
        
        let errorHtml = '';
        if (error) {
            errorHtml = `<div class="status-details"><small class="error-text">${error}</small></div>`;
        }
        
        statusDiv.innerHTML = `
            <div class="operation-status error">
                <div class="status-header">
                    <i class="fas fa-exclamation-triangle"></i>
                    <span class="status-message">${message}</span>
                </div>
                ${errorHtml}
            </div>
        `;
    }

    async loadAppVersion() {
        try {
            const response = await fetch(`${this.getApiBasePath()}/version`);
            const data = await response.json();
            
            const versionElement = document.getElementById('app-version');
            if (versionElement && data.version) {
                versionElement.textContent = `v${data.version}`;
            }
        } catch (error) {
            console.warn('Ошибка загрузки версии приложения:', error);
        }
    }

    setupSidebar() {
        const sidebar = document.getElementById('sidebar');
        const sidebarToggle = document.getElementById('sidebar-toggle');
        const container = document.querySelector('.container');
        
        if (!sidebar || !sidebarToggle) return;

        // Функция для обновления иконки
        const updateToggleIcon = (isCollapsed) => {
            const icon = sidebarToggle.querySelector('i');
            if (icon) {
                icon.className = isCollapsed ? 'fas fa-chevron-right' : 'fas fa-chevron-left';
            }
        };

        // Загружаем состояние из localStorage (по умолчанию sidebar развернута)
        const isCollapsed = localStorage.getItem('sidebar_collapsed') === 'true';
        if (isCollapsed) {
            sidebar.classList.add('collapsed');
            document.body.classList.add('sidebar-collapsed');
            updateToggleIcon(true);
        } else {
            // Если состояние не сохранено, считаем что sidebar развернута
            sidebar.classList.remove('collapsed');
            document.body.classList.remove('sidebar-collapsed');
            localStorage.setItem('sidebar_collapsed', 'false');
            updateToggleIcon(false);
        }

        // Обработчик для кнопки сворачивания
        sidebarToggle.addEventListener('click', () => {
            sidebar.classList.toggle('collapsed');
            document.body.classList.toggle('sidebar-collapsed');
            
            // Сохраняем состояние и обновляем иконку
            const isNowCollapsed = sidebar.classList.contains('collapsed');
            localStorage.setItem('sidebar_collapsed', isNowCollapsed.toString());
            updateToggleIcon(isNowCollapsed);
        });
    }

    // Функции для работы с прогресс-баром импорта
    showImportProgress() {
        const container = document.getElementById('import-progress-container');
        if (container) {
            container.style.display = 'block';
            container.className = 'operation-status active';
        }
    }

    hideImportProgress() {
        const container = document.getElementById('import-progress-container');
        if (container) {
            container.style.display = 'none';
        }
    }

    updateImportProgress(status, currentStep, overallProgress, stepProgress, totalRecords, processedRecords, errorMessage = null) {
        const container = document.getElementById('import-progress-container');
        if (!container) return;

        // Обновляем классы для анимации
        container.className = 'operation-status ' + status;

        // Обновляем текст текущего шага
        const currentStepText = document.getElementById('current-step-text');
        if (currentStepText) {
            currentStepText.textContent = currentStep;
        }

        // Обновляем общий прогресс
        const overallProgressText = document.getElementById('overall-progress-text');
        if (overallProgressText) {
            overallProgressText.textContent = Math.round(overallProgress) + '%';
        }

        // Обновляем прогресс-бар
        const progressBarFill = document.getElementById('progress-bar-fill');
        if (progressBarFill) {
            progressBarFill.style.width = overallProgress + '%';
        }

        const totalRecordsText = document.getElementById('total-records-text');
        if (totalRecordsText) {
            totalRecordsText.textContent = totalRecords.toLocaleString();
        }

        // Показываем ошибку если есть
        if (errorMessage) {
            this.showNotification('Ошибка: ' + errorMessage, 'error');
        }
    }

    startBackgroundTaskMonitoring(taskId) {
        // Показываем прогресс-бар
        this.showImportProgress();
        
        const interval = setInterval(async () => {
            try {
                const resp = await fetch(this.getApiBasePath() + `/background-tasks/${taskId}`);
                if (resp.ok) {
                    const task = await resp.json();
                    
                    // Обновляем прогресс
                    this.updateBackgroundTaskProgress(task);
                    
                    // Если задача завершена или произошла ошибка, останавливаем мониторинг
                    if (task.status === 'completed' || task.status === 'error') {
                        clearInterval(interval);
                        
                        if (task.status === 'completed') {
                            this.showNotification(`Импорт завершен: ${task.processed_records || 0} записей`, 'success');
                            this.updateHostsStatus();
                        } else {
                            this.showNotification(`Ошибка импорта: ${task.error_message || 'Неизвестная ошибка'}`, 'error');
                        }
                        
                        // Скрываем прогресс-бар через 3 секунды
                        this.delay(3000).then(() => {
                            this.hideImportProgress();
                        });
                    }
                }
            } catch (err) {
                console.error('Ошибка мониторинга импорта:', err);
            }
        }, 2000); // Обновляем каждые 2 секунды
        
        return interval;
    }

    // Функции для работы с прогресс-баром обновления хостов
    showBackgroundUpdateProgress() {
        const container = document.getElementById('background-update-progress-container');
        if (container) {
            container.style.display = 'block';
            container.classList.add('fade-in');
        }
    }

    hideBackgroundUpdateProgress() {
        const container = document.getElementById('background-update-progress-container');
        if (container) {
            container.style.display = 'none';
        }
    }

    updateBackgroundUpdateProgress(data) {
        const statusText = document.getElementById('background-current-step-text');
        if (statusText) {
            statusText.textContent = data.current_step || 'Инициализация...';
        }

        if (data.status === 'processing' || data.status === 'initializing') {
            const cancelUpdateBtn = document.getElementById('cancel-update-btn');
            if (cancelUpdateBtn) {
                cancelUpdateBtn.style.display = 'inline-block';
            }
        }

        const progressText = document.getElementById('background-overall-progress-text');
        if (progressText) {
            progressText.textContent = Math.round(data.progress_percent || 0) + '%';
        }

        const progressBarFill = document.getElementById('background-progress-bar-fill');
        if (progressBarFill) {
            progressBarFill.style.width = (data.progress_percent || 0) + '%';
        }

        const processedCvesText = document.getElementById('background-processed-cves-text');
        if (processedCvesText) {
            processedCvesText.textContent = (data.processed_cves || 0).toLocaleString();
        }

        const totalCvesText = document.getElementById('background-total-cves-text');
        if (totalCvesText) {
            totalCvesText.textContent = (data.total_cves || 0).toLocaleString();
        }

        const updatedHostsText = document.getElementById('background-updated-hosts-text');
        if (updatedHostsText) {
            updatedHostsText.textContent = (data.updated_hosts || 0).toLocaleString();
        }

        if (data.error_message && data.status !== 'cancelled' && !data.error_message.toLowerCase().includes('отменено')) {
            this.showNotification('Ошибка: ' + data.error_message, 'error');
        }

        if (data.status === 'completed' || data.status === 'error' || data.status === 'cancelled') {
            const cancelUpdateBtn = document.getElementById('cancel-update-btn');
            if (cancelUpdateBtn) {
                cancelUpdateBtn.style.display = 'none';
            }
            
            setTimeout(() => {
                this.hideBackgroundUpdateProgress();
            }, 3000);
        }
    }

    startBackgroundUpdateMonitoring() {
        return this.setupManager.startBackgroundUpdateMonitoring();
    }

    stopBackgroundUpdateMonitoring() {
        return this.setupManager.stopBackgroundUpdateMonitoring();
    }
    
    updateBackgroundTaskProgress(task) {
        return this.setupManager.updateBackgroundTaskProgress(task);
    }

    formatTime(seconds) {
        return this.setupManager.formatTime(seconds);
    }

    async loadBackgroundTasksData() {
        return this.setupManager.loadBackgroundTasksData();
    }

    updateBackgroundTasksUI(data) {
        return this.setupManager.updateBackgroundTasksUI(data);
    }

    getStatusText(status) {
        return this.setupManager.getStatusText(status);
    }

    async cancelTask(taskType) {
        return this.setupManager.cancelTask(taskType);
    }

    async checkActiveImportTasks() {
        return this.setupManager.checkActiveImportTasks();
    }

    // setupCollapsibleBlocks перенесен в SetupManager
}

// Инициализация приложения при загрузке страницы
document.addEventListener('DOMContentLoaded', () => {
    window.vulnAnalizer = new VulnAnalizer();
    
    // Обработчик изменения хэша URL
    window.addEventListener('hashchange', () => {
        const currentPage = window.location.hash.replace('#', '') || 'analysis';
        if (currentPage === 'hosts') {
            window.vulnAnalizer.checkActiveImportTasks();
        }
    });
});