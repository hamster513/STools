/**
 * Модуль для управления логами фоновых задач
 */
class LogsManager {
    constructor() {
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.loadLogsStats();
        this.loadLogsFiles();
    }

    setupEventListeners() {
        // Кнопка обновления логов
        const refreshLogsBtn = document.getElementById('refresh-logs-btn');
        if (refreshLogsBtn) {
            refreshLogsBtn.addEventListener('click', () => {
                this.loadLogsStats();
                this.loadLogsFiles();
                this.showNotification('Логи обновлены', 'success');
            });
        }

        // Кнопка очистки старых логов
        const cleanupLogsBtn = document.getElementById('cleanup-logs-btn');
        if (cleanupLogsBtn) {
            cleanupLogsBtn.addEventListener('click', () => {
                this.cleanupOldLogs();
            });
        }

        // Фильтр по типу задачи
        const taskTypeFilter = document.getElementById('logs-task-type-filter');
        if (taskTypeFilter) {
            taskTypeFilter.addEventListener('change', () => {
                this.loadLogsFiles();
            });
        }
    }

    async loadLogsStats() {
        try {
            console.log('Загружаем статистику логов...');
            const response = await fetch('/api/logs/stats', {
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('auth_token')}`
                }
            });

            console.log('Ответ сервера:', response.status, response.statusText);

            if (response.ok) {
                const data = await response.json();
                console.log('Данные статистики:', data);
                this.updateLogsStatsUI(data.stats);
            } else {
                const errorText = await response.text();
                console.error('Ошибка ответа сервера:', errorText);
                this.showNotification(`Ошибка загрузки статистики логов: ${response.status} ${response.statusText}`, 'error');
            }
        } catch (error) {
            console.error('Ошибка загрузки статистики логов:', error);
            this.showNotification(`Ошибка загрузки статистики логов: ${error.message}`, 'error');
        }
    }

    updateLogsStatsUI(stats) {
        const statsContainer = document.getElementById('logs-stats');
        if (!statsContainer) return;

        const statsHTML = `
            <div class="stats-grid">
                <div class="stat-item">
                    <div class="stat-number">${stats.total_files}</div>
                    <div class="stat-label">Всего файлов</div>
                </div>
                <div class="stat-item">
                    <div class="stat-number">${stats.total_size_mb} МБ</div>
                    <div class="stat-label">Общий размер</div>
                </div>
            </div>
            <div class="stats-by-type">
                <h5>По типам задач:</h5>
                ${Object.entries(stats.by_task_type).map(([taskType, typeStats]) => `
                    <div class="stat-type-item">
                        <span class="stat-type-name">${this.getTaskTypeName(taskType)}:</span>
                        <span class="stat-type-value">${typeStats.count} файлов (${typeStats.total_size_mb} МБ)</span>
                    </div>
                `).join('')}
            </div>
        `;

        statsContainer.innerHTML = statsHTML;
    }

    async loadLogsFiles() {
        try {
            const taskTypeFilter = document.getElementById('logs-task-type-filter');
            const taskType = taskTypeFilter ? taskTypeFilter.value : '';

            const url = taskType ? 
                `/api/logs/files?task_type=${taskType}` : 
                '/api/logs/files';

            console.log('Загружаем файлы логов:', url);

            const response = await fetch(url, {
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('auth_token')}`
                }
            });

            console.log('Ответ сервера для файлов:', response.status, response.statusText);

