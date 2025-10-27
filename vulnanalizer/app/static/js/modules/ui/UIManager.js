/**
 * UIManager - Менеджер пользовательского интерфейса
 * v=7.5
 */
class UIManager {
    constructor(app) {
        this.app = app;
        this.storage = app.storage;
        this.eventManager = app.eventManager;
    }

    // Инициализация темы
    initTheme() {
        const savedTheme = this.storage.get('theme') || 'light';
        document.body.classList.remove('light-theme', 'dark-theme');
        document.body.classList.add(`${savedTheme}-theme`);
        this.updateThemeText(savedTheme);
    }

    // Обновление текста темы
    updateThemeText(theme) {
        const themeText = this.app.getElementSafe('theme-text');
        if (themeText) {
            if (theme === 'dark') {
                themeText.textContent = 'Светлая тема';
            } else {
                themeText.textContent = 'Темная тема';
            }
        }
    }

    // Переключение темы
    toggleTheme() {
        const currentTheme = document.body.classList.contains('dark-theme') ? 'dark' : 'light';
        const newTheme = currentTheme === 'light' ? 'dark' : 'light';
        
        // Удаляем старые классы и добавляем новый
        document.body.classList.remove('light-theme', 'dark-theme');
        document.body.classList.add(`${newTheme}-theme`);
        
        this.storage.set('theme', newTheme);
        this.updateThemeText(newTheme);
        
        // Эмитируем событие смены темы
        if (this.eventManager) {
            this.eventManager.emit('themeChanged', { theme: newTheme });
        }
    }

    // Обновление хлебных крошек
    updateBreadcrumb(page) {
        // Заголовки страниц больше не обновляются
        // Только обновляем статусы
    }

    // Инициализация активной страницы
    initializeActivePage() {
        const currentPage = window.location.hash.replace('#', '') || 'analysis';
        const targetElement = this.app.getElementSafe(`${currentPage}-page`);
        const analysisPage = this.app.getElementSafe('analysis-page');
        
        if (targetElement) {
            targetElement.classList.add('active');
        } else if (analysisPage) {
            analysisPage.classList.add('active');
        }
        
        const analysisTab = document.getElementById('analysis-tab');
        if (analysisTab) {
            analysisTab.classList.add('active');
        }
    }

    // Обновление видимости сайдбара
    updateSidebarVisibility(isAdmin) {
        const adminTabs = ['users', 'background-tasks', 'settings'];
        
        adminTabs.forEach(tabId => {
            const tab = document.getElementById(`${tabId}-tab`);
            if (tab) {
                if (isAdmin) {
                    tab.style.display = 'block';
                } else {
                    tab.style.display = 'none';
                }
            }
        });
    }

    // Обновление видимости меню
    updateMenuVisibility(isAdmin) {
        const adminMenuItems = ['users-link', 'background-tasks-link', 'settings-link'];
        
        adminMenuItems.forEach(menuId => {
            const menuItem = document.getElementById(menuId);
            if (menuItem) {
                if (isAdmin) {
                    menuItem.style.display = 'block';
                } else {
                    menuItem.style.display = 'none';
                }
            }
        });
    }

    // Переключение страниц
    switchPage(page) {
        // Заголовки страниц больше не обновляются
        // Только обновляем статусы
        
        switch(page) {
            case 'analysis':
                this.app.updateHostsStatus();
                break;
            case 'hosts':
                this.app.updateHostsStatus();
                this.app.checkActiveImportTasks(); // Проверяем активные задачи импорта
                // Проверяем статус файла VM
                if (this.app.hostsService) {
                    this.app.hostsService.checkVMFileStatus();
                }
                break;
            case 'settings':
                // Загружаем настройки VulnAnalizer
                this.app.loadDatabaseSettings();
                break;
            case 'background-tasks':
                // Перенаправляем на отдельную страницу фоновых задач
                window.location.href = '/background-tasks/';
                break;
            default:
                break;
        }
    }

    // Выход из системы
    logout() {
        // Очищаем данные пользователя
        this.storage.remove('auth_token');
        this.storage.remove('user_info');
        
        // Перенаправляем на страницу входа
        window.location.href = '/auth/';
    }

    // Показать прогресс операции
    showOperationProgress(operation, message, progress = 0) {
        const progressDiv = this.app.getElementSafe(`${operation}-progress`);
        if (progressDiv) {
            progressDiv.style.display = 'block';
            progressDiv.innerHTML = `
                <div class="operation-progress">
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: ${progress}%"></div>
                    </div>
                    <div class="progress-message">${message}</div>
                </div>
            `;
        }
    }

    // Обновить прогресс операции
    updateOperationProgress(operation, message, progress, detail = '') {
        const progressDiv = this.app.getElementSafe(`${operation}-progress`);
        if (progressDiv) {
            const progressFill = progressDiv.querySelector('.progress-fill');
            const progressMessage = progressDiv.querySelector('.progress-message');
            
            if (progressFill) {
                progressFill.style.width = `${progress}%`;
            }
            
            if (progressMessage) {
                progressMessage.textContent = message;
                if (detail) {
                    progressMessage.innerHTML += `<br><small>${detail}</small>`;
                }
            }
        }
    }

    // Показать завершение операции
    showOperationComplete(operation, title, message) {
        const progressDiv = this.app.getElementSafe(`${operation}-progress`);
        if (progressDiv) {
            progressDiv.innerHTML = `
                <div class="operation-complete">
                    <div class="complete-icon">✓</div>
                    <div class="complete-title">${title}</div>
                    <div class="complete-message">${message}</div>
                </div>
            `;
            
            // Скрываем через 3 секунды
            setTimeout(() => {
                progressDiv.style.display = 'none';
            }, 3000);
        }
    }

