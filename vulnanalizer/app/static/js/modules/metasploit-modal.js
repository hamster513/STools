/**
 * Модуль для работы с модальным окном Metasploit
 */
class MetasploitModalModule {
    constructor(app) {
        this.app = app;
        this.modal = null;
        this.init();
    }

    init() {
        this.modal = document.getElementById('metasploit-modal');
        this.setupEventListeners();
    }

    setupEventListeners() {
        // Закрытие модального окна по клику на X
        const closeBtn = document.getElementById('metasploit-modal-close');
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

        // Загружаем данные Metasploit
        this.loadMetasploitData();
    }

    hide() {
        if (!this.modal) return;

        this.modal.style.display = 'none';
        this.modal.classList.remove('show');
    }

    showLoading() {
        const loading = document.getElementById('metasploit-modal-loading');
        const content = document.getElementById('metasploit-modal-content');
        const error = document.getElementById('metasploit-modal-error');

        if (loading) loading.style.display = 'block';
        if (content) content.style.display = 'none';
        if (error) error.style.display = 'none';
    }

    showError(message) {
        const loading = document.getElementById('metasploit-modal-loading');
        const content = document.getElementById('metasploit-modal-content');
        const error = document.getElementById('metasploit-modal-error');
        const errorMessage = document.getElementById('metasploit-error-message');

        if (loading) loading.style.display = 'none';
        if (content) content.style.display = 'none';
        if (error) error.style.display = 'block';
        if (errorMessage) errorMessage.textContent = message;
    }

    showContent() {
        const loading = document.getElementById('metasploit-modal-loading');
        const content = document.getElementById('metasploit-modal-content');
        const error = document.getElementById('metasploit-modal-error');

        if (loading) loading.style.display = 'none';
        if (content) content.style.display = 'block';
        if (error) error.style.display = 'none';
    }

    async loadMetasploitData() {
        try {
            const response = await fetch(`${this.app.getApiBasePath()}/metasploit/preview`);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const result = await response.json();

            if (result.success) {
                this.displayMetasploitData(result.modules);
                this.showContent();
            } else {
                throw new Error(result.error || 'Ошибка загрузки данных');
            }
        } catch (error) {
            console.error('Error loading metasploit data:', error);
            this.showError(error.message);
        }
    }

    displayMetasploitData(modules) {
        const tableBody = document.getElementById('metasploit-table-body');
        const countSpan = document.getElementById('metasploit-count');
        
        if (!tableBody || !countSpan) return;

        // Обновляем счетчик
        countSpan.textContent = modules.length;

        // Очищаем таблицу
        tableBody.innerHTML = '';

        // Добавляем строки с данными
        modules.forEach(module => {
            const row = document.createElement('tr');
            
            // Форматируем даты
            const disclosureDate = module.disclosure_date ? new Date(module.disclosure_date).toLocaleDateString('ru-RU') : '-';
            const createdAt = module.created_at ? new Date(module.created_at).toLocaleDateString('ru-RU') : '-';
            
            // Обрезаем длинные тексты
            const name = module.name ? (module.name.length > 50 ? module.name.substring(0, 50) + '...' : module.name) : '-';
            const moduleName = module.module_name ? (module.module_name.length > 30 ? module.module_name.substring(0, 30) + '...' : module.module_name) : '-';
            
            row.innerHTML = `
                <td title="${module.module_name || ''}">${moduleName}</td>
                <td title="${module.name || ''}">${name}</td>
                <td>
                    <span class="rank-badge rank-${module.rank_text || 'unknown'}">
                        ${module.rank_text || 'unknown'} (${module.rank || 0})
                    </span>
                </td>
                <td>
                    <span class="type-badge type-${module.type || 'unknown'}">
                        ${module.type || 'unknown'}
                    </span>
                </td>
                <td>${disclosureDate}</td>
                <td>${createdAt}</td>
            `;
            
            tableBody.appendChild(row);
        });
    }
}

// Экспорт модуля
if (typeof module !== 'undefined' && module.exports) {
    module.exports = MetasploitModalModule;
} else {
    window.MetasploitModalModule = MetasploitModalModule;
}
