/**
 * Модуль аутентификации
 * v=2.1
 */
class AuthModule {
    constructor(app) {
        this.app = app;
        this.init();
    }

    init() {
        this.checkAuth();
        this.setupUserMenu();
    }

    checkAuth() {
        const token = localStorage.getItem('auth_token');
        
        if (!token) {
            window.location.href = '/auth/';
            return;
        }

        fetch('/auth/api/me', {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        }).then(response => {
            if (response.ok) {
                return response.json();
            } else {
                localStorage.removeItem('auth_token');
                localStorage.removeItem('user_info');
                window.location.href = '/auth/';
                throw new Error('Auth failed');
            }
        }).then(userData => {
            console.log('🔍 API /auth/api/me вернул:', userData);
            
            if (userData.user) {
                console.log('🔍 Сохраняем userData.user:', userData.user);
                localStorage.setItem('user_info', JSON.stringify(userData.user));
            } else {
                console.log('🔍 Сохраняем userData:', userData);
                localStorage.setItem('user_info', JSON.stringify(userData));
            }
        }).catch((error) => {
            localStorage.removeItem('auth_token');
            localStorage.removeItem('user_info');
            window.location.href = '/auth/';
        });
    }

    setupUserMenu() {
        const userToggle = document.getElementById('user-toggle');
        const userDropdown = document.getElementById('user-dropdown');
        const themeLink = document.getElementById('theme-link');
        const logoutLink = document.getElementById('logout-link');
        const userName = document.getElementById('user-name');

        // Загружаем информацию о пользователе
        const userInfo = localStorage.getItem('user_info');
        if (userInfo) {
            try {
                const user = JSON.parse(userInfo);
                if (userName) {
                    userName.textContent = user.username;
                }
            } catch (e) {
            }
        }

        // Переключение выпадающего меню пользователя
        if (userToggle) {
            userToggle.addEventListener('click', (e) => {
                e.stopPropagation();
                const settingsDropdown = document.getElementById('settings-dropdown');
                if (settingsDropdown) {
                    settingsDropdown.classList.remove('show');
                }
                userDropdown.classList.toggle('show');
            });
        }

        // Закрытие при клике вне меню пользователя
        document.addEventListener('click', (e) => {
            if (userToggle && !userToggle.contains(e.target) && !userDropdown.contains(e.target)) {
                userDropdown.classList.remove('show');
            }
        });

        // Обработка клика по пункту "Тема"
        if (themeLink) {
            themeLink.addEventListener('click', (e) => {
                e.preventDefault();
                this.toggleTheme();
            });
        }

        // Обработка клика по пункту "Выйти"
        if (logoutLink) {
            logoutLink.addEventListener('click', (e) => {
                e.preventDefault();
                this.logout();
            });
        }

        // Устанавливаем текущую тему
        this.updateThemeDisplay();
    }

    toggleTheme() {
        const currentTheme = localStorage.getItem('theme') || 'light';
        const newTheme = currentTheme === 'light' ? 'dark' : 'light';
        
        localStorage.setItem('theme', newTheme);
        document.body.className = `${newTheme}-theme`;
        
        this.updateThemeDisplay();
    }

    updateThemeDisplay() {
        const currentTheme = localStorage.getItem('theme') || 'light';
        const themeText = document.getElementById('theme-text');
        const themeIcon = document.querySelector('#theme-link i');
        
        if (themeText) {
            themeText.textContent = currentTheme === 'light' ? 'Темная' : 'Светлая';
        }
        
        if (themeIcon) {
            themeIcon.className = currentTheme === 'light' ? 'fas fa-moon' : 'fas fa-sun';
        }
        
        document.body.className = `${currentTheme}-theme`;
    }

    logout() {
        localStorage.removeItem('auth_token');
        localStorage.removeItem('user_info');
        window.location.href = '/auth/';
    }
}

// Экспорт модуля
if (typeof module !== 'undefined' && module.exports) {
    module.exports = AuthModule;
} else {
    window.AuthModule = AuthModule;
}
