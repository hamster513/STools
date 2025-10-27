
class BackgroundTasksManager {
    constructor() {
        this.init();
    }

    init() {
        this.checkAuth();
        this.setupEventListeners();
        this.loadBackgroundTasksData();
    }

    checkAuth() {
        // Ищем единый токен stools_auth_token для всех сервисов STools
        const token = localStorage.getItem('stools_auth_token');
        if (!token) {
            window.location.href = '/auth/';
            return;
        }
    }

    setupEventListeners() {
        // Кнопка обновления
        const refreshTasksBtn = document.getElementById('refresh-tasks-btn');
        if (refreshTasksBtn) {
            refreshTasksBtn.addEventListener('click', () => {
                this.loadBackgroundTasksData();
                this.showNotification('Данные обновлены', 'success');
            });
        }

        // Кнопка очистки задач
        const clearTasksBtn = document.getElementById('clear-tasks-btn');
        if (clearTasksBtn) {
            clearTasksBtn.addEventListener('click', () => {
                this.clearBackgroundTasks();
            });
        }

        // Автоматическое обновление каждые 2 секунды
        this.startAutoRefresh();
    }

    startAutoRefresh() {
        // Очищаем предыдущий интервал
        if (this.autoRefreshInterval) {
            clearInterval(this.autoRefreshInterval);
        }


        
        this.autoRefreshInterval = setInterval(() => {
            this.loadBackgroundTasksData();
        }, 2000); // Обновляем каждые 2 секунды
    }

    stopAutoRefresh() {
        if (this.autoRefreshInterval) {
            clearInterval(this.autoRefreshInterval);
            this.autoRefreshInterval = null;

        }
    }

    async loadBackgroundTasksData() {
        try {

            const resp = await fetch('/vulnanalizer/api/background-tasks/status', {
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('auth_token')}`
                }
            });
            
            if (resp.ok) {
                const data = await resp.json();

                
                this.updateBackgroundTasksUI(data);
            } else {

                this.showNotification('Ошибка загрузки данных о фоновых задачах', 'error');
            }
        } catch (err) {

            this.showNotification('Ошибка загрузки данных о фоновых задачах', 'error');
        }
    }

    updateBackgroundTasksUI(data) {
        // Обновляем список активных задач
        const activeTasksContainer = document.getElementById('active-tasks-list');
        if (activeTasksContainer) {
            if (data.active_tasks && data.active_tasks.length > 0) {
                activeTasksContainer.innerHTML = data.active_tasks.map(task => `
                    <div class="task-item active-task">
                        <div class="task-header">
                            <h4>${task.task_type}</h4>
                            <span class="task-status ${task.status}">${this.getStatusText(task.status)}</span>
                        </div>
                        <div class="task-progress">
                            <div class="operation-progress-bar" style="height: 10px; background: #f8f9fa; border: 1px solid #dee2e6; border-radius: 8px; overflow: hidden; position: relative; width: 100%;">
                                <div class="operation-progress-fill" style="width: ${this.calculateProgressFromStep(task.current_step)}%; height: 100%; background: #007bff; border-radius: 8px; transition: width 0.3s ease; position: relative; overflow: hidden; min-width: 0; max-width: 100%; display: block;"></div>
                            </div>
                            <span class="progress-text">${this.calculateProgressFromStep(task.current_step)}%</span>
                        </div>
                        <div class="task-details">
                            <p><strong>Текущий шаг:</strong> ${task.current_step || 'Инициализация...'}</p>
                        </div>
                        <div class="task-actions">
                            <button class="btn btn-danger btn-sm" onclick="backgroundTasksManager.cancelTask('${task.task_type}')">
                                <i class="fas fa-stop"></i> Отменить
                            </button>
                        </div>
                    </div>
                `).join('');
            } else {
                activeTasksContainer.innerHTML = '<p class="no-tasks">Нет активных задач</p>';
            }
        }

        // Обновляем список завершенных задач
        const completedTasksContainer = document.getElementById('completed-tasks-list');
        if (completedTasksContainer) {
            if (data.recent_completed_tasks && data.recent_completed_tasks.length > 0) {
                completedTasksContainer.innerHTML = data.recent_completed_tasks.map(task => `
                    <div class="task-item completed-task ${task.status}">
                        <div class="task-header">
                            <h4>${task.task_type}</h4>
                            <span class="task-status ${task.status}">${this.getStatusText(task.status)}</span>
                        </div>
                        <div class="task-details">
                            <p><strong>Описание:</strong> ${task.description || 'Нет описания'}</p>
                            <p><strong>Завершено:</strong> ${task.end_time ? new Date(task.end_time).toLocaleString() : 'Неизвестно'}</p>
                            ${task.error_message ? `<p><strong>Ошибка:</strong> <span class="error-text">${task.error_message}</span></p>` : ''}
                        </div>
                    </div>
                `).join('');
            } else {
                completedTasksContainer.innerHTML = '<p class="no-tasks">Нет завершенных задач</p>';
            }
        }

        // Обновляем статистику
        const statsContainer = document.getElementById('tasks-stats');
        if (statsContainer) {
            statsContainer.innerHTML = `
                <div class="stats-grid">
                    <div class="stat-item">
                        <div class="stat-number">${data.total_active}</div>
                        <div class="stat-label">Активных задач</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-number">${data.total_completed}</div>
                        <div class="stat-label">Завершенных задач</div>
                    </div>
                </div>
            `;
        }
    }

    getStatusText(status) {
        const statusMap = {
            'idle': 'Ожидает',
            'processing': 'Выполняется',
            'running': 'Запущена',
            'initializing': 'Инициализация',
            'completed': 'Завершена',
            'error': 'Ошибка',
            'cancelled': 'Отменена'
        };
        return statusMap[status] || status;
    }

    calculateProgressFromStep(currentStep) {
        if (!currentStep) return 0;
        
        // Ищем паттерн (число/число) в current_step, учитывая возможный текст между числами
        const match = currentStep.match(/\((\d+(?:,\d+)*)\/(\d+(?:,\d+)*)/);
        if (match) {
            const processed = parseInt(match[1].replace(/,/g, ''));
            const total = parseInt(match[2].replace(/,/g, ''));
            
            if (total > 0) {
                return Math.round((processed / total) * 100);
            }
        }
        
        // Если паттерн не найден, возвращаем 0
        return 0;
    }

    async cancelTask(taskType) {
        try {
            const resp = await fetch(`/vulnanalizer/api/background-tasks/${taskType}/cancel`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('auth_token')}`
                }
            });
            
