class VulnAnalizer {
    constructor() {
        // Инициализируем UIManager для управления боковой панелью и темами
        if (typeof UIManager !== 'undefined') {
            this.uiManager = new UIManager();
        } else {
            console.warn('UIManager not found, UI management will be limited');
            this.uiManager = null;
        }
        
        this.init();
        this.operationStatus = {}; // Хранит статус текущих операций
        this.lastNotifiedCompletionTime = localStorage.getItem('app_last_notification_time'); // Отслеживаем последнее показанное уведомление
        this.paginationState = {
            currentPage: 1,
            totalPages: 1,
            totalCount: 0,
            limit: 100
        };
    }

    // Получение базового пути для API
    getApiBasePath() {
        // Определяем, находимся ли мы в подпути /vulnanalizer/
        const path = window.location.pathname;
        if (path.startsWith('/vulnanalizer/')) {
            return '/vulnanalizer/api';
        }
        return '/api';
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
        
        if (typeof HostsModule !== 'undefined') {
            this.hostsModule = new HostsModule(this);
        }
        
        if (typeof SettingsModule !== 'undefined') {
            this.settingsModule = new SettingsModule(this);
        }
        
        if (typeof CVEModalModule !== 'undefined') {
            this.cveModal = new CVEModalModule(this);
        } else {
            console.warn('CVEModalModule не найден!');
        }
        
        if (typeof MetasploitModule !== 'undefined') {
            this.metasploitModule = new MetasploitModule(this);
        } else {
            console.warn('MetasploitModule не найден!');
        }
        
        if (typeof MetasploitModalModule !== 'undefined') {
            this.metasploitModal = new MetasploitModalModule(this);
        } else {
            console.warn('MetasploitModalModule не найден!');
        }
        
        if (typeof EPSSModalModule !== 'undefined') {
            this.epssModal = new EPSSModalModule(this);
        } else {
            console.warn('EPSSModalModule не найден!');
        }
        
        if (typeof ExploitDBModalModule !== 'undefined') {
            this.exploitdbModal = new ExploitDBModalModule(this);
        } else {
            console.warn('ExploitDBModalModule не найден!');
        }
        
        if (typeof CVEPreviewModalModule !== 'undefined') {
            this.cvePreviewModal = new CVEPreviewModalModule(this);
        } else {
            console.warn('CVEPreviewModalModule не найден!');
        }
    }

    init() {
        // Проверяем авторизацию
        this.checkAuth();
        
        this.setupNavigation();
        this.setupSettings();
        this.setupUserMenu();
        this.setupForms();
        this.setupEPSS();
        this.setupExploitDB();
        this.setupCVE();
        this.setupHosts();
        this.setupVM();
        this.setupCollapsibleBlocks();
        
        // Инициализируем модули после настройки всех компонентов
        this.initModules();
        
        // Инициализируем активную страницу
        this.initializeActivePage();
        
        // Загружаем статус хостов при инициализации
        setTimeout(async () => {
            this.updateHostsStatus();
            this.updateEPSSStatus();
            this.updateExploitDBStatus();
            this.updateCVEStatus();
            this.updateMetasploitStatus();
            this.loadBackgroundTasksData();
            this.checkActiveImportTasks(); // Проверяем активные задачи импорта и обновления
            
            // Загружаем настройки базы данных
            await this.loadDatabaseSettings();
        }, 100);
    }

    checkAuth() {
        const token = localStorage.getItem('auth_token');

        
        if (!token) {
            // Если нет токена, перенаправляем на страницу входа

            window.location.href = '/auth/';
            return;
        }

        // Проверяем токен через auth сервис

        fetch('/auth/api/me', {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        }).then(response => {

            if (response.ok) {
                return response.json();
            } else {

                localStorage.removeItem('auth_token');
                localStorage.removeItem('user_info');
                window.location.href = '/auth/';
                throw new Error('Auth failed');
            }
        }).then(userData => {
            // Сохраняем информацию о пользователе

            
            // Сохраняем только объект пользователя, а не весь ответ API
            if (userData.user) {
                localStorage.setItem('user_info', JSON.stringify(userData.user));
            } else {
                localStorage.setItem('user_info', JSON.stringify(userData));
            }
        }).catch((error) => {
            localStorage.removeItem('auth_token');
            localStorage.removeItem('user_info');
            window.location.href = '/auth/';
        });
    }

    initTheme() {
        const savedTheme = localStorage.getItem('theme') || 'light';
        document.body.className = `${savedTheme}-theme`;
        this.updateThemeText(savedTheme);
    }

    updateThemeText(theme) {
        const themeText = document.getElementById('theme-text');
        const themeIcon = document.querySelector('#theme-link i');
        
        if (theme === 'dark') {
            themeText.textContent = 'Темная';
            themeIcon.className = 'fas fa-moon';
        } else {
            themeText.textContent = 'Светлая';
            themeIcon.className = 'fas fa-sun';
        }
    }

    updateBreadcrumb(page) {
        // Заголовки страниц больше не обновляются
        // Функция оставлена для совместимости
    }

    toggleTheme() {
        const body = document.body;
        
        if (body.classList.contains('light-theme')) {
            body.className = 'dark-theme';
            localStorage.setItem('theme', 'dark');
            this.updateThemeText('dark');
        } else {
            body.className = 'light-theme';
            localStorage.setItem('theme', 'light');
            this.updateThemeText('light');
        }
    }

    initializeActivePage() {
        // Скрываем все страницы
        const allPages = document.querySelectorAll('.page-content');
        allPages.forEach(page => {
            page.classList.remove('active');
        });
        
        // Показываем первую страницу (analysis) по умолчанию
        const analysisPage = document.getElementById('analysis-page');
        if (analysisPage) {
            analysisPage.classList.add('active');
        }
        
        // Устанавливаем активную вкладку
        const analysisTab = document.querySelector('.sidebar-tab[data-page="analysis"]');
        if (analysisTab) {
            analysisTab.classList.add('active');
        }
    }

    setupNavigation() {
        const sidebarTabs = document.querySelectorAll('.sidebar-tab');
        
        sidebarTabs.forEach(tab => {
            tab.addEventListener('click', async (e) => {
                e.preventDefault();
                
                // Убираем активный класс со всех вкладок
                sidebarTabs.forEach(t => t.classList.remove('active'));
                
                // Добавляем активный класс к текущей вкладке
                tab.classList.add('active');
                
                // Скрываем все страницы
                document.querySelectorAll('.page-content').forEach(page => {
                    page.classList.remove('active');
                });
                
                // Показываем нужную страницу
                const targetPage = tab.getAttribute('data-page');
                const targetElement = document.getElementById(`${targetPage}-page`);
                if (targetElement) {
                    targetElement.classList.add('active');
                } else {
                    console.error(`Page element not found: ${targetPage}-page`);
                }
                
                // Обновляем заголовок страницы
                this.switchPage(targetPage);
                
                // Если переключаемся на страницу настроек, загружаем настройки
                if (targetPage === 'settings') {
                    await this.loadDatabaseSettings();
                    
                    // Инициализируем CVE Manager если он еще не инициализирован
                    if (typeof CVEManager !== 'undefined' && !this.cveManager) {
                        this.cveManager = new CVEManager(this);
                    }
                }
            });
        });
    }

    setupSettings() {
        const settingsToggle = document.getElementById('settings-toggle');
        const settingsDropdown = document.getElementById('settings-dropdown');

        // Загружаем версию приложения
        this.loadAppVersion();

        // Переключение выпадающего меню настроек
        if (settingsToggle) {
            settingsToggle.addEventListener('click', (e) => {
                e.stopPropagation();
                // Закрываем меню пользователя при открытии настроек
                const userDropdown = document.getElementById('user-dropdown');
                if (userDropdown) {
                    userDropdown.classList.remove('show');
                }
                settingsDropdown.classList.toggle('show');
            });
        }

        // Закрытие при клике вне меню настроек
        document.addEventListener('click', (e) => {
            if (settingsToggle && !settingsToggle.contains(e.target) && !settingsDropdown.contains(e.target)) {
                settingsDropdown.classList.remove('show');
            }
        });
    }

    setupUserMenu() {
        const userToggle = document.getElementById('user-toggle');
        const userDropdown = document.getElementById('user-dropdown');
        const themeLink = document.getElementById('theme-link');
        const logoutLink = document.getElementById('logout-link');
        const userName = document.getElementById('user-name');

        // Загружаем информацию о пользователе
        const userInfo = localStorage.getItem('user_info');
        if (userInfo) {
            try {
                const user = JSON.parse(userInfo);
                if (userName) {
                    userName.textContent = user.username;
                }
            } catch (e) {
                console.error('Error parsing user info:', e);
            }
        }

        // Переключение выпадающего меню пользователя
        if (userToggle) {
            userToggle.addEventListener('click', (e) => {
                e.stopPropagation();
                // Закрываем меню настроек при открытии пользователя
                const settingsDropdown = document.getElementById('settings-dropdown');
                if (settingsDropdown) {
                    settingsDropdown.classList.remove('show');
                }
                userDropdown.classList.toggle('show');
            });
        }

        // Закрытие при клике вне меню пользователя
        document.addEventListener('click', (e) => {
            if (userToggle && !userToggle.contains(e.target) && !userDropdown.contains(e.target)) {
                userDropdown.classList.remove('show');
            }
        });

        // Обработка клика по пункту "Тема"
        if (themeLink) {
            themeLink.addEventListener('click', (e) => {
                e.preventDefault();
                userDropdown.classList.remove('show');
                this.toggleTheme();
            });
        }

        // Обработка клика по пункту "Выйти"
        if (logoutLink) {
            logoutLink.addEventListener('click', (e) => {
                e.preventDefault();
                userDropdown.classList.remove('show');
                this.logout();
            });
        }
    }

    logout() {
        // Очищаем данные пользователя
        localStorage.removeItem('auth_token');
        localStorage.removeItem('user_info');
        
        // Перенаправляем на страницу входа
        window.location.href = '/auth/';
    }

    switchPage(page) {
        // Заголовки страниц больше не обновляются
        // Только обновляем статусы
        
        switch(page) {
            case 'analysis':
                this.updateHostsStatus();
                break;
            case 'hosts':
                this.updateHostsStatus();
                this.checkActiveImportTasks(); // Проверяем активные задачи импорта
                break;
            case 'settings':
                this.updateEPSSStatus();
                this.updateExploitDBStatus();
                break;
            default:
                break;
        }
    }