    // Показать ошибку операции
    showOperationError(operation, title, message) {
        const progressDiv = this.app.getElementSafe(`${operation}-progress`);
        if (progressDiv) {
            progressDiv.innerHTML = `
                <div class="operation-error">
                    <div class="error-icon">✗</div>
                    <div class="error-title">${title}</div>
                    <div class="error-message">${message}</div>
                </div>
            `;
            
            // Скрываем через 5 секунд
            setTimeout(() => {
                progressDiv.style.display = 'none';
            }, 5000);
        }
    }

    // Загрузка данных о фоновых задачах
    async loadBackgroundTasks() {
        const contentDiv = document.getElementById('background-tasks-content');
        if (!contentDiv) {
            console.error('❌ Не найден контейнер для задач');
            return;
        }
        
        try {
            // Показываем спиннер
            contentDiv.innerHTML = `
                <div class="loading-spinner">
                    <i class="fas fa-spinner fa-spin"></i>
                    <span>Загрузка задач...</span>
                </div>
            `;
            
            // Загружаем данные через API
            const response = await fetch('/vulnanalizer/api/background-tasks/status', {
                method: 'GET',
                headers: {
                    'Authorization': `Bearer ${this.storage.get('auth_token')}`,
                    'Content-Type': 'application/json'
                }
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            
            // Объединяем активные и завершенные задачи
            const allTasks = [
                ...(data.active_tasks || []),
                ...(data.completed_tasks || [])
            ];
            
            this.renderBackgroundTasks(allTasks);
            
        } catch (error) {
            console.error('❌ Ошибка загрузки фоновых задач:', error);
            contentDiv.innerHTML = `
                <div class="error-message">
                    <i class="fas fa-exclamation-triangle"></i>
                    <span>Ошибка загрузки задач: ${error.message}</span>
                </div>
            `;
        }
    }

    // Отрисовка фоновых задач
    renderBackgroundTasks(tasks) {
        const contentDiv = document.getElementById('background-tasks-content');
        if (!contentDiv) {
            console.error('❌ Не найден контейнер для задач');
            return;
        }
        
        if (!tasks || tasks.length === 0) {
            contentDiv.innerHTML = `
                <div class="no-tasks-message">
                    <i class="fas fa-check-circle"></i>
                    <span>Нет активных задач</span>
                </div>
            `;
            return;
        }
        
        contentDiv.innerHTML = tasks.map(task => `
            <div class="content-block task-item ${task.status}">
                <div class="content-block-header">
                    <div class="content-block-title">
                        <i class="fas fa-tasks"></i>
                        <span>${task.task_type}</span>
                    </div>
                    <div class="content-block-actions">
                        <span class="badge ${task.status}">${task.status}</span>
                    </div>
                </div>
                <div class="content-block-body">
                    <p><strong>Описание:</strong> ${task.description || 'Нет описания'}</p>
                    <p><strong>Создано:</strong> ${task.created_at ? new Date(task.created_at).toLocaleString() : 'Неизвестно'}</p>
                    ${task.updated_at ? `<p><strong>Обновлено:</strong> ${new Date(task.updated_at).toLocaleString()}</p>` : ''}
                    ${task.current_step ? `<p><strong>Текущий шаг:</strong> ${task.current_step}</p>` : ''}
                    ${task.progress_percent !== null && task.progress_percent !== undefined ? `
                        <div class="progress-bar">
                            <div class="progress-track">
                                <div class="progress-fill" style="width: ${task.progress_percent}%"></div>
                            </div>
                            <div class="progress-text">${task.progress_percent}%</div>
                        </div>
                    ` : ''}
                    ${task.status === 'running' ? `
                        <div class="task-actions">
                            <button onclick="cancelTask('${task.id}')" class="btn btn-danger btn-sm">
                                <i class="fas fa-stop"></i> Остановить
                            </button>
                        </div>
                    ` : ''}
                    ${task.total_records ? `<p><strong>Записей:</strong> ${task.processed_records || 0}/${task.total_records}</p>` : ''}
                    ${task.error_message ? `<p class="error-text"><strong>Ошибка:</strong> ${task.error_message}</p>` : ''}
                </div>
            </div>
        `).join('');
    }

    // Отмена задачи
    async cancelTask(taskId) {
        try {
            const response = await fetch(`/vulnanalizer/api/background-tasks/${taskId}/cancel`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${this.storage.get('auth_token')}`
                }
            });
            
            if (response.ok) {
                this.app.notificationManager.showNotification('Задача отменена', 'success');
                this.loadBackgroundTasks(); // Обновляем список
            } else {
                const error = await response.json();
                this.app.notificationManager.showNotification(`Ошибка отмены задачи: ${error.detail}`, 'error');
            }
        } catch (error) {
            console.error('Ошибка отмены задачи:', error);
            this.app.notificationManager.showNotification('Ошибка отмены задачи', 'error');
        }
    }
}

// Глобальная функция для отмены задач
window.cancelTask = function(taskId) {
    if (window.app && window.app.uiManager) {
        window.app.uiManager.cancelTask(taskId);
    }
};

// Экспорт для использования в других модулях
if (typeof module !== 'undefined' && module.exports) {
    module.exports = UIManager;
} else {
    window.UIManager = UIManager;
}
