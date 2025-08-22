/**
 * Модуль для работы с EPSS
 */
class EPSSModule {
    constructor(app) {
        this.app = app;
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.updateStatus();
    }

    setupEventListeners() {
        // Загрузка CSV
        const epssForm = document.getElementById('epss-upload-form');
        if (epssForm) {
            epssForm.addEventListener('submit', async (e) => {
                e.preventDefault();
                await this.uploadEPSS();
            });
        }
        
        // Кнопка скачивания с сайта
        const epssDownloadBtn = document.getElementById('epss-download-btn');
        if (epssDownloadBtn) {
            epssDownloadBtn.addEventListener('click', async () => {
                await this.downloadEPSS();
            });
        }
    }

    async updateStatus() {
        try {
            const data = await this.app.api.getEPSSStatus();
            
            if (data.success) {
                const statusDiv = document.getElementById('epss-status');
                if (statusDiv) {
                    statusDiv.innerHTML = `
                        <div style="margin-bottom: 15px;">
                            <b>Записей в базе EPSS:</b> ${data.count}
                        </div>
                        
                        <!-- Подсказка с ссылками для EPSS -->
                        <div style="background-color: #f8f9fa; border: 1px solid #dee2e6; border-radius: 8px; padding: 12px; font-size: 0.875rem;">
                            <h4 style="margin: 0 0 8px 0; font-size: 0.9rem; font-weight: 600; color: #1e293b;">📋 Ссылки для скачивания EPSS</h4>
                            <p style="margin: 0 0 8px 0; line-height: 1.4;">Для offline загрузки используйте следующие ссылки:</p>
                            <div style="display: flex; flex-direction: column; gap: 6px;">
                                <a href="https://epss.empiricalsecurity.com/epss_scores-current.csv.gz" target="_blank" style="display: flex; align-items: center; gap: 6px; color: #2563eb; text-decoration: none; font-size: 0.8rem; padding: 4px 8px; border-radius: 4px;">
                                    🔗 <span style="flex: 1;">EPSS Scores (текущая версия)</span>
                                    <span style="font-size: 0.7rem; color: #64748b; font-style: italic;">~2MB</span>
                                </a>
                                <a href="https://epss.empiricalsecurity.com/" target="_blank" style="display: flex; align-items: center; gap: 6px; color: #2563eb; text-decoration: none; font-size: 0.8rem; padding: 4px 8px; border-radius: 4px;">
                                    🔗 <span style="flex: 1;">EPSS Scores (официальный сайт)</span>
                                    <span style="font-size: 0.7rem; color: #64748b; font-style: italic;">~2MB (gz)</span>
                                </a>
                                <a href="https://epss.cyentia.com/" target="_blank" style="display: flex; align-items: center; gap: 6px; color: #2563eb; text-decoration: none; font-size: 0.8rem; padding: 4px 8px; border-radius: 4px;">
                                    🌐 <span style="flex: 1;">Официальный сайт EPSS</span>
                                </a>
                            </div>
                        </div>
                    `;
                }
            } else {
                const statusDiv = document.getElementById('epss-status');
                if (statusDiv) {
                    statusDiv.innerHTML = '<span style="color:var(--error-color)">Ошибка получения статуса EPSS</span>';
                }
            }
        } catch (err) {
            const statusDiv = document.getElementById('epss-status');
            if (statusDiv) {
                statusDiv.innerHTML = '<span style="color:var(--error-color)">Ошибка получения статуса EPSS</span>';
            }
        }
    }

    async uploadEPSS() {
        const fileInput = document.getElementById('epss-file');
        if (!fileInput.files.length) {
            if (this.app.notifications && this.app.notifications.show) {
                this.app.notifications.show('Выберите файл для загрузки', 'warning');
            }
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
        
        try {
            // Симулируем прогресс загрузки
            this.updateOperationProgress('epss', 'Обработка файла EPSS...', 25, 'Чтение CSV файла...');
            await new Promise(resolve => setTimeout(resolve, 500));
            
            this.updateOperationProgress('epss', 'Загрузка данных в базу...', 50, 'Валидация и подготовка данных...');
            await new Promise(resolve => setTimeout(resolve, 500));
            
            this.updateOperationProgress('epss', 'Сохранение записей...', 75, 'Запись в базу данных...');
            
            const data = await this.app.api.uploadEPSS(fileInput.files[0]);
            
            if (data.success) {
                this.updateOperationProgress('epss', 'Завершение операции...', 90, 'Финальная обработка...');
                await new Promise(resolve => setTimeout(resolve, 300));
                
                this.showOperationComplete('epss', 'EPSS данные успешно загружены', `Загружено записей: ${data.count}`);
                if (this.app.notifications && this.app.notifications.show) {
                    this.app.notifications.show(`Загружено записей: ${data.count}`, 'success');
                }
                this.updateStatus();
                fileInput.value = '';
            } else {
                this.showOperationError('epss', 'Ошибка загрузки EPSS', data.detail || 'Неизвестная ошибка');
                if (this.app.notifications && this.app.notifications.show) {
                    this.app.notifications.show('Ошибка загрузки EPSS', 'error');
                }
            }
        } catch (err) {
            console.error('EPSS upload error:', err);
            this.showOperationError('epss', 'Ошибка загрузки EPSS', err.message);
            if (this.app.notifications && this.app.notifications.show) {
                this.app.notifications.show('Ошибка загрузки EPSS', 'error');
            }
        } finally {
            // Восстанавливаем кнопку
            btnText.textContent = 'Загрузить CSV';
            spinner.style.display = 'none';
            uploadBtn.disabled = false;
        }
    }

    async downloadEPSS() {
        const epssDownloadBtn = document.getElementById('epss-download-btn');
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
            
            const data = await this.app.api.downloadEPSS();
            
            if (data.success) {
                this.updateOperationProgress('epss', 'Завершение операции...', 90, 'Финальная обработка...');
                await new Promise(resolve => setTimeout(resolve, 300));
                
                this.showOperationComplete('epss', 'EPSS данные успешно скачаны', `Загружено записей: ${data.count}`);
                if (this.app.notifications && this.app.notifications.show) {
                    this.app.notifications.show(`Загружено записей: ${data.count}`, 'success');
                }
                this.updateStatus();
            } else {
                this.showOperationError('epss', 'Ошибка скачивания EPSS', data.detail || 'Неизвестная ошибка');
                if (this.app.notifications && this.app.notifications.show) {
                    this.app.notifications.show('Ошибка скачивания EPSS', 'error');
                }
            }
        } catch (err) {
            console.error('EPSS download error:', err);
            this.showOperationError('epss', 'Ошибка скачивания EPSS', err.message);
            if (this.app.notifications && this.app.notifications.show) {
                this.app.notifications.show('Ошибка скачивания EPSS', 'error');
            }
        } finally {
            // Восстанавливаем кнопку
            btnText.textContent = 'Скачать с сайта';
            spinner.style.display = 'none';
            epssDownloadBtn.disabled = false;
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

    updateOperationProgress(operationId, message, progress = null, details = null) {
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

// Экспорт модуля
if (typeof module !== 'undefined' && module.exports) {
    module.exports = EPSSModule;
} else {
    window.EPSSModule = EPSSModule;
}
