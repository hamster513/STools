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

    // Обновление количества записей в базе
    async updateRecordsCount() {
        try {
            const data = await this.api.get('/hosts/status');
            
            // Обновляем UI количества записей
            this.updateRecordsCountUI(data);
            
            return data;
        } catch (error) {
            this.app.handleError(error, 'обновления количества записей');
            throw error;
        }
    }

    // Обновление UI статуса хостов
    updateHostsStatusUI(data) {
        const statusDiv = this.app.getElementSafe('hosts-status');
        
        if (statusDiv) {
            if (data && data.count !== undefined) {
                statusDiv.innerHTML = '';
            } else {
                statusDiv.innerHTML = '<span style="color:var(--error-color)">Ошибка получения статуса хостов</span>';
            }
        }
    }

    // Обновление UI количества записей
    updateRecordsCountUI(data) {
        const recordsCountElement = this.app.getElementSafe('records-count-value');
        if (recordsCountElement && data.total_count !== undefined) {
            recordsCountElement.textContent = data.total_count.toLocaleString();
        }
    }

    // Импорт хостов с фильтрами
    async importHosts(file, onProgress = null) {
        try {
            if (!file) {
                this.app.showNotification('Выберите файл для загрузки', 'warning');
                return;
            }

            // Получаем фильтры из формы
            const criticalitySelect = document.getElementById('import-criticality-filter');
            const selectedCriticalities = Array.from(criticalitySelect?.selectedOptions || [])
                .map(option => option.value);
            const criticalityFilter = selectedCriticalities.length > 0 ? selectedCriticalities.join(',') : '';
            const osFilter = document.getElementById('import-os-filter')?.value || '';
            

            // Создаем FormData с файлом и фильтрами
            const formData = new FormData();
            formData.append('file', file);
            if (criticalityFilter) {
                formData.append('criticality_filter', criticalityFilter);
            }
            if (osFilter) {
                formData.append('os_filter', osFilter);
            }

            const data = await this.api.uploadFileWithFilters('/hosts/upload', formData, onProgress);
            
            if (data && data.success) {
                const filterInfo = [];
                if (criticalityFilter) filterInfo.push(`критичность: ${criticalityFilter}`);
                if (osFilter) filterInfo.push(`ОС: ${osFilter}`);
                
                const filterText = filterInfo.length > 0 ? ` (фильтры: ${filterInfo.join(', ')})` : '';
                this.app.showNotification(`Импорт завершен: ${data.processed_records || 0} записей${filterText}`, 'success');
                this.updateHostsStatus();
                this.updateRecordsCount(); // Обновляем количество записей в базе
                
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
                        this.updateRecordsCount(); // Обновляем количество записей в базе
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
            console.log('🗑️ Начинаем очистку данных хостов...');
            const data = await this.api.post('/hosts/clear');
            
            if (data && data.success) {
                const message = data.deleted_count 
                    ? `Удалено ${data.deleted_count} записей хостов`
                    : 'Данные хостов очищены';
                this.app.showNotification(message, 'success');
                this.updateHostsStatus();
            } else {
                const errorMsg = data?.message || data?.error || 'Неизвестная ошибка';
                this.app.showNotification(`Ошибка очистки: ${errorMsg}`, 'error');
                console.error('❌ Ошибка очистки:', data);
            }
        } catch (error) {
            console.error('❌ Ошибка при очистке хостов:', error);
            this.app.handleError(error, 'очистки данных хостов');
            throw error;
        }
    }

    // Проверка статуса файла VM
    async checkVMFileStatus() {
        try {
            const data = await this.api.get('/vm/file-status');
            this.updateVMFileStatusUI(data);
        } catch (error) {
            console.error('Ошибка проверки статуса файла VM:', error);
            this.updateVMFileStatusUI({ success: false, message: 'Ошибка проверки файла' });
        }
    }

    // Обновление UI статуса файла VM
    updateVMFileStatusUI(data) {
        const fileInfoElement = this.app.getElementSafe('vm-file-info');
        const manualImportBtn = this.app.getElementSafe('vm-manual-import-btn');
        
        if (fileInfoElement) {
            if (data && data.success && data.file_exists) {
                fileInfoElement.innerHTML = `
                    <strong>Файл найден:</strong> ${data.filename}<br>
                    <small>Размер: ${data.file_size_mb?.toFixed(2) || 'неизвестно'} МБ | Создан: ${data.created_at || 'неизвестно'}</small>
                `;
                if (manualImportBtn) {
                    manualImportBtn.style.display = 'inline-block';
                }
            } else {
                fileInfoElement.innerHTML = '<span style="color: var(--warning-color)">Файл не найден</span>';
                if (manualImportBtn) {
                    manualImportBtn.style.display = 'none';
                }
            }
        }
    }

    // Ручной импорт из файла VM
    async startVMManualImport() {
        try {
            // Получаем фильтры из UI
            const criticalitySelect = document.getElementById('import-criticality-filter');
            console.log('🔍 Найден элемент criticalitySelect:', criticalitySelect);
            
            const selectedCriticalities = Array.from(criticalitySelect?.selectedOptions || [])
                .map(option => option.value);
            const criticalityFilter = selectedCriticalities.length > 0 ? selectedCriticalities.join(',') : '';
            
            const osFilterElement = document.getElementById('import-os-filter');
            console.log('🔍 Найден элемент osFilterElement:', osFilterElement);
            const osFilter = osFilterElement?.value || '';
            
            const zoneFilterElement = document.getElementById('import-zone-filter');
            console.log('🔍 Найден элемент zoneFilterElement:', zoneFilterElement);
            const zoneFilter = zoneFilterElement?.value || '';
            
            console.log('🔍 Фильтры для ручного импорта:', { 
                criticalityFilter, 
                osFilter, 
                zoneFilter,
                selectedCriticalities,
                criticalitySelectExists: !!criticalitySelect,
                osFilterElementExists: !!osFilterElement,
                zoneFilterElementExists: !!zoneFilterElement
            });
            
            // Создаем объект с фильтрами для отправки
            const requestData = {};
            if (criticalityFilter) {
                requestData.criticality_filter = criticalityFilter;
            }
            if (osFilter) {
                requestData.os_filter = osFilter;
            }
            if (zoneFilter) {
                requestData.zone_filter = zoneFilter;
            }
            
            console.log('🔍 Отправляем данные:', requestData);
            
            const data = await this.api.post('/vm/manual-import', requestData);
            
            if (data && data.success) {
                this.app.showNotification('Ручной импорт из файла VM запущен', 'success');
                this.checkVMFileStatus(); // Обновляем статус файла
            } else {
                this.app.showNotification(`Ошибка запуска импорта: ${data.message || 'Неизвестная ошибка'}`, 'error');
            }
        } catch (error) {
            this.app.handleError(error, 'запуска ручного импорта VM');
        }
    }
}

// Экспорт для использования в других модулях
if (typeof module !== 'undefined' && module.exports) {
    module.exports = HostsService;
} else {
    window.HostsService = HostsService;
}
