/**
 * SetupManager - Менеджер настройки UI компонентов
 * v=7.5 - Добавлена отладка для background-tasks
 */
class SetupManager {
    constructor(app) {
        this.app = app;
        this.api = app.api;
        this.storage = app.storage;
        this.eventManager = app.eventManager;
    }

    // Настройка навигации
    setupNavigation() {
        const sidebarTabs = document.querySelectorAll('.sidebar-tab');
        
        sidebarTabs.forEach(tab => {
            tab.addEventListener('click', async (e) => {
                e.preventDefault();
                
                // Убираем активный класс со всех вкладок
                sidebarTabs.forEach(t => t.classList.remove('active'));
                tab.classList.add('active');
                
                // Скрываем все страницы
                document.querySelectorAll('.page-content').forEach(page => {
                    page.classList.remove('active');
                });
                
                // Показываем нужную страницу
                const targetPage = tab.getAttribute('data-page');
                
                // Специальная обработка для background-tasks
                if (targetPage === 'background-tasks') {
                    
                    // Скрываем все страницы
                    const allPages = document.querySelectorAll('.page-content');
                    allPages.forEach(page => page.classList.remove('active'));
                    
                    // Активируем страницу background-tasks
                    const backgroundTasksPage = document.getElementById('background-tasks-page');
                    if (backgroundTasksPage) {
                        backgroundTasksPage.classList.add('active');
                    } else {
                        console.error('❌ Страница background-tasks-page не найдена');
                    }
                    
                    // Загружаем данные о задачах и истории
                    await this.app.uiManager.loadBackgroundTasks();
                    await this.app.uiManager.loadTaskHistory();
                    
                    // Эмитируем событие смены страницы
                    if (this.eventManager) {
                        this.eventManager.emitPageChange('background-tasks');
                    }
                    
                    return;
                }
                
                const targetElement = this.app.getElementSafe(`${targetPage}-page`);
                if (targetElement) {
                    targetElement.classList.add('active');
                }
                
                // Обновляем заголовок страницы
                this.app.switchPage(targetPage);
                
                // Если переключаемся на страницу настроек, загружаем настройки
                if (targetPage === 'settings') {
                    await this.app.loadDatabaseSettings();
                }
                
                // Эмитируем событие смены страницы
                if (this.eventManager) {
                    this.eventManager.emitPageChange(targetPage);
                }
            });
        });
    }

    // Настройка меню настроек (удалено - теперь в меню пользователя)
    setupSettings() {
        // Элементы settings-toggle и settings-dropdown удалены
        // Настройки теперь доступны через меню пользователя
    }

    // Настройка меню пользователя
    setupUserMenu() {
        const userToggle = this.app.getElementSafe('user-toggle');
        const userDropdown = this.app.getElementSafe('user-dropdown');
        const themeLink = this.app.getElementSafe('theme-link');
        const logoutLink = this.app.getElementSafe('logout-link');
        const userName = this.app.getElementSafe('user-name');

        // Загружаем информацию о пользователе
        const userInfo = this.storage.get('user_info');
        if (userInfo) {
            try {
                const user = typeof userInfo === 'string' ? JSON.parse(userInfo) : userInfo;
                if (userName) {
                    userName.textContent = user.username;
                }
            } catch (e) {
                console.warn('Ошибка парсинга пользователя:', e);
            }
        }

        // Переключение выпадающего меню пользователя
        if (userToggle) {
            userToggle.addEventListener('click', (e) => {
                e.stopPropagation();
                userDropdown.classList.toggle('show');
            });
        }

        // Закрытие выпадающих меню при клике вне их
        document.addEventListener('click', (e) => {
            if (userDropdown && !userDropdown.contains(e.target) && !userToggle.contains(e.target)) {
                userDropdown.classList.remove('show');
            }
        });

        // Переключение темы
        if (themeLink) {
            themeLink.addEventListener('click', (e) => {
                e.preventDefault();
                this.app.toggleTheme();
            });
        }

        // Выход
        if (logoutLink) {
            logoutLink.addEventListener('click', (e) => {
                e.preventDefault();
                this.app.logout();
            });
        }
    }