            if (resp.ok) {
                const data = await resp.json();
                if (data.success) {
                    this.showNotification(`Задача ${taskType} отменена`, 'success');
                    // Перезагружаем данные
                    this.loadBackgroundTasksData();
                } else {
                    this.showNotification(data.message || 'Ошибка отмены задачи', 'error');
                }
            } else {
                this.showNotification('Ошибка отмены задачи', 'error');
            }
        } catch (err) {

            this.showNotification('Ошибка отмены задачи', 'error');
        }
    }

    async clearBackgroundTasks() {
        if (!confirm('Вы уверены, что хотите очистить все завершенные фоновые задачи? Это действие нельзя отменить.')) {
            return;
        }

        try {
            const token = localStorage.getItem('auth_token');
            // Используем относительный URL, как и кнопка "Обновить"
            const url = '/vulnanalizer/api/background-tasks/clear';
            const response = await fetch(url, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                }
            });

            const result = await response.json();

            if (result.success) {
                this.showNotification(result.message, 'success');
                // Обновляем данные после очистки
                this.loadBackgroundTasksData();
            } else {
                this.showNotification(result.message || 'Ошибка очистки задач', 'error');
            }
        } catch (err) {
            
            // Проверяем, является ли ошибка проблемой смешанного контента
            if (err.message.includes('Failed to fetch') || err.message.includes('ERR_SSL_PROTOCOL_ERROR')) {
                this.showNotification('Ошибка: Проблема с протоколом. Откройте страницу по адресу http://localhost:8000/background-tasks', 'error');
            } else {
                this.showNotification('Ошибка очистки задач: ' + err.message, 'error');
            }
        }
    }

    showNotification(message, type = 'info') {
        if (window.uiManager && window.uiManager.showNotification) {
            window.uiManager.showNotification(message, type);
        } else {
            alert(message);
        }
    }

    destroy() {
        this.stopAutoRefresh();
    }
}

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', () => {
    window.backgroundTasksManager = new BackgroundTasksManager();
});

// Очистка ресурсов при уходе со страницы
window.addEventListener('beforeunload', () => {
    if (window.backgroundTasksManager) {
        window.backgroundTasksManager.destroy();
    }
});
