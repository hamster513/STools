/**
 * Модуль для работы с модальным окном EPSS
 */
class EPSSModalModule {
    constructor(app) {
        this.app = app;
        this.modal = null;
        this.init();
    }

    init() {
        this.modal = document.getElementById('epss-modal');
        this.setupEventListeners();
    }

    setupEventListeners() {
        // Закрытие модального окна по клику на X
        const closeBtn = document.getElementById('epss-modal-close');
        if (closeBtn) {
            closeBtn.addEventListener('click', () => {
                this.hide();
            });
        }

        // Закрытие модального окна по клику вне его
        if (this.modal) {
            this.modal.addEventListener('click', (e) => {
                if (e.target === this.modal) {
                    this.hide();
                }
            });
        }

        // Закрытие по Escape
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.modal && this.modal.style.display !== 'none') {
                this.hide();
            }
        });
    }

    show() {
        if (!this.modal) return;

        // Показываем модальное окно
        this.modal.style.display = 'block';
        this.modal.classList.add('show');

        // Показываем загрузку
        this.showLoading();

        // Загружаем данные EPSS
        this.loadEPSSData();
    }

    hide() {
        if (!this.modal) return;

        this.modal.style.display = 'none';
        this.modal.classList.remove('show');
    }

    showLoading() {
        const loading = document.getElementById('epss-modal-loading');
        const content = document.getElementById('epss-modal-content');
        const error = document.getElementById('epss-modal-error');

        if (loading) loading.style.display = 'block';
        if (content) content.style.display = 'none';
        if (error) error.style.display = 'none';
    }

    showError(message) {
        const loading = document.getElementById('epss-modal-loading');
        const content = document.getElementById('epss-modal-content');
        const error = document.getElementById('epss-modal-error');
        const errorMessage = document.getElementById('epss-error-message');

        if (loading) loading.style.display = 'none';
        if (content) content.style.display = 'none';
        if (error) error.style.display = 'block';
        if (errorMessage) errorMessage.textContent = message;
    }

    showContent() {
        const loading = document.getElementById('epss-modal-loading');
        const content = document.getElementById('epss-modal-content');
        const error = document.getElementById('epss-modal-error');

        if (loading) loading.style.display = 'none';
        if (content) content.style.display = 'block';
        if (error) error.style.display = 'none';
    }

    async loadEPSSData() {
        try {
            const response = await fetch(`${this.app.getApiBasePath()}/epss/preview`);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const result = await response.json();

            if (result.success) {
                this.displayEPSSData(result.records);
                this.showContent();
            } else {
                throw new Error(result.error || 'Ошибка загрузки данных');
            }
        } catch (error) {
            console.error('Error loading EPSS data:', error);
            this.showError(error.message);
        }
    }

    displayEPSSData(records) {
        const tableBody = document.getElementById('epss-table-body');
        const countSpan = document.getElementById('epss-count');
        
        if (!tableBody || !countSpan) return;

        // Обновляем счетчик
        countSpan.textContent = records.length;

        // Очищаем таблицу
        tableBody.innerHTML = '';

        // Добавляем строки с данными
        records.forEach(record => {
            const row = document.createElement('tr');
            
            // Форматируем даты
            const date = record.date ? new Date(record.date).toLocaleDateString('ru-RU') : '-';
            const createdAt = record.created_at ? new Date(record.created_at).toLocaleDateString('ru-RU') : '-';
            
            // Форматируем EPSS score
            const epssScore = record.epss ? (record.epss * 100).toFixed(2) + '%' : '-';
            const percentile = record.percentile ? (record.percentile * 100).toFixed(1) + '%' : '-';
            const cvss = record.cvss ? record.cvss.toFixed(1) : '-';
            
            row.innerHTML = `
                <td><strong>${record.cve || '-'}</strong></td>
                <td><span class="epss-score">${epssScore}</span></td>
                <td><span class="epss-percentile">${percentile}</span></td>
                <td>${cvss}</td>
                <td>${date}</td>
                <td>${createdAt}</td>
            `;
            
            tableBody.appendChild(row);
        });
    }
}

// Экспорт модуля
if (typeof module !== 'undefined' && module.exports) {
    module.exports = EPSSModalModule;
} else {
    window.EPSSModalModule = EPSSModalModule;
}
