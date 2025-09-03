/**
 * Модуль для работы с модальным окном риска
 * v=1.8
 */
class RiskModalModule {
    constructor(app) {
        this.app = app;
        this.modal = null;
        this.init();
    }

    init() {
        this.modal = document.getElementById('risk-modal');
        this.setupEventListeners();
    }

    setupEventListeners() {
        // Закрытие модального окна по клику на X
        const closeBtn = document.getElementById('risk-modal-close');
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

    show(hostId, cveId) {
        if (!this.modal) return;

        // Показываем модальное окно
        this.modal.style.display = 'flex';
        this.modal.classList.add('show');

        // Показываем загрузку
        this.showLoading();

        // Загружаем данные о риске
        this.loadRiskData(hostId, cveId);
    }

    hide() {
        if (!this.modal) return;

        this.modal.style.display = 'none';
        this.modal.classList.remove('show');
    }

    showLoading() {
        const loading = document.getElementById('risk-modal-loading');
        const content = document.getElementById('risk-modal-content');
        const error = document.getElementById('risk-modal-error');

        if (loading) loading.style.display = 'block';
        if (content) content.style.display = 'none';
        if (error) error.style.display = 'none';
    }

    showError(message) {
        const loading = document.getElementById('risk-modal-loading');
        const content = document.getElementById('risk-modal-content');
        const error = document.getElementById('risk-modal-error');
        const errorMessage = document.getElementById('risk-error-message');

        if (loading) loading.style.display = 'none';
        if (content) content.style.display = 'none';
        if (error) error.style.display = 'block';
        if (errorMessage) errorMessage.textContent = message;
    }

    showContent() {
        const loading = document.getElementById('risk-modal-loading');
        const content = document.getElementById('risk-modal-content');
        const error = document.getElementById('risk-modal-error');

        if (loading) loading.style.display = 'none';
        if (content) content.style.display = 'block';
        if (error) error.style.display = 'none';
    }

    async loadRiskData(hostId, cveId) {
        try {
            const url = `${this.app.getApiBasePath()}/hosts/${hostId}/risk-calculation/${cveId}`;
            const response = await fetch(url);
            const data = await response.json();

            if (data.success) {
                this.displayRiskData(data.risk_data, hostId, cveId);
            } else {
                this.showError(data.message || 'Ошибка загрузки данных о риске');
            }
        } catch (err) {
            console.error('Risk data loading error:', err);
            this.showError('Ошибка загрузки данных о риске');
        }
    }

    displayRiskData(riskData, hostId, cveId) {
        const hostElement = document.getElementById('risk-host-info');
        const cveElement = document.getElementById('risk-cve-info');
        const riskScoreElement = document.getElementById('risk-score-value');
        const riskLevelElement = document.getElementById('risk-level-value');
        const formulaElement = document.getElementById('risk-formula');
        const calculationDetailsElement = document.getElementById('risk-calculation-details');
        const factorsElement = document.getElementById('risk-factors');

        if (hostElement) {
            hostElement.innerHTML = `
                <strong>Хост:</strong> ${riskData.hostname || 'N/A'} 
                <br><strong>IP:</strong> ${riskData.ip_address || 'N/A'}
                <br><strong>Критичность:</strong> <span class="criticality-${riskData.criticality?.toLowerCase() || 'unknown'}">${riskData.criticality || 'N/A'}</span>
            `;
        }

        if (cveElement) {
            cveElement.innerHTML = `
                <strong>CVE:</strong> ${cveId || 'N/A'}
                <br><strong>Описание:</strong> ${riskData.cve_description || 'N/A'}
            `;
        }

        if (riskScoreElement) {
            // Используем пересчитанный риск вместо значения из базы данных
            const displayRisk = riskData.calculated_risk_percent || riskData.risk_score || 0;
            riskScoreElement.textContent = `${displayRisk}%`;
            riskScoreElement.className = `risk-score ${this.getRiskClass(displayRisk)}`;
        }

        if (riskLevelElement) {
            const displayRisk = riskData.calculated_risk_percent || riskData.risk_score || 0;
            riskLevelElement.textContent = this.getRiskLevel(displayRisk);
            riskLevelElement.className = `risk-level ${this.getRiskClass(displayRisk)}`;
        }

        if (formulaElement) {
            // Используем реальные компоненты формулы, если они доступны
            const components = riskData.formula_components || {};
            const epss = components.epss || riskData.epss_score || 0;
            const cvss = components.cvss || riskData.cvss_score || 0;
            const cvssFactor = components.cvss_factor || ((cvss / 10) || 0);
            const impact = components.impact || riskData.impact || 1;
            const cveParam = components.cve_param || 1.0;
            const exdbParam = components.exdb_param || 1.0;
            const msfParam = components.msf_param || 1.0;
            
            // Реальная формула: Risk = EPSS × (CVSS ÷ 10) × Impact × CVE_param × ExDB_param × MSF_param
            const calculatedRisk = epss * cvssFactor * impact * cveParam * exdbParam * msfParam;
            const calculatedRiskPercent = Math.min(1, calculatedRisk) * 100;
            
            formulaElement.innerHTML = `
                <h5>Формула расчета риска:</h5>
                <div class="risk-formula-display">
                    <div class="formula-main">
                        <strong>Risk = EPSS × (CVSS ÷ 10) × Impact × CVE_param × ExDB_param × MSF_param</strong>
                    </div>
                    <div class="formula-breakdown">
                        <div class="formula-component">
                            <strong>EPSS:</strong> ${(epss * 100).toFixed(2)}% = ${epss.toFixed(5)}
                        </div>
                        <div class="formula-component">
                            <strong>CVSS:</strong> ${cvss.toFixed(1)} ÷ 10 = ${cvssFactor.toFixed(2)}
                        </div>
                        <div class="formula-component">
                            <strong>Impact:</strong> ${impact.toFixed(2)}
                        </div>
                        <div class="formula-component">
                            <strong>CVE_param:</strong> ${cveParam}
                        </div>
                        <div class="formula-component">
                            <strong>ExDB_param:</strong> ${exdbParam}
                        </div>
                        <div class="formula-component">
                            <strong>MSF_param:</strong> ${msfParam}
                        </div>
                    </div>
                    <div class="formula-result">
                        <strong>Результат:</strong> ${epss.toFixed(5)} × ${cvssFactor.toFixed(2)} × ${impact.toFixed(2)} × ${cveParam} × ${exdbParam} × ${msfParam} = <span class="formula-final-result">${(calculatedRisk * 100).toFixed(2)}%</span>
                    </div>
                    <div class="formula-note">
                        <small><em>Примечание: Финальный риск ограничен 100% (произведено округление)</em></small>
                    </div>
                </div>
            `;
        }

        if (calculationDetailsElement) {
            const components = riskData.formula_components || {};
            
            calculationDetailsElement.innerHTML = `
                <h5>Детали расчета:</h5>
                <div class="risk-calculation-breakdown">
                    <div class="risk-factor">
                        <strong>Базовый риск:</strong> ${riskData.base_risk || 0}%
                    </div>
                    <div class="risk-factor">
                        <strong>Множитель критичности:</strong> ${riskData.criticality_multiplier || 1.0}x
                    </div>
                    <div class="risk-factor">
                        <strong>Множитель EPSS:</strong> ${riskData.epss_multiplier || 1.0}x
                    </div>
                    <div class="risk-factor">
                        <strong>Множитель эксплойтов:</strong> ${riskData.exploits_multiplier || 1.0}x
                    </div>
                    <div class="risk-factor">
                        <strong>Финальный расчет:</strong> ${riskData.final_calculation || 'N/A'}
                    </div>
                </div>
                
                <h5>Детали параметров формулы:</h5>
                <div class="risk-parameters-breakdown">
                    <div class="risk-parameter">
                        <strong>CVE_param (${components.cve_param || 1.0}):</strong>
                        <div class="parameter-explanation">
                            ${this.getCveParamExplanation(components, riskData)}
                        </div>
                    </div>
                    <div class="risk-parameter">
                        <strong>ExDB_param (${components.exdb_param || 1.0}):</strong>
                        <div class="parameter-explanation">
                            ${this.getExdbParamExplanation(components, riskData)}
                        </div>
                    </div>
                    <div class="risk-parameter">
                        <strong>MSF_param (${components.msf_param || 1.0}):</strong>
                        <div class="parameter-explanation">
                            ${this.getMsfParamExplanation(components, riskData)}
                        </div>
                    </div>
                </div>
            `;
        }

        if (factorsElement) {
            let factorsHtml = '<h5>Факторы риска:</h5><div class="risk-factors-list">';
            
            if (riskData.cvss_score) {
                factorsHtml += `
                    <div class="risk-factor-item">
                        <i class="fas fa-shield-alt"></i>
                        <strong>CVSS:</strong> ${riskData.cvss_score} (${riskData.cvss_severity || 'Unknown'})
                    </div>
                `;
            }
            
            if (riskData.epss_score !== undefined) {
                factorsHtml += `
                    <div class="risk-factor-item">
                        <i class="fas fa-chart-line"></i>
                        <strong>EPSS:</strong> ${(riskData.epss_score * 100).toFixed(2)}%
                    </div>
                `;
            }
            
            if (riskData.exploits_count) {
                factorsHtml += `
                    <div class="risk-factor-item">
                        <i class="fas fa-bug"></i>
                        <strong>Эксплойты:</strong> ${riskData.exploits_count}
                    </div>
                `;
            }
            
            if (riskData.metasploit_rank) {
                factorsHtml += `
                    <div class="risk-factor-item">
                        <i class="fas fa-tools"></i>
                        <strong>Metasploit:</strong> ${riskData.metasploit_rank}
                    </div>
                `;
            }
            
            factorsHtml += '</div>';
            factorsElement.innerHTML = factorsHtml;
        }

        this.showContent();
    }

    getRiskClass(riskScore) {
        if (riskScore >= 70) return 'high-risk';
        if (riskScore >= 40) return 'medium-risk';
        return 'low-risk';
    }

    getRiskLevel(riskScore) {
        if (riskScore >= 70) return 'Высокий';
        if (riskScore >= 40) return 'Средний';
        return 'Низкий';
    }

    // Метод для создания кликабельной ссылки риска
    createRiskLink(riskScore, hostId, cveId) {
        if (!riskScore || riskScore === 'N/A') return '<span class="risk-score">N/A</span>';
        
        const riskClass = this.getRiskClass(riskScore);
        let riskText;
        
        if (riskScore < 0.1) {
            riskText = riskScore.toFixed(2);
        } else if (riskScore < 1) {
            riskText = riskScore.toFixed(1);
        } else {
            riskText = Math.round(riskScore);
        }
        
        return `<span class="risk-score ${riskClass} risk-link" onclick="window.vulnAnalizer.riskModal.show('${hostId}', '${cveId}')" title="Нажмите для просмотра деталей расчета">${riskText}%</span>`;
    }

    // Методы для объяснения параметров формулы
    getCveParamExplanation(components, riskData) {
        const cveParam = components.cve_param || 1.0;
        
        if (cveParam === 1.0) {
            return 'Значение по умолчанию. CVSS метрики (Attack Vector, Privileges Required, User Interaction) не найдены или не применимы.';
        }
        
        let explanation = 'Рассчитан на основе CVSS метрик:';
        
        if (riskData.cvss_v3_attack_vector) {
            explanation += `<br>• Attack Vector: ${riskData.cvss_v3_attack_vector}`;
        }
        if (riskData.cvss_v3_privileges_required) {
            explanation += `<br>• Privileges Required: ${riskData.cvss_v3_privileges_required}`;
        }
        if (riskData.cvss_v3_user_interaction) {
            explanation += `<br>• User Interaction: ${riskData.cvss_v3_user_interaction}`;
        }
        if (riskData.cvss_v2_access_vector) {
            explanation += `<br>• Access Vector (v2): ${riskData.cvss_v2_access_vector}`;
        }
        if (riskData.cvss_v2_access_complexity) {
            explanation += `<br>• Access Complexity (v2): ${riskData.cvss_v2_access_complexity}`;
        }
        if (riskData.cvss_v2_authentication) {
            explanation += `<br>• Authentication (v2): ${riskData.cvss_v2_authentication}`;
        }
        
        explanation += `<br><br>Финальный множитель: ${cveParam.toFixed(3)}`;
        return explanation;
    }

    getExdbParamExplanation(components, riskData) {
        const exdbParam = components.exdb_param || 1.0;
        
        if (exdbParam === 1.0) {
            return 'Значение по умолчанию. Эксплойт не найден в базе данных ExploitDB или тип эксплойта не определен.';
        }
        
        const exdbTypes = {
            1.3: 'remote - удаленный эксплойт (высокий риск)',
            1.2: 'webapps - веб-приложение (повышенный риск)',
            1.05: 'local - локальный эксплойт (небольшое повышение)',
            0.85: 'dos - отказ в обслуживании (снижение риска)',
            1.0: 'hardware - аппаратный эксплойт (нейтральный)'
        };
        
        const explanation = exdbTypes[exdbParam] || `Неизвестный тип: ${exdbParam}`;
        return `Тип эксплойта: ${explanation}`;
    }

    getMsfParamExplanation(components, riskData) {
        const msfParam = components.msf_param || 1.0;
        
        if (msfParam === 1.0) {
            return 'Значение по умолчанию. Эксплойт не найден в базе данных Metasploit или ранг не определен.';
        }
        
        const msfRanks = {
            1.3: 'excellent - отличный эксплойт (высокий риск)',
            1.25: 'good - хороший эксплойт (повышенный риск)',
            1.2: 'normal - обычный эксплойт (небольшое повышение)',
            1.1: 'average - средний эксплойт (минимальное повышение)',
            0.8: 'low/unknown - низкий/неизвестный ранг (снижение риска)',
            1.0: 'manual - ручной эксплойт (нейтральный)'
        };
        
        const explanation = msfRanks[msfParam] || `Неизвестный ранг: ${msfParam}`;
        return `Ранг Metasploit: ${explanation}`;
    }
}

// Экспорт для использования в других модулях
if (typeof module !== 'undefined' && module.exports) {
    module.exports = RiskModalModule;
} else {
    window.RiskModalModule = RiskModalModule;
}
