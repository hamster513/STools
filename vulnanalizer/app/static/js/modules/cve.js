/**
 * Модуль для работы с CVE
 */
class CVEModule {
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
        const cveForm = document.getElementById('cve-upload-form');
        if (cveForm) {
            cveForm.addEventListener('submit', async (e) => {
                e.preventDefault();
                await this.uploadCVE();
            });
        }
        
        // Кнопка скачивания с сайта
        const cveDownloadBtn = document.getElementById('cve-download-btn');
        if (cveDownloadBtn) {
            cveDownloadBtn.addEventListener('click', async () => {
                await this.downloadCVE();
            });
        }

        // Кнопка отмены загрузки CVE
        const cveCancelBtn = document.getElementById('cve-cancel-btn');
        if (cveCancelBtn) {
            cveCancelBtn.addEventListener('click', async () => {
                await this.cancelCVE();
            });
        }

        // Кнопка получения ссылок для скачивания
        const cveUrlsBtn = document.getElementById('cve-urls-btn');
        if (cveUrlsBtn) {
            cveUrlsBtn.addEventListener('click', async () => {
                await this.getDownloadUrls();
            });
        }

        // Кнопка просмотра данных
        const cvePreviewBtn = document.getElementById('cve-preview-btn');
        if (cvePreviewBtn) {
            cvePreviewBtn.addEventListener('click', () => {
                this.showCVEPreview();
            });
        }
    }

    async updateStatus() {
        try {
            const data = await this.app.api.getCVEStatus();
            
            if (data.success) {
                const statusDiv = document.getElementById('cve-status');
                if (statusDiv) {
                    statusDiv.innerHTML = `
                        <div style="margin-bottom: 15px;">
                            <b>Записей в базе CVE:</b> ${data.count}
                        </div>
                        
                        <!-- Подсказка с ссылками для CVE -->
                        <div style="background-color: #f8f9fa; border: 1px solid #dee2e6; border-radius: 8px; padding: 12px; font-size: 0.875rem;">
                            <h4 style="margin: 0 0 8px 0; font-size: 0.9rem; font-weight: 600; color: #1e293b;">📋 Ссылки для скачивания CVE</h4>
                            <p style="margin: 0 0 8px 0; line-height: 1.4;">Для offline загрузки используйте следующие ссылки:</p>
                            <div style="display: flex; flex-direction: column; gap: 6px;">
                                <a href="https://nvd.nist.gov/feeds/json/cve/1.1/" target="_blank" style="display: flex; align-items: center; gap: 6px; color: #2563eb; text-decoration: none; font-size: 0.8rem; padding: 4px 8px; border-radius: 4px;">
                                    🔗 <span style="flex: 1;">NVD CVE Feeds (официальный сайт)</span>
                                    <span style="font-size: 0.7rem; color: #64748b; font-style: italic;">JSON/GZ</span>
                                </a>
                                <a href="https://nvd.nist.gov/vuln/data-feeds" target="_blank" style="display: flex; align-items: center; gap: 6px; color: #2563eb; text-decoration: none; font-size: 0.8rem; padding: 4px 8px; border-radius: 4px;">
                                    🌐 <span style="flex: 1;">NVD Data Feeds (документация)</span>
                                </a>
                            </div>
                        </div>
                    `;
                }
            } else {
                const statusDiv = document.getElementById('cve-status');
                if (statusDiv) {
                    statusDiv.innerHTML = '<span style="color:var(--error-color)">Ошибка получения статуса CVE</span>';
                }
            }
        } catch (err) {
            const statusDiv = document.getElementById('cve-status');
            if (statusDiv) {
                statusDiv.innerHTML = '<span style="color:var(--error-color)">Ошибка получения статуса CVE</span>';
            }
        }
    }

    async uploadCVE() {
        const fileInput = document.getElementById('cve-file');
        if (!fileInput.files.length) {
            this.app.notifications.show('Выберите файл для загрузки', 'warning');
            return;
        }
        
        const uploadBtn = document.getElementById('cve-upload-btn');
        const btnText = uploadBtn.querySelector('.btn-text');
        const spinner = uploadBtn.querySelector('.fa-spinner');
        
        // Показываем индикатор загрузки
        btnText.textContent = 'Загрузка...';
        spinner.style.display = 'inline-block';
        uploadBtn.disabled = true;
        
        // Показываем прогресс в статусбаре
        this.showOperationProgress('cve', 'Загрузка файла CVE...', 0);
        
        try {
            // Симулируем прогресс загрузки
            this.updateOperationProgress('cve', 'Обработка файла CVE...', 25, 'Чтение CSV файла...');
            await new Promise(resolve => setTimeout(resolve, 500));
            
            this.updateOperationProgress('cve', 'Загрузка данных в базу...', 50, 'Валидация и подготовка данных...');
            await new Promise(resolve => setTimeout(resolve, 500));
            
            this.updateOperationProgress('cve', 'Сохранение записей...', 75, 'Запись в базу данных...');
            
            const data = await this.app.api.uploadCVE(fileInput.files[0]);
            
            if (data.success) {
                this.updateOperationProgress('cve', 'Завершение операции...', 90, 'Финальная обработка...');
                await new Promise(resolve => setTimeout(resolve, 300));
                
                this.showOperationComplete('cve', 'CVE данные успешно загружены', `Загружено записей: ${data.count}`);
                this.app.notifications.show(`Загружено записей: ${data.count}`, 'success');
                this.updateStatus();
                fileInput.value = '';
            } else {
                this.showOperationError('cve', 'Ошибка загрузки CVE', data.detail || 'Неизвестная ошибка');
                this.app.notifications.show('Ошибка загрузки CVE', 'error');
            }
        } catch (err) {
            console.error('CVE upload error:', err);
            this.showOperationError('cve', 'Ошибка загрузки CVE', err.message);
            this.app.notifications.show('Ошибка загрузки CVE', 'error');
        } finally {
            // Восстанавливаем кнопку
            btnText.textContent = 'Загрузить CSV';
            spinner.style.display = 'none';
            uploadBtn.disabled = false;
        }
    }

    async downloadCVE() {
        const cveDownloadBtn = document.getElementById('cve-download-btn');
        const btnText = cveDownloadBtn.querySelector('.btn-text');
        const spinner = cveDownloadBtn.querySelector('.fa-spinner');
        
        // Показываем индикатор загрузки
        btnText.textContent = 'Скачивание...';
        spinner.style.display = 'inline-block';
        cveDownloadBtn.disabled = true;
        
        // Показываем кнопку отмены
        const cveCancelBtn = document.getElementById('cve-cancel-btn');
        if (cveCancelBtn) {
            cveCancelBtn.style.display = 'inline-block';
        }
        
        // Показываем прогресс в статусбаре
        this.showOperationProgress('cve', 'Подключение к серверу CVE...', 0);
        
        try {
            this.updateOperationProgress('cve', 'Скачивание файла...', 25, 'Загрузка с empiricalsecurity.com...');
            await new Promise(resolve => setTimeout(resolve, 800));
            
            this.updateOperationProgress('cve', 'Обработка данных...', 50, 'Распаковка и парсинг CSV...');
            await new Promise(resolve => setTimeout(resolve, 1000));
            
            this.updateOperationProgress('cve', 'Сохранение в базу...', 75, 'Запись CVE данных...');
            
            const data = await this.app.api.downloadCVE();
            
            if (data.success) {
                this.updateOperationProgress('cve', 'Завершение операции...', 90, 'Финальная обработка...');
                await new Promise(resolve => setTimeout(resolve, 300));
                
                this.showOperationComplete('cve', 'CVE данные успешно скачаны', `Загружено записей: ${data.count}`);
                this.app.notifications.show(`Загружено записей: ${data.count}`, 'success');
                this.updateStatus();
            } else {
                this.showOperationError('cve', 'Ошибка скачивания CVE', data.detail || 'Неизвестная ошибка');
                this.app.notifications.show('Ошибка скачивания CVE', 'error');
            }
        } catch (err) {
            console.error('CVE download error:', err);
            this.showOperationError('cve', 'Ошибка скачивания CVE', err.message);
            this.app.notifications.show('Ошибка скачивания CVE', 'error');
        } finally {
            // Восстанавливаем кнопку
            btnText.textContent = 'Скачать с NVD';
            spinner.style.display = 'none';
            cveDownloadBtn.disabled = false;
            
            // Скрываем кнопку отмены
            const cveCancelBtn = document.getElementById('cve-cancel-btn');
            if (cveCancelBtn) {
                cveCancelBtn.style.display = 'none';
            }
        }
    }

    async cancelCVE() {
        const cveCancelBtn = document.getElementById('cve-cancel-btn');
        const btnText = cveCancelBtn.querySelector('.btn-text');
        const spinner = cveCancelBtn.querySelector('.fa-spinner');
        
        // Показываем индикатор
        btnText.textContent = 'Отмена...';
        spinner.style.display = 'inline-block';
        cveCancelBtn.disabled = true;
        
        try {
            const data = await this.app.api.cancelCVE();
            
            if (data.success) {
                this.app.notifications.show('Загрузка CVE отменена', 'success');
                // Скрываем кнопку отмены
                cveCancelBtn.style.display = 'none';
                // Показываем кнопку скачивания
                const cveDownloadBtn = document.getElementById('cve-download-btn');
                if (cveDownloadBtn) {
                    cveDownloadBtn.disabled = false;
                }
            } else {
                this.app.notifications.show(data.message || 'Ошибка отмены загрузки', 'warning');
            }
        } catch (err) {
            console.error('CVE cancel error:', err);
            this.app.notifications.show('Ошибка отмены загрузки CVE', 'error');
        } finally {
            // Восстанавливаем кнопку
            btnText.textContent = 'Остановить загрузку';
            spinner.style.display = 'none';
            cveCancelBtn.disabled = false;
        }
    }

    async getDownloadUrls() {
        try {
            const data = await this.app.api.getCVEDownloadUrls();
            
            if (data.success) {
                let urlsHtml = '<div style="background-color: #f8f9fa; border: 1px solid #dee2e6; border-radius: 8px; padding: 12px; margin-top: 10px;">';
                urlsHtml += '<h4 style="margin: 0 0 8px 0; font-size: 0.9rem; font-weight: 600; color: #1e293b;">📋 Ссылки для скачивания CVE по годам</h4>';
                urlsHtml += '<p style="margin: 0 0 8px 0; line-height: 1.4; font-size: 0.8rem;">Скачайте файлы по ссылкам ниже для offline загрузки:</p>';
                
                data.urls.forEach(urlInfo => {
                    urlsHtml += `<div style="margin-bottom: 6px;">`;
                    urlsHtml += `<a href="${urlInfo.url}" target="_blank" style="display: flex; align-items: center; gap: 6px; color: #2563eb; text-decoration: none; font-size: 0.8rem; padding: 4px 8px; border-radius: 4px;">`;
                    urlsHtml += `🔗 <span style="flex: 1;">CVE ${urlInfo.year} (${urlInfo.filename})</span>`;
                    urlsHtml += `</a>`;
                    urlsHtml += `</div>`;
                });
                
                urlsHtml += '</div>';
                
                const statusDiv = document.getElementById('cve-status');
                if (statusDiv) {
                    statusDiv.innerHTML = urlsHtml;
                }
            } else {
                this.app.notifications.show('Ошибка получения ссылок CVE', 'error');
            }
        } catch (err) {
            console.error('CVE URLs error:', err);
            this.app.notifications.show('Ошибка получения ссылок CVE', 'error');
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

    showCVEPreview() {
        // Показываем модальное окно через основной класс приложения
        if (this.app.cvePreviewModal) {
            this.app.cvePreviewModal.show();
        } else {
            console.error('CVEPreviewModal not found in app');
        }
    }
}

// Экспорт модуля
if (typeof module !== 'undefined' && module.exports) {
    module.exports = CVEModule;
} else {
    window.CVEModule = CVEModule;
}
