/**
 * STools UI Manager - Универсальный менеджер интерфейса
 * Управляет всеми UI компонентами: верхняя панель, боковая панель, темы, выпадающие меню
 */

class UIManager {
    constructor() {
        this.sidebarCollapsed = false;
        this.currentTheme = 'light';
        this.dropdowns = new Map();
        

        this.init();
    }

    init() {
        this.initTheme();
        this.initSidebar();
        this.initDropdowns();
        this.initTopPanel();
        this.initDropZones();
        this.bindGlobalEvents();
    }

    // ===== ТЕМЫ =====
    initTheme() {
        this.currentTheme = localStorage.getItem('theme') || 'light';
        this.applyTheme(this.currentTheme);
        this.updateThemeUI();
    }

    applyTheme(theme) {
        document.body.className = `${theme}-theme`;
        this.currentTheme = theme;
        localStorage.setItem('theme', theme);
    }

    toggleTheme() {
        const newTheme = this.currentTheme === 'light' ? 'dark' : 'light';
        this.applyTheme(newTheme);
        this.updateThemeUI();
    }

    updateThemeUI() {
        const themeText = document.getElementById('theme-text');
        const themeIcon = document.querySelector('#theme-link i');
        
        if (themeText && themeIcon) {
            if (this.currentTheme === 'dark') {
                themeText.textContent = 'Темная';
                themeIcon.className = 'fas fa-moon';
            } else {
                themeText.textContent = 'Светлая';
                themeIcon.className = 'fas fa-sun';
            }
        }
    }

    // ===== БОКОВАЯ ПАНЕЛЬ =====
    initSidebar() {
        const sidebar = document.getElementById('sidebar');
        const sidebarToggle = document.getElementById('sidebar-toggle');
        
        if (!sidebar || !sidebarToggle) return;

        // Загружаем состояние
        this.sidebarCollapsed = localStorage.getItem('sidebar_collapsed') === 'true';
        this.updateSidebarState();

        // Обработчик кнопки
        sidebarToggle.addEventListener('click', () => {
            this.toggleSidebar();
        });
    }

    toggleSidebar() {
        this.sidebarCollapsed = !this.sidebarCollapsed;
        this.updateSidebarState();
        localStorage.setItem('sidebar_collapsed', this.sidebarCollapsed.toString());
    }

    updateSidebarState() {
        const sidebar = document.getElementById('sidebar');
        const toggleIcon = document.querySelector('#sidebar-toggle i');
        
        if (this.sidebarCollapsed) {
            sidebar.classList.add('collapsed');
            document.body.classList.add('layout-sidebar-collapsed');
            if (toggleIcon) {
                toggleIcon.className = 'fas fa-chevron-right';
            }
        } else {
            sidebar.classList.remove('collapsed');
            document.body.classList.remove('layout-sidebar-collapsed');
            if (toggleIcon) {
                toggleIcon.className = 'fas fa-chevron-left';
            }
        }
    }

    // ===== ВЫПАДАЮЩИЕ МЕНЮ =====
    initDropdowns() {
        // Настройки
        this.initDropdown('settings-toggle', 'settings-dropdown');
        
        // Пользователь
        this.initDropdown('user-toggle', 'user-dropdown');
    }

    initDropdown(toggleId, dropdownId) {
        const toggle = document.getElementById(toggleId);
        const dropdown = document.getElementById(dropdownId);
        
        if (!toggle || !dropdown) {
            return;
        }

        this.dropdowns.set(toggleId, { toggle, dropdown, isOpen: false });

        toggle.addEventListener('click', (e) => {
            e.stopPropagation();
            this.toggleDropdown(toggleId);
        });

        // Закрытие при клике вне меню
        document.addEventListener('click', (e) => {
            if (!dropdown.contains(e.target) && !toggle.contains(e.target)) {
                this.closeDropdown(toggleId);
            }
        });
    }

    toggleDropdown(dropdownId) {
        const dropdown = this.dropdowns.get(dropdownId);
        if (!dropdown) {
            return;
        }

        if (dropdown.isOpen) {
            this.closeDropdown(dropdownId);
        } else {
            this.openDropdown(dropdownId);
        }
    }

