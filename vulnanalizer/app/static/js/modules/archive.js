/**
 * Модуль для работы с архивами баз данных
 * v=1.0
 */
class ArchiveModule {
    constructor(app) {
        this.app = app;
        this.init();
    }

    init() {
        this.setupEventListeners();
    }

    setupEventListeners() {
        // Обработчик формы загрузки архива
        const uploadForm = document.getElementById('archive-upload-form');
        if (uploadForm) {
            uploadForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.uploadArchive();
            });
        }
    }

    async uploadArchive() {
        const fileInput = document.getElementById('archive-file');
        if (!fileInput.files.length) {
            if (this.app.notifications && this.app.notifications.show) {
                this.app.notifications.show('Выберите файл для загрузки', 'error');
            }
            return;
        }

        const file = fileInput.files[0];
        
        // Проверяем размер файла
        const maxSize = 5 * 1024 * 1024 * 1024; // 5 GB
        if (file.size > maxSize) {
            if (this.app.notifications && this.app.notifications.show) {
                this.app.notifications.show('Файл слишком большой (макс. 5 GB)', 'error');
            }
            return;
        }

        const uploadBtn = document.getElementById('archive-upload-btn');
        const btnText = uploadBtn.querySelector('.btn-text');
        const spinner = uploadBtn.querySelector('.fa-spinner');
        
        // Показываем прогресс
        uploadBtn.disabled = true;
        btnText.textContent = 'Загрузка...';
        spinner.style.display = 'inline-block';

        this.showOperationProgress('archive', 'Загрузка архива...', 0);

        try {
            // Создаем FormData
            const formData = new FormData();
            formData.append('file', file);

            // Загружаем с отображением прогресса
            this.updateOperationProgress('archive', 'Передача файла на сервер...', 10, 'Загружаем архив...');
            
            const response = await fetch('/vulnanalizer/api/archive/upload', {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('stools_auth_token')}`
                },
                body: formData
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Ошибка загрузки архива');
            }

            this.updateOperationProgress('archive', 'Обработка архива...', 30, 'Распаковка и анализ файлов...');
            
            const data = await response.json();

            if (data.success) {
                this.updateOperationProgress('archive', 'Импорт данных...', 60, 'Загрузка в базу данных...');
                
                // Формируем детальное сообщение
                let detailsHtml = '<ul style="text-align: left; margin: 1rem 0;">';
                
                if (data.details.epss.success) {
                    detailsHtml += `<li><i class="fas fa-check-circle" style="color: #4CAF50;"></i> EPSS: ${data.details.epss.count} записей</li>`;
                }
                if (data.details.exploitdb.success) {
                    detailsHtml += `<li><i class="fas fa-check-circle" style="color: #4CAF50;"></i> ExploitDB: ${data.details.exploitdb.count} записей</li>`;
                }
                if (data.details.metasploit.success) {
                    detailsHtml += `<li><i class="fas fa-check-circle" style="color: #4CAF50;"></i> Metasploit: ${data.details.metasploit.count} модулей</li>`;
                }
                if (data.details.cve.success) {
                    detailsHtml += `<li><i class="fas fa-check-circle" style="color: #4CAF50;"></i> CVE: ${data.details.cve.count} записей</li>`;
                }
                
                detailsHtml += '</ul>';
                detailsHtml += `<p><strong>Всего импортировано:</strong> ${data.total_records} записей из ${data.databases_imported} баз данных</p>`;

                this.updateOperationProgress('archive', 'Завершение...', 90, 'Финальная обработка...');
                await new Promise(resolve => setTimeout(resolve, 300));
                
                this.showOperationComplete('archive', 'Архив успешно загружен', detailsHtml);
                
                if (this.app.notifications && this.app.notifications.show) {
                    this.app.notifications.show(data.message, 'success');
                }

                // Обновляем статусы всех баз данных
                if (this.app.updateEPSSStatus) this.app.updateEPSSStatus();
                if (this.app.updateExploitDBStatus) this.app.updateExploitDBStatus();
                if (this.app.updateCVEStatus) this.app.updateCVEStatus();
                if (this.app.updateMetasploitStatus) this.app.updateMetasploitStatus();

                // Очищаем форму
                fileInput.value = '';
            } else {
                this.showOperationError('archive', 'Ошибка загрузки архива', data.detail || 'Неизвестная ошибка');
                if (this.app.notifications && this.app.notifications.show) {
                    this.app.notifications.show('Ошибка загрузки архива', 'error');
                }
            }
        } catch (err) {
            console.error('Archive upload error:', err);
            this.showOperationError('archive', 'Ошибка загрузки архива', err.message);
            if (this.app.notifications && this.app.notifications.show) {
                this.app.notifications.show('Ошибка загрузки архива: ' + err.message, 'error');
            }
        } finally {
            uploadBtn.disabled = false;
            btnText.textContent = 'Загрузить архив';
            spinner.style.display = 'none';
        }
    }

    // Методы для отображения прогресса (делегируем в app)
    showOperationProgress(operationId, message, progress = null) {
        if (this.app.showOperationProgress) {
            this.app.showOperationProgress(operationId, message, progress);
        }
    }

    updateOperationProgress(operationId, message, progress, details = null) {
        if (this.app.updateOperationProgress) {
            this.app.updateOperationProgress(operationId, message, progress, details);
        }
    }

    showOperationComplete(operationId, message, details = null) {
        if (this.app.showOperationComplete) {
            this.app.showOperationComplete(operationId, message, details);
        }
    }

    showOperationError(operationId, message, details = null) {
        if (this.app.showOperationError) {
            this.app.showOperationError(operationId, message, details);
        }
    }
}

