/**
 * CVEService - Сервис для работы с CVE
 * v=7.2
 */
class CVEService {
    constructor(app) {
        this.app = app;
        this.api = app.api;
        this.storage = app.storage;
        this.eventManager = app.eventManager;
    }

    // Обновление статуса CVE
    async updateCVEStatus() {
        try {
            const data = await this.api.get('/cve/status');
            this.updateCVEStatusUI(data);
            return data;
        } catch (error) {
            this.app.handleError(error, 'обновления статуса CVE');
            throw error;
        }
    }

    // Обновление UI статуса CVE
    updateCVEStatusUI(data) {
        const statusDiv = this.app.getElementSafe('cve-status');
        if (!statusDiv) return;

        if (data && data.count !== undefined) {
            statusDiv.innerHTML = `
                <div class="status-success">
                    <i class="fas fa-check-circle"></i>
                    <span class="status-message">CVE в базе: ${data.count}</span>
                </div>
            `;
        } else {
            statusDiv.innerHTML = '<span style="color:var(--error-color)">Ошибка получения статуса CVE</span>';
        }
    }

    // Загрузка CVE
    async uploadCVE(file) {
        try {
            if (!file) {
                this.app.showNotification('Выберите файл для загрузки', 'warning');
                return;
            }

            // Показываем прогресс
            this.app.showOperationProgress('cve', 'Загрузка CVE...');

            // Задержка для UI
            await this.app.delay(VulnAnalizer.DELAYS.MEDIUM);
            await this.app.delay(VulnAnalizer.DELAYS.MEDIUM);

            const data = await this.api.uploadFile('/cve/upload', file);
            
            if (data && data.success) {
                this.app.showNotification(`Загружено записей: ${data.count}`, 'success');
                this.updateCVEStatus();
                
                // Эмитируем событие
                if (this.eventManager) {
                    this.eventManager.emitDataUpdate({ type: 'cve_upload', count: data.count });
                }
            } else {
                this.app.showOperationError('cve', 'Ошибка загрузки CVE', data.detail || 'Неизвестная ошибка');
                this.app.showNotification('Ошибка загрузки CVE', 'error');
            }

            return data;
        } catch (error) {
            this.app.showOperationError('cve', 'Ошибка загрузки CVE', error.message);
            this.app.showNotification('Ошибка загрузки CVE', 'error');
            throw error;
        }
    }

    // Получение ссылок для загрузки CVE
    async getCVEDownloadUrls() {
        try {
            const data = await this.api.get('/cve/download-urls');
            
            if (data && data.urls) {
                return data.urls;
            } else {
                return [];
            }
        } catch (error) {
            console.error('Ошибка получения ссылок CVE:', error);
            throw error;
        }
    }

    // Отмена загрузки CVE
    async cancelCVEUpload() {
        try {
            const data = await this.api.post('/cve/cancel');
            
            if (data && data.success) {
                this.app.showNotification('Загрузка CVE отменена', 'info');
            } else {
                this.app.showNotification(data.message || 'Ошибка отмены загрузки', 'warning');
            }
        } catch (error) {
            this.app.handleError(error, 'отмены загрузки CVE');
            throw error;
        }
    }

    // Поиск CVE
    async searchCVE(query, filters = {}) {
        try {
            if (!query || query.trim() === '') {
                throw new Error('CVE ID не указан');
            }

            // Очищаем CVE ID от лишних символов
            const cleanCveId = query.trim().toUpperCase();
            
            const data = await this.api.get(`/cve/search/${cleanCveId}`);
            
            // Отображаем результаты поиска
            this.displayCVEResults(data);
            
            // Эмитируем событие поиска
            if (this.eventManager) {
                this.eventManager.emitDataUpdate({ type: 'cve_search', results: data });
            }

            return data;
        } catch (error) {
            this.app.handleError(error, 'поиска CVE');
            // Отображаем сообщение об ошибке
            this.displayCVENotFound(query);
            throw error;
        }
    }

    // Валидация CVE ID
    validateCVEId(cveId) {
        const cveRegex = /^CVE-\d{4}-\d{4,}$/;
        return cveRegex.test(cveId);
    }

    // Получение детальной информации о CVE
    async getCVEDetails(cveId) {
        try {
            if (!this.validateCVEId(cveId)) {
                throw new Error('Неверный формат CVE ID');
            }

            const data = await this.api.get(`/cve/${cveId}`);
            return data;
        } catch (error) {
            this.app.handleError(error, 'получения деталей CVE');
            throw error;
        }
    }

    // Очистка данных CVE
    async clearCVEData() {
        try {
            const data = await this.api.post('/cve/clear');
            
            if (data && data.success) {
                this.app.showNotification('Данные CVE очищены', 'success');
                this.updateCVEStatus();
            } else {
                this.app.showNotification(`Ошибка очистки: ${data.error}`, 'error');
            }
        } catch (error) {
            this.app.handleError(error, 'очистки данных CVE');
            throw error;
        }
    }