            if (response.ok) {
                const data = await response.json();
                console.log('Данные файлов логов:', data);
                this.updateLogsFilesUI(data.files);
            } else {
                const errorText = await response.text();
                console.error('Ошибка ответа сервера для файлов:', errorText);
                this.showNotification(`Ошибка загрузки файлов логов: ${response.status} ${response.statusText}`, 'error');
            }
        } catch (error) {
            console.error('Ошибка загрузки файлов логов:', error);
            this.showNotification(`Ошибка загрузки файлов логов: ${error.message}`, 'error');
        }
    }

    updateLogsFilesUI(files) {
        const filesContainer = document.getElementById('logs-files-list');
        if (!filesContainer) return;

        if (files.length === 0) {
            filesContainer.innerHTML = '<div class="no-files">Файлы логов не найдены</div>';
            return;
        }

        const filesHTML = files.map(file => `
            <div class="log-file-item">
                <div class="log-file-header">
                    <div class="log-file-info">
                        <h5>${this.getTaskTypeName(file.task_type)} (ID: ${file.task_id})</h5>
                        <span class="log-file-name">${file.file_name}</span>
                    </div>
                    <div class="log-file-actions">
                        <button class="btn btn-primary btn-sm" onclick="logsManager.downloadLogFile('${file.id}')">
                            <i class="fas fa-download"></i> Скачать
                        </button>
                        <button class="btn btn-danger btn-sm" onclick="logsManager.deleteLogFile('${file.id}')">
                            <i class="fas fa-trash"></i> Удалить
                        </button>
                    </div>
                </div>
                <div class="log-file-details">
                    <div class="log-file-detail">
                        <span class="detail-label">Размер:</span>
                        <span class="detail-value">${file.file_size_mb} МБ</span>
                    </div>
                    <div class="log-file-detail">
                        <span class="detail-label">Создан:</span>
                        <span class="detail-value">${this.formatDateTime(file.created_at)}</span>
                    </div>
                    ${file.duration ? `
                    <div class="log-file-detail">
                        <span class="detail-label">Длительность:</span>
                        <span class="detail-value">${file.duration}</span>
                    </div>
                    ` : ''}
                </div>
            </div>
        `).join('');

        filesContainer.innerHTML = filesHTML;
    }

    async downloadLogFile(logFileId) {
        try {
            const response = await fetch(`/api/logs/files/${logFileId}/download`, {
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('auth_token')}`
                }
            });

            if (response.ok) {
                // Получаем имя файла из заголовка Content-Disposition
                const contentDisposition = response.headers.get('Content-Disposition');
                let filename = 'log_file.log';
                if (contentDisposition) {
                    const filenameMatch = contentDisposition.match(/filename="(.+)"/);
                    if (filenameMatch) {
                        filename = filenameMatch[1];
                    }
                }

                // Создаем blob и скачиваем файл
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = filename;
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(url);
                document.body.removeChild(a);

                this.showNotification('Файл лога скачан', 'success');
            } else {
                this.showNotification('Ошибка скачивания файла лога', 'error');
            }
        } catch (error) {
            console.error('Ошибка скачивания файла лога:', error);
            this.showNotification('Ошибка скачивания файла лога', 'error');
        }
    }

    async deleteLogFile(logFileId) {
        if (!confirm('Вы уверены, что хотите удалить этот файл лога? Это действие нельзя отменить.')) {
            return;
        }

        try {
            const response = await fetch(`/api/logs/files/${logFileId}`, {
                method: 'DELETE',
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('auth_token')}`
                }
            });

            if (response.ok) {
                const data = await response.json();
                if (data.success) {
                    this.showNotification('Файл лога удален', 'success');
                    this.loadLogsStats();
                    this.loadLogsFiles();
                } else {
                    this.showNotification(data.message || 'Ошибка удаления файла лога', 'error');
                }
            } else {
                this.showNotification('Ошибка удаления файла лога', 'error');
            }
        } catch (error) {
            console.error('Ошибка удаления файла лога:', error);
            this.showNotification('Ошибка удаления файла лога', 'error');
        }
    }

    async cleanupOldLogs() {
        const days = prompt('Введите количество дней для очистки старых логов (по умолчанию 30):', '30');
        if (!days || isNaN(days) || days < 1) {
            return;
        }

        if (!confirm(`Вы уверены, что хотите удалить все файлы логов старше ${days} дней? Это действие нельзя отменить.`)) {
            return;
        }

        try {
            const response = await fetch('/api/logs/cleanup', {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('auth_token')}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ days: parseInt(days) })
            });

            if (response.ok) {
                const data = await response.json();
                if (data.success) {
                    this.showNotification(data.message, 'success');
                    this.loadLogsStats();
                    this.loadLogsFiles();
                } else {
                    this.showNotification(data.message || 'Ошибка очистки логов', 'error');
                }
            } else {
                this.showNotification('Ошибка очистки логов', 'error');
            }
        } catch (error) {
            console.error('Ошибка очистки логов:', error);
            this.showNotification('Ошибка очистки логов', 'error');
        }
    }

    getTaskTypeName(taskType) {
        const taskTypeNames = {
            'vm_import': 'VM Импорт',
            'hosts_update': 'Обновление хостов',
            'backup_create': 'Создание бэкапа',
            'epss_download': 'Загрузка EPSS',
            'risk_recalculation': 'Пересчет рисков'
        };
        return taskTypeNames[taskType] || taskType;
    }

    formatDateTime(dateTimeString) {
        if (!dateTimeString) return 'Неизвестно';
        try {
            const date = new Date(dateTimeString);
            return date.toLocaleString('ru-RU');
        } catch (error) {
            return dateTimeString;
        }
    }

    showNotification(message, type = 'info') {
        if (window.uiManager && window.uiManager.showNotification) {
            window.uiManager.showNotification(message, type);
        } else {
            alert(message);
        }
    }
}

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', () => {
    // Инициализируем только если мы на странице настроек
    if (document.getElementById('logs-management')) {
        console.log('Инициализируем LogsManager...');
        window.logsManager = new LogsManager();
        console.log('LogsManager инициализирован');
    } else {
        console.log('Элемент logs-management не найден, LogsManager не инициализирован');
    }
});
