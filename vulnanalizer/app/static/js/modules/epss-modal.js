/**
 * Модуль для модального окна предварительного просмотра EPSS данных
 */
class EPSSModalModule extends BaseModalModule {
    constructor(app) {
        super(app, {
            modalId: 'epss-modal',
            closeId: 'epss-modal-close',
            contentId: 'epss-modal-content',
            apiEndpoint: '/vulnanalizer/api/epss/preview',
            tableId: 'epss-table',
            title: 'EPSS'
        });
    }

    getTableHeaders() {
        return `
            <th>CVE ID</th>
            <th>EPSS Score</th>
            <th>Percentile</th>
            <th>CVSS Score</th>
            <th>Created At</th>
        `;
    }

    getColumnCount() {
        return 5;
    }

    formatRow(record) {
        const epssScore = this.formatEPSSScore(record.epss);
        const percentile = this.formatPercentile(record.percentile);
        const cvssScore = this.formatCVSSScore(record.cvss);

        return `
            <td>${record.cve || 'N/A'}</td>
            <td>${epssScore}</td>
            <td>${percentile}</td>
            <td>${cvssScore}</td>
            <td>${this.formatDate(record.created_at)}</td>
        `;
    }

    formatEPSSScore(score) {
        if (score === null || score === undefined) return 'N/A';
        const scoreClass = this.getEPSSScoreClass(score);
        return `<span class="epss-score ${scoreClass}">${(score * 100).toFixed(2)}%</span>`;
    }

    getEPSSScoreClass(score) {
        if (score >= 0.7) return 'epss-high';
        if (score >= 0.4) return 'epss-medium';
        return 'epss-low';
    }

    formatPercentile(percentile) {
        if (percentile === null || percentile === undefined) return 'N/A';
        const percentileClass = this.getPercentileClass(percentile);
        return `<span class="epss-percentile ${percentileClass}">${(percentile * 100).toFixed(1)}%</span>`;
    }

    getPercentileClass(percentile) {
        if (percentile >= 0.8) return 'percentile-high';
        if (percentile >= 0.5) return 'percentile-medium';
        return 'percentile-low';
    }

    formatCVSSScore(score) {
        if (score === null || score === undefined) return 'N/A';
        const scoreClass = this.getCVSSScoreClass(score);
        return `<span class="cvss-score ${scoreClass}">${score}</span>`;
    }

    getCVSSScoreClass(score) {
        if (score >= 9.0) return 'cvss-critical';
        if (score >= 7.0) return 'cvss-high';
        if (score >= 4.0) return 'cvss-medium';
        return 'cvss-low';
    }

    formatDate(dateString) {
        if (!dateString) return 'N/A';
        try {
            const date = new Date(dateString);
            return date.toLocaleDateString('ru-RU');
        } catch (e) {
            return dateString;
        }
    }
}
