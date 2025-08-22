/**
 * Модуль для интеграции с VM MaxPatrol
 */
class VMModule {
    constructor(app) {
        this.app = app;
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.loadVMSettings();
        this.updateStatus();
    }

    setupEventListeners() {
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
                this.updateStatus();
            });
        }
    }

    async loadVMSettings() {
        try {
            const data = await this.app.api.getVMSettings();
            
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
            const data = await this.app.api.saveVMSettings(settings);
            
            if (data.success) {
                this.app.notifications.show('VM настройки сохранены успешно', 'success');
                this.updateStatus();
            } else {
                this.app.notifications.show(`Ошибка сохранения: ${data.error}`, 'error');
            }
        } catch (error) {
            this.app.notifications.show(`Ошибка сохранения: ${error.message}`, 'error');
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
                this.app.notifications.show('Заполните все обязательные поля для подключения', 'error');
                return;
            }
        }

        try {
            const data = await this.app.api.testVMConnection(settings);
            
            if (data.success && data.data.success) {
                this.app.notifications.show(`Подключение успешно! ${data.data.message}`, 'success');
            } else {
                this.app.notifications.show(`Ошибка подключения: ${data.data.error || data.error}`, 'error');
            }
        } catch (error) {
            this.app.notifications.show(`Ошибка подключения: ${error.message}`, 'error');
        }
    }

    async importVMHosts() {
        const operationId = 'vm-import';
        this.showOperationProgress(operationId, 'Импорт хостов из VM MaxPatrol...');

        try {
            const data = await this.app.api.importVMHosts();
            
            if (data.success) {
                this.showOperationComplete(operationId, 'Импорт завершен успешно', 
                    `Импортировано: ${data.data.inserted} новых, обновлено: ${data.data.updated} существующих записей`);
                this.updateStatus();
                this.app.hosts.updateStatus(); // Обновляем статус хостов
            } else {
                this.showOperationError(operationId, 'Ошибка импорта', data.error);
            }
        } catch (error) {
            this.showOperationError(operationId, 'Ошибка импорта', error.message);
        }
    }

    async updateStatus() {
        try {
            const data = await this.app.api.getVMStatus();
            
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

    // Методы для работы с прогрессом операций
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

// Экспорт модуля
if (typeof module !== 'undefined' && module.exports) {
    module.exports = VMModule;
} else {
    window.VMModule = VMModule;
}
