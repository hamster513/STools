/**
 * MetasploitService - Сервис для работы с Metasploit
 * v=7.1
 */
class MetasploitService {
    constructor(app) {
        this.app = app;
        this.api = app.api;
        this.storage = app.storage;
        this.eventManager = app.eventManager;
    }

    // Обновление статуса Metasploit
    async updateMetasploitStatus() {
        try {
            const resp = await fetch(this.app.getApiBasePath() + '/metasploit/status');
            const data = await resp.json();
            
            const statusDiv = this.app.getElementSafe('metasploit-status');
            if (statusDiv) {
                if (data && data.count !== undefined) {
                    statusDiv.innerHTML = `
                        <div class="status-success">
                            <i class="fas fa-check-circle"></i>
                            <span class="status-message">Metasploit в базе: ${data.count}</span>
                        </div>
                    `;
                } else {
                    statusDiv.innerHTML = '<span style="color:var(--error-color)">Ошибка получения статуса Metasploit</span>';
                }
            }
        } catch (err) {
            this.app.handleError(err, 'обновления статуса Metasploit');
        }
    }

    // Загрузка Metasploit
    async uploadMetasploit(file) {
        try {
            if (!file) {
                this.app.showNotification('Выберите файл для загрузки', 'warning');
                return;
            }

            // Показываем прогресс
            this.app.showOperationProgress('metasploit', 'Загрузка Metasploit...');

            // Задержки для UI
            await this.app.delay(VulnAnalizer.DELAYS.MEDIUM);
            await this.app.delay(VulnAnalizer.DELAYS.LONG);

            const data = await this.api.uploadFile('/metasploit/upload', file);
            
            if (data && data.success) {
                this.app.showNotification(`Загружено записей: ${data.count}`, 'success');
                this.updateMetasploitStatus();
                
                // Эмитируем событие
                if (this.eventManager) {
                    this.eventManager.emitDataUpdate({ type: 'metasploit_upload', count: data.count });
                }
            } else {
                this.app.showOperationError('metasploit', 'Ошибка загрузки Metasploit', data.detail || 'Неизвестная ошибка');
                this.app.showNotification('Ошибка загрузки Metasploit', 'error');
            }

            return data;
        } catch (err) {
            this.app.showOperationError('metasploit', 'Ошибка загрузки Metasploit', err.message);
            this.app.showNotification('Ошибка загрузки Metasploit', 'error');
            throw err;
        }
    }

    // Настройка Metasploit
    setupMetasploit() {
        const metasploitForm = this.app.getElementSafe('metasploit-upload-form');
        if (!metasploitForm) return;

        metasploitForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const fileInput = metasploitForm.querySelector('input[type="file"]');
            const file = fileInput.files[0];
            
            if (file) {
                await this.uploadMetasploit(file);
            }
        });
    }

    // Очистка данных Metasploit
    async clearMetasploitData() {
        try {
            const data = await this.api.post('/metasploit/clear');
            
            if (data && data.success) {
                this.app.showNotification('Данные Metasploit очищены', 'success');
                this.updateMetasploitStatus();
            } else {
                this.app.showNotification(`Ошибка очистки: ${data.error}`, 'error');
            }
        } catch (error) {
            this.app.handleError(error, 'очистки данных Metasploit');
            throw error;
        }
    }

    // Поиск эксплойтов Metasploit
    async searchMetasploit(query, filters = {}) {
        try {
            const params = {
                query,
                ...filters
            };

            const data = await this.api.get('/metasploit/search', params);
            
            // Эмитируем событие поиска
            if (this.eventManager) {
                this.eventManager.emitDataUpdate({ type: 'metasploit_search', results: data.results });
            }

            return data;
        } catch (error) {
            this.app.handleError(error, 'поиска Metasploit');
            throw error;
        }
    }

    // Получение детальной информации об эксплойте
    async getMetasploitDetails(exploitId) {
        try {
            const data = await this.api.get(`/metasploit/${exploitId}`);
            return data;
        } catch (error) {
            this.app.handleError(error, 'получения деталей Metasploit');
            throw error;
        }
    }
}

// Экспорт для использования в других модулях
if (typeof module !== 'undefined' && module.exports) {
    module.exports = MetasploitService;
} else {
    window.MetasploitService = MetasploitService;
}
