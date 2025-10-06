/**
 * EPSSService - Сервис для работы с EPSS
 * v=7.1
 */
class EPSSService {
    constructor(app) {
        this.app = app;
        this.api = app.api;
        this.storage = app.storage;
        this.eventManager = app.eventManager;
    }

    // Обновление статуса EPSS
    async updateEPSSStatus() {
        try {
            const resp = await fetch(this.app.getApiBasePath() + '/epss/status');
            const data = await resp.json();
            
            const statusDiv = this.app.getElementSafe('epss-status');
            if (statusDiv) {
                if (data && data.count !== undefined) {
                    statusDiv.innerHTML = `
                        <div class="status-success">
                            <i class="fas fa-check-circle"></i>
                            <span class="status-message">EPSS в базе: ${data.count}</span>
                        </div>
                    `;
                } else {
                    statusDiv.innerHTML = '<span style="color:var(--error-color)">Ошибка получения статуса EPSS</span>';
                }
            }
        } catch (err) {
            this.app.handleError(err, 'обновления статуса EPSS');
        }
    }

    // Загрузка EPSS
    async uploadEPSS(file) {
        try {
            if (!file) {
                this.app.showNotification('Выберите файл для загрузки', 'warning');
                return;
            }

            // Показываем прогресс
            this.app.showOperationProgress('epss', 'Загрузка EPSS...');

            // Задержки для UI
            await this.app.delay(VulnAnalizer.DELAYS.MEDIUM);
            await this.app.delay(VulnAnalizer.DELAYS.MEDIUM);

            const data = await this.api.uploadFile('/epss/upload', file);
            
            if (data && data.success) {
                this.app.showNotification(`Загружено записей: ${data.count}`, 'success');
                this.updateEPSSStatus();
                
                // Эмитируем событие
                if (this.eventManager) {
                    this.eventManager.emitDataUpdate({ type: 'epss_upload', count: data.count });
                }
            } else {
                this.app.showOperationError('epss', 'Ошибка загрузки EPSS', data.detail || 'Неизвестная ошибка');
                this.app.showNotification('Ошибка загрузки EPSS', 'error');
            }

            return data;
        } catch (err) {
            this.app.showOperationError('epss', 'Ошибка загрузки EPSS', err.message);
            this.app.showNotification('Ошибка загрузки EPSS', 'error');
            throw err;
        }
    }

    // Настройка EPSS
    setupEPSS() {
        const epssForm = this.app.getElementSafe('epss-upload-form');
        if (!epssForm) return;

        epssForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const fileInput = epssForm.querySelector('input[type="file"]');
            const file = fileInput.files[0];
            
            if (file) {
                await this.uploadEPSS(file);
            }
        });
    }

    // Очистка данных EPSS
    async clearEPSSData() {
        try {
            const data = await this.api.post('/epss/clear');
            
            if (data && data.success) {
                this.app.showNotification('Данные EPSS очищены', 'success');
                this.updateEPSSStatus();
            } else {
                this.app.showNotification(`Ошибка очистки: ${data.error}`, 'error');
            }
        } catch (error) {
            this.app.handleError(error, 'очистки данных EPSS');
            throw error;
        }
    }
}

// Экспорт для использования в других модулях
if (typeof module !== 'undefined' && module.exports) {
    module.exports = EPSSService;
} else {
    window.EPSSService = EPSSService;
}
