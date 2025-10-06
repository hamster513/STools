/**
 * HostsUIManager - Менеджер UI для работы с хостами
 * v=7.1
 */
class HostsUIManager {
    constructor(app) {
        this.app = app;
        this.api = app.api;
        this.storage = app.storage;
        this.eventManager = app.eventManager;
    }

    // Рендеринг результатов поиска хостов
    renderHostsResults(hosts, groupBy = '', paginationData = null) {
        const resultsDiv = this.app.getElementSafe('hosts-search-results');
        if (!resultsDiv) return;
        
        if (!hosts || hosts.length === 0) {
            resultsDiv.innerHTML = '<div class="no-results">Хосты не найдены</div>';
            return;
        }

        let html = '';
        
        if (paginationData) {
            html += this.renderPaginationInfo(paginationData);
        }

        if (groupBy) {
            html += this.renderGroupedHosts(hosts, groupBy);
        } else {
            html += this.renderHostsList(hosts);
        }

        resultsDiv.innerHTML = html;
        this.setupHostsPagination();
    }

    // Рендеринг информации о пагинации
    renderPaginationInfo(paginationData) {
        const existingCountElement = this.app.getElementSafe('hosts-count');
        if (existingCountElement) {
            existingCountElement.textContent = `Найдено: ${paginationData.total_count || 0}`;
        }

        return `
            <div class="pagination-info">
                <span>Страница ${paginationData.current_page || 1} из ${paginationData.total_pages || 1}</span>
                <span>Всего записей: ${paginationData.total_count || 0}</span>
            </div>
        `;
    }

    // Рендеринг сгруппированных хостов
    renderGroupedHosts(hosts, groupBy) {
        const grouped = this.groupHosts(hosts, groupBy);
        let html = '';

        Object.keys(grouped).forEach(groupKey => {
            const groupHosts = grouped[groupKey];
            const groupTitle = this.getGroupTitle(groupBy, groupKey);
            const groupCount = this.getGroupCount(groupBy, groupHosts);

            html += `
                <div class="host-group">
                    <div class="group-header">
                        <h3>${groupTitle}</h3>
                        <span class="group-count">${groupCount}</span>
                    </div>
                    <div class="group-hosts">
                        ${groupHosts.map(host => this.renderHostItem(host)).join('')}
                    </div>
                </div>
            `;
        });

        return html;
    }

    // Рендеринг списка хостов
    renderHostsList(hosts) {
        return `
            <div class="hosts-list">
                ${hosts.map(host => this.renderHostItem(host)).join('')}
            </div>
        `;
    }

    // Группировка хостов
    groupHosts(hosts, groupBy) {
        const grouped = {};

        hosts.forEach(host => {
            let groupKey = '';
            
            switch (groupBy) {
                case 'os':
                    groupKey = host.os || 'Неизвестно';
                    break;
                case 'risk_level':
                    groupKey = this.getRiskLevel(host.risk_score);
                    break;
                case 'has_exploits':
                    groupKey = host.has_exploits ? 'С эксплойтами' : 'Без эксплойтов';
                    break;
                default:
                    groupKey = 'Все хосты';
            }

            if (!grouped[groupKey]) {
                grouped[groupKey] = [];
            }
            grouped[groupKey].push(host);
        });

        return grouped;
    }

    // Получение заголовка группы
    getGroupTitle(groupBy, groupKey) {
        switch (groupBy) {
            case 'os':
                return `ОС: ${groupKey}`;
            case 'risk_level':
                return `Уровень риска: ${groupKey}`;
            case 'has_exploits':
                return groupKey;
            default:
                return groupKey;
        }
    }

    // Получение количества в группе
    getGroupCount(groupBy, hosts) {
        switch (groupBy) {
            case 'os':
                return `${hosts.length} хостов`;
            case 'risk_level':
                return `${hosts.length} хостов`;
            case 'has_exploits':
                return `${hosts.length} хостов`;
            default:
                return `${hosts.length} хостов`;
        }
    }

    // Рендеринг элемента хоста
    renderHostItem(host) {
        let exploitsBadge = '';
        if (host.has_exploits) {
            exploitsBadge = '<span class="exploits-badge">Есть эксплойты</span>';
        }

        let riskBadge = '';
        if (host.risk_score !== null && host.risk_score !== undefined) {
            const riskLevel = this.getRiskLevel(host.risk_score);
            const riskClass = this.getRiskClass(host.risk_score);
            riskBadge = `<span class="risk-badge ${riskClass}">${riskLevel}</span>`;
        }

        return `
            <div class="host-item">
                <div class="host-info">
                    <div class="host-name">${host.hostname || host.ip}</div>
                    <div class="host-details">
                        <span class="host-ip">${host.ip}</span>
                        <span class="host-os">${host.os || 'Неизвестно'}</span>
                    </div>
                </div>
                <div class="host-badges">
                    ${exploitsBadge}
                    ${riskBadge}
                </div>
            </div>
        `;
    }

    // Получение уровня риска
    getRiskLevel(riskScore) {
        if (riskScore >= 0.8) return 'Критический';
        if (riskScore >= 0.6) return 'Высокий';
        if (riskScore >= 0.4) return 'Средний';
        if (riskScore >= 0.2) return 'Низкий';
        return 'Очень низкий';
    }

    // Получение класса риска
    getRiskClass(riskScore) {
        if (riskScore >= 0.8) return 'critical';
        if (riskScore >= 0.6) return 'high';
        if (riskScore >= 0.4) return 'medium';
        if (riskScore >= 0.2) return 'low';
        return 'very-low';
    }

    // Настройка пагинации хостов
    setupHostsPagination() {
        const prevPageBtn = this.app.getElementSafe('prev-page-btn');
        if (prevPageBtn) {
            prevPageBtn.addEventListener('click', () => {
                if (this.app.paginationState.currentPage > 1) {
                    this.app.searchHosts(this.app.paginationState.currentPage - 1);
                }
            });
        }

        const nextPageBtn = this.app.getElementSafe('next-page-btn');
        if (nextPageBtn) {
            nextPageBtn.addEventListener('click', () => {
                if (this.app.paginationState.currentPage < this.app.paginationState.totalPages) {
                    this.app.searchHosts(this.app.paginationState.currentPage + 1);
                }
            });
        }

        const resultsPerPageSelect = this.app.getElementSafe('results-per-page');
        if (resultsPerPageSelect) {
            resultsPerPageSelect.addEventListener('change', (e) => {
                this.app.paginationState.limit = parseInt(e.target.value);
                this.app.paginationState.currentPage = 1;
                this.app.searchHosts(1);
            });
        }
    }

    // Показать прогресс импорта
    showImportProgress() {
        const progressDiv = this.app.getElementSafe('import-progress');
        if (progressDiv) {
            progressDiv.style.display = 'block';
        }
    }

    // Скрыть прогресс импорта
    hideImportProgress() {
        const progressDiv = this.app.getElementSafe('import-progress');
        if (progressDiv) {
            progressDiv.style.display = 'none';
        }
    }
}

// Экспорт для использования в других модулях
if (typeof module !== 'undefined' && module.exports) {
    module.exports = HostsUIManager;
} else {
    window.HostsUIManager = HostsUIManager;
}
