/**
 * ApiManager - Централизованное управление API запросами
 * v=7.1
 */
class ApiManager {
    constructor(app) {
        this.app = app;
        this.cache = new Map();
        this.cacheTimeout = 5 * 60 * 1000; // 5 минут
        this.retryAttempts = 3;
        this.retryDelay = 1000;
    }

    // Получение базового пути для API
    getApiBasePath() {
        const path = window.location.pathname;
        if (path.startsWith('/vulnanalizer/')) {
            return '/vulnanalizer/api';
        }
        return '/api';
    }

    // Основной метод для API запросов с кэшированием и повторными попытками
    async request(url, options = {}) {
        const cacheKey = `${url}_${JSON.stringify(options)}`;
        
        // Проверяем кэш
        if (options.method !== 'POST' && options.method !== 'PUT' && options.method !== 'DELETE') {
            const cached = this.getFromCache(cacheKey);
            if (cached) {
                return cached;
            }
        }

        // Выполняем запрос с повторными попытками
        for (let attempt = 1; attempt <= this.retryAttempts; attempt++) {
            try {
                const response = await fetch(url, {
                    ...options,
                    headers: {
                        'Content-Type': 'application/json',
                        ...options.headers
                    }
                });

                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }

                const data = await response.json();
                
                // Кэшируем успешные GET запросы
                if (!options.method || options.method === 'GET') {
                    this.setCache(cacheKey, data);
                }

                return data;
            } catch (error) {
                console.error(`API Request attempt ${attempt} failed:`, error);
                
                if (attempt === this.retryAttempts) {
                    throw error;
                }
                
                // Задержка перед повторной попыткой
                await this.delay(this.retryDelay * attempt);
            }
        }
    }

    // Кэширование
    setCache(key, data) {
        this.cache.set(key, {
            data,
            timestamp: Date.now()
        });
    }

    getFromCache(key) {
        const item = this.cache.get(key);
        if (item && Date.now() - item.timestamp < this.cacheTimeout) {
            return item.data;
        }
        this.cache.delete(key);
        return null;
    }

    // Очистка кэша
    clearCache() {
        this.cache.clear();
    }

    // Утилита для задержки
    async delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    // Специализированные методы для разных типов запросов
    async get(endpoint, params = {}) {
        const url = new URL(this.getApiBasePath() + endpoint, window.location.origin);
        Object.keys(params).forEach(key => url.searchParams.append(key, params[key]));
        
        return this.request(url.toString());
    }

    async post(endpoint, data = {}) {
        return this.request(this.getApiBasePath() + endpoint, {
            method: 'POST',
            body: JSON.stringify(data)
        });
    }

    async put(endpoint, data = {}) {
        return this.request(this.getApiBasePath() + endpoint, {
            method: 'PUT',
            body: JSON.stringify(data)
        });
    }

    async delete(endpoint) {
        return this.request(this.getApiBasePath() + endpoint, {
            method: 'DELETE'
        });
    }

    // Загрузка файлов
    async uploadFile(endpoint, file, onProgress = null) {
        const formData = new FormData();
        formData.append('file', file);

        return new Promise((resolve, reject) => {
            const xhr = new XMLHttpRequest();
            
            if (onProgress) {
                xhr.upload.addEventListener('progress', (e) => {
                    if (e.lengthComputable) {
                        const percentComplete = (e.loaded / e.total) * 100;
                        onProgress(percentComplete);
                    }
                });
            }

            xhr.addEventListener('load', () => {
                if (xhr.status >= 200 && xhr.status < 300) {
                    try {
                        const response = JSON.parse(xhr.responseText);
                        resolve(response);
                    } catch (e) {
                        resolve(xhr.responseText);
                    }
                } else {
                    reject(new Error(`HTTP ${xhr.status}: ${xhr.statusText}`));
                }
            });

            xhr.addEventListener('error', () => {
                reject(new Error('Network error'));
            });

            xhr.open('POST', this.getApiBasePath() + endpoint);
            xhr.send(formData);
        });
    }
}

// Экспорт для использования в других модулях
if (typeof module !== 'undefined' && module.exports) {
    module.exports = ApiManager;
} else {
    window.ApiManager = ApiManager;
}
