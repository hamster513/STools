/**
 * Базовый класс для модальных окон предварительного просмотра данных
 */
class BaseModalModule {
    constructor(app, config) {
        this.app = app;
        this.config = config;
        this.modalId = config.modalId;
        this.closeId = config.closeId;
        this.contentId = config.contentId;
        this.apiEndpoint = config.apiEndpoint;
        this.tableId = config.tableId;
        this.title = config.title;
        
        this.init();
    }

    init() {
        this.setupEventListeners();
    }

    setupEventListeners() {
        // Закрытие по клику на крестик
        const closeBtn = document.getElementById(this.closeId);
        if (closeBtn) {
            closeBtn.addEventListener('click', () => this.hide());
        }

        // Закрытие по клику вне модального окна
        const modal = document.getElementById(this.modalId);
        if (modal) {
            modal.addEventListener('click', (e) => {
                if (e.target === modal) {
                    this.hide();
                }
            });
        }

        // Закрытие по Escape
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                this.hide();
            }
        });
    }

    show() {
        const modal = document.getElementById(this.modalId);
        if (modal) {
            modal.style.display = 'flex';
            modal.style.flexDirection = 'column';
            modal.style.alignItems = 'center';
            modal.style.justifyContent = 'center';
            modal.classList.add('show');
            
            // Принудительно исправляем стили внутренних элементов
            const modalHeader = modal.querySelector('.modal-header');
            const modalBody = modal.querySelector('.modal-body');
            
            if (modalHeader) {
                modalHeader.style.display = 'flex';
                modalHeader.style.flexDirection = 'row';
                modalHeader.style.justifyContent = 'space-between';
                modalHeader.style.alignItems = 'center';
                modalHeader.style.width = '100%';
            }
            
            if (modalBody) {
                modalBody.style.display = 'flex';
                modalBody.style.flexDirection = 'column';
                modalBody.style.flex = '1';
                modalBody.style.width = '100%';
            }
            

            
            this.loadData();
        } else {
        }
    }

    hide() {
        const modal = document.getElementById(this.modalId);
        if (modal) {
            modal.style.display = 'none';
            modal.classList.remove('show');
        }
    }

    showLoading() {
        const content = document.getElementById(this.contentId);
        if (content) {
            content.innerHTML = `
                <div class="modal-loading">
                    <div class="spinner"></div>
                    <p>Загрузка данных...</p>
                </div>
            `;
        }
    }

    showError(message) {
        const content = document.getElementById(this.contentId);
        if (content) {
            content.innerHTML = `
                <div class="modal-error">
                    <i class="fas fa-exclamation-triangle"></i>
                    <p>Ошибка загрузки: ${message}</p>
                </div>
            `;
        }
    }

    showContent() {
        const content = document.getElementById(this.contentId);
        if (content) {
            content.innerHTML = `
                <div class="modal-table-container">
                    <table id="${this.tableId}" class="data-table">
                        <thead>
                            <tr>
                                ${this.getTableHeaders()}
                            </tr>
                        </thead>
                        <tbody>
                            <!-- Данные будут загружены динамически -->
                        </tbody>
                    </table>
                </div>
            `;
        }
    }

    async loadData() {
        this.showLoading();
        
        try {
            const response = await fetch(this.apiEndpoint);
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            
            if (data.success && data.records) {
                this.showContent();
                this.displayData(data.records);
            } else {
                this.showError(data.error || 'Неизвестная ошибка');
            }
        } catch (error) {
            this.showError(error.message);
        }
    }

    displayData(records) {
        const tbody = document.querySelector(`#${this.tableId} tbody`);
        if (!tbody) return;

        tbody.innerHTML = '';
        
        if (records.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="${this.getColumnCount()}" class="no-data">
                        Нет данных для отображения
                    </td>
                </tr>
            `;
            return;
        }

        records.forEach(record => {
            const row = document.createElement('tr');
            row.innerHTML = this.formatRow(record);
            tbody.appendChild(row);
        });
    }

    // Методы для переопределения в дочерних классах
    getTableHeaders() {
        throw new Error('getTableHeaders() должен быть переопределен в дочернем классе');
    }

    getColumnCount() {
        throw new Error('getColumnCount() должен быть переопределен в дочернем классе');
    }

    formatRow(record) {
        throw new Error('formatRow() должен быть переопределен в дочернем классе');
    }
}
