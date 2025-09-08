/**
 * Модуль утилит и хелперов
 * v=2.1
 */
class UtilsModule {
    constructor(app) {
        this.app = app;
    }

    /**
     * Форматирование времени
     * @param {number} seconds - Время в секундах
     * @returns {string} Отформатированное время
     */
    formatTime(seconds) {
        if (!seconds || seconds < 0) return '-';
        
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        const secs = Math.floor(seconds % 60);
        
        if (hours > 0) {
            return `${hours}ч ${minutes}м ${secs}с`;
        } else if (minutes > 0) {
            return `${minutes}м ${secs}с`;
        } else {
            return `${secs}с`;
        }
    }

    /**
     * Форматирование размера файла
     * @param {number} bytes - Размер в байтах
     * @returns {string} Отформатированный размер
     */
    formatFileSize(bytes) {
        if (bytes === 0) return '0 Б';
        
        const k = 1024;
        const sizes = ['Б', 'КБ', 'МБ', 'ГБ', 'ТБ'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    /**
     * Форматирование числа с разделителями
     * @param {number} num - Число для форматирования
     * @returns {string} Отформатированное число
     */
    formatNumber(num) {
        return num.toLocaleString('ru-RU');
    }

    /**
     * Форматирование даты
     * @param {string|Date} date - Дата для форматирования
     * @returns {string} Отформатированная дата
     */
    formatDate(date) {
        if (!date) return '-';
        
        const d = new Date(date);
        return d.toLocaleString('ru-RU');
    }

    /**
     * Форматирование CVSS с версией
     * @param {number} cvss - CVSS значение
     * @param {string} source - Источник CVSS
     * @returns {string} Отформатированный CVSS
     */
    formatCVSS(cvss, source) {
        if (!cvss) return 'N/A';
        
        if (source && source.includes('v2')) {
            return `v2: ${cvss}`;
        } else if (source && source.includes('v3')) {
            return `v3: ${cvss}`;
        } else {
            return `${cvss}`;
        }
    }

    /**
     * Форматирование EPSS в процентах
     * @param {number} epss - EPSS значение (0-1)
     * @returns {string} EPSS в процентах
     */
    formatEPSS(epss) {
        if (epss === null || epss === undefined) return 'N/A';
        return `${(epss * 100).toFixed(2)}%`;
    }

    /**
     * Форматирование риска
     * @param {number} risk - Риск в процентах
     * @returns {string} Отформатированный риск
     */
    formatRisk(risk) {
        if (risk === null || risk === undefined) return 'N/A';
        
        if (risk < 0.1) {
            return risk.toFixed(2);
        } else if (risk < 1) {
            return risk.toFixed(1);
        } else {
            return Math.round(risk).toString();
        }
    }

    /**
     * Получение класса риска
     * @param {number} risk - Риск в процентах
     * @returns {string} CSS класс риска
     */
    getRiskClass(risk) {
        if (risk >= 70) return 'high-risk';
        if (risk >= 40) return 'medium-risk';
        return 'low-risk';
    }

    /**
     * Получение класса критичности
     * @param {string} criticality - Критичность
     * @returns {string} CSS класс критичности
     */
    getCriticalityClass(criticality) {
        if (!criticality) return '';
        return `criticality-${criticality.toLowerCase()}`;
    }

    /**
     * Валидация IP адреса
     * @param {string} ip - IP адрес для проверки
     * @returns {boolean} Результат валидации
     */
    isValidIP(ip) {
        const ipv4Regex = /^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$/;
        const ipv6Regex = /^(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}$/;
        
        return ipv4Regex.test(ip) || ipv6Regex.test(ip);
    }

    /**
     * Валидация CVE ID
     * @param {string} cve - CVE ID для проверки
     * @returns {boolean} Результат валидации
     */
    isValidCVE(cve) {
        const cveRegex = /^CVE-\d{4}-\d{4,}$/;
        return cveRegex.test(cve);
    }

    /**
     * Валидация email
     * @param {string} email - Email для проверки
     * @returns {boolean} Результат валидации
     */
    isValidEmail(email) {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return emailRegex.test(email);
    }

    /**
     * Валидация пароля
     * @param {string} password - Пароль для проверки
     * @returns {object} Результат валидации с деталями
     */
    validatePassword(password) {
        const result = {
            isValid: true,
            errors: []
        };

        if (!password) {
            result.isValid = false;
            result.errors.push('Пароль не может быть пустым');
            return result;
        }

        if (password.length < 8) {
            result.isValid = false;
            result.errors.push('Пароль должен содержать минимум 8 символов');
        }

        if (!/[A-Z]/.test(password)) {
            result.isValid = false;
            result.errors.push('Пароль должен содержать хотя бы одну заглавную букву');
        }

        if (!/[a-z]/.test(password)) {
            result.isValid = false;
            result.errors.push('Пароль должен содержать хотя бы одну строчную букву');
        }

        if (!/\d/.test(password)) {
            result.isValid = false;
            result.errors.push('Пароль должен содержать хотя бы одну цифру');
        }

        return result;
    }

    /**
     * Дебаунс функция
     * @param {Function} func - Функция для выполнения
     * @param {number} wait - Время ожидания в миллисекундах
     * @returns {Function} Дебаунсированная функция
     */
    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    /**
     * Троттлинг функция
     * @param {Function} func - Функция для выполнения
     * @param {number} limit - Лимит времени в миллисекундах
     * @returns {Function} Троттлированная функция
     */
    throttle(func, limit) {
        let inThrottle;
        return function() {
            const args = arguments;
            const context = this;
            if (!inThrottle) {
                func.apply(context, args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        };
    }

    /**
     * Копирование в буфер обмена
     * @param {string} text - Текст для копирования
     * @returns {Promise<boolean>} Результат копирования
     */
    async copyToClipboard(text) {
        try {
            await navigator.clipboard.writeText(text);
            return true;
        } catch (err) {
            return false;
        }
    }

    /**
     * Скачивание файла
     * @param {Blob} blob - Blob для скачивания
     * @param {string} filename - Имя файла
     */
    downloadFile(blob, filename) {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
    }

    /**
     * Генерация случайного ID
     * @param {number} length - Длина ID
     * @returns {string} Случайный ID
     */
    generateId(length = 8) {
        const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
        let result = '';
        for (let i = 0; i < length; i++) {
            result += chars.charAt(Math.floor(Math.random() * chars.length));
        }
        return result;
    }

    /**
     * Проверка поддержки функций браузера
     * @returns {object} Объект с поддержкой функций
     */
    checkBrowserSupport() {
        return {
            fetch: typeof fetch !== 'undefined',
            localStorage: typeof localStorage !== 'undefined',
            sessionStorage: typeof sessionStorage !== 'undefined',
            clipboard: navigator.clipboard && typeof navigator.clipboard.writeText === 'function',
            fileReader: typeof FileReader !== 'undefined',
            webWorkers: typeof Worker !== 'undefined',
            serviceWorkers: 'serviceWorker' in navigator
        };
    }

    /**
     * Получение информации о браузере
     * @returns {object} Информация о браузере
     */
    getBrowserInfo() {
        const userAgent = navigator.userAgent;
        let browser = 'Unknown';
        let version = 'Unknown';

        if (userAgent.includes('Chrome')) {
            browser = 'Chrome';
            version = userAgent.match(/Chrome\/(\d+)/)?.[1] || 'Unknown';
        } else if (userAgent.includes('Firefox')) {
            browser = 'Firefox';
            version = userAgent.match(/Firefox\/(\d+)/)?.[1] || 'Unknown';
        } else if (userAgent.includes('Safari')) {
            browser = 'Safari';
            version = userAgent.match(/Version\/(\d+)/)?.[1] || 'Unknown';
        } else if (userAgent.includes('Edge')) {
            browser = 'Edge';
            version = userAgent.match(/Edge\/(\d+)/)?.[1] || 'Unknown';
        }

        return {
            browser,
            version,
            userAgent,
            language: navigator.language,
            platform: navigator.platform,
            cookieEnabled: navigator.cookieEnabled,
            onLine: navigator.onLine
        };
    }

    /**
     * Логирование с уровнем
     * @param {string} level - Уровень логирования
     * @param {string} message - Сообщение
     * @param {any} data - Дополнительные данные
     */
    log(level, message, data = null) {
        // Логирование отключено
    }

    /**
     * Получение логов
     * @returns {Array} Массив логов
     */
    getLogs() {
        try {
            return JSON.parse(localStorage.getItem('app_logs') || '[]');
        } catch (err) {
            return [];
        }
    }

    /**
     * Очистка логов
     */
    clearLogs() {
        try {
            localStorage.removeItem('app_logs');
        } catch (err) {
        }
    }
}

// Экспорт модуля
if (typeof module !== 'undefined' && module.exports) {
    module.exports = UtilsModule;
} else {
    window.UtilsModule = UtilsModule;
}