    // Настройка форм
    setupForms() {
        // Форма настроек VM перенесена в modules/vm.js

        // Форма настроек Impact
        const impactForm = this.app.getElementSafe('impact-form');
        if (impactForm) {
            impactForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.app.saveImpactSettings();
            });
        }

        // Форма поиска CVE
        const cveSearchForm = this.app.getElementSafe('cve-search-form');
        if (cveSearchForm) {
            cveSearchForm.addEventListener('submit', (e) => {
                e.preventDefault();
                const cveIdInput = this.app.getElementSafe('cve-id');
                if (cveIdInput && cveIdInput.value.trim()) {
                    this.app.searchCVE(cveIdInput.value.trim());
                } else {
                    console.warn('CVE ID не указан');
                    this.app.showNotification('Пожалуйста, введите CVE ID', 'warning');
                }
            });
        }

        // Обработка ползунка порога риска
        const thresholdSlider = this.app.getElementSafe('risk-threshold');
        const thresholdValue = this.app.getElementSafe('threshold-value');
        if (thresholdSlider && thresholdValue) {
            thresholdSlider.addEventListener('input', (e) => {
                const value = e.target.value;
                thresholdValue.textContent = value;
                this.app.updateThresholdSlider(value);
            });
        }

        // Кнопка проверки подключения VM перенесена в modules/vm.js
    }

    // Настройка EPSS
    setupEPSS() {
        const epssForm = this.app.getElementSafe('epss-upload-form');
        if (!epssForm) return;

        epssForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const fileInput = epssForm.querySelector('input[type="file"]');
            const file = fileInput.files[0];
            
            if (!file) {
                this.app.showNotification('Выберите файл для загрузки', 'warning');
                return;
            }

            try {
                // Показываем прогресс
                this.app.showOperationProgress('epss', 'Загрузка EPSS...');

                // Задержки для UI
                await this.app.delay(VulnAnalizer.DELAYS.MEDIUM);
                await this.app.delay(VulnAnalizer.DELAYS.MEDIUM);

                const data = await this.api.uploadFile('/epss/upload', file);
                
                if (data && data.success) {
                    this.app.showNotification(`Загружено записей: ${data.count}`, 'success');
                    this.app.updateEPSSStatus();
                } else {
                    this.app.showOperationError('epss', 'Ошибка загрузки EPSS', data.detail || 'Неизвестная ошибка');
                    this.app.showNotification('Ошибка загрузки EPSS', 'error');
                }
            } catch (err) {
                this.app.showOperationError('epss', 'Ошибка загрузки EPSS', err.message);
                this.app.showNotification('Ошибка загрузки EPSS', 'error');
            }
        });
    }

    // Настройка ExploitDB
    setupExploitDB() {
        const exploitdbForm = this.app.getElementSafe('exploitdb-upload-form');
        if (!exploitdbForm) return;

        exploitdbForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const fileInput = exploitdbForm.querySelector('input[type="file"]');
            const file = fileInput.files[0];
            
            if (!file) {
                this.app.showNotification('Выберите файл для загрузки', 'warning');
                return;
            }

            try {
                // Показываем прогресс
                this.app.showOperationProgress('exploitdb', 'Загрузка ExploitDB...');

                // Задержки для UI
                await this.app.delay(VulnAnalizer.DELAYS.MEDIUM);
                await this.app.delay(VulnAnalizer.DELAYS.LONG);

                const data = await this.api.uploadFile('/exploitdb/upload', file);
                
                if (data && data.success) {
                    this.app.showNotification(`Загружено записей: ${data.count}`, 'success');
                    this.app.updateExploitDBStatus();
                } else {
                    this.app.showOperationError('exploitdb', 'Ошибка загрузки ExploitDB', data.detail || 'Неизвестная ошибка');
                    this.app.showNotification('Ошибка загрузки ExploitDB', 'error');
                }
            } catch (err) {
                this.app.showOperationError('exploitdb', 'Ошибка загрузки ExploitDB', err.message);
                this.app.showNotification('Ошибка загрузки ExploitDB', 'error');
            }
        });
    }

    // Настройка CVE
    setupCVE() {
        if (this.app.cveService) {
            this.app.cveService.setupCVE();
        }
    }

    // Настройка хостов
    setupHosts() {
        // Делегируем настройку хостов в HostsService
        if (this.app.hostsService) {
            // Настройка формы поиска хостов
            const hostsForm = this.app.getElementSafe('hosts-search-form');
            if (hostsForm) {
                hostsForm.addEventListener('submit', (e) => {
                    e.preventDefault();
                    this.app.debouncedSearchHosts(1);
                });
            }

            // Настройка формы импорта хостов
            const hostsImportForm = this.app.getElementSafe('hosts-upload-form');
            if (hostsImportForm) {
                hostsImportForm.addEventListener('submit', async (e) => {
                    e.preventDefault();
                    const fileInput = hostsImportForm.querySelector('input[type="file"]');
                    const file = fileInput.files[0];
                    
                    if (file) {
                        await this.app.hostsService.importHosts(file);
                    }
                });
            }

            // Настройка кнопки ручного импорта VM
            const vmManualImportBtn = this.app.getElementSafe('vm-manual-import-btn');
            if (vmManualImportBtn) {
                vmManualImportBtn.addEventListener('click', async (e) => {
                    e.preventDefault();
                    await this.app.hostsService.startVMManualImport();
                });
            }
        }
    }

    // Настройка сворачиваемых блоков
    setupCollapsibleBlocks() {
        const collapsibleHeaders = document.querySelectorAll('.collapsible-header');
        
        collapsibleHeaders.forEach(header => {
            // Инициализируем стрелки как свернутые по умолчанию
            const arrow = header.querySelector('.collapsible-arrow i');
            if (arrow) {
                arrow.style.transform = 'rotate(-90deg)';
            }
            header.classList.add('collapsed');
            
            // Инициализируем контент как свернутый
            const targetId = header.getAttribute('data-target');
            const content = this.app.getElementSafe(targetId);
            if (content) {
                content.style.display = 'none';
            }
            
            header.addEventListener('click', (e) => {
                // Предотвращаем срабатывание при клике на форму внутри
                if (e.target.closest('form') || (e.target.closest('button') && !e.target.closest('.formula-btn'))) {
                    return;
                }
                const targetId = header.getAttribute('data-target');
                const content = this.app.getElementSafe(targetId);
                
                if (content) {
                    const isCollapsed = content.style.display === 'none' || content.style.display === '';
                    
                    if (isCollapsed) {
                        // Разворачиваем блок
                        content.style.display = 'block';
                        arrow.style.transform = 'rotate(0deg)';
                        header.classList.remove('collapsed');
                    } else {
                        // Сворачиваем блок
                        content.style.display = 'none';
                        arrow.style.transform = 'rotate(-90deg)';
                        header.classList.add('collapsed');
                    }
                }
            });
        });
    }

    // Инициализация всех настроек
    init() {
        this.setupNavigation();
        this.setupSettings();
        this.setupUserMenu();
        this.setupForms();
        this.setupEPSS();
        this.setupExploitDB();
        this.setupCVE();
        this.setupHosts();
        this.setupCollapsibleBlocks();
    }

    // Загрузка данных фоновых задач
    async loadBackgroundTasksData() {
        try {
            const response = await fetch('/vulnanalizer/api/background-tasks/status');
            if (response.ok) {
                const data = await response.json();
                return data;
            } else {
                console.warn('⚠️ Ошибка загрузки данных фоновых задач:', response.status);
            }
        } catch (error) {
            console.error('Ошибка загрузки данных фоновых задач:', error);
        }
    }

    // Проверка активных задач импорта
    async checkActiveImportTasks() {
        try {
            const response = await fetch('/vulnanalizer/api/hosts/import-progress');
            if (response.ok) {
                const data = await response.json();
                return data;
            } else {
                console.warn('⚠️ Ошибка проверки активных задач импорта:', response.status);
            }
        } catch (error) {
            console.error('Ошибка проверки активных задач импорта:', error);
        }
    }

    // Загрузка настроек базы данных
    async loadDatabaseSettings() {
        try {
            const response = await fetch('/vulnanalizer/api/system/settings');
            if (response.ok) {
                const data = await response.json();
                return data;
            } else {
                console.warn('⚠️ Ошибка загрузки настроек базы данных:', response.status);
            }
        } catch (error) {
            console.error('Ошибка загрузки настроек базы данных:', error);
        }
    }
}

// Экспорт для использования в других модулях
if (typeof module !== 'undefined' && module.exports) {
    module.exports = SetupManager;
} else {
    window.SetupManager = SetupManager;
}
