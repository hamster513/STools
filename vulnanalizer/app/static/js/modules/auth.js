/**
 * Модуль аутентификации
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
        console.log('checkAuth: token from localStorage:', token ? 'exists' : 'not found');
        
        if (!token) {
            console.log('checkAuth: no token, redirecting to login');
            window.location.href = '/auth/';
            return;
        }

        console.log('checkAuth: checking token with auth service');
        fetch('/auth/api/me', {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        }).then(response => {
            console.log('checkAuth: auth service response status:', response.status);
            if (response.ok) {
                return response.json();
            } else {
                console.log('checkAuth: auth failed, clearing localStorage and redirecting');
                localStorage.removeItem('auth_token');
                localStorage.removeItem('user_info');
                window.location.href = '/auth/';
                throw new Error('Auth failed');
            }
        }).then(userData => {
            console.log('checkAuth: userData from auth service:', userData);
            console.log('checkAuth: userData.user:', userData.user);
            console.log('checkAuth: userData.user.is_admin:', userData.user?.is_admin);
            
            if (userData.user) {
                localStorage.setItem('user_info', JSON.stringify(userData.user));
            } else {
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
                console.error('Error parsing user info:', e);
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
