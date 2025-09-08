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
        
        // Загружаем настройки с небольшой задержкой, чтобы DOM был готов
        setTimeout(() => {
            this.loadVMSettings();
            this.updateStatus();
        }, 100);
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
            
            // API возвращает данные напрямую, а не в формате {success: true, data: {...}}
            if (data && typeof data === 'object') {
                this.populateVMSettings(data);
            }
        } catch (error) {
            console.error('Ошибка загрузки VM настроек:', error);
        }
    }

    populateVMSettings(settings) {
        console.log('Загружаем VM настройки:', settings);
        
        const vmEnabled = document.getElementById('vm-enabled');
        const vmHost = document.getElementById('vm-host');
        const vmUsername = document.getElementById('vm-username');
        const vmPassword = document.getElementById('vm-password');
        const vmClientSecret = document.getElementById('vm-client-secret');
        const vmOsFilter = document.getElementById('vm-os-filter');
        const vmLimit = document.getElementById('vm-limit');

        console.log('Найденные элементы:', {
            vmEnabled: !!vmEnabled,
            vmHost: !!vmHost,
            vmUsername: !!vmUsername,
            vmPassword: !!vmPassword,
            vmClientSecret: !!vmClientSecret,
            vmOsFilter: !!vmOsFilter,
            vmLimit: !!vmLimit
        });

        if (vmEnabled) vmEnabled.value = settings.vm_enabled || 'false';
        if (vmHost) vmHost.value = settings.vm_host || '';
        if (vmUsername) vmUsername.value = settings.vm_username || '';
        if (vmPassword) vmPassword.value = settings.vm_password || '';
        if (vmClientSecret) vmClientSecret.value = settings.vm_client_secret || '';
        if (vmOsFilter) vmOsFilter.value = settings.vm_os_filter || '';
        if (vmLimit) vmLimit.value = settings.vm_limit || '0';
        
        console.log('VM настройки загружены в форму');
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
                this.showNotification('VM настройки сохранены успешно', 'success');
                this.updateStatus();
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
            const data = await this.app.api.testVMConnection(settings);
            
            // Проверяем структуру ответа
            if (data && typeof data === 'object' && data.success) {
                // Успешное подключение
                const message = data.message || 'Подключение успешно';
                this.showNotification(message, 'success');
            } else {
                // Обработка ошибок
                let errorMsg = 'Неизвестная ошибка';
                if (data && data.error) {
                    errorMsg = data.error;
                } else if (data && data.message) {
                    errorMsg = data.message;
                } else if (!data) {
                    errorMsg = 'Сервер не вернул ответ';
                }
                this.showNotification(`Ошибка подключения: ${errorMsg}`, 'error');
            }
        } catch (error) {
            console.error('VM connection test error:', error);
            this.showNotification(`Ошибка подключения: ${error.message}`, 'error');
        }
    }

    async importVMHosts() {
        const operationId = 'vm-import';
        this.showOperationProgress(operationId, 'Импорт хостов из VM MaxPatrol...');

        try {
            const data = await this.app.api.importVMHosts();
            
            if (data.success) {
                this.showOperationComplete(operationId, 'Импорт запущен успешно', 
                    `Задача импорта создана с ID: ${data.task_id}. Следите за прогрессом в разделе "Фоновые задачи".`);
                this.updateStatus();
                
                // Запускаем мониторинг прогресса
                this.startProgressMonitoring();
            } else {
                this.showOperationError(operationId, 'Ошибка запуска импорта', data.message);
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

    // Вспомогательный метод для показа уведомлений
    showNotification(message, type = 'info') {
        if (this.app.uiManager && this.app.uiManager.showNotification) {
            this.app.uiManager.showNotification(message, type);
        } else if (this.app.showNotification) {
            this.app.showNotification(message, type);
        } else {
            // Fallback - простое уведомление в консоль
            console.log(`[${type.toUpperCase()}] ${message}`);
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

    startProgressMonitoring() {
        // Очищаем предыдущий интервал
        if (this.progressInterval) {
            clearInterval(this.progressInterval);
            this.progressInterval = null;
        }

        // Запускаем мониторинг каждые 2 секунды
        this.progressInterval = setInterval(async () => {
            try {
                const data = await this.app.api.getBackgroundTasksStatus();
                
                // Ищем задачу импорта VM
                const vmTask = data.find(task => task.task_type === 'vm_import');
                
                if (vmTask) {
                    const operationId = 'vm-import';
                    
                    if (vmTask.status === 'completed') {
                        this.showOperationComplete(operationId, 'Импорт завершен успешно', 
                            `Импортировано: ${vmTask.processed_records || 0} хостов`);
                        this.stopProgressMonitoring();
                        this.updateStatus();
                    } else if (vmTask.status === 'error') {
                        this.showOperationError(operationId, 'Ошибка импорта', vmTask.error_message);
                        this.stopProgressMonitoring();
                    } else if (vmTask.status === 'processing' || vmTask.status === 'running') {
                        const progress = vmTask.progress_percent || 0;
                        this.showOperationProgress(operationId, vmTask.current_step || 'Обработка...', progress);
                    }
                }
            } catch (error) {
                console.error('Ошибка мониторинга прогресса VM:', error);
            }
        }, 2000);
    }

    stopProgressMonitoring() {
        if (this.progressInterval) {
            clearInterval(this.progressInterval);
            this.progressInterval = null;
        }
    }
}

// Экспорт модуля
if (typeof module !== 'undefined' && module.exports) {
    module.exports = VMModule;
} else {
    window.VMModule = VMModule;
}
