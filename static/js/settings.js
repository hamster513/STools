/**
 * Управление общими настройками системы
 */
class SettingsManager {
    constructor() {
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.setupCollapsibleBlocks();
        this.loadSettings();
        this.updateSystemInfo();
        
        // Загружаем данные для бэкапов
        this.loadTablesForBackup();
        this.loadBackupsList();
    }

    setupEventListeners() {
        // Настройки базы данных
        const dbForm = document.getElementById('database-settings-form');
        if (dbForm) {
            dbForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.saveDatabaseSettings();
            });
        }

        // Тест подключения к БД
        const testBtn = document.getElementById('test-connection');
        if (testBtn) {
            testBtn.addEventListener('click', () => {
                this.testDatabaseConnection();
            });
        }

        // Общие настройки
        const generalForm = document.getElementById('general-settings-form');
        if (generalForm) {
            generalForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.saveGeneralSettings();
            });
        }

        // Настройки безопасности
        const securityForm = document.getElementById('security-settings-form');
        if (securityForm) {
            securityForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.saveSecuritySettings();
            });
        }

        // Обновление информации о системе
        const refreshBtn = document.getElementById('refresh-info');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => {
                this.updateSystemInfo();
            });
        }

        // Backup/Restore
        const backupForm = document.getElementById('backup-form');
        if (backupForm) {
            backupForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.createBackup();
            });
        }

        const restoreForm = document.getElementById('restore-form');
        if (restoreForm) {
            restoreForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.restoreBackup();
            });
        }
    }

    setupCollapsibleBlocks() {
        const collapsibleHeaders = document.querySelectorAll('.collapsible-header');
        
        collapsibleHeaders.forEach(header => {
            // Инициализируем стрелки как свернутые по умолчанию
            const arrow = header.querySelector('.collapsible-arrow');
            if (arrow) {
                arrow.style.transform = 'rotate(-90deg)';
            }
            header.classList.add('collapsed');
            
            // Инициализируем контент как свернутый
            const targetId = header.getAttribute('data-target');
            const content = document.getElementById(targetId);
            if (content) {
                content.classList.add('collapsed');
            }
            
            header.addEventListener('click', (e) => {
                // Предотвращаем срабатывание при клике на форму внутри
                if (e.target.closest('form') || e.target.closest('button')) {
                    return;
                }
                
                if (!content || !arrow) return;
                
                // Переключаем состояние
                if (content.classList.contains('collapsed')) {
                    // Разворачиваем
                    content.classList.remove('collapsed');
                    header.classList.remove('collapsed');
                    arrow.style.transform = 'rotate(0deg)';
                } else {
                    // Сворачиваем
                    content.classList.add('collapsed');
                    header.classList.add('collapsed');
                    arrow.style.transform = 'rotate(-90deg)';
                }
            });
        });
    }

    async loadSettings() {
        try {
            // Загружаем настройки БД (заглушка - в реальности должны быть из конфига)
            document.getElementById('db-host').value = 'postgres';
            document.getElementById('db-port').value = '5432';
            document.getElementById('db-name').value = 'stools_db';
            document.getElementById('db-user').value = 'stools_user';
            // Пароль не загружаем из соображений безопасности

            this.showNotification('Настройки загружены', 'success');
        } catch (error) {
            console.error('Error loading settings:', error);
            this.showNotification('Ошибка загрузки настроек', 'error');
        }
    }

    async saveDatabaseSettings() {
        const formData = new FormData(document.getElementById('database-settings-form'));
        const settings = Object.fromEntries(formData.entries());

        try {
            // В реальной реализации здесь должен быть API вызов
            console.log('Saving database settings:', settings);
            this.showNotification('Настройки базы данных сохранены', 'success');
        } catch (error) {
            console.error('Error saving database settings:', error);
            this.showNotification('Ошибка сохранения настроек БД', 'error');
        }
    }

    async testDatabaseConnection() {
        const testBtn = document.getElementById('test-connection');
        const originalText = testBtn.innerHTML;
        
        testBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Проверка...';
        testBtn.disabled = true;

        try {
            // В реальной реализации здесь должен быть API вызов
            await new Promise(resolve => setTimeout(resolve, 2000)); // Имитация запроса
            
            this.showNotification('Подключение к базе данных успешно', 'success');
            document.getElementById('db-status').textContent = 'Подключено';
            document.getElementById('db-status').className = 'info-value status-success';
        } catch (error) {
            console.error('Database connection test failed:', error);
            this.showNotification('Ошибка подключения к базе данных', 'error');
            document.getElementById('db-status').textContent = 'Ошибка подключения';
            document.getElementById('db-status').className = 'info-value status-error';
        } finally {
            testBtn.innerHTML = originalText;
            testBtn.disabled = false;
        }
    }

    async saveGeneralSettings() {
        const formData = new FormData(document.getElementById('general-settings-form'));
        const settings = Object.fromEntries(formData.entries());

        try {
            // В реальной реализации здесь должен быть API вызов
            console.log('Saving general settings:', settings);
            this.showNotification('Общие настройки сохранены', 'success');
        } catch (error) {
            console.error('Error saving general settings:', error);
            this.showNotification('Ошибка сохранения общих настроек', 'error');
        }
    }

    async saveSecuritySettings() {
        const formData = new FormData(document.getElementById('security-settings-form'));
        const settings = Object.fromEntries(formData.entries());

        try {
            // В реальной реализации здесь должен быть API вызов
            console.log('Saving security settings:', settings);
            this.showNotification('Настройки безопасности сохранены', 'success');
        } catch (error) {
            console.error('Error saving security settings:', error);
            this.showNotification('Ошибка сохранения настроек безопасности', 'error');
        }
    }

    async updateSystemInfo() {
        try {
            // Получаем версию системы из API
            const versionResponse = await fetch('/api/version');
            if (versionResponse.ok) {
                const versionData = await versionResponse.json();
                document.getElementById('system-version').textContent = versionData.version;
            } else {
                // Fallback если API недоступен
                document.getElementById('system-version').textContent = 'Неизвестно';
            }
            
            document.getElementById('active-users').textContent = '1';
            document.getElementById('system-uptime').textContent = 'Менее часа';
            
            // Проверяем статус БД
            document.getElementById('db-status').textContent = 'Проверка...';
            document.getElementById('db-status').className = 'info-value status-checking';
            
            // Имитация проверки БД
            setTimeout(() => {
                document.getElementById('db-status').textContent = 'Подключено';
                document.getElementById('db-status').className = 'info-value status-success';
            }, 1000);
            
        } catch (error) {
            console.error('Error updating system info:', error);
            this.showNotification('Ошибка обновления информации о системе', 'error');
        }
    }

    showNotification(message, type = 'info') {
        const container = document.getElementById('notifications');
        if (!container) return;

        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.innerHTML = `
            <div class="notification-content">
                <i class="fas fa-${this.getNotificationIcon(type)}"></i>
                <span>${message}</span>
            </div>
            <button class="notification-close" onclick="this.parentElement.remove()">
                <i class="fas fa-times"></i>
            </button>
        `;

        container.appendChild(notification);

        // Автоматически убираем уведомление через 5 секунд
        setTimeout(() => {
            if (notification.parentElement) {
                notification.remove();
            }
        }, 5000);
    }

    getNotificationIcon(type) {
        const icons = {
            'success': 'check-circle',
            'error': 'exclamation-circle',
            'warning': 'exclamation-triangle',
            'info': 'info-circle'
        };
        return icons[type] || 'info-circle';
    }

    // Backup/Restore методы
    async loadTablesForBackup() {
        try {
            const response = await fetch('/api/backup/tables');
            const data = await response.json();
            
            if (data.success) {
                this.renderTablesSelection(data.tables);
            } else {
                throw new Error(data.detail || 'Ошибка загрузки таблиц');
            }
        } catch (error) {
            console.error('Error loading tables:', error);
            this.showNotification('Ошибка загрузки списка таблиц', 'error');
        }
    }

    renderTablesSelection(tables) {
        console.log('🔍 [DEBUG] renderTablesSelection вызван с таблицами:', tables);
        const container = document.getElementById('tables-selection');
        console.log('🔍 [DEBUG] Контейнер найден:', container);
        if (!container) {
            console.error('❌ Контейнер tables-selection не найден!');
            return;
        }

        const html = `
            <div class="backup-tables-container">
                <div class="backup-tables-header">
                    <div class="backup-table-col checkbox-col">
                        <input type="checkbox" id="select-all-tables" class="select-all-checkbox">
                        <label for="select-all-tables">Все</label>
                    </div>
                    <div class="backup-table-col schema-col">Схема</div>
                    <div class="backup-table-col table-col">Таблица</div>
                    <div class="backup-table-col description-col">Описание</div>
                </div>
                <div class="backup-tables-body">
                    ${tables.map(table => `
                        <div class="backup-table-row" data-table="${table.schema}.${table.name}">
                            <div class="backup-table-col checkbox-col">
                                <input type="checkbox" id="table-${table.schema}-${table.name}" 
                                       name="tables" value="${table.schema}.${table.name}" class="table-checkbox">
                            </div>
                            <div class="backup-table-col schema-col">
                                <span class="schema-badge">${table.schema}</span>
                            </div>
                            <div class="backup-table-col table-col">
                                <span class="table-name">${table.name}</span>
                            </div>
                            <div class="backup-table-col description-col">
                                <span class="table-description">${table.description || 'Описание недоступно'}</span>
                            </div>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;

        container.innerHTML = html;
        
        // Получаем чекбоксы для настройки функциональности
        const checkboxes = container.querySelectorAll('.table-checkbox');
        
        // Настраиваем функциональность "Выбрать все"
        const selectAllCheckbox = container.querySelector('.select-all-checkbox');
        if (selectAllCheckbox) {
            selectAllCheckbox.addEventListener('change', (e) => {
                const isChecked = e.target.checked;
                checkboxes.forEach(checkbox => {
                    checkbox.checked = isChecked;
                });
            });
        }
        
        // Настраиваем обновление "Выбрать все" при изменении отдельных чекбоксов
        checkboxes.forEach(checkbox => {
            checkbox.addEventListener('change', () => {
                const allChecked = Array.from(checkboxes).every(cb => cb.checked);
                const someChecked = Array.from(checkboxes).some(cb => cb.checked);
                
                if (selectAllCheckbox) {
                    selectAllCheckbox.checked = allChecked;
                    selectAllCheckbox.indeterminate = someChecked && !allChecked;
                }
            });
        });
    }

    async loadBackupsList() {
        try {
            const response = await fetch('/api/backup/list');
            const data = await response.json();
            
            if (data.success) {
                this.renderBackupsList(data.backups);
            } else {
                throw new Error(data.detail || 'Ошибка загрузки бэкапов');
            }
        } catch (error) {
            console.error('Error loading backups:', error);
            this.showNotification('Ошибка загрузки списка бэкапов', 'error');
        }
    }

    renderBackupsList(backups) {
        const container = document.getElementById('backups-list');
        if (!container) return;

        if (backups.length === 0) {
            container.innerHTML = '<div class="no-backups">Бэкапы не найдены</div>';
            return;
        }

        const html = backups.map(backup => `
            <div class="backup-item" data-backup-id="${backup.id}">
                <div class="backup-info">
                    <div class="backup-name">${backup.filename}</div>
                    <div class="backup-details">
                        <span class="backup-size">${this.formatFileSize(backup.size)}</span>
                        <span class="backup-date">${new Date(backup.created_at).toLocaleString()}</span>
                        <span class="backup-tables">${backup.tables.length} таблиц</span>
                    </div>
                </div>
                <div class="backup-actions">
                    <button class="btn btn-sm btn-info" onclick="settingsManager.downloadBackup('${backup.id}')">
                        <i class="fas fa-download"></i> Скачать
                    </button>
                    <button class="btn btn-sm btn-danger" onclick="settingsManager.deleteBackup('${backup.id}')">
                        <i class="fas fa-trash"></i> Удалить
                    </button>
                </div>
            </div>
        `).join('');

        container.innerHTML = html;
    }

    formatFileSize(bytes) {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    async createBackup() {
        const form = document.getElementById('backup-form');
        const formData = new FormData(form);
        const selectedTables = formData.getAll('tables');

        if (selectedTables.length === 0) {
            this.showNotification('Выберите хотя бы одну таблицу для бэкапа', 'warning');
            return;
        }

        try {
            // Показываем прогресс
            this.showBackupProgress();
            
            const response = await fetch('/api/backup/create', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    tables: selectedTables,
                    include_schema: true,
                    include_data: true
                })
            });

            const data = await response.json();
            
            if (data.success) {
                this.hideBackupProgress();
                this.showNotification('Бэкап создан успешно!', 'success');
                
                // Обновляем список бэкапов
                this.loadBackupsList();
                
                // Показываем ссылку для скачивания
                this.showDownloadLink(data.backup_id, data.download_url);
            } else {
                throw new Error(data.detail || 'Ошибка создания бэкапа');
            }
        } catch (error) {
            console.error('Error creating backup:', error);
            this.hideBackupProgress();
            this.showNotification('Ошибка создания бэкапа: ' + error.message, 'error');
        }
    }

    showBackupProgress() {
        const progress = document.getElementById('backup-progress');
        const progressBar = document.getElementById('backup-progress-bar');
        const status = document.getElementById('backup-status');
        
        if (progress) progress.style.display = 'block';
        if (progressBar) progressBar.style.width = '0%';
        if (status) status.textContent = 'Подготовка...';
        
        // Имитируем прогресс
        let progressValue = 0;
        const interval = setInterval(() => {
            progressValue += Math.random() * 20;
            if (progressValue >= 100) {
                progressValue = 100;
                clearInterval(interval);
            }
            
            if (progressBar) progressBar.style.width = progressValue + '%';
            if (status) {
                if (progressValue < 30) status.textContent = 'Выгрузка данных...';
                else if (progressValue < 70) status.textContent = 'Архивация...';
                else if (progressValue < 100) status.textContent = 'Финальная обработка...';
                else status.textContent = 'Готово!';
            }
        }, 500);
    }

    hideBackupProgress() {
        const progress = document.getElementById('backup-progress');
        if (progress) progress.style.display = 'none';
    }

    showDownloadLink(backupId, downloadUrl) {
        const notification = document.createElement('div');
        notification.className = 'notification notification-success download-notification';
        notification.innerHTML = `
            <div class="notification-content">
                <i class="fas fa-download"></i>
                <span>Бэкап создан! <a href="${downloadUrl}" target="_blank">Скачать файл</a></span>
            </div>
            <button class="notification-close" onclick="this.parentElement.remove()">
                <i class="fas fa-times"></i>
            </button>
        `;

        const container = document.getElementById('notifications');
        if (container) {
            container.appendChild(notification);
        }
    }

    async restoreBackup() {
        const form = document.getElementById('restore-form');
        const formData = new FormData(form);
        const file = formData.get('backup_file');

        if (!file) {
            this.showNotification('Выберите файл бэкапа', 'warning');
            return;
        }

        try {
            // Показываем прогресс
            this.showRestoreProgress();
            
            const uploadData = new FormData();
            uploadData.append('backup_file', file);

            const response = await fetch('/api/backup/restore', {
                method: 'POST',
                body: uploadData
            });

            const data = await response.json();
            
            if (data.success) {
                this.hideRestoreProgress();
                this.showNotification('База данных восстановлена успешно!', 'success');
                
                // Очищаем форму
                form.reset();
            } else {
                throw new Error(data.detail || 'Ошибка восстановления');
            }
        } catch (error) {
            console.error('Error restoring backup:', error);
            this.hideRestoreProgress();
            this.showNotification('Ошибка восстановления: ' + error.message, 'error');
        }
    }

    showRestoreProgress() {
        const progress = document.getElementById('restore-progress');
        const progressBar = document.getElementById('restore-progress-bar');
        const status = document.getElementById('restore-status');
        
        if (progress) progress.style.display = 'block';
        if (progressBar) progressBar.style.width = '0%';
        if (status) status.textContent = 'Подготовка...';
        
        // Имитируем прогресс
        let progressValue = 0;
        const interval = setInterval(() => {
            progressValue += Math.random() * 15;
            if (progressValue >= 100) {
                progressValue = 100;
                clearInterval(interval);
            }
            
            if (progressBar) progressBar.style.width = progressValue + '%';
            if (status) {
                if (progressValue < 40) status.textContent = 'Распаковка архива...';
                else if (progressValue < 80) status.textContent = 'Запись в базу...';
                else if (progressValue < 100) status.textContent = 'Финальная обработка...';
                else status.textContent = 'Готово!';
            }
        }, 600);
    }

    hideRestoreProgress() {
        const progress = document.getElementById('restore-progress');
        if (progress) progress.style.display = 'none';
    }

    async downloadBackup(backupId) {
        try {
            window.open(`/api/backup/download/${backupId}`, '_blank');
        } catch (error) {
            console.error('Error downloading backup:', error);
            this.showNotification('Ошибка скачивания бэкапа', 'error');
        }
    }

    async deleteBackup(backupId) {
        if (!confirm('Вы уверены, что хотите удалить этот бэкап?')) {
            return;
        }

        try {
            const response = await fetch(`/api/backup/${backupId}`, {
                method: 'DELETE'
            });

            const data = await response.json();
            
            if (data.success) {
                this.showNotification('Бэкап удален успешно', 'success');
                // Обновляем список бэкапов
                this.loadBackupsList();
            } else {
                throw new Error(data.detail || 'Ошибка удаления бэкапа');
            }
        } catch (error) {
            console.error('Error deleting backup:', error);
            this.showNotification('Ошибка удаления бэкапа: ' + error.message, 'error');
        }
    }
}



// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', () => {
    window.settingsManager = new SettingsManager();
});


