class LoginManager {
    constructor() {
        this.init();
    }

    init() {
        this.setupForm();
        this.setupTheme();
    }

    setupForm() {
        const form = document.getElementById('login-form');
        const errorDiv = document.getElementById('login-error');

        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const formData = new FormData(form);
            const username = formData.get('username');
            const password = formData.get('password');

            try {
                const response = await fetch('/auth/api/login', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/x-www-form-urlencoded',
                    },
                    body: `username=${encodeURIComponent(username)}&password=${encodeURIComponent(password)}`
                });

                if (response.ok) {
                    const data = await response.json();
                    console.log('🔐 Данные авторизации получены:', data);
                    
                    // Сохраняем токен с единым префиксом stools_ для всех сервисов
                    localStorage.setItem('auth_token', data.access_token);
                    localStorage.setItem('stools_user_info', JSON.stringify(data.user));
                    
                    console.log('💾 Токены сохранены в localStorage');
                    console.log('🔑 auth_token:', localStorage.getItem('auth_token') ? 'сохранен' : 'НЕ СОХРАНЕН');
                    console.log('👤 stools_user_info:', localStorage.getItem('stools_user_info') ? 'сохранен' : 'НЕ СОХРАНЕН');
                    
                    // Перенаправляем на главную страницу
                    console.log('🚀 Перенаправляем на /vulnanalizer/');
                    window.location.href = '/vulnanalizer/';
                } else {
                    const errorData = await response.json();
                    this.showError(errorData.detail || 'Ошибка входа');
                }
            } catch (error) {
                console.error('Login error:', error);
                this.showError('Ошибка соединения с сервером');
            }
        });
    }

    showError(message) {
        const errorDiv = document.getElementById('login-error');
        errorDiv.textContent = message;
        errorDiv.style.display = 'block';
        
        // Скрываем ошибку через 5 секунд
        setTimeout(() => {
            errorDiv.style.display = 'none';
        }, 5000);
    }

    setupTheme() {
        // Загружаем сохраненную тему
        const savedTheme = localStorage.getItem('theme') || 'light';
        document.body.className = `${savedTheme}-theme`;
    }
}

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', () => {
    new LoginManager();
});
