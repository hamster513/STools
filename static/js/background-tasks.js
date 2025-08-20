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
        const token = localStorage.getItem('auth_token');
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

        // Автоматическое обновление каждые 2 секунды
        this.startAutoRefresh();
    }

    startAutoRefresh() {
        // Очищаем предыдущий интервал
        if (this.autoRefreshInterval) {
            clearInterval(this.autoRefreshInterval);
        }

        console.log('Starting auto-refresh for background tasks...');
        
        this.autoRefreshInterval = setInterval(() => {
            this.loadBackgroundTasksData();
        }, 2000); // Обновляем каждые 2 секунды
    }

    stopAutoRefresh() {
        if (this.autoRefreshInterval) {
            clearInterval(this.autoRefreshInterval);
            this.autoRefreshInterval = null;
            console.log('Auto-refresh stopped for background tasks');
        }
    }

    async loadBackgroundTasksData() {
        try {
            console.log('Loading background tasks data...');
            const resp = await fetch('/vulnanalizer/api/background-tasks/status', {
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('auth_token')}`
                }
            });
            
            if (resp.ok) {
                const data = await resp.json();
                console.log('Background tasks data:', data);
                
                this.updateBackgroundTasksUI(data);
            } else {
                console.error('Failed to load background tasks data');
                this.showNotification('Ошибка загрузки данных о фоновых задачах', 'error');
            }
        } catch (err) {
            console.error('Error loading background tasks data:', err);
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
                            <div class="progress-bar">
                                <div class="progress-bar-fill" style="width: ${task.progress_percent}%"></div>
                            </div>
                            <span class="progress-text">${task.progress_percent}%</span>
                        </div>
                        <div class="task-details">
                            <p><strong>Текущий шаг:</strong> ${task.current_step || 'Инициализация...'}</p>
                            <p><strong>Обработано:</strong> ${task.processed_items}/${task.total_items}</p>
                            <p><strong>Обновлено записей:</strong> ${task.updated_records}</p>
                            <p><strong>Начато:</strong> ${task.start_time ? new Date(task.start_time).toLocaleString() : 'Неизвестно'}</p>
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
                            <p><strong>Обработано:</strong> ${task.processed_items}/${task.total_items}</p>
                            <p><strong>Обновлено записей:</strong> ${task.updated_records}</p>
                            <p><strong>Начато:</strong> ${task.start_time ? new Date(task.start_time).toLocaleString() : 'Неизвестно'}</p>
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
            console.error('Error cancelling task:', err);
            this.showNotification('Ошибка отмены задачи', 'error');
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

