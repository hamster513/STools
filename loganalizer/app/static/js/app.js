class LogAnalizer {
    constructor() {
        this.selectedFiles = [];
        this.uploadedFiles = [];
        this.settings = {};
        this.presets = [];
        this.customSettings = [];
        this.currentEditingSetting = null;
        this.operationStatus = {}; // Хранит статус текущих операций
        this.init();
    }

    init() {
        this.setupTheme();
        this.setupNavigation();
        this.setupFileUpload();
        this.setupEventListeners();
        this.loadInitialData();
    }

    setupTheme() {
        const savedTheme = localStorage.getItem('theme') || 'light';
        document.documentElement.setAttribute('data-theme', savedTheme);
        this.updateThemeIcon(savedTheme);
    }

    updateThemeIcon(theme) {
        const themeBtn = document.getElementById('theme-toggle');
        const icon = themeBtn.querySelector('i');
        if (theme === 'dark') {
            icon.className = 'fas fa-moon';
        } else {
            icon.className = 'fas fa-sun';
        }
    }

    toggleTheme() {
        const currentTheme = document.documentElement.getAttribute('data-theme');
        const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
        document.documentElement.setAttribute('data-theme', newTheme);
        localStorage.setItem('theme', newTheme);
        this.updateThemeIcon(newTheme);
    }

    setupNavigation() {
        const navLinks = document.querySelectorAll('.nav-link');
        navLinks.forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const page = link.getAttribute('data-page');
                this.switchPage(page);
            });
        });
    }

    switchPage(page) {
        // Скрываем все страницы
        document.querySelectorAll('.page-content').forEach(content => {
            content.classList.remove('active');
        });

        // Убираем активный класс со всех ссылок
        document.querySelectorAll('.nav-link').forEach(link => {
            link.classList.remove('active');
        });

        // Показываем нужную страницу
        const targetPage = document.getElementById(`${page}-page`);
        if (targetPage) {
            targetPage.classList.add('active');
        }

        // Добавляем активный класс к ссылке
        const activeLink = document.querySelector(`[data-page="${page}"]`);
        if (activeLink) {
            activeLink.classList.add('active');
        }

        // Загружаем данные для страницы
        if (page === 'import') {
            this.loadFiles();
        } else if (page === 'analysis') {
            this.loadPresets();
        } else if (page === 'settings') {
            this.loadSettings();
        }
    }

    setupFileUpload() {
        const uploadArea = document.getElementById('upload-area');
        const fileInput = document.getElementById('file-input');

        console.log('Setting up file upload handlers');

        // Drag and drop
        uploadArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadArea.classList.add('dragover');
        });

        uploadArea.addEventListener('dragleave', () => {
            uploadArea.classList.remove('dragover');
        });

        uploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadArea.classList.remove('dragover');
            const files = Array.from(e.dataTransfer.files);
            console.log('Files dropped:', files);
            this.handleFiles(files);
        });

        // Click to select - только если клик не по кнопке
        uploadArea.addEventListener('click', (e) => {
            // Проверяем, что клик не по кнопке
            if (!e.target.closest('button')) {
                console.log('Upload area clicked (not button)');
                fileInput.click();
            }
        });

        fileInput.addEventListener('change', (e) => {
            console.log('File input change event triggered');
            const files = Array.from(e.target.files);
            console.log('Selected files:', files);
            this.handleFiles(files);
        });

        // Отдельный обработчик для кнопки "Выбрать файлы"
        const selectFilesBtn = document.getElementById('select-files-btn');
        if (selectFilesBtn) {
            selectFilesBtn.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                console.log('Select files button clicked');
                fileInput.click();
            });
        }

        console.log('File upload handlers setup complete');
    }

    handleFiles(files) {
        console.log('handleFiles called with:', files);
        this.selectedFiles = files;
        this.updateUploadButton();
        this.showNotification(`Выбрано файлов: ${files.length}`, 'info');
        console.log('✅ Files selected, upload button should be enabled');
    }

    updateUploadButton() {
        const uploadBtn = document.getElementById('upload-btn');
        const isDisabled = this.selectedFiles.length === 0;
        uploadBtn.disabled = isDisabled;
        console.log('Upload button disabled:', isDisabled, 'Selected files:', this.selectedFiles.length);
    }

    setupEventListeners() {
        // Кнопка переключения темы
        document.getElementById('theme-toggle').addEventListener('click', () => {
            this.toggleTheme();
        });

        // Кнопка загрузки
        document.getElementById('upload-btn').addEventListener('click', () => {
            console.log('🚀 Upload button clicked!');
            this.uploadFiles();
        });

        // Кнопка очистки загрузки
        document.getElementById('clear-upload-btn').addEventListener('click', () => {
            this.clearUpload();
        });

        // Кнопка очистки всех файлов
        document.getElementById('clear-all-btn').addEventListener('click', () => {
            this.clearAllFiles();
        });

        // Кнопка анализа
        document.getElementById('analyze-btn').addEventListener('click', () => {
            this.analyzeFiles();
        });

        // Кнопка очистки анализа
        document.getElementById('clear-analysis-btn').addEventListener('click', () => {
            this.clearAnalysis();
        });

        // Кнопки настроек
        document.getElementById('save-settings-btn').addEventListener('click', () => {
            this.saveSettings();
        });

        document.getElementById('reset-settings-btn').addEventListener('click', () => {
            this.resetSettings();
        });

        // Закрытие модального окна
        document.getElementById('preview-close').addEventListener('click', () => {
            this.closePreviewModal();
        });

        // Закрытие модального окна по клику вне его
        document.getElementById('preview-modal').addEventListener('click', (e) => {
            if (e.target.id === 'preview-modal') {
                this.closePreviewModal();
            }
        });

        // Пользовательские настройки анализа
        document.getElementById('add-custom-setting-btn').addEventListener('click', () => {
            this.showCustomSettingModal();
        });

        // Кнопка переключения неактивных настроек
        document.getElementById('toggle-inactive-settings-btn').addEventListener('click', () => {
            this.toggleInactiveSettings();
        });

        // Модальное окно пользовательских настроек
        document.getElementById('custom-setting-close').addEventListener('click', () => {
            this.closeCustomSettingModal();
        });

        document.getElementById('custom-setting-modal').addEventListener('click', (e) => {
            if (e.target.id === 'custom-setting-modal') {
                this.closeCustomSettingModal();
            }
        });

        document.getElementById('save-custom-setting-btn').addEventListener('click', () => {
            this.saveCustomSetting();
        });

        document.getElementById('delete-custom-setting-btn').addEventListener('click', () => {
            this.deleteCustomSetting();
        });

        document.getElementById('cancel-custom-setting-btn').addEventListener('click', () => {
            this.closeCustomSettingModal();
        });
    }

    async uploadFiles() {
        console.log('📤 uploadFiles called with', this.selectedFiles.length, 'files');
        if (this.selectedFiles.length === 0) {
            this.showNotification('Нет файлов для загрузки', 'warning');
            return;
        }

        const uploadBtn = document.getElementById('upload-btn');
        const progressContainer = document.getElementById('upload-progress');
        
        uploadBtn.disabled = true;
        uploadBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Загрузка...';
        
        // Скрываем старый прогресс-бар
        if (progressContainer) {
            progressContainer.style.display = 'none';
        }

        // Показываем прогресс в новом статусбаре
        this.showOperationProgress('upload', 'Подготовка к загрузке файлов...', 0);

        try {
            for (let i = 0; i < this.selectedFiles.length; i++) {
                const file = this.selectedFiles[i];
                const progress = ((i + 1) / this.selectedFiles.length) * 100;
                const fileSize = this.formatFileSize(file.size);
                
                this.updateOperationProgress('upload', 
                    `Загрузка файла ${i + 1} из ${this.selectedFiles.length}`, 
                    progress, 
                    `Обработка: ${file.name} (${fileSize})`
                );

                // Симулируем прогресс обработки файла
                this.updateOperationProgress('upload', 
                    `Анализ файла ${file.name}...`, 
                    progress, 
                    `Проверка формата и размера... (${fileSize})`
                );
                await new Promise(resolve => setTimeout(resolve, 300));

                this.updateOperationProgress('upload', 
                    `Загрузка файла ${file.name}...`, 
                    progress, 
                    `Отправка на сервер... (${fileSize})`
                );
                await new Promise(resolve => setTimeout(resolve, 500));

                this.updateOperationProgress('upload', 
                    `Обработка файла ${file.name}...`, 
                    progress, 
                    `Распаковка и анализ содержимого... (${fileSize})`
                );
                
                await this.uploadSingleFile(file);

                this.updateOperationProgress('upload', 
                    `Завершение обработки ${file.name}...`, 
                    progress, 
                    `Сохранение результатов... (${fileSize})`
                );
                await new Promise(resolve => setTimeout(resolve, 200));
            }

            this.updateOperationProgress('upload', 'Завершение операции...', 95, 'Финальная обработка...');
            await new Promise(resolve => setTimeout(resolve, 300));

            this.showOperationComplete('upload', 'Файлы успешно загружены', 
                `Загружено файлов: ${this.selectedFiles.length}`);
            this.showNotification('Файлы успешно загружены', 'success');
            this.clearUpload();
            this.loadFiles();
        } catch (error) {
            console.error('Upload error:', error);
            this.showOperationError('upload', 'Ошибка загрузки файлов', error.message);
            this.showNotification('Ошибка загрузки файлов: ' + error.message, 'error');
        } finally {
            uploadBtn.disabled = false;
            uploadBtn.innerHTML = '<i class="fas fa-upload"></i> Загрузить';
        }
    }

    async uploadSingleFile(file) {
        const formData = new FormData();
        formData.append('file', file);

        // Получаем настройки для загрузки
        const settings = await this.getSettings();
        formData.append('max_file_size', settings.max_file_size_mb || 100);
        formData.append('extract_nested', settings.extract_nested_archives || true);
        formData.append('max_depth', settings.max_extraction_depth || 5);

        console.log('📤 Sending file to server:', file.name);
        const response = await fetch('/api/logs/upload', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Ошибка загрузки файла');
        }

        const result = await response.json();
        console.log('📥 Server response:', result);
        
        if (result.upload_id) {
            console.log('🆔 Upload ID received:', result.upload_id);
            // Запускаем отслеживание прогресса через SSE
            this.trackServerProgress(result.upload_id, (progress) => {
                console.log('📊 Server progress:', progress);
            });
        }
        
        return result;
    }

    trackServerProgress(uploadId, progressCallback) {
        console.log('🔍 Starting server progress tracking for:', uploadId);
        
        const eventSource = new EventSource(`/api/upload-progress/${uploadId}`);
        console.log('🔗 Creating EventSource for:', `/api/upload-progress/${uploadId}`);

        eventSource.onopen = () => {
            console.log('🔗 SSE connection opened successfully');
        };

        eventSource.onmessage = (event) => {
            console.log('📨 Raw SSE message:', event.data);
            try {
                const data = JSON.parse(event.data);
                console.log('📊 Server progress:', data);
                
                if (progressCallback) {
                    progressCallback(data);
                }

                // Обновляем статус бар на основе данных сервера
                switch (data.status) {
                    case 'starting':
                        this.updateOperationProgress('upload', data.message, data.progress, data.details);
                        break;
                    case 'extracting':
                        this.updateOperationProgress('upload', data.message, data.progress, data.details);
                        break;
                    case 'saving_to_db':
                        this.updateOperationProgress('upload', data.message, data.progress, data.details);
                        break;
                    case 'filtering':
                        this.updateOperationProgress('upload', data.message, data.progress, data.details);
                        break;
                    case 'filtering_file':
                        this.updateOperationProgress('upload', data.message, data.progress, data.details);
                        break;
                    case 'completed':
                        this.showOperationComplete('upload', data.message, data.details);
                        this.loadFiles(); // Обновляем список файлов
                        eventSource.close();
                        break;
                    case 'error':
                        this.showOperationError('upload', data.message, data.details);
                        eventSource.close();
                        break;
                    default:
                        this.updateOperationProgress('upload', data.message, data.progress, data.details);
                }
            } catch (error) {
                console.error('❌ Error parsing SSE data:', error);
            }
        };

        eventSource.onerror = (error) => {
            console.error('❌ SSE error:', error);
            console.log('SSE readyState:', eventSource.readyState);
            console.log('SSE URL:', eventSource.url);
            
            // Проверяем, не завершилось ли соединение нормально
            if (eventSource.readyState === EventSource.CLOSED) {
                console.log('🔗 SSE connection closed normally');
                return;
            }
            
            // Fallback mechanism только если соединение не закрыто нормально
            this.startFallbackProgressTracking(uploadId);
        };
    }

    startFallbackProgressTracking(uploadId) {
        console.log('🔄 Starting fallback progress tracking for:', uploadId);
        
        let retryCount = 0;
        const maxRetries = 10; // Максимальное количество попыток
        
        setTimeout(() => {
            const fallbackInterval = setInterval(async () => {
                try {
                    const response = await fetch(`/api/upload-progress-json/${uploadId}`);
                    if (response.ok) {
                        const data = await response.json();
                        console.log('📊 Fallback progress data:', data);

                        if (data.status === 'completed') {
                            console.log('✅ Upload completed via fallback');
                            setTimeout(async () => {
                                console.log('🔄 Reloading files list after completion (fallback)');
                                await this.loadFiles();
                                this.showOperationComplete('upload', data.message, data.details);
                            }, 1000);
                            clearInterval(fallbackInterval);
                        } else if (data.status === 'error') {
                            console.log('❌ Upload error via fallback');
                            this.showOperationError('upload', data.message, data.details);
                            clearInterval(fallbackInterval);
                        } else if (data.status === 'not_found') {
                            retryCount++;
                            console.log(`⚠️ Upload ID not found (attempt ${retryCount}/${maxRetries}), will retry...`);
                            
                            // Если слишком много попыток, прекращаем
                            if (retryCount >= maxRetries) {
                                console.log('🛑 Max retries reached, stopping fallback tracking');
                                clearInterval(fallbackInterval);
                                // Не показываем ошибку пользователю, так как загрузка могла завершиться успешно
                            }
                        } else if (data.status && data.progress !== undefined) {
                            this.updateOperationProgress('upload', data.message, data.progress, data.details);
                            retryCount = 0; // Сбрасываем счетчик при успешном получении данных
                        }
                    } else {
                        retryCount++;
                        console.log(`⚠️ Fallback response not ok (attempt ${retryCount}/${maxRetries})`);
                        
                        if (retryCount >= maxRetries) {
                            console.log('🛑 Max retries reached, stopping fallback tracking');
                            clearInterval(fallbackInterval);
                        }
                    }
                } catch (error) {
                    retryCount++;
                    console.error(`❌ Fallback error (attempt ${retryCount}/${maxRetries}):`, error);
                    
                    if (retryCount >= maxRetries) {
                        console.log('🛑 Max retries reached, stopping fallback tracking');
                        clearInterval(fallbackInterval);
                    }
                }
            }, 2000);
        }, 1000);
    }

    clearUpload() {
        console.log('clearUpload called');
        this.selectedFiles = [];
        document.getElementById('file-input').value = '';
        this.updateUploadButton();
        
        // Очищаем новый статусбар
        const uploadStatus = document.getElementById('upload-status');
        if (uploadStatus) {
            uploadStatus.innerHTML = '';
        }
        
        this.showNotification('Выбор файлов очищен', 'info');
    }

    async loadFiles() {
        try {
            const response = await fetch('/api/logs/files');
            const data = await response.json();

            if (data.success) {
                this.uploadedFiles = data.data;
                this.renderFiles();
            }
        } catch (error) {
            console.error('Error loading files:', error);
            this.showNotification('Ошибка загрузки списка файлов', 'error');
        }
    }

    renderFiles() {
        const filesList = document.getElementById('files-list');
        
        if (this.uploadedFiles.length === 0) {
            filesList.innerHTML = '<p class="no-files">Нет загруженных файлов</p>';
            return;
        }

        const filesHtml = this.uploadedFiles.map(file => `
            <div class="file-item" data-file-id="${file.id}">
                <div class="file-info">
                    <div class="file-icon">
                        <i class="fas fa-file-alt"></i>
                    </div>
                    <div class="file-details">
                        <h4>${file.original_name}</h4>
                        <p>Размер: ${this.formatFileSize(file.file_size)} | Тип: ${file.file_type} | Загружен: ${new Date(file.upload_date).toLocaleString()}</p>
                    </div>
                </div>
                <div class="file-actions">
                    <button type="button" class="btn btn-secondary btn-sm" onclick="logAnalizer.previewFile('${file.id}')">
                        <i class="fas fa-eye"></i> Просмотр
                    </button>
                    ${file.has_filtered_version ? `
                        <button type="button" class="btn btn-info btn-sm" onclick="logAnalizer.previewFilteredFile('${file.id}')">
                            <i class="fas fa-filter"></i> Отфильтрованный
                        </button>
                    ` : ''}
                    <button type="button" class="btn btn-warning btn-sm" onclick="logAnalizer.filterFile('${file.id}')">
                        <i class="fas fa-magic"></i> ${file.has_filtered_version ? 'Перефильтровать' : 'Фильтровать'}
                    </button>
                    <button type="button" class="btn btn-danger btn-sm" onclick="logAnalizer.deleteFile('${file.id}')">
                        <i class="fas fa-trash"></i> Удалить
                    </button>
                </div>
            </div>
        `).join('');

        filesList.innerHTML = filesHtml;
    }

    formatFileSize(bytes) {
        if (bytes === 0) return '0 Б';
        const k = 1024;
        const sizes = ['Б', 'КБ', 'МБ', 'ГБ'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    async previewFile(fileId) {
        try {
            const response = await fetch(`/api/logs/files/${fileId}/preview`);
            const data = await response.json();

            if (data.success) {
                this.showPreviewModal(data.original_name, data.preview);
            }
        } catch (error) {
            console.error('Error previewing file:', error);
            this.showNotification('Ошибка предварительного просмотра', 'error');
        }
    }

    async previewFilteredFile(fileId) {
        try {
            const response = await fetch(`/api/logs/files/${fileId}/filtered`);
            const data = await response.json();

            if (data.success) {
                const title = `Отфильтрованный файл (${data.total_lines} строк)`;
                const content = data.preview;
                this.showPreviewModal(title, content);
            } else {
                this.showNotification('Отфильтрованный файл не найден', 'warning');
            }
        } catch (error) {
            console.error('Error previewing filtered file:', error);
            this.showNotification('Ошибка предварительного просмотра отфильтрованного файла', 'error');
        }
    }

    async filterFile(fileId) {
        try {
            // Находим информацию о файле
            const file = this.uploadedFiles.find(f => f.id === fileId);
            if (!file) {
                this.showNotification('Файл не найден', 'error');
                return;
            }

            const fileSize = this.formatFileSize(file.file_size);
            
            // Показываем прогресс фильтрации
            this.showOperationProgress('filter', 'Начало фильтрации файла...', 0);
            
            this.updateOperationProgress('filter', 
                `Подготовка к фильтрации ${file.original_name}...`, 
                10, 
                `Размер файла: ${fileSize}`
            );
            await new Promise(resolve => setTimeout(resolve, 300));

            this.updateOperationProgress('filter', 
                `Чтение файла ${file.original_name}...`, 
                25, 
                `Обработка: ${fileSize}`
            );
            await new Promise(resolve => setTimeout(resolve, 500));

            this.updateOperationProgress('filter', 
                `Применение фильтров к ${file.original_name}...`, 
                50, 
                `Фильтрация: ${fileSize}`
            );
            await new Promise(resolve => setTimeout(resolve, 300));

            this.updateOperationProgress('filter', 
                `Сохранение отфильтрованных данных ${file.original_name}...`, 
                75, 
                `Сохранение: ${fileSize}`
            );
            await new Promise(resolve => setTimeout(resolve, 200));

            const response = await fetch(`/api/logs/files/${fileId}/filter`, {
                method: 'POST'
            });
            const data = await response.json();

            if (data.success) {
                this.updateOperationProgress('filter', 
                    `Завершение фильтрации ${file.original_name}...`, 
                    90, 
                    `Финальная обработка: ${fileSize}`
                );
                await new Promise(resolve => setTimeout(resolve, 300));

                this.showOperationComplete('filter', 'Фильтрация завершена', 
                    `Файл ${file.original_name} (${fileSize}) успешно отфильтрован`);
                this.showNotification(data.message, 'success');
                // Обновляем список файлов после фильтрации
                this.loadFiles();
            } else {
                this.showOperationError('filter', 'Ошибка фильтрации файла', data.message || 'Неизвестная ошибка');
                this.showNotification('Ошибка фильтрации файла', 'error');
            }
        } catch (error) {
            console.error('Error filtering file:', error);
            this.showOperationError('filter', 'Ошибка фильтрации файла', error.message);
            this.showNotification('Ошибка фильтрации файла', 'error');
        }
    }

    showPreviewModal(title, content) {
        document.getElementById('preview-title').textContent = title;
        document.getElementById('preview-content').textContent = content.join('\n');
        document.getElementById('preview-modal').classList.add('active');
    }

    closePreviewModal() {
        document.getElementById('preview-modal').classList.remove('active');
    }

    async deleteFile(fileId) {
        if (!confirm('Вы уверены, что хотите удалить этот файл?')) {
            return;
        }

        try {
            const response = await fetch(`/api/logs/files/${fileId}`, {
                method: 'DELETE'
            });

            if (response.ok) {
                this.showNotification('Файл успешно удален', 'success');
                this.loadFiles();
            } else {
                throw new Error('Ошибка удаления файла');
            }
        } catch (error) {
            console.error('Error deleting file:', error);
            this.showNotification('Ошибка удаления файла', 'error');
        }
    }

    async clearAllFiles() {
        if (!confirm('Вы уверены, что хотите удалить все файлы?')) {
            return;
        }

        try {
            const response = await fetch('/api/logs/files/clear', {
                method: 'POST'
            });

            if (response.ok) {
                this.showNotification('Все файлы успешно удалены', 'success');
                this.loadFiles();
                
                // Очищаем статусбар
                const uploadStatus = document.getElementById('upload-status');
                if (uploadStatus) {
                    uploadStatus.innerHTML = '';
                }
            } else {
                throw new Error('Ошибка очистки файлов');
            }
        } catch (error) {
            console.error('Error clearing files:', error);
            this.showNotification('Ошибка очистки файлов', 'error');
        }
    }

    async loadPresets() {
        try {
            const response = await fetch('/api/presets');
            const data = await response.json();

            if (data.success) {
                this.presets = data.data;
                this.renderPresets();
            }
        } catch (error) {
            console.error('Error loading presets:', error);
        }
    }

    renderPresets() {
        const presetSelect = document.getElementById('preset-select');
        presetSelect.innerHTML = '<option value="">Выберите пресет...</option>';
        
        this.presets.forEach(preset => {
            const option = document.createElement('option');
            option.value = preset.id;
            option.textContent = preset.name;
            presetSelect.appendChild(option);
        });
    }

    async analyzeFiles() {
        const systemName = document.getElementById('system-name').value.trim();
        const presetId = document.getElementById('preset-select').value;
        const selectedFiles = this.getSelectedFilesForAnalysis();

        if (selectedFiles.length === 0) {
            this.showNotification('Выберите файлы для анализа', 'warning');
            return;
        }

        if (!systemName) {
            this.showNotification('Введите название системы', 'warning');
            return;
        }

        const analyzeBtn = document.getElementById('analyze-btn');
        analyzeBtn.disabled = true;
        analyzeBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Анализ...';

        try {
            const response = await fetch('/api/logs/analyze', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    file_ids: selectedFiles,
                    system_name: systemName,
                    preset_id: presetId
                })
            });

            const data = await response.json();

            if (data.success) {
                this.renderAnalysisResults(data);
                this.showNotification('Анализ завершен успешно', 'success');
            } else {
                throw new Error(data.detail || 'Ошибка анализа');
            }
        } catch (error) {
            console.error('Analysis error:', error);
            this.showNotification('Ошибка анализа: ' + error.message, 'error');
        } finally {
            analyzeBtn.disabled = false;
            analyzeBtn.innerHTML = '<i class="fas fa-search"></i> Анализировать';
        }
    }

    getSelectedFilesForAnalysis() {
        // Здесь можно добавить логику выбора файлов для анализа
        // Пока возвращаем все загруженные файлы
        return this.uploadedFiles.map(file => file.id);
    }

    renderAnalysisResults(data) {
        const resultsContainer = document.getElementById('analysis-results');
        
        let html = `
            <div class="analysis-summary">
                <h3>Результаты анализа для системы: ${data.system_name}</h3>
                <p>Проанализировано файлов: ${data.results.length}</p>
            </div>
        `;

        data.results.forEach(result => {
            html += `
                <div class="result-item">
                    <div class="result-header">
                        <h4>${result.original_name}</h4>
                        <div class="result-stats">
                            <span>Найдено важных строк: ${result.total_lines}</span>
                        </div>
                    </div>
                    <div class="important-lines">
                        ${result.important_lines.map(line => `
                            <div class="line-item">
                                <span class="line-number">${line.line_number}</span>
                                <span class="line-level ${line.level.toLowerCase()}">${line.level}</span>
                                <span class="line-content">${line.content}</span>
                            </div>
                        `).join('')}
                    </div>
                </div>
            `;
        });

        resultsContainer.innerHTML = html;
    }

    clearAnalysis() {
        document.getElementById('system-name').value = '';
        document.getElementById('preset-select').value = '';
        document.getElementById('analysis-results').innerHTML = '';
        this.showNotification('Анализ очищен', 'info');
    }

    async loadSettings() {
        try {
            console.log('🔄 Loading settings from server...');
            const response = await fetch('/api/settings');
            const data = await response.json();

            if (data.success) {
                this.settings = data.data;
                console.log('📊 Settings loaded:', this.settings);
                this.renderSettings();
            } else {
                console.error('❌ Settings loading failed:', data);
            }
        } catch (error) {
            console.error('❌ Error loading settings:', error);
        }
    }

    renderSettings() {
        console.log('🎨 Rendering settings:', this.settings);
        
        // Настройки загрузки
        const maxFileSize = this.settings.max_file_size_mb || 100;
        document.getElementById('max-file-size').value = maxFileSize;
        console.log('📁 Max file size:', maxFileSize);
        
        // Поддерживаемые форматы
        const formatsContainer = document.getElementById('supported-formats');
        const formats = this.settings.supported_formats || [];
        formatsContainer.innerHTML = formats.map(format => `
            <div class="format-item">
                <input type="checkbox" id="format-${format}" value="${format}" checked>
                <label for="format-${format}">${format}</label>
            </div>
        `).join('');
        console.log('📋 Supported formats:', formats);

        // Настройки распаковки
        const extractNested = this.settings.extract_nested_archives || true;
        document.getElementById('extract-nested').checked = extractNested;
        const maxDepth = this.settings.max_extraction_depth || 5;
        document.getElementById('max-depth').value = maxDepth;
        console.log('📦 Extract nested:', extractNested, 'Max depth:', maxDepth);

        // Настройки фильтрации
        const maxFilteringSize = this.settings.max_filtering_file_size_mb || 50;
        document.getElementById('max-filtering-file-size').value = maxFilteringSize;
        console.log('🔍 Max filtering file size:', maxFilteringSize);

        // Важные уровни логов
        const levelsContainer = document.getElementById('important-log-levels');
        const selectedLevels = this.settings.important_log_levels || [];
        
        // Все доступные уровни логов
        const allLevels = ['ERROR', 'WARN', 'CRITICAL', 'FATAL', 'ALERT', 'EMERGENCY', 'INFO', 'DEBUG'];
        
        levelsContainer.innerHTML = allLevels.map(level => {
            const isChecked = selectedLevels.includes(level);
            return `
                <div class="level-item">
                    <input type="checkbox" id="level-${level}" value="${level}" ${isChecked ? 'checked' : ''}>
                    <label for="level-${level}">${level}</label>
                </div>
            `;
        }).join('');
        console.log('⚠️ All log levels:', allLevels);
        console.log('⚠️ Selected log levels:', selectedLevels);
    }

    async saveSettings() {
        const settings = {
            max_file_size_mb: parseInt(document.getElementById('max-file-size').value),
            supported_formats: this.getCheckedValues('supported-formats'),
            extract_nested_archives: document.getElementById('extract-nested').checked,
            max_extraction_depth: parseInt(document.getElementById('max-depth').value),
            max_filtering_file_size_mb: parseInt(document.getElementById('max-filtering-file-size').value),
            important_log_levels: this.getCheckedValues('important-log-levels')
        };

        try {
            const response = await fetch('/api/settings', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(settings)
            });

            if (response.ok) {
                this.showNotification('Настройки сохранены', 'success');
                this.settings = settings;
            } else {
                throw new Error('Ошибка сохранения настроек');
            }
        } catch (error) {
            console.error('Error saving settings:', error);
            this.showNotification('Ошибка сохранения настроек', 'error');
        }
    }

    getCheckedValues(containerId) {
        const container = document.getElementById(containerId);
        const checkboxes = container.querySelectorAll('input[type="checkbox"]:checked');
        return Array.from(checkboxes).map(cb => cb.value);
    }

    async resetSettings() {
        if (!confirm('Вы уверены, что хотите сбросить настройки к умолчанию?')) {
            return;
        }

        try {
            const response = await fetch('/api/settings', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({})
            });

            if (response.ok) {
                this.showNotification('Настройки сброшены к умолчанию', 'success');
                this.loadSettings();
            } else {
                throw new Error('Ошибка сброса настроек');
            }
        } catch (error) {
            console.error('Error resetting settings:', error);
            this.showNotification('Ошибка сброса настроек', 'error');
        }
    }

    async loadInitialData() {
        await this.loadSettings();
        await this.loadFiles();
        await this.loadPresets();
        await this.loadCustomAnalysisSettings();
    }

    async getSettings() {
        if (Object.keys(this.settings).length === 0) {
            await this.loadSettings();
        }
        return this.settings;
    }

    showNotification(message, type = 'info') {
        const notifications = document.getElementById('notifications');
        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        
        let icon = 'fas fa-info-circle';
        if (type === 'success') icon = 'fas fa-check-circle';
        if (type === 'error') icon = 'fas fa-exclamation-circle';
        if (type === 'warning') icon = 'fas fa-exclamation-triangle';

        notification.innerHTML = `
            <i class="${icon}"></i>
            <span>${message}</span>
        `;

        notifications.appendChild(notification);

        // Удаляем уведомление через 5 секунд
        setTimeout(() => {
            notification.remove();
        }, 5000);
    }

    // Пользовательские настройки анализа
    async loadCustomAnalysisSettings() {
        try {
            const response = await fetch('/api/custom-analysis-settings');
            if (response.ok) {
                const data = await response.json();
                this.customSettings = data.data || [];
                this.renderCustomAnalysisSettings();
            }
        } catch (error) {
            console.error('Error loading custom analysis settings:', error);
        }
    }

    toggleInactiveSettings() {
        const container = document.getElementById('custom-analysis-settings');
        const toggleBtn = document.getElementById('toggle-inactive-settings-btn');
        const toggleText = toggleBtn.querySelector('.toggle-text');
        const toggleIcon = toggleBtn.querySelector('i');
        
        const inactiveItems = container.querySelectorAll('.custom-setting-item.inactive');
        const isShowingInactive = inactiveItems[0]?.classList.contains('show-inactive');
        
        if (isShowingInactive) {
            // Скрываем неактивные настройки
            inactiveItems.forEach(item => {
                item.classList.remove('show-inactive');
            });
            toggleText.textContent = 'Развернуть';
            toggleIcon.className = 'fas fa-eye';
        } else {
            // Показываем неактивные настройки
            inactiveItems.forEach(item => {
                item.classList.add('show-inactive');
            });
            toggleText.textContent = 'Свернуть';
            toggleIcon.className = 'fas fa-eye-slash';
        }
    }

    renderCustomAnalysisSettings() {
        const container = document.getElementById('custom-analysis-settings');
        if (!container) return;

        if (this.customSettings.length === 0) {
            container.innerHTML = '<p class="no-settings">Нет пользовательских настроек анализа</p>';
            return;
        }

        container.innerHTML = this.customSettings.map(setting => `
            <div class="custom-setting-item ${!setting.enabled ? 'inactive' : ''}" data-setting-id="${setting.id}">
                <div class="custom-setting-info">
                    <div class="custom-setting-name">${setting.name}</div>
                    <div class="custom-setting-pattern">${setting.pattern}</div>
                    ${setting.description ? `<div class="custom-setting-description">${setting.description}</div>` : ''}
                </div>
                <div class="custom-setting-status">
                    <label class="custom-setting-enabled-checkbox">
                        <input type="checkbox" class="setting-enabled-checkbox" data-setting-id="${setting.id}" ${setting.enabled ? 'checked' : ''}>
                        <span class="checkbox-label">Активна</span>
                    </label>
                    <div class="custom-setting-actions">
                        <button type="button" class="btn btn-secondary btn-sm edit-setting-btn" data-setting-id="${setting.id}">
                            <i class="fas fa-edit"></i>
                        </button>
                        <button type="button" class="btn btn-danger btn-sm delete-setting-btn" data-setting-id="${setting.id}">
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                </div>
            </div>
        `).join('');

        // Добавляем обработчики для кнопок редактирования и удаления
        container.querySelectorAll('.edit-setting-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const settingId = e.target.closest('.edit-setting-btn').dataset.settingId;
                this.editCustomSetting(settingId);
            });
        });

        container.querySelectorAll('.delete-setting-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const settingId = e.target.closest('.delete-setting-btn').dataset.settingId;
                this.deleteCustomSetting(settingId);
            });
        });

        // Добавляем обработчики для чекбоксов
        container.querySelectorAll('.setting-enabled-checkbox').forEach(checkbox => {
            checkbox.addEventListener('change', (e) => {
                // Предотвращаем двойные клики
                if (e.target.disabled) return;
                
                const settingId = e.target.dataset.settingId;
                const enabled = e.target.checked;
                
                // Временно отключаем чекбокс
                e.target.disabled = true;
                
                this.updateSettingEnabled(settingId, enabled).finally(() => {
                    // Включаем чекбокс обратно
                    e.target.disabled = false;
                });
            });
        });
    }

    showCustomSettingModal(setting = null) {
        const modal = document.getElementById('custom-setting-modal');
        const title = document.getElementById('custom-setting-title');
        const form = document.getElementById('custom-setting-form');
        const deleteBtn = document.getElementById('delete-custom-setting-btn');

        if (setting) {
            // Редактирование существующей настройки
            title.textContent = 'Редактирование настройки анализа';
            form.querySelector('#custom-setting-name').value = setting.name;
            form.querySelector('#custom-setting-pattern').value = setting.pattern;
            form.querySelector('#custom-setting-description').value = setting.description || '';
            form.querySelector('#custom-setting-enabled').checked = setting.enabled;
            deleteBtn.style.display = 'inline-block';
            this.currentEditingSetting = setting;
        } else {
            // Создание новой настройки
            title.textContent = 'Новая настройка анализа';
            form.reset();
            deleteBtn.style.display = 'none';
            this.currentEditingSetting = null;
        }

        modal.classList.add('active');
    }

    closeCustomSettingModal() {
        const modal = document.getElementById('custom-setting-modal');
        modal.classList.remove('active');
        this.currentEditingSetting = null;
    }

    async saveCustomSetting() {
        const form = document.getElementById('custom-setting-form');
        const formData = new FormData(form);
        
        const settingData = {
            name: formData.get('name'),
            pattern: formData.get('pattern'),
            description: formData.get('description'),
            enabled: formData.get('enabled') === 'on'
        };

        try {
            let response;
            if (this.currentEditingSetting) {
                // Обновление существующей настройки
                response = await fetch(`/api/custom-analysis-settings/${this.currentEditingSetting.id}`, {
                    method: 'PUT',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(settingData)
                });
            } else {
                // Создание новой настройки
                response = await fetch('/api/custom-analysis-settings', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(settingData)
                });
            }

            if (response.ok) {
                this.showNotification(
                    this.currentEditingSetting ? 'Настройка обновлена' : 'Настройка создана', 
                    'success'
                );
                this.closeCustomSettingModal();
                await this.loadCustomAnalysisSettings();
            } else {
                throw new Error('Ошибка сохранения настройки');
            }
        } catch (error) {
            console.error('Error saving custom setting:', error);
            this.showNotification('Ошибка сохранения настройки', 'error');
        }
    }

    editCustomSetting(settingId) {
        const setting = this.customSettings.find(s => s.id === settingId);
        if (setting) {
            this.showCustomSettingModal(setting);
        }
    }

    async updateSettingEnabled(settingId, enabled) {
        try {
            const setting = this.customSettings.find(s => s.id === settingId);
            if (!setting) return;

            // Проверяем, не пытаемся ли мы установить то же состояние
            if (setting.enabled === enabled) {
                return;
            }

            const response = await fetch(`/api/custom-analysis-settings/${settingId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    name: setting.name,
                    pattern: setting.pattern,
                    description: setting.description,
                    enabled: enabled
                })
            });

            if (response.ok) {
                this.showNotification(`Настройка ${enabled ? 'активирована' : 'деактивирована'}`, 'success');
                // Обновляем состояние в локальном массиве
                const setting = this.customSettings.find(s => s.id === settingId);
                if (setting) {
                    setting.enabled = enabled;
                }
            } else {
                const error = await response.text();
                this.showNotification(`Ошибка при обновлении настройки: ${error}`, 'error');
                // Возвращаем чекбокс в предыдущее состояние
                const checkbox = document.querySelector(`[data-setting-id="${settingId}"]`);
                if (checkbox) checkbox.checked = !enabled;
            }
        } catch (error) {
            this.showNotification(`Ошибка при обновлении настройки: ${error.message}`, 'error');
            // Возвращаем чекбокс в предыдущее состояние
            const checkbox = document.querySelector(`[data-setting-id="${settingId}"]`);
            if (checkbox) checkbox.checked = !enabled;
        }
    }

    async deleteCustomSetting(settingId = null) {
        const id = settingId || (this.currentEditingSetting ? this.currentEditingSetting.id : null);
        if (!id) return;

        if (!confirm('Вы уверены, что хотите удалить эту настройку?')) {
            return;
        }

        try {
            const response = await fetch(`/api/custom-analysis-settings/${id}`, {
                method: 'DELETE'
            });

            if (response.ok) {
                this.showNotification('Настройка удалена', 'success');
                if (this.currentEditingSetting) {
                    this.closeCustomSettingModal();
                }
                await this.loadCustomAnalysisSettings();
            } else {
                throw new Error('Ошибка удаления настройки');
            }
        } catch (error) {
            console.error('Error deleting custom setting:', error);
            this.showNotification('Ошибка удаления настройки', 'error');
        }
    }

    // Новые методы для улучшенного статусбара
    showOperationProgress(operationId, message, progress = null) {
        const statusDiv = document.getElementById(`${operationId}-status`);
        if (!statusDiv) return;
        
        let progressHtml = '';
        if (progress !== null) {
            progressHtml = `
                <div class="progress-bar">
                    <div class="progress-fill" style="width: ${progress}%"></div>
                </div>
                <div class="progress-text">${progress.toFixed(1)}%</div>
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
                <div class="progress-bar">
                    <div class="progress-fill" style="width: ${progress}%"></div>
                </div>
                <div class="progress-text">${progress.toFixed(1)}%</div>
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

// Инициализация приложения при загрузке страницы
document.addEventListener('DOMContentLoaded', () => {
    window.logAnalizer = new LogAnalizer();
}); 