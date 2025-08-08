class VulnAnalizer {
    constructor() {
        this.init();
        this.operationStatus = {}; // Хранит статус текущих операций
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

    init() {
        // Проверяем авторизацию
        this.checkAuth();
        
        this.initTheme();
        this.setupNavigation();
        this.setupSettings();
        this.setupUserMenu();
        this.setupForms();
        this.setupEPSS();
        this.setupExploitDB();
        this.setupHosts();
        this.setupVM();
        this.setupUsers();
        this.setupSidebar();
        
        // Загружаем статус хостов при инициализации
        setTimeout(() => {
            this.updateHostsStatus();
        }, 100);
    }

    checkAuth() {
        const token = localStorage.getItem('auth_token');
        if (!token) {
            // Если нет токена, перенаправляем на страницу входа
            window.location.href = '/vulnanalizer/login';
            return;
        }

        // Проверяем токен
        fetch('/vulnanalizer/api/users/me', {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        }).then(response => {
            if (response.ok) {
                return response.json();
            } else {
                localStorage.removeItem('auth_token');
                localStorage.removeItem('user_info');
                window.location.href = '/vulnanalizer/login';
                throw new Error('Auth failed');
            }
        }).then(userData => {
            // Сохраняем информацию о пользователе
            localStorage.setItem('user_info', JSON.stringify(userData));
        }).catch(() => {
            localStorage.removeItem('auth_token');
            localStorage.removeItem('user_info');
            window.location.href = '/vulnanalizer/login';
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

    setupNavigation() {
        const navLinks = document.querySelectorAll('.nav-link');
        
        navLinks.forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                
                // Убираем активный класс со всех ссылок
                navLinks.forEach(l => l.classList.remove('active'));
                
                // Добавляем активный класс к текущей ссылке
                link.classList.add('active');
                
                // Скрываем все страницы
                document.querySelectorAll('.page-content').forEach(page => {
                    page.classList.remove('active');
                });
                
                // Показываем нужную страницу
                const targetPage = link.getAttribute('data-page');
                const targetElement = document.getElementById(`${targetPage}-page`);
                if (targetElement) {
                    targetElement.classList.add('active');
                }
                
                // Обновляем заголовок страницы
                this.switchPage(targetPage);
            });
        });
    }

    setupSettings() {
        const settingsToggle = document.getElementById('settings-toggle');
        const settingsDropdown = document.getElementById('settings-dropdown');
        const usersLink = document.getElementById('users-link');

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

        // Обработка клика по пункту "Пользователи"
        if (usersLink) {
            usersLink.addEventListener('click', (e) => {
                e.preventDefault();
                settingsDropdown.classList.remove('show');
                this.openUsersPage();
            });
        }
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
        window.location.href = '/vulnanalizer/login';
    }

    openUsersPage() {
        // Открываем страницу управления пользователями в том же окне
        // Скрываем все страницы
        document.querySelectorAll('.page-content').forEach(page => {
            page.classList.remove('active');
        });
        
        // Показываем страницу пользователей
        const usersPage = document.getElementById('users-page');
        if (usersPage) {
            usersPage.classList.add('active');
        }
        
        // Обновляем активную ссылку в навигации
        document.querySelectorAll('.nav-link').forEach(link => {
            link.classList.remove('active');
        });
        
        // Обновляем заголовок страницы
        const pageTitle = document.getElementById('page-title');
        if (pageTitle) {
            pageTitle.textContent = 'Пользователи';
        }
        
        // Загружаем пользователей
        this.loadUsers();
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

    setupHosts() {
        // Загрузка CSV хостов
        const hostsForm = document.getElementById('hosts-upload-form');
        if (hostsForm) {
            hostsForm.addEventListener('submit', async (e) => {
                e.preventDefault();
                const fileInput = document.getElementById('hosts-file');
                if (!fileInput.files.length) {
                    this.showNotification('Выберите файл для загрузки', 'warning');
                    return;
                }
                
                const uploadBtn = document.getElementById('hosts-upload-btn');
                const btnText = uploadBtn.querySelector('.btn-text');
                const spinner = uploadBtn.querySelector('.fa-spinner');
                
                // Показываем индикатор загрузки
                btnText.textContent = 'Загрузка...';
                spinner.style.display = 'inline-block';
                uploadBtn.disabled = true;
                
                // Показываем прогресс в статусбаре
                this.showOperationProgress('hosts', 'Загрузка файла хостов...', 0);
                
                const formData = new FormData();
                formData.append('file', fileInput.files[0]);
                
                try {
                    this.updateOperationProgress('hosts', 'Обработка файла хостов...', 25, 'Чтение CSV файла...');
                    await new Promise(resolve => setTimeout(resolve, 500));
                    
                    this.updateOperationProgress('hosts', 'Парсинг данных...', 50, 'Обработка записей хостов...');
                    await new Promise(resolve => setTimeout(resolve, 600));
                    
                    this.updateOperationProgress('hosts', 'Сохранение в базу...', 75, 'Запись хостов в базу данных...');
                    
                    const resp = await fetch(this.getApiBasePath() + '/hosts/upload', {
                        method: 'POST',
                        body: formData
                    });
                    const data = await resp.json();
                    
                    if (data.success) {
                        this.updateOperationProgress('hosts', 'Завершение операции...', 90, 'Финальная обработка...');
                        await new Promise(resolve => setTimeout(resolve, 300));
                        
                        this.showOperationComplete('hosts', 'Хосты успешно загружены', `Загружено хостов: ${data.count}`);
                        this.showNotification(`Загружено хостов: ${data.count}`, 'success');
                        this.updateHostsStatus();
                        fileInput.value = ''; // Очищаем поле файла
                    } else {
                        this.showOperationError('hosts', 'Ошибка загрузки хостов', data.detail || 'Неизвестная ошибка');
                        this.showNotification('Ошибка загрузки хостов', 'error');
                    }
                } catch (err) {
                    console.error('Hosts upload error:', err);
                    this.showOperationError('hosts', 'Ошибка загрузки хостов', err.message);
                    this.showNotification('Ошибка загрузки хостов', 'error');
                } finally {
                    // Восстанавливаем кнопку
                    btnText.textContent = 'Загрузить CSV';
                    spinner.style.display = 'none';
                    uploadBtn.disabled = false;
                }
            });
        }
        
        // Обновление данных EPSS и эксплойтов
        const updateHostsDataBtn = document.getElementById('update-hosts-data-btn');
        if (updateHostsDataBtn) {
            updateHostsDataBtn.addEventListener('click', async () => {
                const btnText = updateHostsDataBtn.querySelector('.btn-text');
                const spinner = updateHostsDataBtn.querySelector('.fa-spinner');
                
                // Показываем индикатор загрузки
                btnText.textContent = 'Обновление...';
                spinner.style.display = 'inline-block';
                updateHostsDataBtn.disabled = true;
                
                // Показываем прогресс в статусбаре
                this.showOperationProgress('hosts', 'Начало обновления данных...', 0);
                
                try {
                    this.updateOperationProgress('hosts', 'Получение списка хостов...', 15, 'Загрузка уникальных CVE...');
                    await new Promise(resolve => setTimeout(resolve, 800));
                    
                    this.updateOperationProgress('hosts', 'Обновление EPSS данных...', 35, 'Загрузка и обновление EPSS оценок...');
                    await new Promise(resolve => setTimeout(resolve, 1000));
                    
                    this.updateOperationProgress('hosts', 'Обновление данных эксплойтов...', 55, 'Поиск и обновление эксплойтов...');
                    await new Promise(resolve => setTimeout(resolve, 1200));
                    
                    this.updateOperationProgress('hosts', 'Расчет рисков...', 75, 'Вычисление оценок риска...');
                    
                    const resp = await fetch(this.getApiBasePath() + '/hosts/update-data', {
                        method: 'POST'
                    });
                    const data = await resp.json();
                    
                    if (data.success) {
                        this.updateOperationProgress('hosts', 'Завершение операции...', 90, 'Финальная обработка...');
                        await new Promise(resolve => setTimeout(resolve, 300));
                        
                        this.showOperationComplete('hosts', 'Данные успешно обновлены', data.message);
                        this.showNotification(data.message, 'success');
                        this.updateHostsStatus();
                    } else {
                        this.showOperationError('hosts', 'Ошибка обновления данных', data.detail || 'Неизвестная ошибка');
                        this.showNotification('Ошибка обновления данных', 'error');
                    }
                } catch (err) {
                    console.error('Hosts data update error:', err);
                    this.showOperationError('hosts', 'Ошибка обновления данных', err.message);
                    this.showNotification('Ошибка обновления данных', 'error');
                } finally {
                    // Восстанавливаем кнопку
                    btnText.textContent = 'Обновить данные EPSS/Эксплойтов';
                    spinner.style.display = 'none';
                    updateHostsDataBtn.disabled = false;
                }
            });
        }
        
        // Поиск хостов
        const hostsSearchForm = document.getElementById('hosts-search-form');
        if (hostsSearchForm) {
            hostsSearchForm.addEventListener('submit', async (e) => {
                e.preventDefault();
                await this.searchHosts();
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
                    <div class="status-info">
                        <i class="fas fa-database"></i>
                        <span>Записей в базе: <strong>${data.count}</strong></span>
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
                statusDiv.innerHTML = `<b>Записей в базе EPSS:</b> ${data.count}`;
            } else {
                statusDiv.innerHTML = '<span style="color:var(--error-color)">Ошибка получения статуса EPSS</span>';
            }
        } catch (err) {
            statusDiv.innerHTML = '<span style="color:var(--error-color)">Ошибка получения статуса EPSS</span>';
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

    async searchHosts() {
        const form = document.getElementById('hosts-search-form');
        const resultsDiv = document.getElementById('hosts-search-results');
        
        if (!form || !resultsDiv) return;
        
        const formData = new FormData(form);
        const params = new URLSearchParams();
        
        // Добавляем параметры поиска
        for (let [key, value] of formData.entries()) {
            if (key === 'exploits_only') {
                // Для чекбокса добавляем значение только если он отмечен
                if (value === 'on') {
                    params.append(key, 'true');
                }
            } else if (value.trim()) {
                params.append(key, value.trim());
            }
        }
        
        try {
            const resp = await fetch(`${this.getApiBasePath()}/hosts/search?${params.toString()}`);
            const data = await resp.json();
            
            if (data.success) {
                const groupBy = formData.get('group_by') || '';
                this.renderHostsResults(data.data, groupBy);
            } else {
                this.showNotification('Ошибка поиска хостов', 'error');
            }
        } catch (err) {
            console.error('Hosts search error:', err);
            this.showNotification('Ошибка поиска хостов', 'error');
        }
    }

    renderHostsResults(hosts, groupBy = '') {
        const resultsDiv = document.getElementById('hosts-search-results');
        if (!resultsDiv) return;
        
        if (!hosts || hosts.length === 0) {
            resultsDiv.innerHTML = `
                <div class="no-results">
                    <i class="fas fa-search"></i>
                    <p>Хосты не найдены</p>
                </div>
            `;
            return;
        }
        
        let html = `<h4>Найдено хостов: ${hosts.length}</h4>`;
        
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
        
        // Автоматически рассчитываем риск для каждого хоста с задержкой
        const allHosts = groupBy ? Object.values(this.groupHosts(hosts, groupBy)).flat() : hosts;
        allHosts.forEach((host, index) => {
            setTimeout(() => {
                this.calculateHostRisk(host.id);
            }, index * 100); // Задержка 100мс между запросами
        });
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
        
        return `
            <div class="host-item single-line">
                <div class="host-name">${host.hostname}</div>
                <div class="host-ip">${host.ip_address}</div>
                <div class="host-cve">${host.cve}</div>
                <div class="host-cvss">CVSS: ${host.cvss || 'N/A'}</div>
                <div class="host-criticality">
                    <span class="${criticalityClass}">${host.criticality}</span>
                </div>
                <div class="host-status">${host.status}</div>
                <div class="host-risk" id="host-risk-${host.id}"></div>
            </div>
        `;
    }

    clearHostsResults() {
        const resultsDiv = document.getElementById('hosts-search-results');
        if (resultsDiv) {
            resultsDiv.innerHTML = '';
        }
    }

    async exportHosts() {
        const form = document.getElementById('hosts-search-form');
        if (!form) return;
        
        const formData = new FormData(form);
        const params = new URLSearchParams();
        
        // Добавляем только заполненные параметры
        for (let [key, value] of formData.entries()) {
            if (value.trim()) {
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
            // Загружаем настройки
            const settingsResponse = await fetch(this.getApiBasePath() + '/settings');
            const settingsData = await settingsResponse.json();
            
            if (settingsData.success) {
                this.populateSettings(settingsData.data);
            }
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
                <div class="progress-bar">
                    <div class="progress-fill" style="width: ${progress}%"></div>
                </div>
                <div class="progress-text">${progress.toFixed(1)}%</div>
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
                <div class="progress-bar">
                    <div class="progress-fill" style="width: ${progress}%"></div>
                </div>
                <div class="progress-text">${progress.toFixed(1)}%</div>
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

    setupUsers() {
        // Проверяем права доступа
        const userInfo = localStorage.getItem('user_info');
        if (userInfo) {
            try {
                const currentUser = JSON.parse(userInfo);
                if (!currentUser.is_admin) {
                    // Скрываем ссылку на управление пользователями для не-админов
                    const usersLink = document.getElementById('users-link');
                    if (usersLink) {
                        usersLink.style.display = 'none';
                    }
                    return; // Не настраиваем функциональность для не-админов
                }
            } catch (e) {
                console.error('Error parsing user info:', e);
                return;
            }
        }

        // Кнопка добавления пользователя
        const addUserBtn = document.getElementById('add-user-btn');
        if (addUserBtn) {
            addUserBtn.addEventListener('click', () => {
                this.openUserModal();
            });
        }

        // Модальное окно пользователя
        const closeModal = document.getElementById('close-modal');
        if (closeModal) {
            closeModal.addEventListener('click', () => {
                this.closeUserModal();
            });
        }

        const cancelBtn = document.getElementById('cancel-btn');
        if (cancelBtn) {
            cancelBtn.addEventListener('click', () => {
                this.closeUserModal();
            });
        }

        const saveBtn = document.getElementById('save-btn');
        if (saveBtn) {
            saveBtn.addEventListener('click', () => {
                this.saveUser();
            });
        }

        // Модальное окно пароля
        const closePasswordModal = document.getElementById('close-password-modal');
        if (closePasswordModal) {
            closePasswordModal.addEventListener('click', () => {
                this.closePasswordModal();
            });
        }

        const cancelPasswordBtn = document.getElementById('cancel-password-btn');
        if (cancelPasswordBtn) {
            cancelPasswordBtn.addEventListener('click', () => {
                this.closePasswordModal();
            });
        }

        const savePasswordBtn = document.getElementById('save-password-btn');
        if (savePasswordBtn) {
            savePasswordBtn.addEventListener('click', () => {
                this.savePassword();
            });
        }

        // Закрытие модальных окон при клике вне их
        window.addEventListener('click', (e) => {
            if (e.target.classList.contains('modal')) {
                e.target.classList.remove('show');
            }
        });

        // Поиск пользователей
        const usersSearch = document.getElementById('users-search');
        if (usersSearch) {
            usersSearch.addEventListener('input', (e) => {
                this.filterUsers();
            });
        }

        // Фильтры пользователей
        const filterButtons = document.querySelectorAll('.filter-btn');
        filterButtons.forEach(btn => {
            btn.addEventListener('click', (e) => {
                // Убираем активный класс со всех кнопок
                filterButtons.forEach(b => b.classList.remove('active'));
                // Добавляем активный класс к текущей кнопке
                e.target.classList.add('active');
                this.filterUsers();
            });
        });

        // Загружаем пользователей при открытии страницы
        this.loadUsers();
    }

    setupSidebar() {
        const sidebar = document.getElementById('sidebar');
        const sidebarToggle = document.getElementById('sidebar-toggle');
        
        if (!sidebar || !sidebarToggle) return;

        // Загружаем состояние из localStorage
        const isCollapsed = localStorage.getItem('sidebar_collapsed') === 'true';
        if (isCollapsed) {
            sidebar.classList.add('collapsed');
        }

        // Обработчик для кнопки сворачивания
        sidebarToggle.addEventListener('click', () => {
            sidebar.classList.toggle('collapsed');
            
            // Сохраняем состояние
            const isNowCollapsed = sidebar.classList.contains('collapsed');
            localStorage.setItem('sidebar_collapsed', isNowCollapsed.toString());
        });
    }

    filterUsers() {
        if (!this.allUsers) return;

        const searchTerm = document.getElementById('users-search')?.value.toLowerCase() || '';
        const activeFilter = document.querySelector('.filter-btn.active')?.dataset.filter || 'all';

        let filteredUsers = this.allUsers.filter(user => {
            // Поиск по имени пользователя и email
            const matchesSearch = user.username.toLowerCase().includes(searchTerm) || 
                                (user.email && user.email.toLowerCase().includes(searchTerm));

            // Фильтрация по статусу
            let matchesFilter = true;
            if (activeFilter === 'active') {
                matchesFilter = user.is_active;
            } else if (activeFilter === 'admin') {
                matchesFilter = user.is_admin;
            }

            return matchesSearch && matchesFilter;
        });

        // Обновляем отображение
        const usersList = document.getElementById('users-list');
        if (usersList) {
            usersList.innerHTML = filteredUsers.map(user => this.createUserCard(user)).join('');
        }

        // Обновляем статистику для отфильтрованных пользователей
        this.updateUsersStats(filteredUsers);
    }

    async loadUsers() {
        try {
            // Проверяем, является ли текущий пользователь администратором
            const userInfo = localStorage.getItem('user_info');
            if (!userInfo) {
                this.showNotification('Ошибка: информация о пользователе не найдена', 'error');
                return;
            }

            const currentUser = JSON.parse(userInfo);
            if (!currentUser.is_admin) {
                this.showNotification('Доступ запрещен: требуются права администратора', 'error');
                // Скрываем страницу пользователей для не-админов
                this.hideUsersPage();
                return;
            }

            const response = await fetch('/vulnanalizer/api/users/all', {
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('auth_token')}`
                }
            });

            if (response.ok) {
                const data = await response.json();
                this.renderUsers(data.data);
            } else if (response.status === 403) {
                this.showNotification('Доступ запрещен: требуются права администратора', 'error');
                this.hideUsersPage();
            } else {
                this.showNotification('Ошибка загрузки пользователей', 'error');
            }
        } catch (error) {
            console.error('Error loading users:', error);
            this.showNotification('Ошибка соединения с сервером', 'error');
        }
    }

    hideUsersPage() {
        // Скрываем страницу пользователей
        const usersPage = document.getElementById('users-page');
        if (usersPage) {
            usersPage.style.display = 'none';
        }
        
        // Показываем сообщение о недоступности
        const usersList = document.getElementById('users-list');
        if (usersList) {
            usersList.innerHTML = `
                <div class="access-denied-message">
                    <i class="fas fa-lock"></i>
                    <h3>Доступ запрещен</h3>
                    <p>Для просмотра и управления пользователями требуются права администратора.</p>
                </div>
            `;
        }
    }

    renderUsers(users) {
        const usersList = document.getElementById('users-list');
        if (!usersList) return;

        // Обновляем статистику
        this.updateUsersStats(users);

        // Рендерим пользователей
        usersList.innerHTML = users.map(user => this.createUserCard(user)).join('');

        // Сохраняем список пользователей для фильтрации
        this.allUsers = users;
    }

    updateUsersStats(users) {
        const totalUsers = document.getElementById('total-users');
        const activeUsers = document.getElementById('active-users');
        const adminUsers = document.getElementById('admin-users');

        if (totalUsers) totalUsers.textContent = users.length;
        if (activeUsers) activeUsers.textContent = users.filter(u => u.is_active).length;
        if (adminUsers) adminUsers.textContent = users.filter(u => u.is_admin).length;
    }

    createUserCard(user) {
        const badges = [];
        if (user.is_admin) badges.push('<span class="user-badge admin">Админ</span>');
        if (user.is_active) badges.push('<span class="user-badge active">Активен</span>');
        if (!user.is_active) badges.push('<span class="user-badge inactive">Неактивен</span>');

        const userInitial = user.username.charAt(0).toUpperCase();
        const email = user.email || 'Email не указан';

        return `
            <div class="user-card" data-user-id="${user.id}" data-username="${user.username}" data-email="${email}" data-admin="${user.is_admin}" data-active="${user.is_active}">
                <div class="user-header">
                    <div class="user-info">
                        <div class="user-avatar">
                            ${userInitial}
                        </div>
                        <div class="user-details">
                            <h4>${user.username}</h4>
                            <div class="user-email">${email}</div>
                        </div>
                    </div>
                    <div class="user-badges">
                        ${badges.join('')}
                    </div>
                </div>
                <div class="user-actions">
                    <button class="btn btn-secondary btn-sm" onclick="vulnAnalizer.editUser(${user.id})">
                        <i class="fas fa-edit"></i> Редактировать
                    </button>
                    <button class="btn btn-warning btn-sm" onclick="vulnAnalizer.changePassword(${user.id})">
                        <i class="fas fa-key"></i> Пароль
                    </button>
                    <button class="btn btn-danger btn-sm" onclick="vulnAnalizer.deleteUser(${user.id})">
                        <i class="fas fa-trash"></i> Удалить
                    </button>
                </div>
            </div>
        `;
    }

    openUserModal(user = null) {
        const modal = document.getElementById('user-modal');
        const modalTitle = document.getElementById('modal-title');
        const form = document.getElementById('user-form');
        const usernameInput = document.getElementById('username');
        const emailInput = document.getElementById('email');
        const passwordInput = document.getElementById('password');
        const confirmPasswordInput = document.getElementById('confirm-password');
        const isAdminCheckbox = document.getElementById('is-admin');
        const isActiveCheckbox = document.getElementById('is-active');

        if (user) {
            modalTitle.textContent = 'Редактировать пользователя';
            usernameInput.value = user.username;
            emailInput.value = user.email || '';
            passwordInput.value = '';
            confirmPasswordInput.value = '';
            isAdminCheckbox.checked = user.is_admin;
            isActiveCheckbox.checked = user.is_active;
            form.dataset.userId = user.id;
        } else {
            modalTitle.textContent = 'Добавить пользователя';
            form.reset();
            delete form.dataset.userId;
        }

        modal.classList.add('show');
    }

    closeUserModal() {
        const modal = document.getElementById('user-modal');
        modal.classList.remove('show');
    }

    async saveUser() {
        const form = document.getElementById('user-form');
        const formData = new FormData(form);
        
        const userData = {
            username: formData.get('username'),
            email: formData.get('email'),
            password: formData.get('password'),
            is_admin: formData.get('is-admin') === 'on',
            is_active: formData.get('is-active') === 'on'
        };

        if (userData.password !== formData.get('confirm-password')) {
            this.showNotification('Пароли не совпадают', 'error');
            return;
        }

        try {
            const userId = form.dataset.userId;
            const url = userId ? `/vulnanalizer/api/users/${userId}/update` : '/vulnanalizer/api/users/register';
            const method = userId ? 'PUT' : 'POST';

            const response = await fetch(url, {
                method: method,
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${localStorage.getItem('auth_token')}`
                },
                body: JSON.stringify(userData)
            });

            if (response.ok) {
                this.showNotification(userId ? 'Пользователь обновлен' : 'Пользователь создан', 'success');
                this.closeUserModal();
                this.loadUsers();
            } else {
                const error = await response.json();
                this.showNotification(error.detail || 'Ошибка сохранения', 'error');
            }
        } catch (error) {
            console.error('Error saving user:', error);
            this.showNotification('Ошибка соединения с сервером', 'error');
        }
    }

    editUser(userId) {
        // Найти пользователя в списке и открыть модальное окно
        const userCard = document.querySelector(`[data-user-id="${userId}"]`);
        if (userCard) {
            const user = {
                id: userId,
                username: userCard.querySelector('.user-details h4').textContent,
                email: userCard.querySelector('.user-email').textContent,
                is_admin: userCard.querySelector('.user-badge.admin') !== null,
                is_active: userCard.querySelector('.user-badge.active') !== null
            };
            this.openUserModal(user);
        }
    }

    changePassword(userId) {
        this.editingUserId = userId;
        const modal = document.getElementById('password-modal');
        modal.classList.add('show');
    }

    closePasswordModal() {
        const modal = document.getElementById('password-modal');
        modal.classList.remove('show');
        this.editingUserId = null;
    }

    async savePassword() {
        const form = document.getElementById('password-form');
        const formData = new FormData(form);

        const passwordData = {
            password: formData.get('new-password'),
            confirm_password: formData.get('confirm-new-password')
        };

        if (!passwordData.password || passwordData.password !== passwordData.confirm_password) {
            this.showNotification('Пароли не совпадают', 'error');
            return;
        }

        try {
            const response = await fetch(`/vulnanalizer/api/users/${this.editingUserId}/password`, {
                method: 'PUT',
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('auth_token')}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    password: passwordData.password
                })
            });

            if (response.ok) {
                this.showNotification('Пароль изменен', 'success');
                this.closePasswordModal();
            } else {
                const error = await response.json();
                this.showNotification(error.detail || 'Ошибка изменения пароля', 'error');
            }
        } catch (error) {
            console.error('Error changing password:', error);
            this.showNotification('Ошибка соединения с сервером', 'error');
        }
    }

    async deleteUser(userId) {
        if (!confirm('Вы уверены, что хотите удалить этого пользователя?')) {
            return;
        }

        try {
            const response = await fetch(`/vulnanalizer/api/users/${userId}/delete`, {
                method: 'DELETE',
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('auth_token')}`
                }
            });

            if (response.ok) {
                this.showNotification('Пользователь удален', 'success');
                this.loadUsers();
            } else {
                const error = await response.json();
                this.showNotification(error.detail || 'Ошибка удаления', 'error');
            }
        } catch (error) {
            console.error('Error deleting user:', error);
            this.showNotification('Ошибка соединения с сервером', 'error');
        }
    }
}

// Инициализация приложения при загрузке страницы
document.addEventListener('DOMContentLoaded', () => {
    window.vulnAnalizer = new VulnAnalizer();
});
