/**
 * Модуль для управления настройками
 * v=3.2
 */
class SettingsModule {
    constructor(app) {
        this.app = app;
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.loadAppVersion();
        this.loadSettings();
    }

    setupEventListeners() {
        // Форма настроек
        const settingsForm = document.getElementById('settings-form');
        if (settingsForm) {
            settingsForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.saveSettings();
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

        // Форма настроек CVSS
        const cvssForm = document.getElementById('cvss-form');
        if (cvssForm) {
            cvssForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.saveCVSSSettings();
            });
        }

        // Форма настроек порога риска
        const thresholdForm = document.getElementById('threshold-form');
        if (thresholdForm) {
            thresholdForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.saveThresholdSettings();
            });
        }

        // Кнопка сброса CVSS к значениям по умолчанию
        const resetCVSSDefaultsBtn = document.getElementById('reset-cvss-defaults');
        if (resetCVSSDefaultsBtn) {
            resetCVSSDefaultsBtn.addEventListener('click', () => {
                this.resetCVSSDefaults();
            });
        }

        // Кнопка сброса Impact к значениям по умолчанию
        const resetImpactDefaultsBtn = document.getElementById('reset-impact-defaults');
        if (resetImpactDefaultsBtn) {
            resetImpactDefaultsBtn.addEventListener('click', () => {
                this.resetImpactDefaults();
            });
        }

        // Обработчики для ExploitDB формы
        const exdbForm = document.getElementById('exdb-form');
        if (exdbForm) {
            exdbForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.saveExploitDBSettings();
            });
        }

        const resetExDBDefaultsBtn = document.getElementById('reset-exdb-defaults');
        if (resetExDBDefaultsBtn) {
            resetExDBDefaultsBtn.addEventListener('click', () => {
                this.resetExploitDBDefaults();
            });
        }

        // Обработчики для Metasploit формы
        const msfForm = document.getElementById('msf-form');
        if (msfForm) {
            msfForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.saveMetasploitSettings();
            });
        }

        const resetMSFDefaultsBtn = document.getElementById('reset-msf-defaults');
        if (resetMSFDefaultsBtn) {
            resetMSFDefaultsBtn.addEventListener('click', () => {
                this.resetMetasploitDefaults();
            });
        }

        // Обработчики для подменю
        this.setupSubmenuHandlers();

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

        // Настройка выпадающего меню настроек
        const settingsDropdown = document.getElementById('settings-dropdown');
        const usersLink = document.getElementById('users-link');
        const backgroundTasksLink = document.getElementById('background-tasks-link');
        const settingsLink = document.getElementById('settings-link');

        // Обработчик для кнопки настроек перенесен в SetupManager.js
        // чтобы избежать дублирования обработчиков

        // Закрытие при клике вне меню настроек
        
        // Модальное окно с формулой расчета риска
        const showFormulaBtn = document.getElementById('show-risk-formula');
        const closeFormulaBtn = document.getElementById('close-risk-formula');
        const formulaModal = document.getElementById('risk-formula-modal');
        
        if (showFormulaBtn) {
            showFormulaBtn.addEventListener('click', () => {
                this.showRiskFormulaModal();
            });
        }
        
        if (closeFormulaBtn) {
            closeFormulaBtn.addEventListener('click', () => {
                this.hideRiskFormulaModal();
            });
        }
        
        // Закрытие модального окна при клике вне его
        if (formulaModal) {
            formulaModal.addEventListener('click', (e) => {
                if (e.target === formulaModal) {
                    this.hideRiskFormulaModal();
                }
            });
        }
        // Обработчик закрытия меню настроек перенесен в SetupManager.js
        // чтобы избежать дублирования обработчиков

        // Обработка клика по пункту "Пользователи"
        if (usersLink) {
            usersLink.addEventListener('click', (e) => {
                e.preventDefault();
                settingsDropdown.classList.remove('show');
                this.app.authManager.openUsersPage();
            });
        }

        // Обработка клика по пункту "Настройки системы"
        if (settingsLink) {
            settingsLink.addEventListener('click', (e) => {
                e.preventDefault();
                settingsDropdown.classList.remove('show');
                // Переключаемся на страницу настроек
                if (this.app && this.app.uiManager) {
                    this.app.uiManager.switchPage('settings');
                }
            });
        }
    }

    async loadDatabaseSettings() {
        try {
            const settings = await this.app.api.getSettings();
            
            // Заполняем форму настроек базы данных
            this.populateSettings(settings);
            
        } catch (error) {
        }
    }

    async loadImpactSettings() {
        try {
            const settings = await this.app.api.getSettings();
            
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
        }
    }

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

    async saveSettings() {
        const form = document.getElementById('settings-form');
        const formData = new FormData(form);
        const settings = {};

        for (let [key, value] of formData.entries()) {
            settings[key] = value;
        }

        try {
            const data = await this.app.api.saveSettings(settings);
            
            if (data.success) {
                window.notifications.show('Настройки успешно сохранены', 'success');
            } else {
                window.notifications.show('Ошибка сохранения настроек', 'error');
            }
        } catch (error) {
            window.notifications.show('Ошибка сохранения настроек', 'error');
        }
    }

    async saveImpactSettings() {
        const form = document.getElementById('impact-form');
        const formData = new FormData(form);
        const settings = {};

        // Собираем данные формы и конвертируем в float
        for (let [key, value] of formData.entries()) {
            settings[key] = parseFloat(value) || 0;
        }

        

        try {
            const data = await this.app.api.saveSettings(settings);
            
            if (data.success) {
                window.notifications.show('Настройки Impact успешно сохранены', 'success');
            } else {
                window.notifications.show('Ошибка сохранения настроек Impact', 'error');
            }
        } catch (error) {
            window.notifications.show('Ошибка сохранения настроек Impact', 'error');
        }
    }

    updateThresholdSlider(value) {
        const slider = document.getElementById('risk-threshold');
        if (slider) {
            const percentage = value + '%';
            slider.style.background = `linear-gradient(to right, var(--success-color) 0%, var(--success-color) ${percentage}, var(--error-color) ${percentage}, var(--error-color) 100%)`;
        }
    }

    async testConnection() {
        try {
            const btn = document.getElementById('test-connection');
            if (!btn) {
                window.notifications.show('❌ Кнопка проверки подключения не найдена', 'error');
                return;
            }
            
            const originalText = btn.innerHTML;
            btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Проверка...';
            btn.disabled = true;

            const data = await this.app.api.testConnection();
            
            if (data.status === 'healthy' && data.database === 'connected') {
                window.notifications.show('Подключение к базе данных успешно', 'success');
            } else {
                window.notifications.show('Ошибка подключения к базе данных', 'error');
            }
        } catch (error) {
            window.notifications.show('❌ Ошибка подключения к базе данных', 'error');
        } finally {
            const btn = document.getElementById('test-connection');
            if (btn) {
                btn.innerHTML = '<i class="fas fa-database"></i> Проверить подключение';
                btn.disabled = false;
            }
        }
    }

    async clearHosts() {
        if (!confirm('Вы уверены, что хотите удалить все записи хостов? Это действие нельзя отменить.')) {
            return;
        }

        try {
            const btn = document.getElementById('clear-hosts-btn');
            const originalText = btn.innerHTML;
            btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Очистка...';
            btn.disabled = true;

            const data = await this.app.api.clearHosts();

            if (data.success) {
                window.notifications.show('Таблица хостов очищена успешно!', 'success');
                if (this.app.hostsModule) {
                    this.app.hostsModule.updateStatus();
                }
            } else {
                window.notifications.show(`Ошибка очистки: ${data.error}`, 'error');
            }
        } catch (error) {
            window.notifications.show('Ошибка очистки хостов', 'error');
        } finally {
            const btn = document.getElementById('clear-hosts-btn');
            btn.innerHTML = '<i class="fas fa-trash"></i> Очистить хосты';
            btn.disabled = false;
        }
    }

    async clearEPSS() {
        if (!confirm('Вы уверены, что хотите удалить все записи EPSS? Это действие нельзя отменить.')) {
            return;
        }

        try {
            const btn = document.getElementById('clear-epss-btn');
            const originalText = btn.innerHTML;
            btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Очистка...';
            btn.disabled = true;

            const data = await this.app.api.clearEPSS();

            if (data.success) {
                window.notifications.show('Таблица EPSS очищена успешно!', 'success');
                if (this.app.epssModule) {
                    this.app.epssModule.updateStatus();
                }
            } else {
                window.notifications.show(`Ошибка очистки: ${data.error}`, 'error');
            }
        } catch (error) {
            window.notifications.show('Ошибка очистки EPSS', 'error');
        } finally {
            const btn = document.getElementById('clear-epss-btn');
            btn.innerHTML = '<i class="fas fa-trash"></i> Очистить EPSS';
            btn.disabled = false;
        }
    }

    async clearExploitDB() {
        if (!confirm('Вы уверены, что хотите удалить все записи ExploitDB? Это действие нельзя отменить.')) {
            return;
        }

        try {
            const btn = document.getElementById('clear-exploitdb-btn');
            const originalText = btn.innerHTML;
            btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Очистка...';
            btn.disabled = true;

            const data = await this.app.api.clearExploitDB();

            if (data.success) {
                window.notifications.show('Таблица ExploitDB очищена успешно!', 'success');
                if (this.app.exploitdbModule) {
                    this.app.exploitdbModule.updateStatus();
                }
            } else {
                window.notifications.show(`Ошибка очистки: ${data.error}`, 'error');
            }
        } catch (error) {
            window.notifications.show('Ошибка очистки ExploitDB', 'error');
        } finally {
            const btn = document.getElementById('clear-exploitdb-btn');
            btn.innerHTML = '<i class="fas fa-trash"></i> Очистить ExploitDB';
            btn.disabled = false;
        }
    }

    async clearCVE() {
        if (!confirm('Вы уверены, что хотите удалить все записи CVE? Это действие нельзя отменить.')) {
            return;
        }

        try {
            const btn = document.getElementById('clear-cve-btn');
            const originalText = btn.innerHTML;
            btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Очистка...';
            btn.disabled = true;

            const data = await this.app.api.clearCVE();

            if (data.success) {
                window.notifications.show('Таблица CVE очищена успешно!', 'success');
                if (this.app.cveModule) {
                    this.app.cveModule.updateStatus();
                }
            } else {
                window.notifications.show(`Ошибка очистки: ${data.error}`, 'error');
            }
        } catch (error) {
            window.notifications.show('Ошибка очистки CVE', 'error');
        } finally {
            const btn = document.getElementById('clear-cve-btn');
            btn.innerHTML = '<i class="fas fa-trash"></i> Очистить CVE';
            btn.disabled = false;
        }
    }

    async loadAppVersion() {
        try {
            const data = await this.app.api.getVersion();
            
            const versionElement = document.getElementById('app-version');
            if (versionElement && data.version) {
                versionElement.textContent = `v${data.version}`;
            }
        } catch (error) {
        }
    }

    async loadSettings() {
        try {
            const settings = await this.app.api.getSettings();
            
            // Загружаем Impact настройки
            this.loadImpactSettings(settings);
            
            // Загружаем CVSS настройки
            this.loadCVSSSettings(settings);
            
            // Загружаем настройки порога риска
            this.loadThresholdSettings(settings);
            
        } catch (error) {
        }
    }

    loadImpactSettings(settings) {
        // Загружаем Impact настройки в форму
        const impactForm = document.getElementById('impact-form');
        if (impactForm) {
            const impactFields = [
                'impact_resource_criticality_critical', 'impact_resource_criticality_high', 'impact_resource_criticality_medium', 'impact_resource_criticality_none',
                'impact_confidential_data_yes', 'impact_confidential_data_no',
                'impact_internet_access_yes', 'impact_internet_access_no'
            ];
            
            impactFields.forEach(field => {
                const input = impactForm.querySelector(`[name="${field}"]`);
                if (input && settings[field]) {
                    input.value = settings[field];
                }
            });
        }
    }

    loadCVSSSettings(settings) {
        // Загружаем CVSS настройки в форму
        const cvssForm = document.getElementById('cvss-form');
        if (cvssForm) {
            const cvssFields = [
                'cvss_v3_attack_vector_network', 'cvss_v3_attack_vector_adjacent', 'cvss_v3_attack_vector_local', 'cvss_v3_attack_vector_physical',
                'cvss_v3_privileges_required_none', 'cvss_v3_privileges_required_low', 'cvss_v3_privileges_required_high',
                'cvss_v3_user_interaction_none', 'cvss_v3_user_interaction_required',
                'cvss_v2_access_vector_network', 'cvss_v2_access_vector_adjacent_network', 'cvss_v2_access_vector_local',
                'cvss_v2_access_complexity_low', 'cvss_v2_access_complexity_medium', 'cvss_v2_access_complexity_high',
                'cvss_v2_authentication_none', 'cvss_v2_authentication_single', 'cvss_v2_authentication_multiple'
            ];
            
            cvssFields.forEach(field => {
                const input = cvssForm.querySelector(`[name="${field}"]`);
                if (input && settings[field]) {
                    input.value = settings[field];
                }
            });
        }
    }

    loadThresholdSettings(settings) {
        // Загружаем настройки порога риска в форму
        const thresholdForm = document.getElementById('threshold-form');
        if (thresholdForm) {
            const thresholdSlider = thresholdForm.querySelector('#risk-threshold');
            const thresholdValue = thresholdForm.querySelector('#threshold-value');
            
            if (thresholdSlider && settings.risk_threshold) {
                thresholdSlider.value = settings.risk_threshold;
                if (thresholdValue) {
                    thresholdValue.textContent = settings.risk_threshold;
                }
            }
        }
    }

    setupSubmenuHandlers() {
        // Обработчики для подменю
        const submenuHeaders = document.querySelectorAll('.submenu-header');
        
        submenuHeaders.forEach(header => {
            header.addEventListener('click', () => {
                const target = header.getAttribute('data-target');
                const content = document.getElementById(target);
                const arrow = header.querySelector('.submenu-arrow');
                
                if (content) {
                    // Переключаем состояние
                    const isActive = content.classList.contains('active');
                    
                    if (isActive) {
                        content.classList.remove('active');
                        header.classList.remove('active');
                    } else {
                        content.classList.add('active');
                        header.classList.add('active');
                    }
                }
            });
        });
    }

    // Методы для работы с CVSS настройками
    async saveCVSSSettings() {
        try {
            const form = document.getElementById('cvss-form');
            const formData = new FormData(form);
            const data = Object.fromEntries(formData.entries());

            // Конвертируем строковые значения в числа
            for (const key in data) {
                if (data[key] !== '') {
                    data[key] = parseFloat(data[key]);
                }
            }

            const response = await this.app.api.saveSettings(data);

            if (response.success) {
                window.notifications.show('Настройки CVSS сохранены успешно!', 'success');
            } else {
                window.notifications.show(`Ошибка сохранения: ${response.error}`, 'error');
            }
        } catch (error) {
            window.notifications.show('Ошибка сохранения настроек CVSS', 'error');
        }
    }

    resetCVSSDefaults() {
        if (!confirm('Сбросить все CVSS параметры к значениям по умолчанию?')) {
            return;
        }

        const defaults = {
            'cvss_v3_attack_vector_network': 1.20,
            'cvss_v3_attack_vector_adjacent': 1.10,
            'cvss_v3_attack_vector_local': 0.95,
            'cvss_v3_attack_vector_physical': 0.85,
            'cvss_v3_privileges_required_none': 1.20,
            'cvss_v3_privileges_required_low': 1.00,
            'cvss_v3_privileges_required_high': 0.85,
            'cvss_v3_user_interaction_none': 1.15,
            'cvss_v3_user_interaction_required': 0.90,
            'cvss_v2_access_vector_network': 1.20,
            'cvss_v2_access_vector_adjacent_network': 1.10,
            'cvss_v2_access_vector_local': 0.95,
            'cvss_v2_access_complexity_low': 1.10,
            'cvss_v2_access_complexity_medium': 1.00,
            'cvss_v2_access_complexity_high': 0.90,
            'cvss_v2_authentication_none': 1.15,
            'cvss_v2_authentication_single': 1.00,
            'cvss_v2_authentication_multiple': 0.90
        };

        // Устанавливаем значения по умолчанию в форму
        for (const [key, value] of Object.entries(defaults)) {
            const input = document.querySelector(`[name="${key}"]`);
            if (input) {
                input.value = value;
            }
        }

        window.notifications.show('CVSS параметры сброшены к значениям по умолчанию', 'info');
    }

    resetImpactDefaults() {
        if (!confirm('Сбросить все Impact параметры к значениям по умолчанию?')) {
            return;
        }

        const defaults = {
            'impact_resource_criticality_critical': 0.33,
            'impact_resource_criticality_high': 0.25,
            'impact_resource_criticality_medium': 0.2,
            'impact_resource_criticality_none': 0.2,
            'impact_confidential_data_yes': 0.33,
            'impact_confidential_data_no': 0.2,
            'impact_internet_access_yes': 0.33,
            'impact_internet_access_no': 0.2
        };

        // Устанавливаем значения по умолчанию в форму
        for (const [key, value] of Object.entries(defaults)) {
            const input = document.querySelector(`[name="${key}"]`);
            if (input) {
                input.value = value;
            }
        }

        window.notifications.show('Impact параметры сброшены к значениям по умолчанию', 'info');
    }

    // Методы для работы с ExploitDB параметрами
    async saveExploitDBSettings() {
        try {
            const form = document.getElementById('exdb-form');
            const formData = new FormData(form);
            const data = Object.fromEntries(formData.entries());

            // Конвертируем строковые значения в числа
            for (const key in data) {
                if (data[key] !== '') {
                    data[key] = parseFloat(data[key]);
                }
            }

            const response = await this.app.api.saveSettings(data);

            if (response.success) {
                window.notifications.show('Настройки ExploitDB сохранены успешно!', 'success');
            } else {
                window.notifications.show(`Ошибка сохранения: ${response.error}`, 'error');
            }
        } catch (error) {
            window.notifications.show('Ошибка сохранения настроек ExploitDB', 'error');
        }
    }

    async loadExploitDBSettings() {
        try {
            const settings = await this.app.api.getSettings();
            
            // Загружаем значения в форму ExploitDB
            const exdbFields = [
                'exdb_remote', 'exdb_webapps', 'exdb_dos', 'exdb_local', 'exdb_hardware'
            ];
            
            for (const field of exdbFields) {
                const input = document.querySelector(`[name="${field}"]`);
                if (input && settings[field] !== undefined) {
                    input.value = settings[field];
                }
            }
        } catch (error) {
        }
    }

    resetExploitDBDefaults() {
        if (!confirm('Сбросить все ExploitDB параметры к значениям по умолчанию?')) {
            return;
        }

        // Значения по умолчанию загружаются из базы данных
        const defaults = {};

        // Устанавливаем значения по умолчанию в форму
        for (const [key, value] of Object.entries(defaults)) {
            const input = document.querySelector(`[name="${key}"]`);
            if (input) {
                input.value = value;
            }
        }

        window.notifications.show('ExploitDB параметры сброшены к значениям по умолчанию', 'info');
    }

    // Методы для работы с Metasploit параметрами
    async saveMetasploitSettings() {
        try {
            const form = document.getElementById('msf-form');
            const formData = new FormData(form);
            const data = Object.fromEntries(formData.entries());

            // Конвертируем строковые значения в числа
            for (const key in data) {
                if (data[key] !== '') {
                    data[key] = parseFloat(data[key]);
                }
            }

            const response = await this.app.api.saveSettings(data);

            if (response.success) {
                window.notifications.show('Настройки Metasploit сохранены успешно!', 'success');
            } else {
                window.notifications.show(`Ошибка сохранения: ${response.error}`, 'error');
            }
        } catch (error) {
            window.notifications.show('Ошибка сохранения настроек Metasploit', 'error');
        }
    }

    async loadMetasploitSettings() {
        try {
            const settings = await this.app.api.getSettings();
            
            // Загружаем значения в форму Metasploit
            const msfFields = [
                'msf_excellent', 'msf_good', 'msf_normal', 'msf_average', 
                'msf_low', 'msf_unknown', 'msf_manual'
            ];
            
            for (const field of msfFields) {
                const input = document.querySelector(`[name="${field}"]`);
                if (input && settings[field] !== undefined) {
                    input.value = settings[field];
                }
            }
        } catch (error) {
        }
    }

    resetMetasploitDefaults() {
        if (!confirm('Сбросить все Metasploit параметры к значениям по умолчанию?')) {
            return;
        }

        // Значения по умолчанию загружаются из базы данных
        const defaults = {};

        // Устанавливаем значения по умолчанию в форму
        for (const [key, value] of Object.entries(defaults)) {
            const input = document.querySelector(`[name="${key}"]`);
            if (input) {
                input.value = value;
            }
        }

        window.notifications.show('Metasploit параметры сброшены к значениям по умолчанию', 'info');
    }

    // Методы для работы с настройками порога риска
    async saveThresholdSettings() {
        try {
            const form = document.getElementById('threshold-form');
            const formData = new FormData(form);
            const data = Object.fromEntries(formData.entries());

            // Конвертируем строковые значения в числа
            for (const key in data) {
                if (data[key] !== '') {
                    data[key] = parseFloat(data[key]);
                }
            }

            const response = await this.app.api.saveSettings(data);

            if (response.success) {
                window.notifications.show('Настройки порога риска сохранены успешно!', 'success');
            } else {
                window.notifications.show(`Ошибка сохранения: ${response.error}`, 'error');
            }
        } catch (error) {
            window.notifications.show('Ошибка сохранения настроек порога риска', 'error');
        }
    }

    // Методы для работы с модальным окном формулы
    showRiskFormulaModal() {
        const modal = document.getElementById('risk-formula-modal');
        if (modal) {
            modal.style.display = 'flex';
            document.body.style.overflow = 'hidden'; // Блокируем прокрутку страницы
            
            // Принудительно устанавливаем стили
            modal.style.position = 'fixed';
            modal.style.top = '50%';
            modal.style.left = '50%';
            modal.style.transform = 'translate(-50%, -50%)';
            modal.style.zIndex = '1000';
        }
    }

    hideRiskFormulaModal() {
        const modal = document.getElementById('risk-formula-modal');
        if (modal) {
            modal.style.display = 'none';
            document.body.style.overflow = ''; // Восстанавливаем прокрутку страницы
        }
    }
}

// Экспорт модуля
if (typeof module !== 'undefined' && module.exports) {
    module.exports = SettingsModule;
} else {
    window.SettingsModule = SettingsModule;
}