    openDropdown(dropdownId) {
        const dropdown = this.dropdowns.get(dropdownId);
        if (!dropdown) {
            return;
        }

        // Закрываем все другие меню
        this.dropdowns.forEach((item, id) => {
            if (id !== dropdownId) {
                this.closeDropdown(id);
            }
        });

        dropdown.dropdown.classList.add('show');
        dropdown.isOpen = true;
    }

    closeDropdown(dropdownId) {
        const dropdown = this.dropdowns.get(dropdownId);
        if (!dropdown) {
            return;
        }

        dropdown.dropdown.classList.remove('show');
        dropdown.isOpen = false;
    }

    // ===== ВЕРХНЯЯ ПАНЕЛЬ =====
    initTopPanel() {
        this.initSystemTabs();
        this.initUserInfo();
        this.initVersionInfo();
    }

    initSystemTabs() {
        const tabs = document.querySelectorAll('.system-tab');
        tabs.forEach(tab => {
            tab.addEventListener('click', (e) => {
                e.preventDefault();
                this.navigateToSystem(tab);
            });
        });
    }

    navigateToSystem(activeTab) {
        // Убираем активный класс у всех вкладок
        document.querySelectorAll('.system-tab').forEach(tab => {
            tab.classList.remove('active');
        });
        
        // Добавляем активный класс к выбранной вкладке
        activeTab.classList.add('active');

        // Определяем, куда переходить
        const tabId = activeTab.id;
        if (tabId === 'vulnanalizer-tab') {
            window.location.href = '/vulnanalizer/';
        } else if (tabId === 'loganalizer-tab') {
            window.location.href = '/loganalizer/';
        }
    }

    initUserInfo() {
        const userInfo = localStorage.getItem('user_info');
        if (userInfo) {
            try {
                const user = JSON.parse(userInfo);
                const userNameElement = document.getElementById('user-name');
                const userRoleElement = document.querySelector('.user-role');
                const userAvatarElement = document.querySelector('.user-avatar');
                
                if (userNameElement) {
                    userNameElement.textContent = user.username || 'Пользователь';
                }
                
                if (userRoleElement) {
                    userRoleElement.textContent = user.is_admin ? 'Администратор' : 'Пользователь';
                }
                
                if (userAvatarElement) {
                    userAvatarElement.textContent = (user.username || 'U').charAt(0).toUpperCase();
                }
            } catch (e) {
                console.error('Error parsing user info:', e);
            }
        }
    }

    async initVersionInfo() {
        try {
            // Определяем базовый путь для API в зависимости от текущего приложения
            const currentPath = window.location.pathname;
            let apiBasePath = '/api';
            
            if (currentPath.includes('/vulnanalizer/')) {
                apiBasePath = '/vulnanalizer/api';
            } else if (currentPath.includes('/loganalizer/')) {
                apiBasePath = '/loganalizer/api';
            }
            
            const response = await fetch(`${apiBasePath}/version`);
            
            // Проверяем, что ответ успешный и содержит JSON
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const contentType = response.headers.get('content-type');
            if (!contentType || !contentType.includes('application/json')) {
                throw new Error('Response is not JSON');
            }
            
            const data = await response.json();
            
            // Не перезаписываем версию, если она уже установлена из шаблона
            const versionElement = document.getElementById('app-version');
            if (versionElement && data.version && !versionElement.textContent.includes('v{{ version }}')) {
                versionElement.textContent = `v${data.version}`;
            }
        } catch (error) {
            // Тихо обрабатываем ошибку, не засоряя консоль
            console.debug('Version info not available:', error.message);
            
            // Пытаемся получить версию из API если не удалось из шаблона
            const versionElement = document.getElementById('app-version');
            if (versionElement && !versionElement.textContent.includes('v{{ version }}')) {
                try {
                    const versionResponse = await fetch('/api/version');
                    if (versionResponse.ok) {
                        const versionData = await versionResponse.json();
                        versionElement.textContent = `v${versionData.version}`;
                    } else {
                        versionElement.textContent = 'vНеизвестно';
                    }
                } catch (apiError) {
                    versionElement.textContent = 'vНеизвестно';
                }
            }
        }
    }