    // Отображение результатов поиска CVE
    displayCVEResults(data) {
        try {
            const cveResults = document.getElementById('cve-results');
            if (!cveResults) {
                console.error('Элемент cve-results не найден');
                return;
            }

            if (!data || !data.success) {
                this.displayCVENotFound();
                return;
            }

            const cve = data.cve;
            const epss = data.epss;
            const risk = data.risk;

            // Формируем HTML для отображения результатов
            const html = `
                <div class="cve-details">
                    <h3>${cve.cve_id}</h3>
                    <div class="cve-info">
                        <div class="cve-description">
                            <h4>Описание:</h4>
                            <p>${cve.description}</p>
                        </div>
                        <div class="cve-metrics">
                            ${cve.cvss_v3_score ? `
                                <div class="metric">
                                    <span class="label">CVSS v3:</span>
                                    <span class="value ${this.getCVSSSeverityClass(cve.cvss_v3_score)}">${cve.cvss_v3_score} (${cve.cvss_v3_severity})</span>
                                </div>
                            ` : ''}
                            ${cve.cvss_v2_score ? `
                                <div class="metric">
                                    <span class="label">CVSS v2:</span>
                                    <span class="value ${this.getCVSSSeverityClass(cve.cvss_v2_score)}">${cve.cvss_v2_score} (${cve.cvss_v2_severity})</span>
                                </div>
                            ` : ''}
                            ${epss ? `
                                <div class="metric">
                                    <span class="label">EPSS:</span>
                                    <span class="value ${epss.epss > 0.7 ? 'high' : epss.epss > 0.3 ? 'medium' : 'low'}">${epss.epss.toFixed(4)} (${(epss.percentile * 100).toFixed(1)}%)</span>
                                </div>
                            ` : ''}
                            ${risk ? `
                                <div class="metric">
                                    <span class="label">Риск:</span>
                                    <span class="value ${this.getRiskSeverityClass(risk.risk_score)}">${risk.risk_score} (${risk.level})</span>
                                </div>
                            ` : ''}
                            <div class="metric">
                                <span class="label">Дата публикации:</span>
                                <span class="value">${cve.published_date}</span>
                            </div>
                            ${cve.last_modified_date ? `
                                <div class="metric">
                                    <span class="label">Последнее изменение:</span>
                                    <span class="value">${cve.last_modified_date}</span>
                                </div>
                            ` : ''}
                        </div>
                    </div>
                </div>
            `;

            cveResults.innerHTML = html;
            cveResults.style.display = 'block';
            
            this.app.showNotification(`CVE ${cve.cve_id} найден`, 'success');
        } catch (error) {
            console.error('Ошибка отображения результатов CVE:', error);
            this.app.showNotification('Ошибка отображения результатов', 'error');
        }
    }

    // Отображение сообщения о том, что CVE не найдена
    displayCVENotFound(cveId = '') {
        try {
            const cveResults = document.getElementById('cve-results');
            if (!cveResults) {
                console.error('Элемент cve-results не найден');
                return;
            }

            const html = `
                <div class="cve-not-found">
                    <h3>CVE не найдена</h3>
                    <p>${cveId ? `CVE ${cveId}` : 'Указанная CVE'} не найдена в базе данных.</p>
                    <p>Проверьте правильность ввода CVE ID или убедитесь, что данные загружены в систему.</p>
                </div>
            `;

            cveResults.innerHTML = html;
            cveResults.style.display = 'block';
            
            this.app.showNotification('CVE не найдена', 'warning');
        } catch (error) {
            console.error('Ошибка отображения сообщения "CVE не найдена":', error);
            this.app.showNotification('Ошибка отображения сообщения', 'error');
        }
    }

    // Получение CSS класса для CVSS
    getCVSSSeverityClass(score) {
        if (score >= 9.0) return 'critical';
        if (score >= 7.0) return 'high';
        if (score >= 4.0) return 'medium';
        return 'low';
    }

    // Получение CSS класса для риска
    getRiskSeverityClass(score) {
        if (score >= 80) return 'critical';
        if (score >= 60) return 'high';
        if (score >= 40) return 'medium';
        return 'low';
    }

    // Настройка CVE
    setupCVE() {
        const cveForm = this.app.getElementSafe('cve-upload-form');
        if (!cveForm) return;

        cveForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const fileInput = cveForm.querySelector('input[type="file"]');
            const file = fileInput.files[0];
            
            if (file) {
                await this.uploadCVE(file);
            }
        });

        // Кнопка отмены
        const cancelBtn = this.app.getElementSafe('cancel-cve-btn');
        if (cancelBtn) {
            cancelBtn.addEventListener('click', () => {
                this.cancelCVEUpload();
            });
        }

        // Обработчик кнопки "Скачать с сайта" убран - используется в cve-manager.js

    }
}

// Экспорт для использования в других модулях
if (typeof module !== 'undefined' && module.exports) {
    module.exports = CVEService;
} else {
    window.CVEService = CVEService;
}
