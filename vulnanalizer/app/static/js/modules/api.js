/**
 * Модуль для работы с API
 */
class ApiModule {
    constructor(app) {
        this.app = app;
        this.basePath = this.getApiBasePath();
    }

    /**
     * Получение базового пути для API
     */
    getApiBasePath() {
        const path = window.location.pathname;
        if (path.startsWith('/vulnanalizer/')) {
            return '/vulnanalizer/api';
        }
        return '/api';
    }

    /**
     * Базовый метод для HTTP запросов
     * @param {string} endpoint - Конечная точка API
     * @param {Object} options - Опции запроса
     */
    async request(endpoint, options = {}) {
        const url = `${this.basePath}${endpoint}`;
        
        const token = localStorage.getItem('auth_token');
        
        const defaultOptions = {
            headers: {
                'Content-Type': 'application/json',
                ...(token && { 'Authorization': `Bearer ${token}` }),
                ...options.headers
            }
        };

        const requestOptions = { ...defaultOptions, ...options };

        try {
            const response = await fetch(url, requestOptions);
            
            // Проверяем статус ответа
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            // Проверяем тип контента
            const contentType = response.headers.get('content-type');
            if (contentType && contentType.includes('application/json')) {
                return await response.json();
            } else if (contentType && contentType.includes('application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')) {
                // Для Excel файлов возвращаем Blob
                return await response.blob();
            } else {
                return await response.text();
            }
        } catch (error) {
            console.error(`API request error for ${endpoint}:`, error);
            throw error;
        }
    }

    /**
     * GET запрос
     * @param {string} endpoint - Конечная точка API
     * @param {Object} params - Параметры запроса
     */
    async get(endpoint, params = {}) {
        const queryString = new URLSearchParams(params).toString();
        const url = queryString ? `${endpoint}?${queryString}` : endpoint;
        
        return this.request(url, { method: 'GET' });
    }

    /**
     * POST запрос
     * @param {string} endpoint - Конечная точка API
     * @param {Object} data - Данные для отправки
     */
    async post(endpoint, data = null) {
        const options = { method: 'POST' };
        
        if (data) {
            if (data instanceof FormData) {
                // Для FormData убираем Content-Type, браузер сам установит
                delete options.headers['Content-Type'];
                options.body = data;
            } else {
                options.body = JSON.stringify(data);
            }
        }
        
        return this.request(endpoint, options);
    }

    /**
     * PUT запрос
     * @param {string} endpoint - Конечная точка API
     * @param {Object} data - Данные для отправки
     */
    async put(endpoint, data = null) {
        const options = { method: 'PUT' };
        
        if (data) {
            options.body = JSON.stringify(data);
        }
        
        return this.request(endpoint, options);
    }

    /**
     * DELETE запрос
     * @param {string} endpoint - Конечная точка API
     */
    async delete(endpoint) {
        return this.request(endpoint, { method: 'DELETE' });
    }

    // ===== МЕТОДЫ ДЛЯ РАБОТЫ С ХОСТАМИ =====

    /**
     * Получить статус хостов
     */
    async getHostsStatus() {
        return this.get('/hosts/status');
    }

    /**
     * Поиск хостов
     * @param {Object} params - Параметры поиска
     */
    async searchHosts(params) {
        return this.get('/hosts/search', params);
    }

    /**
     * Загрузить хосты из файла
     * @param {File} file - Файл для загрузки
     */
    async uploadHosts(file) {
        const formData = new FormData();
        formData.append('file', file);
        return this.post('/hosts/upload', formData);
    }

    /**
     * Экспорт хостов
     * @param {Object} params - Параметры экспорта
     */
    async exportHosts(params) {
        return this.get('/hosts/export', params);
    }

    /**
     * Очистить таблицу хостов
     */
    async clearHosts() {
        return this.post('/hosts/clear');
    }

    /**
     * Получить прогресс импорта хостов
     */
    async getHostsImportProgress() {
        return this.get('/hosts/import-progress');
    }

    /**
     * Запустить фоновое обновление данных
     */
    async startBackgroundUpdate() {
        return this.post('/hosts/update-data-background-parallel');
    }

    /**
     * Отменить фоновое обновление
     */
    async cancelBackgroundUpdate() {
        return this.post('/hosts/update-data-cancel');
    }

    /**
     * Получить прогресс фонового обновления
     */
    async getBackgroundUpdateProgress() {
        return this.get('/hosts/update-data-progress');
    }

    /**
     * Рассчитать риск для хоста
     * @param {number} hostId - ID хоста
     */
    async calculateHostRisk(hostId) {
        return this.get(`/hosts/${hostId}/risk`);
    }

    // ===== МЕТОДЫ ДЛЯ РАБОТЫ С EPSS =====

    /**
     * Получить статус EPSS
     */
    async getEPSSStatus() {
        return this.get('/epss/status');
    }

    /**
     * Загрузить EPSS из файла
     * @param {File} file - Файл для загрузки
     */
    async uploadEPSS(file) {
        const formData = new FormData();
        formData.append('file', file);
        return this.post('/epss/upload', formData);
    }

    /**
     * Скачать EPSS с сайта
     */
    async downloadEPSS() {
        return this.post('/epss/download');
    }

    /**
     * Очистить таблицу EPSS
     */
    async clearEPSS() {
        return this.post('/epss/clear');
    }

