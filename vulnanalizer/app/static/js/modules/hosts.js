/**
 * Модуль для работы с хостами
 * v=4.3
 */
class HostsModule {
    constructor(app) {
        this.app = app;
        this.paginationState = {
            currentPage: 1,
            totalPages: 1,
            totalCount: 0,
            limit: 100
        };
        this.lastNotifiedCompletionTime = localStorage.getItem('hosts_last_notification_time'); // Отслеживаем последнее показанное уведомление
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.updateStatus();
        this.checkActiveImportTasks(); // Проверяем активные задачи импорта
        
        // Отслеживаем изменения innerHTML в hosts-search-results
        this.trackInnerHTMLChanges();
    }

    setupEventListeners() {
        // Форма поиска хостов
        const hostsSearchForm = document.getElementById('hosts-search-form');
        if (hostsSearchForm) {
            hostsSearchForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.searchHosts();
            });
        }

        // Кнопка очистки результатов поиска хостов
        const clearHostsResultsBtn = document.getElementById('clear-hosts-results');
        if (clearHostsResultsBtn) {
            clearHostsResultsBtn.addEventListener('click', () => {
                this.clearResults();
            });
        }

        // Кнопка экспорта хостов
        const exportHostsBtn = document.getElementById('export-hosts');
        if (exportHostsBtn) {
            exportHostsBtn.addEventListener('click', () => {
                this.exportHosts();
            });
        }

        // Загрузка CSV хостов
        const hostsForm = document.getElementById('hosts-upload-form');
        if (hostsForm) {
            hostsForm.addEventListener('submit', async (e) => {
                e.preventDefault();
                await this.uploadHosts();
            });
        }

        // Фоновое обновление данных
        const updateHostsParallelBtn = document.getElementById('update-hosts-parallel-btn');
        const cancelUpdateBtn = document.getElementById('cancel-update-btn');
        
        if (updateHostsParallelBtn) {
            updateHostsParallelBtn.addEventListener('click', async () => {
                await this.startBackgroundUpdate();
            });
        }
        
        if (cancelUpdateBtn) {
            cancelUpdateBtn.addEventListener('click', async () => {
                await this.cancelBackgroundUpdate();
            });
        }

        // Обработчики пагинации
        const prevPageBtn = document.getElementById('prev-page');
        const nextPageBtn = document.getElementById('next-page');
        
        if (prevPageBtn) {
            prevPageBtn.addEventListener('click', () => {
                if (this.paginationState.currentPage > 1) {
                    this.searchHosts(this.paginationState.currentPage - 1);
                }
            });
        }
        
        if (nextPageBtn) {
            nextPageBtn.addEventListener('click', () => {
                if (this.paginationState.currentPage < this.paginationState.totalPages) {
                    this.searchHosts(this.paginationState.currentPage + 1);
                }
            });
        }

        // Обработчик изменения количества записей на странице
        const resultsPerPageSelect = document.getElementById('results-per-page');
        if (resultsPerPageSelect) {
            resultsPerPageSelect.addEventListener('change', (e) => {
                this.paginationState.limit = parseInt(e.target.value);
                this.paginationState.currentPage = 1;
                this.searchHosts(1);
            });
        }

        // Инициализируем мониторинг только один раз
        this.initializeMonitoring();
    }

    async updateStatus() {
        try {
            const data = await this.app.api.getHostsStatus();
            
            if (data.success) {
                const statusDiv = document.getElementById('hosts-status');
                if (statusDiv) {
                    statusDiv.innerHTML = `
                        <div class="status-info">
                            <i class="fas fa-server"></i>
                            <span>Хостов в базе: <strong>${data.count}</strong></span>
                        </div>
                    `;
                }
            } else {
                const statusDiv = document.getElementById('hosts-status');
                if (statusDiv) {
                    statusDiv.innerHTML = `
                        <div class="status-error">
                            <i class="fas fa-exclamation-triangle"></i>
                            <span>Ошибка получения статуса хостов</span>
                        </div>
                    `;
                }
            }
        } catch (err) {
            console.error('Hosts status error:', err);
            const statusDiv = document.getElementById('hosts-status');
            if (statusDiv) {
                statusDiv.innerHTML = `
                    <div class="status-error">
                        <i class="fas fa-exclamation-triangle"></i>
                        <span>Ошибка получения статуса хостов</span>
                    </div>
                `;
            }
        }
    }

    async searchHosts(page = 1) {
        const form = document.getElementById('hosts-search-form');
        const resultsDiv = document.getElementById('hosts-search-results');
        
        if (!form || !resultsDiv) return;
        
        const formData = new FormData(form);
        const params = new URLSearchParams();
        
        // Добавляем параметры поиска
        for (let [key, value] of formData.entries()) {
            if (key === 'exploits_only' || key === 'epss_only') {
                if (value === 'on') {
                    params.append(key, 'true');
                }
            } else if (value.trim()) {
                params.append(key, value.trim());
            }
        }
        
        // Добавляем параметры пагинации
        params.append('page', page);
        params.append('limit', this.paginationState.limit);
        
        try {
            const data = await this.app.api.searchHosts(Object.fromEntries(params));
            
            if (data.success) {
                const groupBy = formData.get('group_by') || '';
                this.renderResults(data.results, groupBy, data);
            } else {
                window.notifications.show('Ошибка поиска хостов', 'error');
            }
        } catch (err) {
            console.error('Hosts search error:', err);
            window.notifications.show('Ошибка поиска хостов', 'error');
        }
    }

    renderResults(hosts, groupBy = '', paginationData = null) {
        // Защита от повторных вызовов
        if (this.isRendering) {
            return;
        }
        
        this.isRendering = true;
        
        const resultsDiv = document.getElementById('hosts-search-results');
        if (!resultsDiv) {
            this.isRendering = false;
            return;
        }
        
        if (!hosts || hosts.length === 0) {
            resultsDiv.innerHTML = `
                <div class="no-results">
                    <i class="fas fa-search"></i>
                    <p>Хосты не найдены</p>
                </div>
            `;
            this.hidePagination();
            return;
        }
        
        // Обновляем состояние пагинации
        if (paginationData) {
            this.paginationState = {
                currentPage: paginationData.page || 1,
                totalPages: paginationData.total_pages || 1,
                totalCount: paginationData.total_count || hosts.length,
                limit: paginationData.limit || 100
            };
        }
        
        // Создаем отдельный элемент для отображения количества найденных хостов
        const resultsContainer = document.querySelector('.hosts-search-results-container');
        const existingCountElement = resultsContainer.querySelector('.hosts-count');
        
        if (existingCountElement) {
            existingCountElement.remove();
        }
        
        const countElement = document.createElement('div');
        countElement.className = 'hosts-count';
        countElement.innerHTML = `<h4>Найдено хостов: ${this.paginationState.totalCount}</h4>`;
        
        // Вставляем элемент с количеством перед заголовком таблицы
        const tableHeader = resultsContainer.querySelector('.hosts-table-header');
        resultsContainer.insertBefore(countElement, tableHeader);
        
        let html = '';
        
        if (groupBy) {
            // Группируем хосты
            const grouped = this.groupHosts(hosts, groupBy);
            
            Object.keys(grouped).forEach(groupKey => {
                const groupHosts = grouped[groupKey];
                const count = this.getGroupCount(groupBy, groupHosts);
                const countLabel = groupBy === 'cve' ? 'хостов' : 'CVE';
                
                html += `
                    <div class="host-group">
                        <h5 class="group-header">
                            <i class="fas fa-folder"></i>
                            ${this.getGroupTitle(groupBy, groupKey)} (${count} ${countLabel})
                        </h5>
                        <div class="group-content">
                `;
                
                groupHosts.forEach(host => {
                    html += this.renderHostItem(host);
                });
                
                html += `
                        </div>
                    </div>
                `;
            });
        } else {
            // Без группировки
            hosts.forEach(host => {
                html += this.renderHostItem(host);
            });
        }
        
        resultsDiv.innerHTML = html;
        
        // Проверяем, что вставилось
        setTimeout(() => {
            // Ищем CVE ссылки в вставленном HTML
            const cveLinks = resultsDiv.querySelectorAll('.cve-link');
            
            if (cveLinks.length === 0) {
                console.warn('CVE ссылки не найдены в DOM после вставки!');
            }
        }, 100);
        
        // Отображаем пагинацию
        this.renderPagination();
        
        // Снимаем блокировку
        this.isRendering = false;
    }

    groupHosts(hosts, groupBy) {
        const grouped = {};
        
        hosts.forEach(host => {
            let groupKey;
            switch (groupBy) {
                case 'hostname':
                    groupKey = host.hostname;
                    break;
                case 'ip_address':
                    groupKey = host.ip_address;
                    break;
                case 'cve':
                    groupKey = host.cve;
                    break;
                default:
                    groupKey = 'default';
            }
            
            if (!grouped[groupKey]) {
                grouped[groupKey] = [];
            }
            grouped[groupKey].push(host);
        });
        
        return grouped;
    }

    getGroupTitle(groupBy, groupKey) {
        switch (groupBy) {
            case 'hostname':
                return `Hostname: ${groupKey}`;
            case 'ip_address':
                return `IP: ${groupKey}`;
            case 'cve':
                return `CVE: ${groupKey}`;
            default:
                return groupKey;
        }
    }

    getGroupCount(groupBy, hosts) {
        switch (groupBy) {
            case 'hostname':
                const uniqueCves = new Set(hosts.map(host => host.cve));
                return uniqueCves.size;
            case 'ip_address':
                const uniqueCvesByIp = new Set(hosts.map(host => host.cve));
                return uniqueCvesByIp.size;
            case 'cve':
                return hosts.length;
            default:
                return hosts.length;
        }
    }

    renderHostItem(host) {
        const criticalityClass = `criticality-${host.criticality.toLowerCase()}`;
        
        // Индикация эксплойтов
        let exploitsIndicator = '';
        if (host.has_exploits) {
            exploitsIndicator = `
                <div class="host-exploits">
                    <span class="exploit-badge" title="Есть эксплойты: ${host.exploits_count}">
                        <i class="fas fa-bug"></i> ${host.exploits_count}
                    </span>
                </div>
            `;
        } else {
            exploitsIndicator = '<div class="host-exploits"></div>';
        }
        
        // Отображение риска
        let riskDisplay = '';
        
        if (host.risk_score !== null && host.risk_score !== undefined) {
            riskDisplay = this.createRiskLink(host.risk_score, host.id, host.cve);
        } else {
            riskDisplay = '<span class="risk-score">N/A</span>';
        }
        
        return `
            <div class="host-item single-line">
                <div class="host-name">${host.hostname}</div>
                <div class="host-ip">${host.ip_address}</div>
                <div class="host-criticality">
                    <span class="${criticalityClass}">${host.criticality}</span>
                </div>
                <div class="host-cve">${this.createCVELink(host.cve)}</div>
                <div class="host-cvss">
                    ${host.cvss ? 
                        (host.cvss_source && host.cvss_source.includes('v2') ? 
                            `v2: ${host.cvss}` : 
                            (host.cvss_source && host.cvss_source.includes('v3') ? 
                                `v3: ${host.cvss}` : 
                                `${host.cvss}`
                            )
                        ) : 
                        'N/A'
                    }
                </div>
                <div class="host-status">
                    ${host.epss_score !== null && host.epss_score !== undefined ? 
                        `${(host.epss_score * 100).toFixed(2)}%` : 
                        'N/A'
                    }
                </div>
                ${exploitsIndicator}
                <div class="host-msf">${this.createMSFDisplay(host)}</div>
                <div class="host-risk" id="host-risk-${host.id}">${riskDisplay}</div>
            </div>
        `;
    }

    createCVELink(cveId) {
        if (!cveId) return 'N/A';
        
        // Проверяем, доступен ли модуль CVE
        if (this.app.cveModal && typeof this.app.cveModal.createCVELink === 'function') {
            return this.app.cveModal.createCVELink(cveId);
        }
        
        // Fallback - создаем простую ссылку
        return `<span class="cve-link" onclick="if(window.vulnAnalizer && window.vulnAnalizer.cveModal) { window.vulnAnalizer.cveModal.show('${cveId}'); }">${cveId}</span>`;
    }

    createRiskLink(riskScore, hostId, cveId) {
        console.log(`🔍 Creating risk link: riskScore=${riskScore}, hostId=${hostId}, cveId=${cveId}`);
        if (!riskScore || riskScore === 'N/A') return '<span class="risk-score">N/A</span>';
        
        // Проверяем, доступен ли модуль риска
        if (this.app.riskModal && typeof this.app.riskModal.createRiskLink === 'function') {
            console.log(`✅ Using riskModal.createRiskLink`);
            return this.app.riskModal.createRiskLink(riskScore, hostId, cveId);
        }
        
        // Fallback - создаем простую ссылку
        console.log(`🔍 Using fallback risk link creation`);
        const riskClass = riskScore >= 70 ? 'high-risk' : 
                         riskScore >= 40 ? 'medium-risk' : 'low-risk';
        
        let riskText;
        if (riskScore < 0.1) {
            riskText = riskScore.toFixed(2);
        } else if (riskScore < 1) {
            riskText = riskScore.toFixed(1);
        } else {
            riskText = Math.round(riskScore);
        }
        
        return `<span class="risk-score ${riskClass} risk-link" onclick="if(window.vulnAnalizer && window.vulnAnalizer.riskModal) { window.vulnAnalizer.riskModal.show('${hostId}', '${cveId}'); }" title="Нажмите для просмотра деталей расчета">${riskText}%</span>`;
    }

    createMSFDisplay(host) {
        // Если у хоста есть информация о Metasploit модуле
        if (host.msf_rank && host.msf_rank !== 'none') {
            const rankClass = this.getMSFRankClass(host.msf_rank);
            const rankText = this.getMSFRankText(host.msf_rank);
            return `<span class="msf-rank ${rankClass}">${rankText}</span>`;
        }
        
        // Если нет информации о Metasploit
        return '<span class="msf-rank none">N/A</span>';
    }

    getMSFRankClass(rank) {
        // Сопоставляем числовые ранги с классами
        if (rank >= 500) return 'excellent';
        if (rank >= 400) return 'good';
        if (rank >= 300) return 'normal';
        if (rank >= 200) return 'average';
        if (rank >= 100) return 'low';
        return 'unknown';
    }

    getMSFRankText(rank) {
        // Сопоставляем числовые ранги с текстом
        if (rank >= 500) return 'EXC';
        if (rank >= 400) return 'GOOD';
        if (rank >= 300) return 'NORM';
        if (rank >= 200) return 'AVG';
        if (rank >= 100) return 'LOW';
        return 'UNK';
    }

    trackInnerHTMLChanges() {
        const resultsDiv = document.getElementById('hosts-search-results');
        if (!resultsDiv) return;
        
        // Создаем наблюдатель за изменениями
        const observer = new MutationObserver((mutations) => {
            mutations.forEach((mutation) => {
                if (mutation.type === 'childList') {
                    // Проверяем CVE ссылки после изменения
                    setTimeout(() => {
                        const cveLinks = resultsDiv.querySelectorAll('.cve-link');
                        
                        if (cveLinks.length === 0) {
                            console.warn('CVE ссылки исчезли после изменения DOM!');
                        }
                    }, 50);
                }
            });
        });
        
        // Начинаем наблюдение
        observer.observe(resultsDiv, {
            childList: true,
            subtree: true
        });
        

    }

    clearResults() {
        const resultsDiv = document.getElementById('hosts-search-results');
        if (resultsDiv) {
            resultsDiv.innerHTML = '';
        }
        this.hidePagination();
    }

    renderPagination() {
        const paginationDiv = document.getElementById('hosts-pagination');
        if (!paginationDiv) return;

        if (this.paginationState.totalPages <= 1) {
            this.hidePagination();
            return;
        }

        // Обновляем информацию о пагинации
        const startRecord = (this.paginationState.currentPage - 1) * this.paginationState.limit + 1;
        const endRecord = Math.min(this.paginationState.currentPage * this.paginationState.limit, this.paginationState.totalCount);
        
        const paginationInfo = document.getElementById('pagination-info');
        if (paginationInfo) {
            paginationInfo.textContent = `Показано ${startRecord}-${endRecord} из ${this.paginationState.totalCount} записей`;
        }

        // Обновляем кнопки навигации
        const prevBtn = document.getElementById('prev-page');
        const nextBtn = document.getElementById('next-page');
        
        if (prevBtn) {
            prevBtn.disabled = this.paginationState.currentPage <= 1;
        }
        
        if (nextBtn) {
            nextBtn.disabled = this.paginationState.currentPage >= this.paginationState.totalPages;
        }

        // Генерируем номера страниц
        this.renderPageNumbers();

        // Показываем пагинацию
        paginationDiv.style.display = 'block';
    }

    renderPageNumbers() {
        const pageNumbersDiv = document.getElementById('page-numbers');
        if (!pageNumbersDiv) return;

        const { currentPage, totalPages } = this.paginationState;
        let html = '';

        // Показываем максимум 5 страниц вокруг текущей
        const startPage = Math.max(1, currentPage - 2);
        const endPage = Math.min(totalPages, currentPage + 2);

        // Добавляем первую страницу если нужно
        if (startPage > 1) {
            html += `<span class="page-number" data-page="1">1</span>`;
            if (startPage > 2) {
                html += `<span class="page-number disabled">...</span>`;
            }
        }

        // Добавляем страницы в диапазоне
        for (let i = startPage; i <= endPage; i++) {
            const isActive = i === currentPage;
            html += `<span class="page-number ${isActive ? 'active' : ''}" data-page="${i}">${i}</span>`;
        }

        // Добавляем последнюю страницу если нужно
        if (endPage < totalPages) {
            if (endPage < totalPages - 1) {
                html += `<span class="page-number disabled">...</span>`;
            }
            html += `<span class="page-number" data-page="${totalPages}">${totalPages}</span>`;
        }

        pageNumbersDiv.innerHTML = html;

        // Добавляем обработчики событий
        pageNumbersDiv.querySelectorAll('.page-number:not(.disabled)').forEach(span => {
            span.addEventListener('click', (e) => {
                const page = parseInt(e.target.dataset.page);
                if (page && page !== currentPage) {
                    this.searchHosts(page);
                }
            });
        });
    }

    hidePagination() {
        const paginationDiv = document.getElementById('hosts-pagination');
        if (paginationDiv) {
            paginationDiv.style.display = 'none';
        }
    }

    async exportHosts() {
        const form = document.getElementById('hosts-search-form');
        if (!form) return;
        
        const formData = new FormData(form);
        const params = {};
        
        // Добавляем только заполненные параметры
        for (let [key, value] of formData.entries()) {
            if (key === 'exploits_only' || key === 'epss_only') {
                if (value === 'on') {
                    params[key] = 'true';
                }
            } else if (value.trim()) {
                params[key] = value.trim();
            }
        }
        
        try {
            // Показываем индикатор загрузки
            const exportBtn = document.getElementById('export-hosts');
            const originalText = exportBtn.innerHTML;
            exportBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Экспорт...';
            exportBtn.disabled = true;
            
            const response = await this.app.api.exportHosts(params);
            
            if (response instanceof Blob) {
                // Это Excel файл, скачиваем его
                const url = window.URL.createObjectURL(response);
                const a = document.createElement('a');
                a.href = url;
                a.download = 'hosts_export.xlsx';
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(url);
                document.body.removeChild(a);
                
                window.notifications.show('Экспорт завершен успешно!', 'success');
            } else {
                window.notifications.show(`Ошибка экспорта: ${response.error}`, 'error');
            }
        } catch (error) {
            console.error('Export error:', error);
            window.notifications.show('Ошибка экспорта: ' + error.message, 'error');
        } finally {
            // Восстанавливаем кнопку
            const exportBtn = document.getElementById('export-hosts');
            exportBtn.innerHTML = '<i class="fas fa-file-excel"></i> Экспорт в Excel';
            exportBtn.disabled = false;
        }
    }

    async uploadHosts() {
        const fileInput = document.getElementById('hosts-file');
        if (!fileInput.files.length) {
            window.notifications.show('Выберите файл для загрузки', 'warning');
            return;
        }
        
        const file = fileInput.files[0];
        const fileSizeMB = (file.size / (1024 * 1024)).toFixed(2);
        
        // Проверяем размер файла (максимум 2GB)
        const maxFileSize = 2 * 1024 * 1024 * 1024;
        if (file.size > maxFileSize) {
            window.notifications.show(`Файл слишком большой (${fileSizeMB} МБ). Максимальный размер: 2 ГБ.`, 'error');
            return;
        }
        
        const uploadBtn = document.getElementById('hosts-upload-btn');
        const btnText = uploadBtn.querySelector('.btn-text');
        const spinner = uploadBtn.querySelector('.fa-spinner');
        
        // Показываем индикатор загрузки
        btnText.textContent = 'Загрузка...';
        spinner.style.display = 'inline-block';
        uploadBtn.disabled = true;
        
        // Показываем прогресс-бар
        this.showImportProgress();
        
        let data = null; // Объявляем переменную data
        
        try {
            // Запускаем мониторинг прогресса ДО загрузки файла
            const progressInterval = this.startProgressMonitoring();
            
            // Показываем начальный прогресс загрузки файла
            this.updateImportProgress('uploading', 'Загрузка файла на сервер...', 5, 0, 0, 0);
            
            data = await this.app.api.uploadHosts(file);
            
            if (data.success) {
                // Файл загружен, но обработка происходит в фоновом режиме
                this.updateImportProgress('processing', 'Файл загружен. Начинаем обработку...', 10, 0, 0, 0);
                
                // НЕ останавливаем мониторинг прогресса - он будет отслеживать фоновую обработку
                // clearInterval(progressInterval); // УБИРАЕМ ЭТУ СТРОКУ
                
                window.notifications.show('Файл загружен. Обработка запущена в фоновом режиме.', 'success');
                this.updateStatus();
                fileInput.value = '';
                
                // Восстанавливаем кнопку после загрузки файла
                btnText.textContent = 'Загрузить файл';
                spinner.style.display = 'none';
                uploadBtn.disabled = false;
                
                // Мониторинг прогресса продолжит работать в фоне
                // и автоматически остановится когда задача завершится
                
            } else {
                // Останавливаем мониторинг прогресса при ошибке
                clearInterval(progressInterval);
                
                this.updateImportProgress('error', 'Ошибка импорта', 0, 0, 0, 0, data.detail || 'Неизвестная ошибка');
                window.notifications.show('Ошибка импорта: ' + (data.detail || 'Неизвестная ошибка'), 'error');
                
                // Скрываем прогресс-бар через 3 секунды
                setTimeout(() => {
                    this.hideImportProgress();
                }, 3000);
            }
        } catch (err) {
            console.error('Hosts upload error:', err);
            let errorMessage = err.message;
            
            if (err.name === 'TypeError' && err.message.includes('JSON')) {
                errorMessage = 'Сервер вернул неверный формат ответа. Возможно, произошла ошибка на сервере или файл слишком большой.';
            } else if (err.name === 'TypeError' && err.message.includes('fetch')) {
                errorMessage = 'Ошибка соединения с сервером. Проверьте подключение к интернету.';
            }
            
            this.updateImportProgress('error', 'Ошибка импорта', 0, 0, 0, 0, errorMessage);
            window.notifications.show('Ошибка импорта: ' + errorMessage, 'error');
            
            // Скрываем прогресс-бар через 3 секунды
            setTimeout(() => {
                this.hideImportProgress();
            }, 3000);
        } finally {
            // Восстанавливаем кнопку только если произошла ошибка
            // При успешной загрузке кнопка уже восстановлена выше
            if (!data || !data.success) {
                btnText.textContent = 'Загрузить файл';
                spinner.style.display = 'none';
                uploadBtn.disabled = false;
            }
        }
    }

    async startBackgroundUpdate() {
        const updateHostsParallelBtn = document.getElementById('update-hosts-parallel-btn');
        const btnText = updateHostsParallelBtn.querySelector('.btn-text');
        const spinner = updateHostsParallelBtn.querySelector('.fa-spinner');
        
        // Блокируем кнопку сразу при нажатии
        updateHostsParallelBtn.disabled = true;
        btnText.textContent = 'Запуск...';
        spinner.style.display = 'inline-block';
        
        // Показываем кнопку отмены
        const cancelUpdateBtn = document.getElementById('cancel-update-btn');
        if (cancelUpdateBtn) {
            cancelUpdateBtn.style.display = 'inline-block';
        }
        
        // Показываем прогресс
        this.showBackgroundUpdateProgress();
        
        try {
            const data = await this.app.api.startBackgroundUpdate();
            
            if (data.success) {
                window.notifications.show('Обновление запущено', 'success');
                this.updateStatus();
                
                // Если процесс завершился сразу, скрываем кнопку отмены
                if (cancelUpdateBtn) {
                    cancelUpdateBtn.style.display = 'none';
                }
                
                // Восстанавливаем кнопку только если задача не запустилась
                btnText.textContent = 'Полное обновление';
                spinner.style.display = 'none';
                updateHostsParallelBtn.disabled = false;
            } else {
                window.notifications.show(data.message, 'error');
                
                // При ошибке также скрываем кнопку отмены
                if (cancelUpdateBtn) {
                    cancelUpdateBtn.style.display = 'none';
                }
                
                // Восстанавливаем кнопку при ошибке
                btnText.textContent = 'Полное обновление';
                spinner.style.display = 'none';
                updateHostsParallelBtn.disabled = false;
            }
        } catch (err) {
            console.error('Background update error:', err);
            window.notifications.show('Ошибка запуска обновления', 'error');
            
            // При ошибке скрываем кнопку отмены
            if (cancelUpdateBtn) {
                cancelUpdateBtn.style.display = 'none';
            }
            
            // Восстанавливаем кнопку при ошибке
            btnText.textContent = 'Полное обновление';
            spinner.style.display = 'none';
            updateHostsParallelBtn.disabled = false;
        }
        // Убираем finally блок - кнопка восстанавливается только при ошибке или если задача не запустилась
    }

    async cancelBackgroundUpdate() {
        try {
            const data = await this.app.api.cancelBackgroundUpdate();
            
            if (data.success) {
                window.notifications.show(data.message, 'info');
                const cancelUpdateBtn = document.getElementById('cancel-update-btn');
                if (cancelUpdateBtn) {
                    cancelUpdateBtn.style.display = 'none';
                }
            } else {
                window.notifications.show(data.message, 'warning');
            }
        } catch (err) {
            console.error('Cancel update error:', err);
            window.notifications.show('Ошибка отмены обновления', 'error');
        }
    }

    async calculateHostRisk(hostId) {
        const riskDiv = document.getElementById(`host-risk-${hostId}`);
        if (!riskDiv) return;
        
        // Показываем индикатор загрузки
        riskDiv.innerHTML = `
            <div class="loading">
                <i class="fas fa-spinner fa-spin"></i>
                <p>Расчет риска...</p>
            </div>
        `;
        
        try {
            const data = await this.app.api.calculateHostRisk(hostId);
            
            if (data.success) {
                this.renderHostRiskResult(hostId, data);
            } else {
                console.error('API error for host', hostId, ':', data);
                riskDiv.innerHTML = `<span class="risk-score">Ошибка</span>`;
            }
        } catch (error) {
            console.error('Host risk calculation error for host', hostId, ':', error);
            riskDiv.innerHTML = `<span class="risk-score">Ошибка</span>`;
        }
    }

    renderHostRiskResult(hostId, data) {
        const riskDiv = document.getElementById(`host-risk-${hostId}`);
        if (!riskDiv) return;
        
        let html = '';
        
        // Отображаем EPSS (в процентах)
        if (data.epss && data.epss.epss !== null) {
            const epssValue = (data.epss.epss * 100).toFixed(2);
            html += `<div class="epss-info">
                <i class="fas fa-chart-line"></i>
                <span class="epss-label">EPSS:</span>
                <span class="epss-value">${epssValue}%</span>
            </div>`;
        }
        
        // Отображаем риск
        if (data.risk && data.risk.calculation_possible) {
            const threshold = parseFloat(localStorage.getItem('risk_threshold') || '75');
            const riskScore = data.risk.risk_score;
            const isHighRisk = riskScore >= threshold;
            const riskClass = isHighRisk ? 'risk-score-high' : 'risk-score-low';
            
            html += `<div class="risk-score ${riskClass}">
                <span class="risk-label">Risk:</span>
                <span class="risk-value">${data.risk.risk_score.toFixed(1)}%</span>
            </div>`;
        } else {
            html += `<div class="risk-score">
                <span class="risk-label">Risk:</span>
                <span class="risk-value">N/A</span>
            </div>`;
        }
        
        // Отображаем информацию об эксплойтах
        if (data.exploitdb && data.exploitdb.length > 0) {
            const exploitCount = data.exploitdb.length;
            const verifiedCount = data.exploitdb.filter(e => e.verified).length;
            
            html += `
                <div class="exploit-info">
                    <i class="fas fa-bug"></i>
                    <span class="exploit-count">${exploitCount}</span>
                    ${verifiedCount > 0 ? `<span class="verified-count" title="Проверенных: ${verifiedCount}">✓</span>` : ''}
                </div>`;
        }
        
        riskDiv.innerHTML = html;
    }

    // ===== МЕТОДЫ ДЛЯ РАБОТЫ С ПРОГРЕССОМ =====

    /**
     * Инициализация мониторинга
     */
    initializeMonitoring() {
        // Очищаем существующие интервалы
        this.cleanupMonitoring();
        
        // Проверяем статус фонового обновления
        this.checkBackgroundUpdateStatus();
        
        // Запускаем мониторинг только если есть активные операции
        this.startMonitoringIfNeeded();
    }

    /**
     * Очистка всех интервалов мониторинга
     */
    cleanupMonitoring() {
        if (this.importProgressInterval) {
            clearInterval(this.importProgressInterval);
            this.importProgressInterval = null;
        }
        if (this.backgroundUpdateInterval) {
            clearInterval(this.backgroundUpdateInterval);
            this.backgroundUpdateInterval = null;
        }
    }

    /**
     * Запуск мониторинга только при необходимости
     */
    async startMonitoringIfNeeded() {
        try {
            // Проверяем статус импорта
            const importStatus = await this.app.api.getHostsImportProgress();
            if (importStatus.status === 'processing' || importStatus.status === 'initializing') {
                this.startProgressMonitoring();
            }

            // Проверяем статус фонового обновления
            const updateStatus = await this.app.api.getBackgroundUpdateProgress();
            if (updateStatus.status === 'processing' || updateStatus.status === 'initializing') {
                this.startBackgroundUpdateMonitoring();
            }
        } catch (error) {
            console.error('Error checking monitoring status:', error);
        }
    }

    showImportProgress() {
        const container = document.getElementById('import-progress-container');
        if (container) {
            container.style.display = 'block';
            container.className = 'operation-status active';
        }
    }

    hideImportProgress() {
        const container = document.getElementById('import-progress-container');
        if (container) {
            container.style.display = 'none';
        }
    }

    updateImportProgress(status, currentStep, overallProgress, stepProgress, totalRecords, processedRecords, errorMessage = null) {
        const container = document.getElementById('import-progress-container');
        if (!container) return;

        container.className = 'operation-status ' + status;

        const currentStepText = document.getElementById('current-step-text');
        if (currentStepText) {
            currentStepText.textContent = currentStep;
        }

        const overallProgressText = document.getElementById('overall-progress-text');
        if (overallProgressText) {
            overallProgressText.textContent = Math.round(overallProgress) + '%';
        }

        const progressBarFill = document.getElementById('progress-bar-fill');
        if (progressBarFill) {
            progressBarFill.style.width = overallProgress + '%';
        }

        const totalRecordsText = document.getElementById('total-records-text');
        if (totalRecordsText) {
            totalRecordsText.textContent = totalRecords.toLocaleString();
        }

        if (errorMessage) {
            window.notifications.show('Ошибка: ' + errorMessage, 'error');
        }
    }

    startProgressMonitoring() {
        // Очищаем предыдущий интервал
        if (this.importProgressInterval) {
            clearInterval(this.importProgressInterval);
            this.importProgressInterval = null;
        }


        
        this.importProgressInterval = setInterval(async () => {
            try {
                const data = await this.app.api.getHostsImportProgress();
                
                // Обновляем UI только если есть данные
                if (data && typeof data === 'object') {
                    this.updateImportProgress(
                        data.status || 'unknown',
                        data.current_step || '',
                        data.progress || 0,
                        data.current_step_progress || 0,
                        data.total_records || 0,
                        data.processed_records || 0,
                        data.error_message || null
                    );

                    // Останавливаем интервал при завершении
                    if (data.status === 'completed' || data.status === 'error' || data.status === 'idle') {
                        this.stopProgressMonitoring();
                        
                        // Показываем уведомление о завершении
                        if (data.status === 'completed') {
                            window.notifications.show(`Импорт завершен: ${data.processed_records || 0} записей`, 'success');
                        } else if (data.status === 'error') {
                            window.notifications.show(`Ошибка импорта: ${data.error_message || 'Неизвестная ошибка'}`, 'error');
                        }
                        
                        // Скрываем прогресс-бар через 3 секунды
                        setTimeout(() => {
                            this.hideImportProgress();
                        }, 3000);
                    }
                }
            } catch (err) {
                console.error('Import progress monitoring error:', err);
                this.stopProgressMonitoring();
                
                // Скрываем прогресс-бар при ошибке
                setTimeout(() => {
                    this.hideImportProgress();
                }, 3000);
            }
        }, 1000);
    }

    stopProgressMonitoring() {
        if (this.importProgressInterval) {
            clearInterval(this.importProgressInterval);
            this.importProgressInterval = null;
    
        }
    }

    showBackgroundUpdateProgress() {
        const container = document.getElementById('background-update-progress-container');
        if (container) {
            container.style.display = 'block';
            container.className = 'operation-status active';
        }
    }

    hideBackgroundUpdateProgress() {
        const container = document.getElementById('background-update-progress-container');
        if (container) {
            container.style.display = 'none';
        }
    }

    updateBackgroundUpdateProgress(data) {
        const container = document.getElementById('background-update-progress-container');
        if (container) {
            container.className = 'operation-status ' + (data.status || 'unknown');
        }

        const statusText = document.getElementById('background-current-step-text');
        if (statusText) {
            statusText.textContent = data.current_step || 'Инициализация...';
        }

        if (data.status === 'processing' || data.status === 'initializing') {
            const cancelUpdateBtn = document.getElementById('cancel-update-btn');
            if (cancelUpdateBtn) {
                cancelUpdateBtn.style.display = 'inline-block';
            }
        }

        const progressText = document.getElementById('background-overall-progress-text');
        if (progressText) {
            progressText.textContent = Math.round(data.progress_percent || 0) + '%';
        }

        const progressBarFill = document.getElementById('background-progress-bar-fill');
        if (progressBarFill) {
            progressBarFill.style.width = (data.progress_percent || 0) + '%';
        }

        const processedCvesText = document.getElementById('background-processed-cves-text');
        if (processedCvesText) {
            processedCvesText.textContent = (data.processed_cves || 0).toLocaleString();
        }

        const totalCvesText = document.getElementById('background-total-cves-text');
        if (totalCvesText) {
            totalCvesText.textContent = (data.total_cves || 0).toLocaleString();
        }

        const updatedHostsText = document.getElementById('background-updated-hosts-text');
        if (updatedHostsText) {
            updatedHostsText.textContent = (data.updated_hosts || 0).toLocaleString();
        }

        if (data.error_message && data.status !== 'cancelled' && !data.error_message.toLowerCase().includes('отменено')) {
            window.notifications.show('Ошибка: ' + data.error_message, 'error');
        }

        if (data.status === 'completed' || data.status === 'error' || data.status === 'cancelled') {
            const cancelUpdateBtn = document.getElementById('cancel-update-btn');
            if (cancelUpdateBtn) {
                cancelUpdateBtn.style.display = 'none';
            }
            
            setTimeout(() => {
                this.hideBackgroundUpdateProgress();
            }, 3000);
        }
    }

    startBackgroundUpdateMonitoring() {
        // Очищаем предыдущий интервал
        if (this.backgroundUpdateInterval) {
            clearInterval(this.backgroundUpdateInterval);
            this.backgroundUpdateInterval = null;
        }


        
        this.backgroundUpdateInterval = setInterval(async () => {
            try {
    
                const data = await this.app.api.getBackgroundUpdateProgress();
                
    
                
                // Обновляем UI только если есть данные
                if (data && typeof data === 'object') {
                    this.updateBackgroundUpdateProgress(data);

                    // Останавливаем интервал при завершении
                    if (data.status === 'completed' || data.status === 'error' || data.status === 'idle') {
            
                        this.stopBackgroundUpdateMonitoring();
                        
                        // Показываем уведомление о завершении только если это новое завершение
                        if (data.status === 'completed' && !this.lastNotifiedCompletionTime) {
                            window.notifications.show(`Обновление завершено: ${data.updated_hosts || 0} записей обновлено`, 'success');
                            this.lastNotifiedCompletionTime = data.end_time || data.last_update || Date.now();
                            localStorage.setItem('hosts_last_notification_time', this.lastNotifiedCompletionTime);
                        } else if (data.status === 'error' && !this.lastNotifiedCompletionTime) {
                            window.notifications.show(`Ошибка обновления: ${data.error_message || 'Неизвестная ошибка'}`, 'error');
                            this.lastNotifiedCompletionTime = data.end_time || data.last_update || Date.now();
                            localStorage.setItem('hosts_last_notification_time', this.lastNotifiedCompletionTime);
                        }
                        
                        // Скрываем прогресс-бар через 3 секунды
                        setTimeout(() => {
                            this.hideBackgroundUpdateProgress();
                        }, 3000);
                    }
                }
            } catch (err) {
                console.error('Background update monitoring error:', err);
                this.stopBackgroundUpdateMonitoring();
                
                // Скрываем прогресс-бар при ошибке
                setTimeout(() => {
                    this.hideBackgroundUpdateProgress();
                }, 3000);
            }
        }, 2000); // Увеличиваем интервал до 2 секунд для стабильности
    }

    stopBackgroundUpdateMonitoring() {
        if (this.backgroundUpdateInterval) {
            clearInterval(this.backgroundUpdateInterval);
            this.backgroundUpdateInterval = null;
    
        }
    }

    async checkBackgroundUpdateStatus() {
        try {
    
            const data = await this.app.api.getBackgroundUpdateProgress();
            
            // Проверяем, что получили валидные данные
            if (!data || typeof data !== 'object') {
    
                return;
            }
            
    
            
            // Инициализируем время последнего уведомления при первой проверке
            if (!this.lastNotifiedCompletionTime && (data.status === 'completed' || data.status === 'error' || data.status === 'idle')) {
                this.lastNotifiedCompletionTime = data.end_time || data.last_update || Date.now();
                localStorage.setItem('hosts_last_notification_time', this.lastNotifiedCompletionTime);
            }
            
            // Проверяем только активные состояния
            if (data.status === 'processing' || data.status === 'initializing') {
                this.showBackgroundUpdateProgress();
                this.updateBackgroundUpdateProgress(data);
                
                const cancelUpdateBtn = document.getElementById('cancel-update-btn');
                if (cancelUpdateBtn) {
                    cancelUpdateBtn.style.display = 'inline-block';
                }
                
                // Запускаем мониторинг прогресса обновления
                this.startBackgroundUpdateMonitoring();
                
    
            } else if (data.status === 'error') {
                // Игнорируем ошибки сервера при отсутствии активного обновления
    
            } else {

            }
        } catch (err) {
            console.error('Error checking background update status:', err);
        }
    }

    async checkActiveImportTasks() {
        try {
    
            const data = await this.app.api.getHostsImportProgress();
            
            if (data && data.status && data.status !== 'idle') {
    
                
                // Показываем прогресс-бар
                this.showImportProgress();
                
                // Обновляем прогресс
                this.updateImportProgress(
                    data.status || 'unknown',
                    data.current_step || '',
                    data.progress || 0,
                    data.current_step_progress || 0,
                    data.total_records || 0,
                    data.processed_records || 0,
                    data.error_message || null
                );
                
                // Запускаем мониторинг прогресса
                this.startProgressMonitoring();
                
                // Блокируем кнопку загрузки если задача активна
                const uploadBtn = document.getElementById('hosts-upload-btn');
                if (uploadBtn && (data.status === 'processing' || data.status === 'initializing')) {
                    const btnText = uploadBtn.querySelector('.btn-text');
                    const spinner = uploadBtn.querySelector('.fa-spinner');
                    
                    btnText.textContent = 'Обработка...';
                    spinner.style.display = 'inline-block';
                    uploadBtn.disabled = true;
                }
            }
            
            // Проверяем также задачи обновления
            await this.checkBackgroundUpdateStatus();
            
        } catch (err) {
            console.error('Error checking active import tasks:', err);
        }
    }

    /**
     * Очистка ресурсов модуля
     */
    destroy() {
        this.cleanupMonitoring();
    }
}

// Экспорт модуля
if (typeof module !== 'undefined' && module.exports) {
    module.exports = HostsModule;
} else {
    window.HostsModule = HostsModule;
}
