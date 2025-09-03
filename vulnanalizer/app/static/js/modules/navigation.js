/**
 * Модуль для навигации и UI
 */
class NavigationModule {
    constructor(app) {
        this.app = app;
        this.init();
    }

    init() {
        this.setupNavigation();
        this.setupSidebar();
        this.checkUserPermissions(); // Проверяем права пользователя
    }

    setupNavigation() {
        const sidebarTabs = document.querySelectorAll('.sidebar-tab');
        
        sidebarTabs.forEach(tab => {
            tab.addEventListener('click', async (e) => {
                e.preventDefault();
                
                // Убираем активный класс со всех вкладок
                sidebarTabs.forEach(t => t.classList.remove('active'));
                
                // Добавляем активный класс к текущей вкладке
                tab.classList.add('active');
                
                // Скрываем все страницы
                document.querySelectorAll('.page-content').forEach(page => {
                    page.classList.remove('active');
                });
                
                // Показываем нужную страницу
                const targetPage = tab.getAttribute('data-page');
                const targetElement = document.getElementById(`${targetPage}-page`);
                if (targetElement) {
                    targetElement.classList.add('active');
                } else {
                    console.error(`Page element not found: ${targetPage}-page`);
                }
                
                // Обновляем заголовок страницы
                this.switchPage(targetPage);
                
                // Если переключаемся на страницу настроек, загружаем настройки
                if (targetPage === 'settings') {
                    await this.app.settings.loadDatabaseSettings();
                }
            });
        });
    }

    setupSidebar() {
        const sidebar = document.getElementById('sidebar');
        const sidebarToggle = document.getElementById('sidebar-toggle');
        const container = document.querySelector('.container');
        
        if (!sidebar || !sidebarToggle) return;

        // Функция для обновления иконки
        const updateToggleIcon = (isCollapsed) => {
            const icon = sidebarToggle.querySelector('i');
            if (icon) {
                icon.className = isCollapsed ? 'fas fa-chevron-right' : 'fas fa-chevron-left';
            }
        };

        // Загружаем состояние из localStorage (по умолчанию sidebar развернута)
        const isCollapsed = localStorage.getItem('sidebar_collapsed') === 'true';
        if (isCollapsed) {
            sidebar.classList.add('collapsed');
            document.body.classList.add('sidebar-collapsed');
            updateToggleIcon(true);
        } else {
            // Если состояние не сохранено, считаем что sidebar развернута
            sidebar.classList.remove('collapsed');
            document.body.classList.remove('sidebar-collapsed');
            localStorage.setItem('sidebar_collapsed', 'false');
            updateToggleIcon(false);
        }

        // Обработчик для кнопки сворачивания
        sidebarToggle.addEventListener('click', () => {
            sidebar.classList.toggle('collapsed');
            document.body.classList.toggle('sidebar-collapsed');
            
            // Сохраняем состояние и обновляем иконку
            const isNowCollapsed = sidebar.classList.contains('collapsed');
            localStorage.setItem('sidebar_collapsed', isNowCollapsed.toString());
            updateToggleIcon(isNowCollapsed);
        });
    }

    // ===== ПРОВЕРКА ПРАВ ПОЛЬЗОВАТЕЛЯ =====
    async checkUserPermissions() {
        try {
            // Проверяем права пользователя
            const response = await fetch('/auth/api/me');
            if (response.ok) {
                const user = await response.json();
                this.updateSidebarVisibility(user.is_admin);
            } else {
                // Если не авторизован, скрываем админские вкладки
                this.updateSidebarVisibility(false);
            }
        } catch (error) {
            console.log('Ошибка проверки прав:', error);
            // При ошибке скрываем админские вкладки
            this.updateSidebarVisibility(false);
        }
    }

    updateSidebarVisibility(isAdmin) {
        // Скрываем/показываем админские вкладки в боковом меню
        const adminTabs = [
            'settings' // Вкладка настроек
        ];
        
        adminTabs.forEach(tabName => {
            const tab = document.querySelector(`[data-page="${tabName}"]`);
            if (tab) {
                if (isAdmin) {
                    tab.style.display = 'block';
                } else {
                    tab.style.display = 'none';
                }
            }
        });
    }

    initializeActivePage() {
        // Скрываем все страницы
        const allPages = document.querySelectorAll('.page-content');
        allPages.forEach(page => {
            page.classList.remove('active');
        });
        
        // Показываем первую страницу (analysis) по умолчанию
        const analysisPage = document.getElementById('analysis-page');
        if (analysisPage) {
            analysisPage.classList.add('active');
        }
        
        // Устанавливаем активную вкладку
        const analysisTab = document.querySelector('.sidebar-tab[data-page="analysis"]');
        if (analysisTab) {
            analysisTab.classList.add('active');
        }
    }

    switchPage(page) {
        // Заголовки страниц больше не обновляются
        // Только обновляем статусы
        
        switch(page) {
            case 'analysis':
                this.app.hosts.updateStatus();
                break;
            case 'hosts':
                this.app.hosts.updateStatus();
                break;
            case 'settings':
                this.app.epss.updateStatus();
                this.app.exploitdb.updateStatus();
                break;
            default:
                break;
        }
    }

    updateBreadcrumb(page) {
        // Заголовки страниц больше не обновляются
        // Функция оставлена для совместимости
    }
}

// Экспорт модуля
if (typeof module !== 'undefined' && module.exports) {
    module.exports = NavigationModule;
} else {
    window.NavigationModule = NavigationModule;
}