    // ===== МЕТОДЫ ДЛЯ РАБОТЫ С EXPLOITDB =====

    /**
     * Получить статус ExploitDB
     */
    async getExploitDBStatus() {
        return this.get('/exploitdb/status');
    }

    /**
     * Загрузить ExploitDB из файла
     * @param {File} file - Файл для загрузки
     */
    async uploadExploitDB(file) {
        const formData = new FormData();
        formData.append('file', file);
        return this.post('/exploitdb/upload', formData);
    }

    /**
     * Скачать ExploitDB с сайта
     */
    async downloadExploitDB() {
        return this.post('/exploitdb/download');
    }

    /**
     * Очистить таблицу ExploitDB
     */
    async clearExploitDB() {
        return this.post('/exploitdb/clear');
    }

    // ===== МЕТОДЫ ДЛЯ РАБОТЫ С CVE =====

    /**
     * Получить статус CVE
     */
    async getCVEStatus() {
        return this.get('/cve/status');
    }

    /**
     * Загрузить CVE из файла
     * @param {File} file - Файл для загрузки
     */
    async uploadCVE(file) {
        const formData = new FormData();
        formData.append('file', file);
        return this.post('/cve/upload', formData);
    }

    /**
     * Скачать CVE с сайта
     */
    async downloadCVE() {
        return this.post('/cve/download');
    }

    /**
     * Отменить загрузку CVE
     */
    async cancelCVE() {
        return this.post('/cve/cancel');
    }

    /**
     * Получить ссылки для скачивания CVE
     */
    async getCVEDownloadUrls() {
        return this.get('/cve/download-urls');
    }

    /**
     * Очистить таблицу CVE
     */
    async clearCVE() {
        return this.post('/cve/clear');
    }

    // ===== МЕТОДЫ ДЛЯ РАБОТЫ С НАСТРОЙКАМИ =====

    /**
     * Получить настройки
     */
    async getSettings() {
        return this.get('/settings');
    }

    /**
     * Сохранить настройки
     * @param {Object} settings - Настройки для сохранения
     */
    async saveSettings(settings) {
        return this.post('/settings', settings);
    }

    /**
     * Проверить подключение к базе данных
     */
    async testConnection() {
        return this.get('/health');
    }

    /**
     * Получить версию приложения
     */
    async getVersion() {
        return this.get('/version');
    }

    // ===== МЕТОДЫ ДЛЯ РАБОТЫ С VM =====

    /**
     * Получить настройки VM
     */
    async getVMSettings() {
        return this.get('/vm/settings');
    }

    /**
     * Сохранить настройки VM
     * @param {Object} settings - Настройки VM
     */
    async saveVMSettings(settings) {
        return this.post('/vm/settings', settings);
    }

    /**
     * Проверить подключение к VM
     * @param {Object} settings - Настройки для проверки
     */
    async testVMConnection(settings) {
        return this.post('/vm/test-connection', settings);
    }

    /**
     * Импортировать хосты из VM
     */
    async importVMHosts() {
        return this.post('/vm/import');
    }

    /**
     * Получить статус VM
     */
    async getVMStatus() {
        return this.get('/vm/status');
    }

    // ===== МЕТОДЫ ДЛЯ РАБОТЫ С ПОЛЬЗОВАТЕЛЯМИ =====

    /**
     * Получить всех пользователей
     */
    async getAllUsers() {
        return this.get('/users/all');
    }

    /**
     * Создать пользователя
     * @param {Object} userData - Данные пользователя
     */
    async createUser(userData) {
        return this.post('/users/register', userData);
    }

    /**
     * Обновить пользователя
     * @param {number} userId - ID пользователя
     * @param {Object} userData - Данные пользователя
     */
    async updateUser(userId, userData) {
        return this.put(`/users/${userId}/update`, userData);
    }

    /**
     * Изменить пароль пользователя
     * @param {number} userId - ID пользователя
     * @param {Object} passwordData - Данные пароля
     */
    async changeUserPassword(userId, passwordData) {
        return this.put(`/users/${userId}/password`, passwordData);
    }

    /**
     * Удалить пользователя
     * @param {number} userId - ID пользователя
     */
    async deleteUser(userId) {
        return this.delete(`/users/${userId}/delete`);
    }

    // ===== МЕТОДЫ ДЛЯ РАБОТЫ С METASPLOIT =====

    /**
     * Получить статус Metasploit
     */
    async getMetasploitStatus() {
        return this.get('/metasploit/status');
    }

    /**
     * Загрузить файл Metasploit
     * @param {FormData} formData - Данные файла
     */
    async uploadMetasploit(formData) {
        return this.post('/metasploit/upload', formData);
    }

    /**
     * Скачать Metasploit с GitHub
     */
    async downloadMetasploit() {
        return this.post('/metasploit/download');
    }

    /**
     * Отменить загрузку Metasploit
     */
    async cancelMetasploit() {
        return this.post('/metasploit/cancel');
    }

    /**
     * Очистить данные Metasploit
     */
    async clearMetasploit() {
        return this.delete('/metasploit/clear');
    }
}

// Экспорт модуля
if (typeof module !== 'undefined' && module.exports) {
    module.exports = ApiModule;
} else {
    window.ApiModule = ApiModule;
}
