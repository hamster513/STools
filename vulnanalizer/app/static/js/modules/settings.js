/**
 * Модуль для управления настройками
 */
class SettingsModule {
    constructor(app) {
        this.app = app;
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.loadAppVersion();
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
        
        // Модальное окно с формулой расчета риска
        const showFormulaBtn = document.getElementById('show-risk-formula');
        const closeFormulaBtn = document.getElementById('close-risk-formula');
        const formulaModal = document.getElementById('risk-formula-modal');
        
        if (showFormulaBtn) {
            console.log('showFormulaBtn найден:', showFormulaBtn);
            showFormulaBtn.addEventListener('click', () => {
                console.log('Клик по кнопке show-risk-formula');
                this.showRiskFormulaModal();
            });
        } else {
            console.log('showFormulaBtn НЕ найден!');
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
                this.app.auth.openUsersPage();
            });
        }
    }

    async loadDatabaseSettings() {
        try {
            const settings = await this.app.api.getSettings();
            
            // Заполняем форму настроек базы данных
            this.populateSettings(settings);
            
        } catch (error) {
            console.error('Error loading database settings:', error);
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
            console.error('Error loading impact settings:', error);
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
                this.app.notifications.show('Настройки успешно сохранены', 'success');
            } else {
                this.app.notifications.show('Ошибка сохранения настроек', 'error');
            }
        } catch (error) {
            console.error('Error saving settings:', error);
            this.app.notifications.show('Ошибка сохранения настроек', 'error');
        }
    }

    async saveImpactSettings() {
        const form = document.getElementById('impact-form');
        const formData = new FormData(form);
        const settings = {};

        for (let [key, value] of formData.entries()) {
            settings[key] = value;
        }

        console.log('DEBUG: Form data entries:', Array.from(formData.entries()));
        console.log('DEBUG: Settings object:', settings);

        try {
            const data = await this.app.api.saveSettings(settings);
            
            if (data.success) {
                // Сохраняем порог риска в localStorage для быстрого доступа
                const threshold = formData.get('risk_threshold');
                if (threshold) {
                    localStorage.setItem('risk_threshold', threshold);
                }
                this.app.notifications.show('Настройки Impact успешно сохранены', 'success');
            } else {
                this.app.notifications.show('Ошибка сохранения настроек Impact', 'error');
            }
        } catch (error) {
            console.error('Error saving impact settings:', error);
            this.app.notifications.show('Ошибка сохранения настроек Impact', 'error');
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
                this.app.notifications.show('❌ Кнопка проверки подключения не найдена', 'error');
                return;
            }
            
            const originalText = btn.innerHTML;
            btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Проверка...';
            btn.disabled = true;

            const data = await this.app.api.testConnection();
            
            if (data.status === 'healthy' && data.database === 'connected') {
                this.app.notifications.show('Подключение к базе данных успешно', 'success');
            } else {
                this.app.notifications.show('Ошибка подключения к базе данных', 'error');
            }
        } catch (error) {
            console.error('Connection test error:', error);
            this.app.notifications.show('❌ Ошибка подключения к базе данных', 'error');
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
            console.error('Clear hosts error:', error);
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
            console.error('Clear EPSS error:', error);
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
            console.error('Clear ExploitDB error:', error);
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
            console.error('Clear CVE error:', error);
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
            console.error('Error loading app version:', error);
        }
    }

    // Методы для работы с модальным окном формулы
    showRiskFormulaModal() {
        const modal = document.getElementById('risk-formula-modal');
        if (modal) {
            console.log('showRiskFormulaModal: открываем модальное окно');
            console.log('До открытия - position:', modal.style.position);
            console.log('До открытия - top:', modal.style.top);
            console.log('До открытия - left:', modal.style.left);
            console.log('До открытия - transform:', modal.style.transform);
            
            modal.style.display = 'flex';
            document.body.style.overflow = 'hidden'; // Блокируем прокрутку страницы
            
            // Принудительно устанавливаем стили
            modal.style.position = 'fixed';
            modal.style.top = '50%';
            modal.style.left = '50%';
            modal.style.transform = 'translate(-50%, -50%)';
            modal.style.zIndex = '1000';
            
            console.log('После открытия - position:', modal.style.position);
            console.log('После открытия - top:', modal.style.top);
            console.log('После открытия - left:', modal.style.left);
            console.log('После открытия - transform:', modal.style.transform);
            
            // Проверяем через небольшую задержку
            setTimeout(() => {
                console.log('Через 100ms - position:', modal.style.position);
                console.log('Через 100ms - top:', modal.style.top);
                console.log('Через 100ms - left:', modal.style.left);
                console.log('Через 100ms - transform:', modal.style.transform);
                console.log('Через 100ms - computed styles:', window.getComputedStyle(modal));
            }, 100);
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
