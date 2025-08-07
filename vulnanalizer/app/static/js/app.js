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
        this.setupTheme();
        this.setupNavigation();
        this.setupForms();
        this.setupEPSS();
        this.setupExploitDB();
        this.setupHosts();
        
        // Загружаем статус хостов при инициализации
        setTimeout(() => {
            this.updateHostsStatus();
        }, 100);
    }

    setupTheme() {
        const themeToggle = document.getElementById('theme-toggle');
        const body = document.body;
        
        // Загружаем сохраненную тему
        const savedTheme = localStorage.getItem('theme') || 'light';
        body.className = `${savedTheme}-theme`;
        
        // Обновляем иконку
        const icon = themeToggle.querySelector('i');
        icon.className = savedTheme === 'light' ? 'fas fa-moon' : 'fas fa-sun';
        
        themeToggle.addEventListener('click', () => {
            this.toggleTheme();
        });
    }

    toggleTheme() {
        const body = document.body;
        const themeToggle = document.getElementById('theme-toggle');
        const icon = themeToggle.querySelector('i');
        
        if (body.classList.contains('light-theme')) {
            body.className = 'dark-theme';
            icon.className = 'fas fa-sun';
            localStorage.setItem('theme', 'dark');
        } else {
            body.className = 'light-theme';
            icon.className = 'fas fa-moon';
            localStorage.setItem('theme', 'light');
        }
    }

    setupNavigation() {
        const navLinks = document.querySelectorAll('.nav-link');
        const pages = document.querySelectorAll('.page-content');
        
        navLinks.forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                
                // Убираем активный класс со всех ссылок
                navLinks.forEach(l => l.classList.remove('active'));
                
                // Добавляем активный класс к текущей ссылке
                link.classList.add('active');
                
                // Скрываем все страницы
                pages.forEach(page => page.classList.remove('active'));
                
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

    switchPage(page) {
        const pageTitle = document.getElementById('page-title');
        
        switch(page) {
            case 'analysis':
                pageTitle.textContent = 'Поиск хостов';
                break;
            case 'settings':
                pageTitle.textContent = 'Настройки';
                this.updateEPSSStatus();
                this.updateExploitDBStatus();
                break;
            case 'hosts':
                pageTitle.textContent = 'Импорт';
                this.updateHostsStatus();
                break;
            default:
                pageTitle.textContent = 'VulnAnalizer';
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
}

// Инициализация приложения при загрузке страницы
document.addEventListener('DOMContentLoaded', () => {
    new VulnAnalizer();
}); 