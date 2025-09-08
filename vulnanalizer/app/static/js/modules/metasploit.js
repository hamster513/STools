/**
 * Модуль для работы с Metasploit
 */
class MetasploitModule {
    constructor(app) {
        this.app = app;
        this.apiBasePath = app.getApiBasePath();
        this.init();
    }

    init() {
        this.setupEventListeners();
        // Добавляем небольшую задержку для инициализации
        setTimeout(() => {
            this.updateMetasploitStatus();
        }, 100);
    }

    setupEventListeners() {
        // Загрузка файла
        const uploadForm = document.getElementById('metasploit-upload-form');
        if (uploadForm) {
            uploadForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.uploadMetasploitFile();
            });
        }

        // Скачивание с GitHub
        const downloadBtn = document.getElementById('metasploit-download-btn');
        if (downloadBtn) {
            downloadBtn.addEventListener('click', () => {
                this.downloadMetasploitFromGitHub();
            });
        }


        // Очистка данных
        const clearBtn = document.getElementById('clear-metasploit-btn');
        if (clearBtn) {
            clearBtn.addEventListener('click', () => {
                this.clearMetasploitData();
            });
        }

        // Отмена загрузки
        const cancelBtn = document.getElementById('metasploit-cancel-btn');
        if (cancelBtn) {
            cancelBtn.addEventListener('click', () => {
                this.cancelMetasploitDownload();
            });
        }

        // Просмотр данных
        const previewBtn = document.getElementById('metasploit-preview-btn');
        if (previewBtn) {
            previewBtn.addEventListener('click', () => {
                this.showMetasploitPreview();
            });
        }
    }

    async uploadMetasploitFile() {
        const fileInput = document.getElementById('metasploit-file');
        const uploadBtn = document.getElementById('metasploit-upload-btn');
        const statusDiv = document.getElementById('metasploit-status');

        if (!fileInput.files[0]) {
            this.app.showNotification('Выберите файл для загрузки', 'warning');
            return;
        }

        const file = fileInput.files[0];
        if (!file.name.endsWith('.json')) {
            this.app.showNotification('Поддерживаются только JSON файлы', 'error');
            return;
        }

        // Показываем спиннер
        this.setButtonLoading(uploadBtn, true);
        this.showStatus(statusDiv, 'Загрузка файла...', 'info');

        try {
            const formData = new FormData();
            formData.append('file', file);

            const response = await fetch(`${this.apiBasePath}/metasploit/upload`, {
                method: 'POST',
                body: formData
            });

            const result = await response.json();

            if (response.ok && result.success) {
                this.showStatus(statusDiv, 
                    `✅ Успешно загружено ${result.count} модулей Metasploit`, 
                    'success'
                );
                this.app.showNotification(
                    `Загружено ${result.count} модулей Metasploit`, 
                    'success'
                );
                this.updateMetasploitStatus();
            } else {
                throw new Error(result.detail || result.error || 'Ошибка загрузки');
            }

        } catch (error) {
            this.showStatus(statusDiv, 
                `❌ Ошибка загрузки: ${error.message}`, 
                'error'
            );
            this.app.showNotification('Ошибка загрузки файла Metasploit', 'error');
        } finally {
            this.setButtonLoading(uploadBtn, false);
        }
    }

    async downloadMetasploitFromGitHub() {
        const downloadBtn = document.getElementById('metasploit-download-btn');
        const statusDiv = document.getElementById('metasploit-status');

        // Показываем спиннер
        this.setButtonLoading(downloadBtn, true);
        this.showStatus(statusDiv, 'Запуск фоновой загрузки...', 'info');

        try {
            const response = await fetch(`${this.apiBasePath}/metasploit/download`, {
                method: 'POST'
            });

            const result = await response.json();

            if (response.ok && result.success) {
                this.showStatus(statusDiv, 
                    `✅ Загрузка Metasploit запущена в фоновом режиме`, 
                    'success'
                );
                this.app.showNotification(
                    `Загрузка Metasploit запущена (Task ID: ${result.task_id})`, 
                    'success'
                );
                
                // Показываем кнопку отмены
                this.showCancelButton();
                
                // Начинаем мониторинг прогресса
                this.startProgressMonitoring();
            } else {
                throw new Error(result.detail || 'Ошибка запуска загрузки');
            }

        } catch (error) {
            this.showStatus(statusDiv, 
                `❌ Ошибка запуска загрузки: ${error.message}`, 
                'error'
            );
            this.app.showNotification('Ошибка запуска загрузки Metasploit', 'error');
        } finally {
            this.setButtonLoading(downloadBtn, false);
        }
    }

    showCancelButton() {
        const cancelBtn = document.getElementById('metasploit-cancel-btn');
        if (cancelBtn) {
            cancelBtn.style.display = 'inline-block';
        }
        
        const downloadBtn = document.getElementById('metasploit-download-btn');
        if (downloadBtn) {
            downloadBtn.disabled = true;
        }
    }

    hideCancelButton() {
        const cancelBtn = document.getElementById('metasploit-cancel-btn');
        if (cancelBtn) {
            cancelBtn.style.display = 'none';
        }
        
        const downloadBtn = document.getElementById('metasploit-download-btn');
        if (downloadBtn) {
            downloadBtn.disabled = false;
        }
    }

    async startProgressMonitoring() {
        const statusDiv = document.getElementById('metasploit-status');
        
        // Проверяем, что элемент существует
        if (!statusDiv) {
            return;
        }
        
        const checkProgress = async () => {
            try {
                const response = await fetch(`${this.apiBasePath}/metasploit/status`);
                
                // Проверяем статус ответа
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }
                
                const result = await response.json();
                
                if (result.success) {
                    if (result.is_downloading && result.task_details) {
                        const task = result.task_details;
                        const progress = task.progress_percent || 0;
                        const step = task.current_step || 'Обработка...';
                        const details = task.details || '';
                        
                        this.showStatus(statusDiv, 
                            `🔄 ${step} (${progress}%)<br><small>${details}</small>`, 
                            'info'
                        );
                        
                        // Продолжаем мониторинг
                        setTimeout(checkProgress, 2000);
                    } else {
                        // Загрузка завершена
                        this.showStatus(statusDiv, 
                            `✅ Загрузка Metasploit завершена. Записей в базе: ${result.count}`, 
                            'success'
                        );
                        this.hideCancelButton();
                        this.updateMetasploitStatus();
                    }
                }
            } catch (error) {
                this.showStatus(statusDiv, 
                    `❌ Ошибка мониторинга прогресса: ${error.message}`, 
                    'error'
                );
                this.hideCancelButton();
            }
        };
        
        // Запускаем мониторинг
        setTimeout(checkProgress, 1000);
    }


    async cancelMetasploitDownload() {
        const cancelBtn = document.getElementById('metasploit-cancel-btn');
        const statusDiv = document.getElementById('metasploit-status');

        // Показываем спиннер
        this.setButtonLoading(cancelBtn, true);
        this.showStatus(statusDiv, 'Отмена загрузки...', 'info');

        try {
            const response = await fetch(`${this.apiBasePath}/metasploit/cancel`, {
                method: 'POST'
            });

            const result = await response.json();

            if (response.ok && result.success) {
                this.showStatus(statusDiv, 
                    `✅ Загрузка Metasploit отменена`, 
                    'success'
                );
                this.app.showNotification('Загрузка Metasploit отменена', 'success');
                this.hideCancelButton();
            } else {
                throw new Error(result.message || 'Ошибка отмены');
            }

        } catch (error) {
            this.showStatus(statusDiv, 
                `❌ Ошибка отмены: ${error.message}`, 
                'error'
            );
            this.app.showNotification('Ошибка отмены загрузки Metasploit', 'error');
        } finally {
            this.setButtonLoading(cancelBtn, false);
        }
    }

    async clearMetasploitData() {
        if (!confirm('Вы уверены, что хотите удалить все данные Metasploit?')) {
            return;
        }

        try {
            const response = await fetch(`${this.apiBasePath}/metasploit/clear`, {
                method: 'DELETE'
            });

            const result = await response.json();

            if (response.ok && result.success) {
                this.app.showNotification('Данные Metasploit успешно очищены', 'success');
                this.updateMetasploitStatus();
            } else {
                throw new Error(result.detail || 'Ошибка очистки');
            }

        } catch (error) {
            this.app.showNotification('Ошибка очистки данных Metasploit', 'error');
        }
    }

    showMetasploitPreview() {
        // Показываем модальное окно через основной класс приложения
        if (this.app.metasploitModal) {
            this.app.metasploitModal.show();
        } else {
        }
    }

    async updateMetasploitStatus() {
        const statusDiv = document.getElementById('metasploit-status');
        
        // Проверяем, что элемент существует
        if (!statusDiv) {
            return;
        }
        
        try {
            const response = await fetch(`${this.apiBasePath}/metasploit/status`);
            
            // Проверяем статус ответа
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const result = await response.json();

            if (result.success) {
                let statusHtml = '<div class="status-info">';
                
                // Показываем количество записей
                statusHtml += `
                    <div class="status-item">
                        <i class="fas fa-database"></i>
                        <span>Записей в базе: <strong>${result.count}</strong></span>
                    </div>
                `;
                
                // Показываем статус загрузки
                if (result.is_downloading) {
                    statusHtml += `
                        <div class="status-item">
                            <i class="fas fa-spinner fa-spin text-primary"></i>
                            <span>Идет загрузка...</span>
                        </div>
                    `;
                    
                    // Показываем детали задачи
                    if (result.task_details) {
                        const task = result.task_details;
                        const progress = task.progress_percent || 0;
                        const step = task.current_step || 'Обработка...';
                        const details = task.details || '';
                        
                        statusHtml += `
                            <div class="status-item">
                                <div class="progress-info">
                                    <div class="progress-step">${step}</div>
                                    <div class="progress-bar">
                                        <div class="progress-fill" style="width: ${progress}%"></div>
                                    </div>
                                    <div class="progress-text">${progress}%</div>
                                </div>
                                <div class="progress-details">${details}</div>
                            </div>
                        `;
                    }
                } else {
                    // Проверяем, есть ли данные
                    if (result.count > 0) {
                        statusHtml += `
                            <div class="status-item">
                                <i class="fas fa-check-circle text-success"></i>
                                <span>Данные загружены</span>
                            </div>
                        `;
                    } else {
                        statusHtml += `
                            <div class="status-item">
                                <i class="fas fa-exclamation-triangle text-warning"></i>
                                <span>Данные Metasploit не загружены</span>
                            </div>
                        `;
                    }
                }
                
                statusHtml += '</div>';
                
                // Добавляем ссылки для скачивания как в ExploitDB
                statusHtml += `
                    <div style="background-color: #f8f9fa; border: 1px solid #dee2e6; border-radius: 8px; padding: 12px; font-size: 0.875rem; margin-top: 15px;">
                        <h4 style="margin: 0 0 8px 0; font-size: 0.9rem; font-weight: 600; color: #1e293b;">📋 Ссылки для скачивания Metasploit</h4>
                        <p style="margin: 0 0 8px 0; line-height: 1.4;">Для offline загрузки используйте следующие ссылки:</p>
                        <div style="display: flex; flex-direction: column; gap: 6px;">
                            <a href="https://github.com/rapid7/metasploit-framework" target="_blank" style="display: flex; align-items: center; gap: 6px; color: #2563eb; text-decoration: none; font-size: 0.8rem; padding: 4px 8px; border-radius: 4px;">
                                📦 <span style="flex: 1;">Metasploit Framework GitHub</span>
                            </a>
                            <a href="https://raw.githubusercontent.com/rapid7/metasploit-framework/master/db/modules_metadata_base.json" target="_blank" style="display: flex; align-items: center; gap: 6px; color: #2563eb; text-decoration: none; font-size: 0.8rem; padding: 4px 8px; border-radius: 4px;">
                                🔗 <span style="flex: 1;">modules_metadata_base.json</span>
                                <span style="font-size: 0.7rem; color: #64748b; font-style: italic;">~2MB</span>
                            </a>
                        </div>
                    </div>
                `;
                
                statusDiv.innerHTML = statusHtml;
            } else {
                throw new Error('Ошибка получения статуса');
            }

        } catch (error) {
            statusDiv.innerHTML = `
                <div class="status-info">
                    <div class="status-item">
                        <i class="fas fa-times-circle text-danger"></i>
                        <span>Ошибка получения статуса</span>
                    </div>
                </div>
            `;
        }
    }

    setButtonLoading(button, loading) {
        const icon = button.querySelector('i.fas');
        const spinner = button.querySelector('i.fa-spinner');
        const text = button.querySelector('.btn-text');

        if (loading) {
            icon.style.display = 'none';
            spinner.style.display = 'inline-block';
            text.textContent = 'Загрузка...';
            button.disabled = true;
        } else {
            icon.style.display = 'inline-block';
            spinner.style.display = 'none';
            text.textContent = text.textContent.replace('Загрузка...', '');
            button.disabled = false;
        }
    }

    showStatus(container, message, type = 'info') {
        const typeClass = type === 'error' ? 'text-danger' : 
                         type === 'success' ? 'text-success' : 
                         type === 'warning' ? 'text-warning' : 'text-info';
        
        container.innerHTML = `
            <div class="alert alert-${type}">
                <i class="fas fa-${type === 'error' ? 'times-circle' : 
                                   type === 'success' ? 'check-circle' : 
                                   type === 'warning' ? 'exclamation-triangle' : 'info-circle'}"></i>
                ${message}
            </div>
        `;
    }
}

// Экспорт модуля
if (typeof module !== 'undefined' && module.exports) {
    module.exports = MetasploitModule;
}
