/**
 * Модуль для модального окна предварительного просмотра Metasploit данных
 */
class MetasploitModalModule extends BaseModalModule {
    constructor(app) {
        super(app, {
            modalId: 'metasploit-modal',
            closeId: 'metasploit-modal-close',
            contentId: 'metasploit-modal-content',
            apiEndpoint: '/vulnanalizer/api/metasploit/preview',
            tableId: 'metasploit-table',
            title: 'Metasploit'
        });
    }

    getTableHeaders() {
        return `
            <th>Name</th>
            <th>Rank</th>
            <th>Type</th>
            <th>Disclosure Date</th>
            <th>Description</th>
        `;
    }

    getColumnCount() {
        return 5;
    }

    formatRow(record) {
        const rankBadge = this.getRankBadge(record.rank_text);
        const typeBadge = this.getTypeBadge(record.type);
        const disclosureDate = record.disclosure_date ? this.formatDate(record.disclosure_date) : 'Не указана';
        const description = this.truncateText(record.description, 100);

        return `
            <td>${record.name || 'N/A'}</td>
            <td>${rankBadge}</td>
            <td>${typeBadge}</td>
            <td>${disclosureDate}</td>
            <td title="${record.description || ''}">${description}</td>
        `;
    }

    getRankBadge(rank) {
        const rankClass = this.getRankClass(rank);
        return `<span class="rank-badge ${rankClass}">${rank || 'N/A'}</span>`;
    }

    getRankClass(rank) {
        switch (rank?.toLowerCase()) {
            case 'manual': return 'rank-manual';
            case 'low': return 'rank-low';
            case 'average': return 'rank-average';
            case 'normal': return 'rank-normal';
            case 'good': return 'rank-good';
            case 'excellent': return 'rank-excellent';
            default: return 'rank-unknown';
        }
    }

    getTypeBadge(type) {
        const typeClass = this.getTypeClass(type);
        return `<span class="type-badge ${typeClass}">${type || 'N/A'}</span>`;
    }

    getTypeClass(type) {
        switch (type?.toLowerCase()) {
            case 'exploit': return 'type-exploit';
            case 'auxiliary': return 'type-auxiliary';
            case 'post': return 'type-post';
            case 'payload': return 'type-payload';
            case 'encoder': return 'type-encoder';
            case 'nop': return 'type-nop';
            default: return 'type-unknown';
        }
    }

    formatDate(dateString) {
        if (!dateString) return 'Не указана';
        try {
            const date = new Date(dateString);
            return date.toLocaleDateString('ru-RU');
        } catch (e) {
            return dateString;
        }
    }

    truncateText(text, maxLength) {
        if (!text) return 'N/A';
        if (text.length <= maxLength) return text;
        return text.substring(0, maxLength) + '...';
    }
}