    setupForms() {
        // Форма настроек
        const settingsForm = document.getElementById('settings-form');
        if (settingsForm) {
            settingsForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.saveSettings();
            });
        }



        // Форма поиска хостов
        const hostsSearchForm = document.getElementById('hosts-search-form');
        if (hostsSearchForm) {
            hostsSearchForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.searchHosts();
            });
        }

        // Кнопка очистки результатов поиска хостов
        const clearHostsResultsBtn = document.getElementById('clear-hosts-results');
        if (clearHostsResultsBtn) {
            clearHostsResultsBtn.addEventListener('click', () => {
                this.clearHostsResults();
            });
        }

        // Кнопка экспорта хостов
        const exportHostsBtn = document.getElementById('export-hosts');
        if (exportHostsBtn) {
            exportHostsBtn.addEventListener('click', () => {
                this.exportHosts();
            });
        }

        // Форма настроек Impact
        const impactForm = document.getElementById('impact-form');
        if (impactForm) {
            impactForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.saveImpactSettings();
            });
        }

        // Обработка ползунка порога риска
        const thresholdSlider = document.getElementById('risk-threshold');
        const thresholdValue = document.getElementById('threshold-value');
        if (thresholdSlider && thresholdValue) {
            thresholdSlider.addEventListener('input', (e) => {
                const value = e.target.value;
                thresholdValue.textContent = value;
                this.updateThresholdSlider(value);
            });
        }

        // Кнопка проверки подключения
        const testConnectionBtn = document.getElementById('test-connection');
        if (testConnectionBtn) {
            testConnectionBtn.addEventListener('click', () => {
                this.testConnection();
            });
        }

        // Кнопки очистки таблиц
        const clearHostsBtn = document.getElementById('clear-hosts-btn');
        if (clearHostsBtn) {
            clearHostsBtn.addEventListener('click', () => {
                this.clearHosts();
            });
        }

        const clearEPSSBtn = document.getElementById('clear-epss-btn');
        if (clearEPSSBtn) {
            clearEPSSBtn.addEventListener('click', () => {
                this.clearEPSS();
            });
        }

        const clearExploitDBBtn = document.getElementById('clear-exploitdb-btn');
        if (clearExploitDBBtn) {
            clearExploitDBBtn.addEventListener('click', () => {
                this.clearExploitDB();
            });
        }

        const clearCVEBtn = document.getElementById('clear-cve-btn');
        if (clearCVEBtn) {
            clearCVEBtn.addEventListener('click', () => {
                this.clearCVE();
            });
        }

        // Загружаем начальные данные
        this.loadInitialData();
    }

    setupEPSS() {
        // Загрузка CSV
        const epssForm = document.getElementById('epss-upload-form');
        if (epssForm) {
            epssForm.addEventListener('submit', async (e) => {
                e.preventDefault();
                const fileInput = document.getElementById('epss-file');
                if (!fileInput.files.length) {
                    this.showNotification('Выберите файл для загрузки', 'warning');
                    return;
                }
                
                const uploadBtn = document.getElementById('epss-upload-btn');
                const btnText = uploadBtn.querySelector('.btn-text');
                const spinner = uploadBtn.querySelector('.fa-spinner');
                
                // Показываем индикатор загрузки
                btnText.textContent = 'Загрузка...';
                spinner.style.display = 'inline-block';
                uploadBtn.disabled = true;
                
                // Показываем прогресс в статусбаре
                this.showOperationProgress('epss', 'Загрузка файла EPSS...', 0);
                
                const formData = new FormData();
                formData.append('file', fileInput.files[0]);
                
                try {
                    // Симулируем прогресс загрузки
                    this.updateOperationProgress('epss', 'Обработка файла EPSS...', 25, 'Чтение CSV файла...');
                    await new Promise(resolve => setTimeout(resolve, 500));
                    
                    this.updateOperationProgress('epss', 'Загрузка данных в базу...', 50, 'Валидация и подготовка данных...');
                    await new Promise(resolve => setTimeout(resolve, 500));
                    
                    this.updateOperationProgress('epss', 'Сохранение записей...', 75, 'Запись в базу данных...');
                    
                    const resp = await fetch(this.getApiBasePath() + '/epss/upload', {
                        method: 'POST',
                        body: formData
                    });
                    const data = await resp.json();
                    
                    if (data.success) {
                        this.updateOperationProgress('epss', 'Завершение операции...', 90, 'Финальная обработка...');
                        await new Promise(resolve => setTimeout(resolve, 300));
                        
                        this.showOperationComplete('epss', 'EPSS данные успешно загружены', `Загружено записей: ${data.count}`);
                        this.showNotification(`Загружено записей: ${data.count}`, 'success');
                        this.updateEPSSStatus();
                        fileInput.value = ''; // Очищаем поле файла
                    } else {
                        this.showOperationError('epss', 'Ошибка загрузки EPSS', data.detail || 'Неизвестная ошибка');
                        this.showNotification('Ошибка загрузки EPSS', 'error');
                    }
                } catch (err) {
                    console.error('EPSS upload error:', err);
                    this.showOperationError('epss', 'Ошибка загрузки EPSS', err.message);
                    this.showNotification('Ошибка загрузки EPSS', 'error');
                } finally {
                    // Восстанавливаем кнопку
                    btnText.textContent = 'Загрузить CSV';
                    spinner.style.display = 'none';
                    uploadBtn.disabled = false;
                }
            });
        }
        
        // Кнопка скачивания с сайта
        const epssDownloadBtn = document.getElementById('epss-download-btn');
        if (epssDownloadBtn) {
            epssDownloadBtn.addEventListener('click', async () => {
                const btnText = epssDownloadBtn.querySelector('.btn-text');
                const spinner = epssDownloadBtn.querySelector('.fa-spinner');
                
                // Показываем индикатор загрузки
                btnText.textContent = 'Скачивание...';
                spinner.style.display = 'inline-block';
                epssDownloadBtn.disabled = true;
                
                // Показываем прогресс в статусбаре
                this.showOperationProgress('epss', 'Подключение к серверу EPSS...', 0);
                
                try {
                    this.updateOperationProgress('epss', 'Скачивание файла...', 25, 'Загрузка с empiricalsecurity.com...');
                    await new Promise(resolve => setTimeout(resolve, 800));
                    
                    this.updateOperationProgress('epss', 'Обработка данных...', 50, 'Распаковка и парсинг CSV...');
                    await new Promise(resolve => setTimeout(resolve, 1000));
                    
                    this.updateOperationProgress('epss', 'Сохранение в базу...', 75, 'Запись EPSS данных...');
                    
                    const resp = await fetch(this.getApiBasePath() + '/epss/download', { method: 'POST' });
                    const data = await resp.json();
                    
                    if (data.success) {
                        this.updateOperationProgress('epss', 'Завершение операции...', 90, 'Финальная обработка...');
                        await new Promise(resolve => setTimeout(resolve, 300));
                        
                        this.showOperationComplete('epss', 'EPSS данные успешно скачаны', `Загружено записей: ${data.count}`);
                        this.showNotification(`Загружено записей: ${data.count}`, 'success');
                        this.updateEPSSStatus();
                    } else {
                        this.showOperationError('epss', 'Ошибка скачивания EPSS', data.detail || 'Неизвестная ошибка');
                        this.showNotification('Ошибка скачивания EPSS', 'error');
                    }
                } catch (err) {
                    console.error('EPSS download error:', err);
                    this.showOperationError('epss', 'Ошибка скачивания EPSS', err.message);
                    this.showNotification('Ошибка скачивания EPSS', 'error');
                } finally {
                    // Восстанавливаем кнопку
                    btnText.textContent = 'Скачать с сайта';
                    spinner.style.display = 'none';
                    epssDownloadBtn.disabled = false;
                }
            });
        }
    }

    setupExploitDB() {
        // Загрузка CSV
        const exploitdbForm = document.getElementById('exploitdb-upload-form');
        if (exploitdbForm) {
            exploitdbForm.addEventListener('submit', async (e) => {
                e.preventDefault();
                const fileInput = document.getElementById('exploitdb-file');
                if (!fileInput.files.length) {
                    this.showNotification('Выберите файл для загрузки', 'warning');
                    return;
                }
                
                const uploadBtn = document.getElementById('exploitdb-upload-btn');
                const btnText = uploadBtn.querySelector('.btn-text');
                const spinner = uploadBtn.querySelector('.fa-spinner');
                
                // Показываем индикатор загрузки
                btnText.textContent = 'Загрузка...';
                spinner.style.display = 'inline-block';
                uploadBtn.disabled = true;
                
                // Показываем прогресс в статусбаре
                this.showOperationProgress('exploitdb', 'Загрузка файла ExploitDB...', 0);
                
                const formData = new FormData();
                formData.append('file', fileInput.files[0]);
                
                try {
                    this.updateOperationProgress('exploitdb', 'Обработка файла ExploitDB...', 25, 'Чтение CSV файла...');
                    await new Promise(resolve => setTimeout(resolve, 500));
                    
                    this.updateOperationProgress('exploitdb', 'Валидация данных...', 50, 'Проверка и подготовка записей...');
                    await new Promise(resolve => setTimeout(resolve, 800));
                    
                    this.updateOperationProgress('exploitdb', 'Сохранение в базу...', 75, 'Запись эксплойтов в базу данных...');
                    
                    const resp = await fetch(this.getApiBasePath() + '/exploitdb/upload', {
                        method: 'POST',
                        body: formData
                    });
                    const data = await resp.json();
                    
                    if (data.success) {
                        this.updateOperationProgress('exploitdb', 'Завершение операции...', 90, 'Финальная обработка...');
                        await new Promise(resolve => setTimeout(resolve, 300));
                        
                        this.showOperationComplete('exploitdb', 'ExploitDB данные успешно загружены', `Загружено записей: ${data.count}`);
                        this.showNotification(`Загружено записей: ${data.count}`, 'success');
                        this.updateExploitDBStatus();
                        fileInput.value = ''; // Очищаем поле файла
                    } else {
                        this.showOperationError('exploitdb', 'Ошибка загрузки ExploitDB', data.detail || 'Неизвестная ошибка');
                        this.showNotification('Ошибка загрузки ExploitDB', 'error');
                    }
                } catch (err) {
                    console.error('ExploitDB upload error:', err);
                    this.showOperationError('exploitdb', 'Ошибка загрузки ExploitDB', err.message);
                    this.showNotification('Ошибка загрузки ExploitDB', 'error');
                } finally {
                    // Восстанавливаем кнопку
                    btnText.textContent = 'Загрузить CSV';
                    spinner.style.display = 'none';
                    uploadBtn.disabled = false;
                }
            });
        }
        
        // Кнопка скачивания с сайта
        const exploitdbDownloadBtn = document.getElementById('exploitdb-download-btn');
        if (exploitdbDownloadBtn) {
            exploitdbDownloadBtn.addEventListener('click', async () => {
                const btnText = exploitdbDownloadBtn.querySelector('.btn-text');
                const spinner = exploitdbDownloadBtn.querySelector('.fa-spinner');
                
                // Показываем индикатор загрузки
                btnText.textContent = 'Скачивание...';
                spinner.style.display = 'inline-block';
                exploitdbDownloadBtn.disabled = true;
                
                // Показываем прогресс в статусбаре
                this.showOperationProgress('exploitdb', 'Подключение к GitLab...', 0);
                
                try {
                    this.updateOperationProgress('exploitdb', 'Скачивание файла...', 25, 'Загрузка с gitlab.com...');
                    await new Promise(resolve => setTimeout(resolve, 1000));
                    
                    this.updateOperationProgress('exploitdb', 'Обработка данных...', 50, 'Парсинг CSV файла эксплойтов...');
                    await new Promise(resolve => setTimeout(resolve, 1200));
                    
                    this.updateOperationProgress('exploitdb', 'Сохранение в базу...', 75, 'Запись эксплойтов в базу данных...');
                    
                    const resp = await fetch(this.getApiBasePath() + '/exploitdb/download', { method: 'POST' });
                    const data = await resp.json();
                    
                    if (data.success) {
                        this.updateOperationProgress('exploitdb', 'Завершение операции...', 90, 'Финальная обработка...');
                        await new Promise(resolve => setTimeout(resolve, 300));
                        
                        this.showOperationComplete('exploitdb', 'ExploitDB данные успешно скачаны', `Загружено записей: ${data.count}`);
                        this.showNotification(`Загружено записей: ${data.count}`, 'success');
                        this.updateExploitDBStatus();
                    } else {
                        this.showOperationError('exploitdb', 'Ошибка скачивания ExploitDB', data.detail || 'Неизвестная ошибка');
                        this.showNotification('Ошибка скачивания ExploitDB', 'error');
                    }
                } catch (err) {
                    console.error('ExploitDB download error:', err);
                    this.showOperationError('exploitdb', 'Ошибка скачивания ExploitDB', err.message);
                    this.showNotification('Ошибка скачивания ExploitDB', 'error');
                } finally {
                    // Восстанавливаем кнопку
                    btnText.textContent = 'Скачать с сайта';
                    spinner.style.display = 'none';
                    exploitdbDownloadBtn.disabled = false;
                }
            });
        }
    }

    setupCVE() {
        // Инициализируем CVE Manager если он доступен
        if (typeof CVEManager !== 'undefined') {
            this.cveManager = new CVEManager(this);
        } else {
            console.warn('CVEManager not found, using legacy CVE functionality');
            this.setupLegacyCVE();
        }
    }
    
    setupLegacyCVE() {
        // Загрузка CSV
        const cveForm = document.getElementById('cve-upload-form');
        if (cveForm) {
            cveForm.addEventListener('submit', async (e) => {
                e.preventDefault();
                const fileInput = document.getElementById('cve-file');
                if (!fileInput.files.length) {
                    this.showNotification('Выберите файл для загрузки', 'warning');
                    return;
                }
                
                const uploadBtn = document.getElementById('cve-upload-btn');
                const btnText = uploadBtn.querySelector('.btn-text');
                const spinner = uploadBtn.querySelector('.fa-spinner');
                
                // Показываем индикатор загрузки
                btnText.textContent = 'Загрузка...';
                spinner.style.display = 'inline-block';
                uploadBtn.disabled = true;
                
                // Показываем прогресс в статусбаре
                this.showOperationProgress('cve', 'Загрузка файла CVE...', 0);
                
                const formData = new FormData();
                formData.append('file', fileInput.files[0]);
                
                try {
                    // Симулируем прогресс загрузки
                    this.updateOperationProgress('cve', 'Обработка файла CVE...', 25, 'Чтение CSV файла...');
                    await new Promise(resolve => setTimeout(resolve, 500));
                    
                    this.updateOperationProgress('cve', 'Загрузка данных в базу...', 50, 'Валидация и подготовка данных...');
                    await new Promise(resolve => setTimeout(resolve, 500));
                    
                    this.updateOperationProgress('cve', 'Сохранение записей...', 75, 'Запись в базу данных...');
                    
                    const resp = await fetch(this.getApiBasePath() + '/cve/upload', {
                        method: 'POST',
                        body: formData
                    });
                    const data = await resp.json();
                    
                    if (data.success) {
                        this.updateOperationProgress('cve', 'Завершение операции...', 90, 'Финальная обработка...');
                        await new Promise(resolve => setTimeout(resolve, 300));
                        
                        this.showOperationComplete('cve', 'CVE данные успешно загружены', `Загружено записей: ${data.count}`);
                        this.showNotification(`Загружено записей: ${data.count}`, 'success');
                        this.updateCVEStatus();
                        fileInput.value = ''; // Очищаем поле файла
                    } else {
                        this.showOperationError('cve', 'Ошибка загрузки CVE', data.detail || 'Неизвестная ошибка');
                        this.showNotification('Ошибка загрузки CVE', 'error');
                    }
                } catch (err) {
                    console.error('CVE upload error:', err);
                    this.showOperationError('cve', 'Ошибка загрузки CVE', err.message);
                    this.showNotification('Ошибка загрузки CVE', 'error');
                } finally {
                    // Восстанавливаем кнопку
                    btnText.textContent = 'Загрузить CSV';
                    spinner.style.display = 'none';
                    uploadBtn.disabled = false;
                }
            });
        }
        
        // Кнопка получения ссылок для скачивания
        const cveUrlsBtn = document.getElementById('cve-urls-btn');
        if (cveUrlsBtn) {
            cveUrlsBtn.addEventListener('click', async () => {
                try {
                    const resp = await fetch(this.getApiBasePath() + '/cve/download-urls');
                    const data = await resp.json();
                    
                    if (data.success) {
                        let urlsHtml = '<div style="background-color: #f8f9fa; border: 1px solid #dee2e6; border-radius: 8px; padding: 12px; margin-top: 10px;">';
                        urlsHtml += '<h4 style="margin: 0 0 8px 0; font-size: 0.9rem; font-weight: 600; color: #1e293b;">📋 Ссылки для скачивания CVE по годам</h4>';
                        urlsHtml += '<p style="margin: 0 0 8px 0; line-height: 1.4; font-size: 0.8rem;">Скачайте файлы по ссылкам ниже для offline загрузки:</p>';
                        
                        data.urls.forEach(urlInfo => {
                            urlsHtml += `<div style="margin-bottom: 6px;">`;
                            urlsHtml += `<a href="${urlInfo.url}" target="_blank" style="display: flex; align-items: center; gap: 6px; color: #2563eb; text-decoration: none; font-size: 0.8rem; padding: 4px 8px; border-radius: 4px;">`;
                            urlsHtml += `🔗 <span style="flex: 1;">CVE ${urlInfo.year} (${urlInfo.filename})</span>`;
                            urlsHtml += `</a>`;
                            urlsHtml += `</div>`;
                        });
                        
                        urlsHtml += '</div>';
                        
                        const statusDiv = document.getElementById('cve-status');
                        if (statusDiv) {
                            statusDiv.innerHTML = urlsHtml;
                        }
                    } else {
                        this.showNotification('Ошибка получения ссылок CVE', 'error');
                    }
                } catch (err) {
                    console.error('CVE URLs error:', err);
                    this.showNotification('Ошибка получения ссылок CVE', 'error');
                }
            });
        }
        
        // Кнопка скачивания с сайта
        const cveDownloadBtn = document.getElementById('cve-download-btn');
        if (cveDownloadBtn) {
            cveDownloadBtn.addEventListener('click', async () => {
                const btnText = cveDownloadBtn.querySelector('.btn-text');
                const spinner = cveDownloadBtn.querySelector('.fa-spinner');
                
                // Показываем индикатор загрузки
                btnText.textContent = 'Скачивание...';
                spinner.style.display = 'inline-block';
                cveDownloadBtn.disabled = true;
                
                // Показываем кнопку отмены
                const cveCancelBtn = document.getElementById('cve-cancel-btn');
                if (cveCancelBtn) {
                    cveCancelBtn.style.display = 'inline-block';
                }
                
                // Показываем прогресс в статусбаре
                this.showOperationProgress('cve', 'Подключение к серверу CVE...', 0);
                
                try {
                    this.updateOperationProgress('cve', 'Скачивание файла...', 25, 'Загрузка с empiricalsecurity.com...');
                    await new Promise(resolve => setTimeout(resolve, 800));
                    
                    this.updateOperationProgress('cve', 'Обработка данных...', 50, 'Распаковка и парсинг CSV...');
                    await new Promise(resolve => setTimeout(resolve, 1000));
                    
                    this.updateOperationProgress('cve', 'Сохранение в базу...', 75, 'Запись CVE данных...');
                    
                    const resp = await fetch(this.getApiBasePath() + '/cve/download', { method: 'POST' });
                    const data = await resp.json();
                    
                    if (data.success) {
                        this.updateOperationProgress('cve', 'Завершение операции...', 90, 'Финальная обработка...');
                        await new Promise(resolve => setTimeout(resolve, 300));
                        
                        this.showOperationComplete('cve', 'CVE данные успешно скачаны', `Загружено записей: ${data.count}`);
                        this.showNotification(`Загружено записей: ${data.count}`, 'success');
                        this.updateCVEStatus();
                    } else {
                        this.showOperationError('cve', 'Ошибка скачивания CVE', data.detail || 'Неизвестная ошибка');
                        this.showNotification('Ошибка скачивания CVE', 'error');
                    }
                } catch (err) {
                    console.error('CVE download error:', err);
                    this.showOperationError('cve', 'Ошибка скачивания CVE', err.message);
                    this.showNotification('Ошибка скачивания CVE', 'error');
                } finally {
                    // Восстанавливаем кнопку
                    btnText.textContent = 'Скачать с NVD';
                    spinner.style.display = 'none';
                    cveDownloadBtn.disabled = false;
                    
                    // Скрываем кнопку отмены
                    const cveCancelBtn = document.getElementById('cve-cancel-btn');
                    if (cveCancelBtn) {
                        cveCancelBtn.style.display = 'none';
                    }
                }
            });
        }
        
        // Кнопка отмены загрузки CVE
        const cveCancelBtn = document.getElementById('cve-cancel-btn');
        if (cveCancelBtn) {
            cveCancelBtn.addEventListener('click', async () => {
                const btnText = cveCancelBtn.querySelector('.btn-text');
                const spinner = cveCancelBtn.querySelector('.fa-spinner');
                
                // Показываем индикатор
                btnText.textContent = 'Отмена...';
                spinner.style.display = 'inline-block';
                cveCancelBtn.disabled = true;
                
                try {
                    const resp = await fetch(this.getApiBasePath() + '/cve/cancel', { method: 'POST' });
                    const data = await resp.json();
                    
                    if (data.success) {
                        this.showNotification('Загрузка CVE отменена', 'success');
                        // Скрываем кнопку отмены
                        cveCancelBtn.style.display = 'none';
                        // Показываем кнопку скачивания
                        const cveDownloadBtn = document.getElementById('cve-download-btn');
                        if (cveDownloadBtn) {
                            cveDownloadBtn.disabled = false;
                        }
                    } else {
                        this.showNotification(data.message || 'Ошибка отмены загрузки', 'warning');
                    }
                } catch (err) {
                    console.error('CVE cancel error:', err);
                    this.showNotification('Ошибка отмены загрузки CVE', 'error');
                } finally {
                    // Восстанавливаем кнопку
                    btnText.textContent = 'Остановить загрузку';
                    spinner.style.display = 'none';
                    cveCancelBtn.disabled = false;
                }
            });
        }


    }

    setupHosts() {
        // Загрузка CSV хостов с поддержкой сжатых файлов
        const hostsForm = document.getElementById('hosts-upload-form');
        if (hostsForm) {
            hostsForm.addEventListener('submit', async (e) => {
                e.preventDefault();
                const fileInput = document.getElementById('hosts-file');
                if (!fileInput.files.length) {
                    this.showNotification('Выберите файл для загрузки', 'warning');
                    return;
                }
                
                const file = fileInput.files[0];
                const fileSizeMB = (file.size / (1024 * 1024)).toFixed(2);
                
                // Проверяем размер файла (максимум 2GB)
                const maxFileSize = 2 * 1024 * 1024 * 1024; // 2GB в байтах
                if (file.size > maxFileSize) {
                    this.showNotification(`Файл слишком большой (${fileSizeMB} МБ). Максимальный размер: 2 ГБ.`, 'error');
                    return;
                }
                
                // Обновляем accept для поддержки сжатых файлов
                fileInput.accept = '.csv,.zip,.gz,.gzip';
                
                const uploadBtn = document.getElementById('hosts-upload-btn');
                const btnText = uploadBtn.querySelector('.btn-text');
                const spinner = uploadBtn.querySelector('.fa-spinner');
                
                // Показываем индикатор загрузки
                btnText.textContent = 'Загрузка...';
                spinner.style.display = 'inline-block';
                uploadBtn.disabled = true;
                
                // Показываем прогресс-бар
                this.showImportProgress();
                
                const formData = new FormData();
                formData.append('file', file);
                
                try {
                    const resp = await fetch(this.getApiBasePath() + '/hosts/upload', {
                        method: 'POST',
                        body: formData
                    });
                    
                    // Проверяем статус ответа
                    if (!resp.ok) {
                        let errorMessage = `HTTP ${resp.status}: ${resp.statusText}`;
                        
                        // Пытаемся получить текст ошибки
                        try {
                            const errorText = await resp.text();
                            if (errorText.includes('<html>')) {
                                errorMessage = `Ошибка сервера (${resp.status}). Возможно, файл слишком большой или произошла внутренняя ошибка.`;
                            } else {
                                errorMessage = errorText;
                            }
                        } catch (textError) {
                            console.error('Error reading response text:', textError);
                        }
                        
                        this.showNotification('Ошибка загрузки: ' + errorMessage, 'error');
                        return;
                    }
                    
                    // Проверяем Content-Type
                    const contentType = resp.headers.get('content-type');
                    if (!contentType || !contentType.includes('application/json')) {
                        const errorMessage = 'Сервер вернул неверный формат ответа. Возможно, произошла ошибка на сервере.';
                        this.showNotification('Ошибка: ' + errorMessage, 'error');
                        return;
                    }
                    
                    const data = await resp.json();
                    
                    if (data.success) {
                        this.showNotification(data.message, 'success');
                        this.updateHostsStatus();
                        fileInput.value = ''; // Очищаем поле файла
                        
                        // Показываем информацию о задаче
                        if (data.task_id) {
                            this.showNotification(`Задача импорта создана: ${data.task_id}`, 'info');
                            
                            // Запускаем мониторинг прогресса фоновой задачи
                            this.startBackgroundTaskMonitoring(data.task_id);
                        }
                    } else {
                        this.showNotification('Ошибка импорта: ' + (data.detail || 'Неизвестная ошибка'), 'error');
                    }
                } catch (err) {
                    console.error('Hosts upload error:', err);
                    let errorMessage = err.message;
                    
                    // Улучшенная обработка ошибок
                    if (err.name === 'TypeError' && err.message.includes('JSON')) {
                        errorMessage = 'Сервер вернул неверный формат ответа. Возможно, произошла ошибка на сервере или файл слишком большой.';
                    } else if (err.name === 'TypeError' && err.message.includes('fetch')) {
                        errorMessage = 'Ошибка соединения с сервером. Проверьте подключение к интернету.';
                    }
                    
                    this.showNotification('Ошибка импорта: ' + errorMessage, 'error');
                } finally {
                    // Восстанавливаем кнопку
                    btnText.textContent = 'Загрузить файл';
                    spinner.style.display = 'none';
                    uploadBtn.disabled = false;
                }
            });
        }
        
        // Запускаем мониторинг прогресса фонового обновления
        this.startBackgroundUpdateMonitoring();
        
        // Проверяем активные задачи при загрузке страницы
        this.checkActiveImportTasks();
        
        // Поиск хостов
        const hostsSearchForm = document.getElementById('hosts-search-form');
        if (hostsSearchForm) {
            hostsSearchForm.addEventListener('submit', async (e) => {
                e.preventDefault();
                await this.searchHosts();
            });
        }

        // Обработчики пагинации
        const prevPageBtn = document.getElementById('prev-page');
        const nextPageBtn = document.getElementById('next-page');
        
        if (prevPageBtn) {
            prevPageBtn.addEventListener('click', () => {
                if (this.paginationState.currentPage > 1) {
                    this.searchHosts(this.paginationState.currentPage - 1);
                }
            });
        }
        
        if (nextPageBtn) {
            nextPageBtn.addEventListener('click', () => {
                if (this.paginationState.currentPage < this.paginationState.totalPages) {
                    this.searchHosts(this.paginationState.currentPage + 1);
                }
            });
        }

        // Обработчик изменения количества записей на странице
        const resultsPerPageSelect = document.getElementById('results-per-page');
        if (resultsPerPageSelect) {
            resultsPerPageSelect.addEventListener('change', (e) => {
                this.paginationState.limit = parseInt(e.target.value);
                this.paginationState.currentPage = 1; // Сбрасываем на первую страницу
                this.searchHosts(1);
            });
        }
    }

    async updateExploitDBStatus() {
        const statusDiv = document.getElementById('exploitdb-status');
        if (!statusDiv) return;
        
        try {
            const resp = await fetch(this.getApiBasePath() + '/exploitdb/status');
            const data = await resp.json();
            
            if (data.success) {
                statusDiv.innerHTML = `
                    <div style="margin-bottom: 15px;">
                        <div class="status-info">
                            <i class="fas fa-database"></i>
                            <span>Записей в базе: <strong>${data.count}</strong></span>
                        </div>
                    </div>
                    
                    <!-- Подсказка с ссылками для ExploitDB -->
                    <div style="background-color: #f8f9fa; border: 1px solid #dee2e6; border-radius: 8px; padding: 12px; font-size: 0.875rem;">
                        <h4 style="margin: 0 0 8px 0; font-size: 0.9rem; font-weight: 600; color: #1e293b;">📋 Ссылки для скачивания ExploitDB</h4>
                        <p style="margin: 0 0 8px 0; line-height: 1.4;">Для offline загрузки используйте следующие ссылки:</p>
                        <div style="display: flex; flex-direction: column; gap: 6px;">
                            <a href="https://gitlab.com/exploit-database/exploitdb/-/raw/main/files_exploits.csv" target="_blank" style="display: flex; align-items: center; gap: 6px; color: #2563eb; text-decoration: none; font-size: 0.8rem; padding: 4px 8px; border-radius: 4px;">
                                🔗 <span style="flex: 1;">ExploitDB Files (основная база)</span>
                                <span style="font-size: 0.7rem; color: #64748b; font-style: italic;">~10MB</span>
                            </a>
                            <a href="https://gitlab.com/exploit-database/exploitdb/-/raw/main/files_shellcodes.csv" target="_blank" style="display: flex; align-items: center; gap: 6px; color: #2563eb; text-decoration: none; font-size: 0.8rem; padding: 4px 8px; border-radius: 4px;">
                                🔗 <span style="flex: 1;">ExploitDB Shellcodes</span>
                                <span style="font-size: 0.7rem; color: #64748b; font-style: italic;">~220KB</span>
                            </a>
                            <a href="https://github.com/offensive-security/exploitdb" target="_blank" style="display: flex; align-items: center; gap: 6px; color: #2563eb; text-decoration: none; font-size: 0.8rem; padding: 4px 8px; border-radius: 4px;">
                                📦 <span style="flex: 1;">GitHub репозиторий ExploitDB</span>
                            </a>
                            <a href="https://www.exploit-db.com/" target="_blank" style="display: flex; align-items: center; gap: 6px; color: #2563eb; text-decoration: none; font-size: 0.8rem; padding: 4px 8px; border-radius: 4px;">
                                🌐 <span style="flex: 1;">Официальный сайт ExploitDB</span>
                            </a>
                        </div>
                    </div>
                `;
            } else {
                statusDiv.innerHTML = `
                    <div class="status-error">
                        <i class="fas fa-exclamation-triangle"></i>
                        <span>Ошибка получения статуса</span>
                    </div>
                `;
            }
        } catch (err) {
            console.error('ExploitDB status error:', err);
            statusDiv.innerHTML = `
                <div class="status-error">
                    <i class="fas fa-exclamation-triangle"></i>
                    <span>Ошибка получения статуса</span>
                </div>
            `;
        }
    }

    async updateEPSSStatus() {
        const statusDiv = document.getElementById('epss-status');
        if (!statusDiv) return;
        
        try {
            const resp = await fetch(this.getApiBasePath() + '/epss/status');
            const data = await resp.json();
            if (data.success) {
                statusDiv.innerHTML = `
                    <div style="margin-bottom: 15px;">
                        <b>Записей в базе EPSS:</b> ${data.count}
                    </div>
                    
                    <!-- Подсказка с ссылками для EPSS -->
                    <div style="background-color: #f8f9fa; border: 1px solid #dee2e6; border-radius: 8px; padding: 12px; font-size: 0.875rem;">
                        <h4 style="margin: 0 0 8px 0; font-size: 0.9rem; font-weight: 600; color: #1e293b;">📋 Ссылки для скачивания EPSS</h4>
                        <p style="margin: 0 0 8px 0; line-height: 1.4;">Для offline загрузки используйте следующие ссылки:</p>
                        <div style="display: flex; flex-direction: column; gap: 6px;">
                            <a href="https://epss.empiricalsecurity.com/epss_scores-current.csv.gz" target="_blank" style="display: flex; align-items: center; gap: 6px; color: #2563eb; text-decoration: none; font-size: 0.8rem; padding: 4px 8px; border-radius: 4px;">
                                🔗 <span style="flex: 1;">EPSS Scores (текущая версия)</span>
                                <span style="font-size: 0.7rem; color: #64748b; font-style: italic;">~2MB</span>
                            </a>
                            <a href="https://epss.empiricalsecurity.com/" target="_blank" style="display: flex; align-items: center; gap: 6px; color: #2563eb; text-decoration: none; font-size: 0.8rem; padding: 4px 8px; border-radius: 4px;">
                                🔗 <span style="flex: 1;">EPSS Scores (официальный сайт)</span>
                                <span style="font-size: 0.7rem; color: #64748b; font-style: italic;">~2MB (gz)</span>
                            </a>
                            <a href="https://epss.cyentia.com/" target="_blank" style="display: flex; align-items: center; gap: 6px; color: #2563eb; text-decoration: none; font-size: 0.8rem; padding: 4px 8px; border-radius: 4px;">
                                🌐 <span style="flex: 1;">Официальный сайт EPSS</span>
                            </a>
                        </div>
                    </div>
                `;
            } else {
                statusDiv.innerHTML = '<span style="color:var(--error-color)">Ошибка получения статуса EPSS</span>';
            }
        } catch (err) {
            statusDiv.innerHTML = '<span style="color:var(--error-color)">Ошибка получения статуса EPSS</span>';
        }
    }

    async updateCVEStatus() {
        const statusDiv = document.getElementById('cve-status');
        if (!statusDiv) return;
        
        try {
            const resp = await fetch(this.getApiBasePath() + '/cve/status');
            const data = await resp.json();
            if (data.success) {
                statusDiv.innerHTML = `
                    <div style="margin-bottom: 15px;">
                        <b>Записей в базе CVE:</b> ${data.count}
                    </div>
                    
                    <!-- Подсказка с ссылками для CVE -->
                    <div style="background-color: #f8f9fa; border: 1px solid #dee2e6; border-radius: 8px; padding: 12px; font-size: 0.875rem;">
                        <h4 style="margin: 0 0 8px 0; font-size: 0.9rem; font-weight: 600; color: #1e293b;">📋 Ссылки для скачивания CVE</h4>
                        <p style="margin: 0 0 8px 0; line-height: 1.4;">Для offline загрузки используйте следующие ссылки:</p>
                        <div style="display: flex; flex-direction: column; gap: 6px;">
                            <a href="https://nvd.nist.gov/feeds/json/cve/1.1/" target="_blank" style="display: flex; align-items: center; gap: 6px; color: #2563eb; text-decoration: none; font-size: 0.8rem; padding: 4px 8px; border-radius: 4px;">
                                🔗 <span style="flex: 1;">NVD CVE Feeds (официальный сайт)</span>
                                <span style="font-size: 0.7rem; color: #64748b; font-style: italic;">JSON/GZ</span>
                            </a>
                            <a href="https://nvd.nist.gov/vuln/data-feeds" target="_blank" style="display: flex; align-items: center; gap: 6px; color: #2563eb; text-decoration: none; font-size: 0.8rem; padding: 4px 8px; border-radius: 4px;">
                                🌐 <span style="flex: 1;">NVD Data Feeds (документация)</span>
                            </a>
                        </div>
                    </div>
                `;
            } else {
                statusDiv.innerHTML = '<span style="color:var(--error-color)">Ошибка получения статуса CVE</span>';
            }
        } catch (err) {
            statusDiv.innerHTML = '<span style="color:var(--error-color)">Ошибка получения статуса CVE</span>';
        }
    }

    async updateMetasploitStatus() {
        // Делегируем обновление статуса в модуль Metasploit
        if (this.metasploitModule) {
            await this.metasploitModule.updateMetasploitStatus();
        }
    }

    async updateHostsStatus() {
        const statusDiv = document.getElementById('hosts-status');
        if (!statusDiv) return;
        
        try {
            const resp = await fetch(this.getApiBasePath() + '/hosts/status');
            const data = await resp.json();
            
            if (data.success) {
                statusDiv.innerHTML = `
                    <div class="status-info">
                        <i class="fas fa-server"></i>
                        <span>Хостов в базе: <strong>${data.count}</strong></span>
                    </div>
                `;
            } else {
                statusDiv.innerHTML = `
                    <div class="status-error">
                        <i class="fas fa-exclamation-triangle"></i>
                        <span>Ошибка получения статуса хостов</span>
                    </div>
                `;
            }
        } catch (err) {
            console.error('Hosts status error:', err);
            statusDiv.innerHTML = `
                <div class="status-error">
                    <i class="fas fa-exclamation-triangle"></i>
                    <span>Ошибка получения статуса хостов</span>
                </div>
            `;
        }
    }

    async searchHosts(page = 1) {
        // Отключаем дублирующий поиск - используем hosts.js
        return;
        
        const form = document.getElementById('hosts-search-form');
        const resultsDiv = document.getElementById('hosts-search-results');
        
        if (!form || !resultsDiv) return;
        
        const formData = new FormData(form);
        const params = new URLSearchParams();
        
        // Добавляем параметры поиска
        for (let [key, value] of formData.entries()) {
            if (key === 'exploits_only' || key === 'epss_only') {
                // Для чекбоксов добавляем значение только если они отмечены
                if (value === 'on') {
                    params.append(key, 'true');
                }
            } else if (value.trim()) {
                params.append(key, value.trim());
            }
        }
        
        // Добавляем параметры пагинации
        params.append('page', page);
        params.append('limit', this.paginationState.limit);
        
        try {
            const resp = await fetch(`${this.getApiBasePath()}/hosts/search?${params.toString()}`);
            const data = await resp.json();
            
            if (data.success) {
                const groupBy = formData.get('group_by') || '';
                this.renderHostsResults(data.results, groupBy, data);
            } else {
                this.showNotification('Ошибка поиска хостов', 'error');
            }
        } catch (err) {
            console.error('Hosts search error:', err);
            this.showNotification('Ошибка поиска хостов', 'error');
        }
    }

    renderHostsResults(hosts, groupBy = '', paginationData = null) {
        const resultsDiv = document.getElementById('hosts-search-results');
        if (!resultsDiv) return;
        
        if (!hosts || hosts.length === 0) {
            resultsDiv.innerHTML = `
                <div class="no-results">
                    <i class="fas fa-search"></i>
                    <p>Хосты не найдены</p>
                </div>
            `;
            this.hidePagination();
            return;
        }
        
        // Обновляем состояние пагинации
        if (paginationData) {
            this.paginationState = {
                currentPage: paginationData.page || 1,
                totalPages: paginationData.total_pages || 1,
                totalCount: paginationData.total_count || hosts.length,
                limit: paginationData.limit || 100
            };
        }
        
        // Создаем отдельный элемент для отображения количества найденных хостов
        const resultsContainer = document.querySelector('.hosts-search-results-container');
        const existingCountElement = resultsContainer.querySelector('.hosts-count');
        
        if (existingCountElement) {
            existingCountElement.remove();
        }
        
        const countElement = document.createElement('div');
        countElement.className = 'hosts-count';
        countElement.innerHTML = `<h4>Найдено хостов: ${this.paginationState.totalCount}</h4>`;
        
        // Вставляем элемент с количеством перед заголовком таблицы
        const tableHeader = resultsContainer.querySelector('.hosts-table-header');
        resultsContainer.insertBefore(countElement, tableHeader);
        
        let html = '';
        
        if (groupBy) {
            // Группируем хосты
            const grouped = this.groupHosts(hosts, groupBy);
            
            Object.keys(grouped).forEach(groupKey => {
                const groupHosts = grouped[groupKey];
                const count = this.getGroupCount(groupBy, groupHosts);
                const countLabel = groupBy === 'cve' ? 'хостов' : 'CVE';
                
                html += `
                    <div class="host-group">
                        <h5 class="group-header">
                            <i class="fas fa-folder"></i>
                            ${this.getGroupTitle(groupBy, groupKey)} (${count} ${countLabel})
                        </h5>
                        <div class="group-content">
                `;
                
                groupHosts.forEach(host => {
                    html += this.renderHostItem(host);
                });
                
                html += `
                        </div>
                    </div>
                `;
            });
        } else {
            // Без группировки
            hosts.forEach(host => {
                html += this.renderHostItem(host);
            });
        }
        
        resultsDiv.innerHTML = html;
        
        // Отображаем пагинацию
        this.renderPagination();
    }

    groupHosts(hosts, groupBy) {
        const grouped = {};
        
        hosts.forEach(host => {
            let groupKey;
            switch (groupBy) {
                case 'hostname':
                    groupKey = host.hostname;
                    break;
                case 'ip_address':
                    groupKey = host.ip_address;
                    break;
                case 'cve':
                    groupKey = host.cve;
                    break;
                default:
                    groupKey = 'default';
            }
            
            if (!grouped[groupKey]) {
                grouped[groupKey] = [];
            }
            grouped[groupKey].push(host);
        });
        
        return grouped;
    }

    getGroupTitle(groupBy, groupKey) {
        switch (groupBy) {
            case 'hostname':
                return `Hostname: ${groupKey}`;
            case 'ip_address':
                return `IP: ${groupKey}`;
            case 'cve':
                return `CVE: ${groupKey}`;
            default:
                return groupKey;
        }
    }

    getGroupCount(groupBy, hosts) {
        switch (groupBy) {
            case 'hostname':
                // Для группировки по hostname считаем уникальные CVE
                const uniqueCves = new Set(hosts.map(host => host.cve));
                return uniqueCves.size;
            case 'ip_address':
                // Для группировки по IP считаем уникальные CVE
                const uniqueCvesByIp = new Set(hosts.map(host => host.cve));
                return uniqueCvesByIp.size;
            case 'cve':
                // Для группировки по CVE считаем количество хостов
                return hosts.length;
            default:
                return hosts.length;
        }
    }

    renderHostItem(host) {
        const criticalityClass = `criticality-${host.criticality.toLowerCase()}`;
        
        // Индикация эксплойтов
        let exploitsIndicator = '';
        if (host.has_exploits) {
            exploitsIndicator = `
                <div class="host-exploits">
                    <span class="exploit-badge" title="Есть эксплойты: ${host.exploits_count}">
                        <i class="fas fa-bug"></i> ${host.exploits_count}
                    </span>
                </div>
            `;
        } else {
            exploitsIndicator = '<div class="host-exploits"></div>';
        }
        
        // Отображение риска
        let riskDisplay = '';
        
        if (host.risk_score !== null && host.risk_score !== undefined) {
            const riskClass = host.risk_score >= 70 ? 'high-risk' : 
                             host.risk_score >= 40 ? 'medium-risk' : 'low-risk';
            
            // Форматируем риск в зависимости от величины
            let riskText;
            if (host.risk_score < 0.1) {
                riskText = host.risk_score.toFixed(2); // Показываем 2 знака для очень маленьких значений
            } else if (host.risk_score < 1) {
                riskText = host.risk_score.toFixed(1); // Показываем 1 знак для маленьких значений
            } else {
                riskText = Math.round(host.risk_score); // Округляем для больших значений
            }
            
            riskDisplay = `<span class="risk-score ${riskClass}">${riskText}%</span>`;
        } else {
            riskDisplay = '<span class="risk-score">N/A</span>';
        }
        
        return `
            <div class="host-item single-line">
                <div class="host-name">${host.hostname}</div>
                <div class="host-ip">${host.ip_address}</div>
                <div class="host-criticality">
                    <span class="${criticalityClass}">${host.criticality}</span>
                </div>
                <div class="host-cve">${host.cve}</div>
                <div class="host-cvss">
                    ${host.cvss ? 
                        (host.cvss_source && host.cvss_source.includes('v2') ? 
                            `v2: ${host.cvss}` : 
                            (host.cvss_source && host.cvss_source.includes('v3') ? 
                                `v3: ${host.cvss}` : 
                                `${host.cvss}`
                            )
                        ) : 
                        'N/A'
                    }
                </div>
                <div class="host-status">
                    ${host.epss_score !== null && host.epss_score !== undefined ? 
                        `${(host.epss_score * 100).toFixed(2)}%` : 
                        'N/A'
                    }
                </div>
                ${exploitsIndicator}
                <div class="host-risk" id="host-risk-${host.id}">${riskDisplay}</div>
            </div>
        `;
    }

    clearHostsResults() {
        const resultsDiv = document.getElementById('hosts-search-results');
        if (resultsDiv) {
            resultsDiv.innerHTML = '';
        }
        this.hidePagination();
    }

    renderPagination() {
        const paginationDiv = document.getElementById('hosts-pagination');
        if (!paginationDiv) return;

        if (this.paginationState.totalPages <= 1) {
            this.hidePagination();
            return;
        }

        // Обновляем информацию о пагинации
        const startRecord = (this.paginationState.currentPage - 1) * this.paginationState.limit + 1;
        const endRecord = Math.min(this.paginationState.currentPage * this.paginationState.limit, this.paginationState.totalCount);
        
        const paginationInfo = document.getElementById('pagination-info');
        if (paginationInfo) {
            paginationInfo.textContent = `Показано ${startRecord}-${endRecord} из ${this.paginationState.totalCount} записей`;
        }

        // Обновляем кнопки навигации
        const prevBtn = document.getElementById('prev-page');
        const nextBtn = document.getElementById('next-page');
        
        if (prevBtn) {
            prevBtn.disabled = this.paginationState.currentPage <= 1;
        }
        
        if (nextBtn) {
            nextBtn.disabled = this.paginationState.currentPage >= this.paginationState.totalPages;
        }

        // Генерируем номера страниц
        this.renderPageNumbers();

        // Показываем пагинацию
        paginationDiv.style.display = 'block';
    }

    renderPageNumbers() {
        const pageNumbersDiv = document.getElementById('page-numbers');
        if (!pageNumbersDiv) return;

        const { currentPage, totalPages } = this.paginationState;
        let html = '';

        // Показываем максимум 5 страниц вокруг текущей
        const startPage = Math.max(1, currentPage - 2);
        const endPage = Math.min(totalPages, currentPage + 2);

        // Добавляем первую страницу если нужно
        if (startPage > 1) {
            html += `<span class="page-number" data-page="1">1</span>`;
            if (startPage > 2) {
                html += `<span class="page-number disabled">...</span>`;
            }
        }

        // Добавляем страницы в диапазоне
        for (let i = startPage; i <= endPage; i++) {
            const isActive = i === currentPage;
            html += `<span class="page-number ${isActive ? 'active' : ''}" data-page="${i}">${i}</span>`;
        }

        // Добавляем последнюю страницу если нужно
        if (endPage < totalPages) {
            if (endPage < totalPages - 1) {
                html += `<span class="page-number disabled">...</span>`;
            }
            html += `<span class="page-number" data-page="${totalPages}">${totalPages}</span>`;
        }

        pageNumbersDiv.innerHTML = html;

        // Добавляем обработчики событий
        pageNumbersDiv.querySelectorAll('.page-number:not(.disabled)').forEach(span => {
            span.addEventListener('click', (e) => {
                const page = parseInt(e.target.dataset.page);
                if (page && page !== currentPage) {
                    this.searchHosts(page);
                }
            });
        });
    }

    hidePagination() {
        const paginationDiv = document.getElementById('hosts-pagination');
        if (paginationDiv) {
            paginationDiv.style.display = 'none';
        }
    }

    async exportHosts() {
        const form = document.getElementById('hosts-search-form');
        if (!form) return;
        
        const formData = new FormData(form);
        const params = new URLSearchParams();
        
        // Добавляем только заполненные параметры
        for (let [key, value] of formData.entries()) {
            if (key === 'exploits_only' || key === 'epss_only') {
                // Для чекбоксов добавляем значение только если они отмечены
                if (value === 'on') {
                    params.append(key, 'true');
                }
            } else if (value.trim()) {
                params.append(key, value.trim());
            }
        }
        
        try {
            // Показываем индикатор загрузки
            const exportBtn = document.getElementById('export-hosts');
            const originalText = exportBtn.innerHTML;
            exportBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Экспорт...';
            exportBtn.disabled = true;
            
            const response = await fetch(`${this.getApiBasePath()}/hosts/export?${params.toString()}`);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            // Проверяем тип ответа
            const contentType = response.headers.get('content-type');
            
            if (contentType && contentType.includes('application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')) {
                // Это Excel файл, скачиваем его
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                
                // Получаем имя файла из заголовка
                const contentDisposition = response.headers.get('content-disposition');
                let filename = 'hosts_export.xlsx';
                if (contentDisposition) {
                    const filenameMatch = contentDisposition.match(/filename=(.+)/);
                    if (filenameMatch) {
                        filename = filenameMatch[1];
                    }
                }
                
                a.download = filename;
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(url);
                document.body.removeChild(a);
                
                this.showNotification('Экспорт завершен успешно!', 'success');
            } else {
                // Это JSON ответ с ошибкой
                const data = await response.json();
                this.showNotification(`Ошибка экспорта: ${data.error}`, 'error');
            }
        } catch (error) {
            console.error('Export error:', error);
            this.showNotification('Ошибка экспорта: ' + error.message, 'error');
        } finally {
            // Восстанавливаем кнопку
            const exportBtn = document.getElementById('export-hosts');
            exportBtn.innerHTML = '<i class="fas fa-file-excel"></i> Экспорт в Excel';
            exportBtn.disabled = false;
        }
    }

    async calculateHostRisk(hostId) {
        const riskDiv = document.getElementById(`host-risk-${hostId}`);
        if (!riskDiv) return;
        
        // Показываем индикатор загрузки
        riskDiv.innerHTML = `
            <div class="loading">
                <i class="fas fa-spinner fa-spin"></i>
                <p>Расчет риска...</p>
            </div>
        `;
        
        try {
            const response = await fetch(`${this.getApiBasePath()}/hosts/${hostId}/risk`);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            
            if (data.success) {
                this.renderHostRiskResult(hostId, data);
            } else {
                console.error('API error for host', hostId, ':', data);
                riskDiv.innerHTML = `<span class="risk-score">Ошибка</span>`;
            }
        } catch (error) {
            console.error('Host risk calculation error for host', hostId, ':', error);
            console.error('Error details:', {
                message: error.message,
                stack: error.stack,
                hostId: hostId
            });
            riskDiv.innerHTML = `<span class="risk-score">Ошибка</span>`;
        }
    }

    renderHostRiskResult(hostId, data) {
        const riskDiv = document.getElementById(`host-risk-${hostId}`);
        if (!riskDiv) return;
        
        let html = '';
        
        // Отображаем EPSS (в процентах)
        if (data.epss && data.epss.epss !== null) {
            const epssValue = (data.epss.epss * 100).toFixed(2);
            html += `<div class="epss-info">
                <i class="fas fa-chart-line"></i>
                <span class="epss-label">EPSS:</span>
                <span class="epss-value">${epssValue}%</span>
            </div>`;
        }
        
        // Отображаем риск
        if (data.risk && data.risk.calculation_possible) {
            const threshold = parseFloat(localStorage.getItem('risk_threshold') || '75');
            const riskScore = data.risk.risk_score;
            const isHighRisk = riskScore >= threshold;
            const riskClass = isHighRisk ? 'risk-score-high' : 'risk-score-low';
            
            html += `<div class="risk-score ${riskClass}">
                <span class="risk-label">Risk:</span>
                <span class="risk-value">${data.risk.risk_score.toFixed(1)}%</span>
            </div>`;
        } else {
            html += `<div class="risk-score">
                <span class="risk-label">Risk:</span>
                <span class="risk-value">N/A</span>
            </div>`;
        }
        
        // Отображаем информацию об эксплойтах
        if (data.exploitdb && data.exploitdb.length > 0) {
            const exploitCount = data.exploitdb.length;
            const verifiedCount = data.exploitdb.filter(e => e.verified).length;
            
            html += `
                <div class="exploit-info">
                    <i class="fas fa-bug"></i>
                    <span class="exploit-count">${exploitCount}</span>
                    ${verifiedCount > 0 ? `<span class="verified-count" title="Проверенных: ${verifiedCount}">✓</span>` : ''}
                </div>`;
        }
        
        riskDiv.innerHTML = html;
    }

    // Загрузка начальных данных
    async loadInitialData() {
        try {
            // Загружаем настройки Impact
            await this.loadImpactSettings();
        } catch (error) {
            console.error('Error loading initial data:', error);
            this.showNotification('Ошибка загрузки данных', 'error');
        }
    }

    // Заполнение формы настроек
    populateSettings(settings) {
        const form = document.getElementById('settings-form');
        if (!form) return;

        Object.keys(settings).forEach(key => {
            const input = form.querySelector(`[name="${key}"]`);
            if (input) {
                input.value = settings[key];
            }
        });

        // Заполняем также форму Impact
        const impactForm = document.getElementById('impact-form');
        if (impactForm) {
            Object.keys(settings).forEach(key => {
                const input = impactForm.querySelector(`[name="${key}"]`);
                if (input) {
                    input.value = settings[key];
                }
            });
            
            // Инициализируем ползунок порога риска
            const thresholdSlider = document.getElementById('risk-threshold');
            const thresholdValue = document.getElementById('threshold-value');
            if (thresholdSlider && thresholdValue) {
                const threshold = settings['risk_threshold'] || '75';
                thresholdSlider.value = threshold;
                thresholdValue.textContent = threshold;
                this.updateThresholdSlider(threshold);
                // Сохраняем в localStorage
                localStorage.setItem('risk_threshold', threshold);
            }
        }
    }

    // Сохранение настроек
    async saveSettings() {
        const form = document.getElementById('settings-form');
        const formData = new FormData(form);
        const settings = {};

        for (let [key, value] of formData.entries()) {
            settings[key] = value;
        }

        try {
            const response = await fetch(this.getApiBasePath() + '/settings', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(settings)
            });

            const data = await response.json();
            
            if (data.success) {
                this.showNotification('Настройки успешно сохранены', 'success');
            } else {
                this.showNotification('Ошибка сохранения настроек', 'error');
            }
        } catch (error) {
            console.error('Error saving settings:', error);
            this.showNotification('Ошибка сохранения настроек', 'error');
        }
    }

    // Загрузка настроек базы данных
    async loadDatabaseSettings() {
        try {
            const response = await fetch(this.getApiBasePath() + '/settings');
            const settings = await response.json();
            
            // Заполняем форму настроек базы данных
            this.populateSettings(settings);
            
        } catch (error) {
            console.error('Error loading database settings:', error);
        }
    }

    // Загрузка настроек Impact
    async loadImpactSettings() {
        try {
            const response = await fetch(this.getApiBasePath() + '/settings');
            const settings = await response.json();
            
            // Устанавливаем значения в форму
            const form = document.getElementById('impact-form');
            if (form) {
                const resourceCriticality = document.getElementById('impact-resource-criticality');
                const confidentialData = document.getElementById('impact-confidential-data');
                const internetAccess = document.getElementById('impact-internet-access');
                
                if (resourceCriticality) {
                    resourceCriticality.value = settings.impact_resource_criticality || 'Medium';
                }
                if (confidentialData) {
                    confidentialData.value = settings.impact_confidential_data || 'Отсутствуют';
                }
                if (internetAccess) {
                    internetAccess.value = settings.impact_internet_access || 'Недоступен';
                }
            }
        } catch (error) {
            console.error('Error loading impact settings:', error);
        }
    }

    // Сохранение настроек Impact
    async saveImpactSettings() {
        const form = document.getElementById('impact-form');
        const formData = new FormData(form);
        const settings = {};

        for (let [key, value] of formData.entries()) {
            settings[key] = value;
        }

        

        try {
            const response = await fetch(this.getApiBasePath() + '/settings', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(settings)
            });


            
            if (!response.ok) {
                const errorText = await response.text();
                console.error('DEBUG: Response error text:', errorText);
                throw new Error(`HTTP ${response.status}: ${errorText}`);
            }

            const data = await response.json();

            
            if (data.success) {
                // Сохраняем порог риска в localStorage для быстрого доступа
                const threshold = formData.get('risk_threshold');
                if (threshold) {
                    localStorage.setItem('risk_threshold', threshold);
                }
                this.showNotification('Настройки Impact успешно сохранены', 'success');
            } else {
                this.showNotification('Ошибка сохранения настроек Impact', 'error');
            }
        } catch (error) {
            console.error('Error saving impact settings:', error);
            this.showNotification('Ошибка сохранения настроек Impact', 'error');
        }
    }

    // Обновление цвета ползунка порога риска
    updateThresholdSlider(value) {
        const slider = document.getElementById('risk-threshold');
        if (slider) {
            const percentage = value + '%';
            slider.style.background = `linear-gradient(to right, var(--success-color) 0%, var(--success-color) ${percentage}, var(--error-color) ${percentage}, var(--error-color) 100%)`;
        }
    }

    // Проверка подключения к базе данных
    async testConnection() {
        try {
            const btn = document.getElementById('test-connection');
            if (!btn) {
                this.showNotification('❌ Кнопка проверки подключения не найдена', 'error');
                return;
            }
            
            const originalText = btn.innerHTML;
            btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Проверка...';
            btn.disabled = true;

            const response = await fetch(this.getApiBasePath() + '/health');
            const data = await response.json();
            
            if (data.status === 'healthy' && data.database === 'connected') {
                this.showNotification('Подключение к базе данных успешно', 'success');
            } else {
                this.showNotification('Ошибка подключения к базе данных', 'error');
            }
        } catch (error) {
            console.error('Connection test error:', error);
            this.showNotification('❌ Ошибка подключения к базе данных', 'error');
        } finally {
            const btn = document.getElementById('test-connection');
            if (btn) {
                btn.innerHTML = '<i class="fas fa-database"></i> Проверить подключение';
                btn.disabled = false;
            }
        }
    }

    // Очистка таблицы хостов
    async clearHosts() {
        if (!confirm('Вы уверены, что хотите удалить все записи хостов? Это действие нельзя отменить.')) {
            return;
        }

        try {
            const btn = document.getElementById('clear-hosts-btn');
            const originalText = btn.innerHTML;
            btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Очистка...';
            btn.disabled = true;

            const response = await fetch(this.getApiBasePath() + '/hosts/clear', {
                method: 'POST'
            });
            const data = await response.json();

            if (data.success) {
                this.showNotification('Таблица хостов очищена успешно!', 'success');
                this.updateHostsStatus();
            } else {
                this.showNotification(`Ошибка очистки: ${data.error}`, 'error');
            }
        } catch (error) {
            console.error('Clear hosts error:', error);
            this.showNotification('Ошибка очистки хостов', 'error');
        } finally {
            const btn = document.getElementById('clear-hosts-btn');
            btn.innerHTML = '<i class="fas fa-trash"></i> Очистить хосты';
            btn.disabled = false;
        }
    }

    // Очистка таблицы EPSS
    async clearEPSS() {
        if (!confirm('Вы уверены, что хотите удалить все записи EPSS? Это действие нельзя отменить.')) {
            return;
        }

        try {
            const btn = document.getElementById('clear-epss-btn');
            const originalText = btn.innerHTML;
            btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Очистка...';
            btn.disabled = true;

            const response = await fetch(this.getApiBasePath() + '/epss/clear', {
                method: 'POST'
            });
            const data = await response.json();

            if (data.success) {
                this.showNotification('Таблица EPSS очищена успешно!', 'success');
                this.updateEPSSStatus();
            } else {
                this.showNotification(`Ошибка очистки: ${data.error}`, 'error');
            }
        } catch (error) {
            console.error('Clear EPSS error:', error);
            this.showNotification('Ошибка очистки EPSS', 'error');
        } finally {
            const btn = document.getElementById('clear-epss-btn');
            btn.innerHTML = '<i class="fas fa-trash"></i> Очистить EPSS';
            btn.disabled = false;
        }
    }

    // Очистка таблицы ExploitDB
    async clearExploitDB() {
        if (!confirm('Вы уверены, что хотите удалить все записи ExploitDB? Это действие нельзя отменить.')) {
            return;
        }

        try {
            const btn = document.getElementById('clear-exploitdb-btn');
            const originalText = btn.innerHTML;
            btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Очистка...';
            btn.disabled = true;

            const response = await fetch(this.getApiBasePath() + '/exploitdb/clear', {
                method: 'POST'
            });
            const data = await response.json();

            if (data.success) {
                this.showNotification('Таблица ExploitDB очищена успешно!', 'success');
                this.updateExploitDBStatus();
            } else {
                this.showNotification(`Ошибка очистки: ${data.error}`, 'error');
            }
        } catch (error) {
            console.error('Clear ExploitDB error:', error);
            this.showNotification('Ошибка очистки ExploitDB', 'error');
        } finally {
            const btn = document.getElementById('clear-exploitdb-btn');
            btn.innerHTML = '<i class="fas fa-trash"></i> Очистить ExploitDB';
            btn.disabled = false;
        }
    }

    // Очистка таблицы CVE
    async clearCVE() {
        if (!confirm('Вы уверены, что хотите удалить все записи CVE? Это действие нельзя отменить.')) {
            return;
        }

        try {
            const btn = document.getElementById('clear-cve-btn');
            const originalText = btn.innerHTML;
            btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Очистка...';
            btn.disabled = true;

            const response = await fetch(this.getApiBasePath() + '/cve/clear', {
                method: 'POST'
            });
            const data = await response.json();

            if (data.success) {
                this.showNotification('Таблица CVE очищена успешно!', 'success');
                this.updateCVEStatus();
            } else {
                this.showNotification(`Ошибка очистки: ${data.error}`, 'error');
            }
        } catch (error) {
            console.error('Clear CVE error:', error);
            this.showNotification('Ошибка очистки CVE', 'error');
        } finally {
            const btn = document.getElementById('clear-cve-btn');
            btn.innerHTML = '<i class="fas fa-trash"></i> Очистить CVE';
            btn.disabled = false;
        }
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
        setTimeout(() => {
            notification.remove();
        }, 5000);
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

    // ===== VM MAXPATROL ИНТЕГРАЦИЯ =====
    
    setupVM() {
        // Настройка формы VM настроек
        const vmSettingsForm = document.getElementById('vm-settings-form');
        if (vmSettingsForm) {
            vmSettingsForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.saveVMSettings();
            });
        }

        // Настройка кнопки тестирования подключения
        const testConnectionBtn = document.getElementById('vm-test-connection-btn');
        if (testConnectionBtn) {
            testConnectionBtn.addEventListener('click', () => {
                this.testVMConnection();
            });
        }

        // Настройка кнопки импорта
        const importBtn = document.getElementById('vm-import-btn');
        if (importBtn) {
            importBtn.addEventListener('click', () => {
                this.importVMHosts();
            });
        }

        // Настройка кнопки обновления статуса
        const refreshStatusBtn = document.getElementById('vm-refresh-status-btn');
        if (refreshStatusBtn) {
            refreshStatusBtn.addEventListener('click', () => {
                this.updateVMStatus();
            });
        }

        // Загружаем VM настройки при инициализации
        this.loadVMSettings();
        this.updateVMStatus();
    }

    async loadVMSettings() {
        try {
            const response = await fetch(`${this.getApiBasePath()}/vm/settings`);
            const data = await response.json();
            
            if (data.success) {
                this.populateVMSettings(data.data);
            }
        } catch (error) {
            console.error('Error loading VM settings:', error);
        }
    }

    populateVMSettings(settings) {
        const vmEnabled = document.getElementById('vm-enabled');
        const vmHost = document.getElementById('vm-host');
        const vmUsername = document.getElementById('vm-username');
        const vmPassword = document.getElementById('vm-password');
        const vmClientSecret = document.getElementById('vm-client-secret');
        const vmOsFilter = document.getElementById('vm-os-filter');
        const vmLimit = document.getElementById('vm-limit');

        if (vmEnabled) vmEnabled.value = settings.vm_enabled || 'false';
        if (vmHost) vmHost.value = settings.vm_host || '';
        if (vmUsername) vmUsername.value = settings.vm_username || '';
        if (vmPassword) vmPassword.value = settings.vm_password || '';
        if (vmClientSecret) vmClientSecret.value = settings.vm_client_secret || '';
        if (vmOsFilter) vmOsFilter.value = settings.vm_os_filter || '';
        if (vmLimit) vmLimit.value = settings.vm_limit || '0';
    }

    async saveVMSettings() {
        const form = document.getElementById('vm-settings-form');
        if (!form) return;

        const formData = new FormData(form);
        const settings = {};
        
        for (let [key, value] of formData.entries()) {
            settings[key] = value;
        }

        try {
            const response = await fetch(`${this.getApiBasePath()}/vm/settings`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(settings)
            });

            const data = await response.json();
            
            if (data.success) {
                this.showNotification('VM настройки сохранены успешно', 'success');
                this.updateVMStatus();
            } else {
                this.showNotification(`Ошибка сохранения: ${data.error}`, 'error');
            }
        } catch (error) {
            this.showNotification(`Ошибка сохранения: ${error.message}`, 'error');
        }
    }

    async testVMConnection() {
        const form = document.getElementById('vm-settings-form');
        if (!form) return;

        const formData = new FormData(form);
        const settings = {};
        
        for (let [key, value] of formData.entries()) {
            settings[key] = value;
        }

        // Проверяем обязательные поля
        const requiredFields = ['vm_host', 'vm_username', 'vm_password', 'vm_client_secret'];
        for (let field of requiredFields) {
            if (!settings[field]) {
                this.showNotification('Заполните все обязательные поля для подключения', 'error');
                return;
            }
        }

        try {
            const response = await fetch(`${this.getApiBasePath()}/vm/test-connection`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(settings)
            });

            const data = await response.json();
            
            if (data.success && data.data.success) {
                this.showNotification(`Подключение успешно! ${data.data.message}`, 'success');
            } else {
                this.showNotification(`Ошибка подключения: ${data.data.error || data.error}`, 'error');
            }
        } catch (error) {
            this.showNotification(`Ошибка подключения: ${error.message}`, 'error');
        }
    }

    async importVMHosts() {
        const operationId = 'vm-import';
        this.showOperationProgress(operationId, 'Импорт хостов из VM MaxPatrol...');

        try {
            const response = await fetch(`${this.getApiBasePath()}/vm/import`, {
                method: 'POST'
            });

            const data = await response.json();
            
            if (data.success) {
                this.showOperationComplete(operationId, 'Импорт завершен успешно', 
                    `Импортировано: ${data.data.inserted} новых, обновлено: ${data.data.updated} существующих записей`);
                this.updateVMStatus();
                this.updateHostsStatus(); // Обновляем статус хостов
            } else {
                this.showOperationError(operationId, 'Ошибка импорта', data.error);
            }
        } catch (error) {
            this.showOperationError(operationId, 'Ошибка импорта', error.message);
        }
    }

    async updateVMStatus() {
        try {
            const response = await fetch(`${this.getApiBasePath()}/vm/status`);
            const data = await response.json();
            
            if (data.success) {
                this.populateVMStatus(data.data);
            }
        } catch (error) {
            console.error('Error updating VM status:', error);
        }
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
            console.error('Error loading app version:', error);
        }
    }

    populateVMStatus(data) {
        const lastImport = document.getElementById('vm-last-import');
        const importCount = document.getElementById('vm-import-count');
        const importStatus = document.getElementById('vm-import-status');

        if (lastImport) {
            if (data.import_status.last_import) {
                const date = new Date(data.import_status.last_import);
                lastImport.textContent = date.toLocaleString('ru-RU');
            } else {
                lastImport.textContent = 'Не выполнялся';
            }
        }

        if (importCount) {
            importCount.textContent = data.import_status.last_import_count || 0;
        }

        if (importStatus) {
            if (data.import_status.last_import_error) {
                importStatus.textContent = `Ошибка: ${data.import_status.last_import_error}`;
                importStatus.className = 'error-text';
            } else if (data.settings.vm_enabled === 'true') {
                importStatus.textContent = 'Настроено и активно';
                importStatus.className = 'success-text';
            } else {
                importStatus.textContent = 'Не настроено';
                importStatus.className = '';
            }
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
                        setTimeout(() => {
                            this.hideImportProgress();
                        }, 3000);
                    }
                }
            } catch (err) {
                console.error('Background task monitoring error:', err);
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
        // Очищаем предыдущий интервал
        if (this.backgroundUpdateInterval) {
            clearInterval(this.backgroundUpdateInterval);
            this.backgroundUpdateInterval = null;
        }


        
        this.backgroundUpdateInterval = setInterval(async () => {
            try {
    
                const data = await fetch(this.getApiBasePath() + '/hosts/update-data-progress').then(r => r.json());
                
    
                
                // Обновляем UI только если есть данные
                if (data && typeof data === 'object') {
                    this.updateBackgroundUpdateProgress(data);

                    // Останавливаем интервал при завершении
                    if (data.status === 'completed' || data.status === 'error' || data.status === 'idle') {
            
                        this.stopBackgroundUpdateMonitoring();
                        
                        // Показываем уведомление о завершении только если это новое завершение
                        if (data.status === 'completed' && !this.lastNotifiedCompletionTime) {
                            this.showNotification(`Обновление завершено: ${data.updated_hosts || 0} записей обновлено`, 'success');
                            this.lastNotifiedCompletionTime = data.end_time || data.last_update || Date.now();
                            localStorage.setItem('app_last_notification_time', this.lastNotifiedCompletionTime);
                        } else if (data.status === 'error' && !this.lastNotifiedCompletionTime) {
                            this.showNotification(`Ошибка обновления: ${data.error_message || 'Неизвестная ошибка'}`, 'error');
                            this.lastNotifiedCompletionTime = data.end_time || data.last_update || Date.now();
                            localStorage.setItem('app_last_notification_time', this.lastNotifiedCompletionTime);
                        }
                        
                        // Скрываем прогресс-бар через 3 секунды
                        setTimeout(() => {
                            this.hideBackgroundUpdateProgress();
                        }, 3000);
                    }
                }
            } catch (err) {
                console.error('Background update monitoring error in main app:', err);
                this.stopBackgroundUpdateMonitoring();
                
                // Скрываем прогресс-бар при ошибке
                setTimeout(() => {
                    this.hideBackgroundUpdateProgress();
                }, 3000);
            }
        }, 2000);
    }

    stopBackgroundUpdateMonitoring() {
        if (this.backgroundUpdateInterval) {
            clearInterval(this.backgroundUpdateInterval);
            this.backgroundUpdateInterval = null;
    
        }
    }
    
    updateBackgroundTaskProgress(task) {
        const container = document.getElementById('import-progress-container');
        if (!container) return;

        // Обновляем классы для анимации
        container.className = 'progress-info ' + task.status;

        // Обновляем текст текущего шага
        const currentStepText = document.getElementById('current-step-text');
        if (currentStepText) {
            currentStepText.textContent = task.current_step || 'Обработка...';
        }

        // Обновляем общий прогресс
        const overallProgressText = document.getElementById('overall-progress-text');
        if (overallProgressText) {
            // Используем progress_percent из API для правильного расчета
            const progress = task.progress_percent !== undefined ? 
                Math.round(task.progress_percent) : 
                (task.total_items > 0 ? Math.round((task.processed_items / task.total_items) * 100) : 0);
            overallProgressText.textContent = progress + '%';
        }

        // Обновляем прогресс-бар
        const progressBarFill = document.getElementById('progress-bar-fill');
        if (progressBarFill) {
            // Используем progress_percent из API для правильного расчета
            const progress = task.progress_percent !== undefined ? 
                task.progress_percent : 
                (task.total_items > 0 ? (task.processed_items / task.total_items) * 100 : 0);
            progressBarFill.style.width = progress + '%';
        }

        // Обновляем количество записей
        const processedRecordsText = document.getElementById('processed-records-text');
        if (processedRecordsText && task.processed_records !== undefined) {
            processedRecordsText.textContent = task.processed_records.toLocaleString();
        }

        const totalRecordsText = document.getElementById('total-records-text');
        if (totalRecordsText && task.total_records !== undefined) {
            totalRecordsText.textContent = task.total_records.toLocaleString();
        }
    }

    formatTime(seconds) {
        if (!seconds || seconds < 0) return '-';
        
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        const secs = Math.floor(seconds % 60);
        
        if (hours > 0) {
            return `${hours}ч ${minutes}м ${secs}с`;
        } else if (minutes > 0) {
            return `${minutes}м ${secs}с`;
        } else {
            return `${secs}с`;
        }
    }

    // Функции для работы с фоновым обновлением
    showBackgroundUpdateProgress() {
        const container = document.getElementById('background-update-progress-container');
        if (container) {
            container.style.display = 'block';
        }
    }

    hideBackgroundUpdateProgress() {
        const container = document.getElementById('background-update-progress-container');
        if (container) {
            container.style.display = 'none';
        }
    }







    async loadBackgroundTasksData() {
        try {
    
            const resp = await fetch(this.getApiBasePath() + '/background-tasks/status');
            if (resp.ok) {
                const data = await resp.json();
    
                
                this.updateBackgroundTasksUI(data);
            } else {
                console.error('Failed to load background tasks data');
                this.showNotification('Ошибка загрузки данных о фоновых задачах', 'error');
            }
        } catch (err) {
            console.error('Error loading background tasks data:', err);
            this.showNotification('Ошибка загрузки данных о фоновых задачах', 'error');
        }
    }

    updateBackgroundTasksUI(data) {
        // Обновляем список активных задач
        const activeTasksContainer = document.getElementById('active-tasks-list');
        if (activeTasksContainer) {
            if (data.active_tasks && data.active_tasks.length > 0) {
                activeTasksContainer.innerHTML = data.active_tasks.map(task => `
                    <div class="task-item active-task">
                        <div class="task-header">
                            <h4>${task.task_type}</h4>
                            <span class="task-status ${task.status}">${this.getStatusText(task.status)}</span>
                        </div>
                        <div class="task-progress">
                            <div class="operation-progress-bar">
                                <div class="operation-progress-fill" style="width: ${task.progress_percent}%"></div>
                            </div>
                            <span class="operation-progress-text">${task.progress_percent}%</span>
                        </div>
                        <div class="task-details">
                            <p><strong>Текущий шаг:</strong> ${task.current_step || 'Инициализация...'}</p>
                            <p><strong>Обработано:</strong> ${task.processed_items}/${task.total_items}</p>
                            <p><strong>Обновлено записей:</strong> ${task.updated_records}</p>
                            <p><strong>Начато:</strong> ${task.start_time ? new Date(task.start_time).toLocaleString() : 'Неизвестно'}</p>
                        </div>
                        <div class="task-actions">
                            <button class="btn btn-danger btn-sm" onclick="window.vulnAnalizer.cancelTask('${task.task_type}')">
                                <i class="fas fa-stop"></i> Отменить
                            </button>
                        </div>
                    </div>
                `).join('');
            } else {
                activeTasksContainer.innerHTML = '<p class="no-tasks">Нет активных задач</p>';
            }
        }

        // Обновляем список завершенных задач
        const completedTasksContainer = document.getElementById('completed-tasks-list');
        if (completedTasksContainer) {
            if (data.recent_completed_tasks && data.recent_completed_tasks.length > 0) {
                completedTasksContainer.innerHTML = data.recent_completed_tasks.map(task => `
                    <div class="task-item completed-task">
                        <div class="task-header">
                            <h4>${task.task_type}</h4>
                            <span class="task-status ${task.status}">${this.getStatusText(task.status)}</span>
                        </div>
                        <div class="task-details">
                            <p><strong>Описание:</strong> ${task.description || 'Нет описания'}</p>
                            <p><strong>Обработано:</strong> ${task.processed_items}/${task.total_items}</p>
                            <p><strong>Обновлено записей:</strong> ${task.updated_records}</p>
                            <p><strong>Начато:</strong> ${task.start_time ? new Date(task.start_time).toLocaleString() : 'Неизвестно'}</p>
                            <p><strong>Завершено:</strong> ${task.end_time ? new Date(task.end_time).toLocaleString() : 'Неизвестно'}</p>
                            ${task.error_message ? `<p><strong>Ошибка:</strong> <span class="error-text">${task.error_message}</span></p>` : ''}
                        </div>
                    </div>
                `).join('');
            } else {
                completedTasksContainer.innerHTML = '<p class="no-tasks">Нет завершенных задач</p>';
            }
        }

        // Обновляем статистику
        const statsContainer = document.getElementById('tasks-stats');
        if (statsContainer) {
            statsContainer.innerHTML = `
                <div class="stats-grid">
                    <div class="stat-item">
                        <div class="stat-number">${data.total_active}</div>
                        <div class="stat-label">Активных задач</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-number">${data.total_completed}</div>
                        <div class="stat-label">Завершенных задач</div>
                    </div>
                </div>
            `;
        }
    }

    getStatusText(status) {
        const statusMap = {
            'idle': 'Ожидает',
            'processing': 'Выполняется',
            'running': 'Запущена',
            'initializing': 'Инициализация',
            'completed': 'Завершена',
            'error': 'Ошибка',
            'cancelled': 'Отменена'
        };
        return statusMap[status] || status;
    }

    async cancelTask(taskType) {
        try {
            const resp = await fetch(this.getApiBasePath() + `/background-tasks/${taskType}/cancel`, {
                method: 'POST'
            });
            
            if (resp.ok) {
                const data = await resp.json();
                if (data.success) {
                    this.showNotification(`Задача ${taskType} отменена`, 'success');
                    // Перезагружаем данные
                    this.loadBackgroundTasksData();
                } else {
                    this.showNotification(data.message || 'Ошибка отмены задачи', 'error');
                }
            } else {
                this.showNotification('Ошибка отмены задачи', 'error');
            }
        } catch (err) {
            console.error('Error cancelling task:', err);
            this.showNotification('Ошибка отмены задачи', 'error');
        }
    }

    async checkActiveImportTasks() {
        try {
    
            
            // Проверяем импорт
            const importResponse = await fetch(this.getApiBasePath() + '/hosts/import-progress', {
                method: 'GET',
                headers: {
                    'Cache-Control': 'no-cache',
                    'Pragma': 'no-cache'
                }
            });
            
            if (importResponse.ok) {
                const importData = await importResponse.json();
                
                if (importData && importData.status && importData.status !== 'idle' && importData.status !== 'completed' && importData.status !== 'error' && importData.status !== 'cancelled') {
        
                    
                    // Показываем уведомление о том, что есть активная задача
                    this.showNotification(`Обнаружена активная задача импорта: ${importData.current_step}`, 'info');
                    
                    // Показываем прогресс-бар если мы на странице хостов
                    const hostsPage = document.getElementById('hosts-page');
                    if (hostsPage && hostsPage.classList.contains('active')) {
                        this.showImportProgress();
                        this.updateImportProgress(
                            importData.status || 'unknown',
                            importData.current_step || '',
                            importData.progress || 0,
                            importData.current_step_progress || 0,
                            importData.total_records || 0,
                            importData.processed_records || 0,
                            importData.error_message || null
                        );
                        this.startBackgroundTaskMonitoring(importData.task_id);
                    }
                }
            }
            
            // Проверяем обновление
            const updateResponse = await fetch(this.getApiBasePath() + '/hosts/update-data-progress', {
                method: 'GET',
                headers: {
                    'Cache-Control': 'no-cache',
                    'Pragma': 'no-cache'
                }
            });
            
            if (updateResponse.ok) {
                const updateData = await updateResponse.json();
                
                if (updateData && updateData.status && updateData.status !== 'idle' && updateData.status !== 'completed' && updateData.status !== 'error' && updateData.status !== 'cancelled') {
        
                    
                    // Показываем уведомление о том, что есть активная задача обновления
                    this.showNotification(`Обнаружена активная задача обновления: ${updateData.current_step}`, 'info');
                    
                    // Показываем прогресс-бар если мы на странице хостов
                    const hostsPage = document.getElementById('hosts-page');
                    if (hostsPage && hostsPage.classList.contains('active')) {
                        this.showBackgroundUpdateProgress();
                        this.updateBackgroundUpdateProgress(updateData);
                        this.startBackgroundUpdateMonitoring();
                    }
                }
            }
        } catch (err) {
            console.error('Error checking active tasks in main app:', err);
        }
    }

    setupCollapsibleBlocks() {
        console.log('setupCollapsibleBlocks вызван');
        const collapsibleHeaders = document.querySelectorAll('.collapsible-header');
        console.log('Найдено collapsible headers:', collapsibleHeaders.length);
        
        collapsibleHeaders.forEach(header => {
            // Инициализируем стрелки как свернутые по умолчанию
            const arrow = header.querySelector('.collapsible-arrow i');
            if (arrow) {
                arrow.style.transform = 'rotate(-90deg)';
            }
            header.classList.add('collapsed');
            
            // Инициализируем контент как свернутый
            const targetId = header.getAttribute('data-target');
            const content = document.getElementById(targetId);
            if (content) {
                content.style.display = 'none';
            }
            
            header.addEventListener('click', (e) => {
                console.log('Клик по collapsible header:', e.target);
                console.log('Клик по форме:', e.target.closest('form'));
                console.log('Клик по кнопке:', e.target.closest('button'));
                console.log('Клик по formula-btn:', e.target.closest('.formula-btn'));
                
                // Предотвращаем срабатывание при клике на форму внутри
                if (e.target.closest('form') || (e.target.closest('button') && !e.target.closest('.formula-btn'))) {
                    console.log('Блокируем клик');
                    return;
                }
                
                console.log('Обрабатываем клик');
                const targetId = header.getAttribute('data-target');
                const content = document.getElementById(targetId);
                
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
}

// Инициализация приложения при загрузке страницы
document.addEventListener('DOMContentLoaded', () => {
    window.vulnAnalizer = new VulnAnalizer();
    
    // Проверяем активную страницу из URL и проверяем активные задачи
    setTimeout(() => {
        const currentPage = window.location.hash.replace('#', '') || 'analysis';
        if (currentPage === 'hosts') {
            window.vulnAnalizer.checkActiveImportTasks();
        }
    }, 500);
    
    // Обработчик изменения хэша URL
    window.addEventListener('hashchange', () => {
        const currentPage = window.location.hash.replace('#', '') || 'analysis';
        if (currentPage === 'hosts') {
            window.vulnAnalizer.checkActiveImportTasks();
        }
    });
});