    // ===== ГЛОБАЛЬНЫЕ СОБЫТИЯ =====
    bindGlobalEvents() {
        // Обработка выхода
        const logoutLink = document.getElementById('logout-link');
        if (logoutLink) {
            logoutLink.addEventListener('click', (e) => {
                e.preventDefault();
                this.logout();
            });
        }

        // Обработка переключения темы
        const themeLink = document.getElementById('theme-link');
        if (themeLink) {
            themeLink.addEventListener('click', (e) => {
                e.preventDefault();
                this.toggleTheme();
            });
        }

        // Обработка перехода к пользователям
        const usersLink = document.getElementById('users-link');
        if (usersLink) {
            usersLink.addEventListener('click', (e) => {
                e.preventDefault();
                this.navigateToUsers();
            });
        }

        // Обработка перехода к управлению очередями
        const backgroundTasksLink = document.getElementById('background-tasks-link');
        if (backgroundTasksLink) {
            backgroundTasksLink.addEventListener('click', (e) => {
                e.preventDefault();
                this.navigateToBackgroundTasks();
            });
        }

        // Обработка перехода к настройкам системы
        const settingsLink = document.getElementById('settings-link');
        if (settingsLink) {
            settingsLink.addEventListener('click', (e) => {
                e.preventDefault();
                this.navigateToSystemSettings();
            });
        }
    }

    logout() {
        localStorage.removeItem('auth_token');
        localStorage.removeItem('user_info');
        window.location.href = '/auth/';
    }

    navigateToUsers() {
        // Закрываем выпадающее меню
        this.closeDropdown('settings-toggle');
        
        // Переходим к странице пользователей
        window.location.href = '/users/';
    }

    navigateToBackgroundTasks() {
        // Закрываем выпадающее меню
        this.closeDropdown('settings-toggle');
        
        // Переходим к странице управления очередями
        window.location.href = '/background-tasks/';
    }

    navigateToSystemSettings() {
        // Закрываем выпадающее меню
        this.closeDropdown('settings-toggle');
        
        // Переходим к странице настроек системы
        window.location.href = '/settings/';
    }

    showUsersPage() {
        // Показываем страницу пользователей (если есть такая функциональность)
        const usersPage = document.getElementById('users-page');
        if (usersPage) {
            // Скрываем все страницы
            document.querySelectorAll('.page-content').forEach(page => {
                page.classList.remove('active');
            });
            
            // Показываем страницу пользователей
            usersPage.classList.add('active');
            
            // Активируем соответствующую вкладку в боковом меню
            const usersTab = document.querySelector('[data-page="users"]');
            if (usersTab) {
                document.querySelectorAll('.sidebar-tab').forEach(tab => {
                    tab.classList.remove('active');
                });
                usersTab.classList.add('active');
            }
        }
    }

    // ===== DROP ZONES =====
    initDropZones() {
        const fileInputs = document.querySelectorAll('input[type="file"]');
        
        fileInputs.forEach(input => {
            this.setupDropZone(input);
        });
    }

    setupDropZone(input) {
        // Предотвращаем стандартное поведение браузера
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            input.addEventListener(eventName, this.preventDefaults, false);
        });

        // Обработчики для визуальной обратной связи
        ['dragenter', 'dragover'].forEach(eventName => {
            input.addEventListener(eventName, () => {
                input.classList.add('drag-over');
            }, false);
        });

        ['dragleave', 'drop'].forEach(eventName => {
            input.addEventListener(eventName, () => {
                input.classList.remove('drag-over');
            }, false);
        });

        // Обработка сброшенных файлов
        input.addEventListener('drop', (e) => {
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                input.files = files;
                // Вызываем событие change для активации обработчиков
                const event = new Event('change', { bubbles: true });
                input.dispatchEvent(event);
            }
        }, false);
    }

    preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }



    // ===== УТИЛИТЫ =====
    showNotification(message, type = 'info') {
        // Создаем уведомление
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.textContent = message;
        
        // Добавляем в контейнер уведомлений
        const container = document.getElementById('notifications') || document.body;
        container.appendChild(notification);
        
        // Показываем
        setTimeout(() => {
            notification.classList.add('show');
        }, 100);
        
        // Скрываем через 5 секунд
        setTimeout(() => {
            notification.classList.remove('show');
            setTimeout(() => {
                container.removeChild(notification);
            }, 300);
        }, 5000);
    }
}

// Экспортируем для использования в других модулях
window.UIManager = UIManager;
