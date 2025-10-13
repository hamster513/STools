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
}

// Экспорт для использования в других модулях
if (typeof module !== 'undefined' && module.exports) {
    module.exports = UIManager;
} else {
    window.UIManager = UIManager;
}
