/**
 * EventManager - Централизованное управление событиями (паттерн Observer)
 * v=7.1
 */
class EventManager {
    constructor() {
        this.events = {};
        this.oneTimeEvents = new Set();
    }

    // Подписка на событие
    on(event, callback, options = {}) {
        if (!this.events[event]) {
            this.events[event] = [];
        }

        const listener = {
            callback,
            once: options.once || false,
            priority: options.priority || 0,
            context: options.context || null
        };

        this.events[event].push(listener);
        
        // Сортируем по приоритету (высший приоритет первым)
        this.events[event].sort((a, b) => b.priority - a.priority);

        // Возвращаем функцию для отписки
        return () => this.off(event, callback);
    }

    // Подписка на событие с автоматической отпиской после первого срабатывания
    once(event, callback, options = {}) {
        return this.on(event, callback, { ...options, once: true });
    }

    // Отписка от события
    off(event, callback) {
        if (!this.events[event]) return;

        this.events[event] = this.events[event].filter(
            listener => listener.callback !== callback
        );

        if (this.events[event].length === 0) {
            delete this.events[event];
        }
    }

    // Генерация события
    emit(event, data = null) {
        if (!this.events[event]) return;

        const listeners = [...this.events[event]]; // Копируем массив
        
        listeners.forEach(listener => {
            try {
                if (listener.context) {
                    listener.callback.call(listener.context, data);
                } else {
                    listener.callback(data);
                }

                // Удаляем одноразовые слушатели
                if (listener.once) {
                    this.off(event, listener.callback);
                }
            } catch (error) {
                console.error(`Error in event listener for '${event}':`, error);
            }
        });
    }

    // Асинхронная генерация события
    async emitAsync(event, data = null) {
        if (!this.events[event]) return;

        const listeners = [...this.events[event]];
        const promises = [];

        listeners.forEach(listener => {
            const promise = new Promise((resolve, reject) => {
                try {
                    const result = listener.context 
                        ? listener.callback.call(listener.context, data)
                        : listener.callback(data);

                    // Если callback возвращает Promise, ждем его
                    if (result && typeof result.then === 'function') {
                        result.then(resolve).catch(reject);
                    } else {
                        resolve(result);
                    }

                    // Удаляем одноразовые слушатели
                    if (listener.once) {
                        this.off(event, listener.callback);
                    }
                } catch (error) {
                    reject(error);
                }
            });

            promises.push(promise);
        });

        return Promise.allSettled(promises);
    }

    // Удаление всех слушателей события
    removeAllListeners(event) {
        if (event) {
            delete this.events[event];
        } else {
            this.events = {};
        }
    }

    // Получение количества слушателей события
    listenerCount(event) {
        return this.events[event] ? this.events[event].length : 0;
    }

    // Получение списка всех событий
    eventNames() {
        return Object.keys(this.events);
    }

    // Специализированные методы для часто используемых событий
    onUserLogin(callback, options = {}) {
        return this.on('user:login', callback, options);
    }

    onUserLogout(callback, options = {}) {
        return this.on('user:logout', callback, options);
    }

    onDataUpdate(callback, options = {}) {
        return this.on('data:update', callback, options);
    }

    onError(callback, options = {}) {
        return this.on('error', callback, options);
    }

    onNotification(callback, options = {}) {
        return this.on('notification', callback, options);
    }

    onThemeChange(callback, options = {}) {
        return this.on('theme:change', callback, options);
    }

    onPageChange(callback, options = {}) {
        return this.on('page:change', callback, options);
    }

    // Генерация специализированных событий
    emitUserLogin(user) {
        this.emit('user:login', user);
    }

    emitUserLogout() {
        this.emit('user:logout');
    }

    emitDataUpdate(data) {
        this.emit('data:update', data);
    }

    emitError(error, context = null) {
        this.emit('error', { error, context });
    }

    emitNotification(message, type = 'info') {
        this.emit('notification', { message, type });
    }

    emitThemeChange(theme) {
        this.emit('theme:change', theme);
    }

    emitPageChange(page) {
        this.emit('page:change', page);
    }

    // Метод для отладки
    debug() {
        console.log('EventManager Debug:', {
            events: this.eventNames(),
            listeners: Object.keys(this.events).reduce((acc, event) => {
                acc[event] = this.events[event].length;
                return acc;
            }, {})
        });
    }
}

// Экспорт для использования в других модулях
if (typeof module !== 'undefined' && module.exports) {
    module.exports = EventManager;
} else {
    window.EventManager = EventManager;
}
