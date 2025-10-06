/**
 * HostsService - Сервис для работы с хостами
 * v=7.1
 */
class HostsService {
    constructor(app) {
        this.app = app;
        this.api = app.api;
        this.storage = app.storage;
        this.eventManager = app.eventManager;
    }

    // Поиск хостов
    async searchHosts(page = 1, filters = {}) {
        try {
            const params = {
                page,
                limit: this.app.paginationState.limit,
                ...filters
            };

            const data = await this.api.get('/hosts/search', params);
            
            // Обновляем состояние пагинации
            this.app.paginationState = {
                currentPage: data.page || page,
                totalPages: data.total_pages || 1,
                totalCount: data.total_count || 0,
                limit: this.app.paginationState.limit
            };

            // Эмитируем событие обновления данных
            if (this.eventManager) {
                this.eventManager.emitDataUpdate({ hosts: data.hosts, pagination: this.app.paginationState });
            }

            return data;
        } catch (error) {
            this.app.handleError(error, 'поиска хостов');
            throw error;
        }
    }

    // Обновление статуса хостов
    async updateHostsStatus() {
        try {
            const data = await this.api.get('/hosts/status');
            
            // Обновляем UI статуса
            this.updateHostsStatusUI(data);
            
            return data;
        } catch (error) {
            this.app.handleError(error, 'обновления статуса хостов');
            throw error;
        }
    }

    // Обновление UI статуса хостов
    updateHostsStatusUI(data) {
        const statusDiv = this.app.getElementSafe('hosts-status');
        if (!statusDiv) return;

        if (data && data.count !== undefined) {
            statusDiv.innerHTML = `
                <div class="status-success">
                    <i class="fas fa-check-circle"></i>
                    <span class="status-message">Хостов в базе: ${data.count}</span>
                </div>
            `;
        } else {
            statusDiv.innerHTML = '<span style="color:var(--error-color)">Ошибка получения статуса хостов</span>';
        }
    }

    // Импорт хостов
    async importHosts(file, onProgress = null) {
        try {
            if (!file) {
                this.app.showNotification('Выберите файл для загрузки', 'warning');
                return;
            }

            const data = await this.api.uploadFile('/hosts/upload', file, onProgress);
            
            if (data && data.success) {
                this.app.showNotification(`Импорт завершен: ${data.processed_records || 0} записей`, 'success');
                this.updateHostsStatus();
                
                // Эмитируем событие импорта
                if (this.eventManager) {
                    this.eventManager.emitDataUpdate({ type: 'import', records: data.processed_records });
                }
            } else {
                this.app.showNotification('Ошибка импорта: ' + (data.detail || 'Неизвестная ошибка'), 'error');
            }

            return data;
        } catch (error) {
            this.app.handleError(error, 'импорта хостов');
            throw error;
        }
    }

    // Экспорт хостов
    async exportHosts(filters = {}) {
        try {
            const params = new URLSearchParams();
            Object.keys(filters).forEach(key => {
                if (filters[key] !== null && filters[key] !== undefined) {
                    params.append(key, filters[key]);
                }
            });

            const response = await fetch(`${this.api.getApiBasePath()}/hosts/export?${params.toString()}`);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `hosts_export_${new Date().toISOString().split('T')[0]}.csv`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);

            this.app.showNotification('Экспорт завершен', 'success');
        } catch (error) {
            this.app.handleError(error, 'экспорта хостов');
            throw error;
        }
    }

    // Расчет риска хоста
    async calculateHostRisk(hostId) {
        try {
            const response = await this.api.get(`/hosts/${hostId}/risk`);
            
            if (response && response.risk_score !== undefined) {
                return response;
            } else {
                throw new Error('Неверный формат ответа');
            }
        } catch (error) {
            this.app.handleError(error, 'расчета риска хоста');
            throw error;
        }
    }

    // Мониторинг импорта
    startImportMonitoring(taskId) {
        const interval = setInterval(async () => {
            try {
                const task = await this.api.get(`/hosts/import-status/${taskId}`);
                
                if (task.status === 'completed' || task.status === 'error') {
                    clearInterval(interval);
                    
                    if (task.status === 'completed') {
                        this.app.showNotification(`Импорт завершен: ${task.processed_records || 0} записей`, 'success');
                        this.updateHostsStatus();
                    } else {
                        this.app.showNotification(`Ошибка импорта: ${task.error_message || 'Неизвестная ошибка'}`, 'error');
                    }
                    
                    // Скрываем прогресс-бар через 3 секунды
                    this.app.delay(3000).then(() => {
                        this.hideImportProgress();
                    });
                }
            } catch (err) {
                console.error('Ошибка мониторинга импорта:', err);
            }
        }, 2000);

        return interval;
    }

    // Показать прогресс импорта
    showImportProgress() {
        const progressDiv = this.app.getElementSafe('import-progress');
        if (progressDiv) {
            progressDiv.style.display = 'block';
        }
    }

    // Скрыть прогресс импорта
    hideImportProgress() {
        const progressDiv = this.app.getElementSafe('import-progress');
        if (progressDiv) {
            progressDiv.style.display = 'none';
        }
    }

    // Проверка активных задач импорта
    async checkActiveImportTasks() {
        try {
            const response = await this.api.get('/hosts/import-status');
            
            if (response && response.status && response.status !== 'idle' && response.status !== 'completed' && response.status !== 'error' && response.status !== 'cancelled') {
                this.app.showNotification(`Обнаружена активная задача импорта: ${response.current_step}`, 'info');
                this.showImportProgress();
                this.startImportMonitoring(response.task_id);
            }
        } catch (err) {
            console.warn('Ошибка проверки активных задач импорта:', err);
        }
    }

    // Отмена импорта
    async cancelImport() {
        try {
            const data = await this.api.post('/hosts/cancel-import');
            
            if (data && data.success) {
                this.app.showNotification('Импорт отменен', 'info');
                this.hideImportProgress();
            } else {
                this.app.showNotification(data.message || 'Ошибка отмены импорта', 'error');
            }
        } catch (error) {
            this.app.handleError(error, 'отмены импорта');
            throw error;
        }
    }

    // Очистка данных хостов
    async clearHostsData() {
        try {
            const data = await this.api.post('/hosts/clear');
            
            if (data && data.success) {
                this.app.showNotification('Данные хостов очищены', 'success');
                this.updateHostsStatus();
            } else {
                this.app.showNotification(`Ошибка очистки: ${data.error}`, 'error');
            }
        } catch (error) {
            this.app.handleError(error, 'очистки данных хостов');
            throw error;
        }
    }
}

// Экспорт для использования в других модулях
if (typeof module !== 'undefined' && module.exports) {
    module.exports = HostsService;
} else {
    window.HostsService = HostsService;
}
