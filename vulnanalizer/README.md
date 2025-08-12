# VulnAnalizer - Анализатор уязвимостей

## Версия 0.3.0001

### Новые возможности в версии 0.3.0001

#### Загрузка базы CVE
Добавлена возможность загрузки базы данных CVE (Common Vulnerabilities and Exposures) из NVD (National Vulnerability Database).

**Возможности:**
- Загрузка JSON файлов CVE (поддерживаются архивы .gz)
- Автоматическое скачивание с NVD за период с 2010 года
- Парсинг CVSS v2 и v3 оценок
- Извлечение описаний уязвимостей
- Хранение exploitability и impact scores

**Источники данных:**
- NVD CVE Feeds: https://nvd.nist.gov/feeds/json/cve/1.1/
- Поддерживаемые форматы: JSON, GZ (архив)

#### Улучшенная интеграция с хостами
- Автоматическое обновление CVSS оценок при импорте хостов
- Приоритет CVSS: CVE база > EPSS > исходный CVSS хоста
- Отображение источника CVSS оценки (CVSS v3, CVSS v2, EPSS, Host)
- Пометка для CVSS v2 оценок

#### Сортировка по уровню риска
Добавлена возможность сортировки хостов по различным критериям:
- По риску (убывание/возрастание)
- По CVSS (убывание/возрастание)
- По EPSS (убывание/возрастание)
- По количеству эксплойтов (убывание/возрастание)

### Структура базы данных

#### Таблица CVE
```sql
CREATE TABLE cve (
    id SERIAL PRIMARY KEY,
    cve_id VARCHAR(20) UNIQUE NOT NULL,
    description TEXT,
    cvss_v3_base_score DECIMAL(3,1),
    cvss_v3_base_severity VARCHAR(20),
    cvss_v2_base_score DECIMAL(3,1),
    cvss_v2_base_severity VARCHAR(20),
    exploitability_score DECIMAL(3,1),
    impact_score DECIMAL(3,1),
    published_date TIMESTAMP,
    last_modified_date TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### Обновленная таблица hosts
Добавлено поле `cvss_source` для хранения источника CVSS оценки.

### API Endpoints

#### CVE
- `POST /api/cve/upload` - Загрузка CVE из файла
- `POST /api/cve/download` - Скачивание CVE с NVD
- `GET /api/cve/status` - Статус CVE данных
- `POST /api/cve/clear` - Очистка CVE данных
- `GET /api/cve/download-urls` - Ссылки для скачивания

#### Hosts (обновлено)
- `GET /api/hosts/search` - Поиск хостов с поддержкой сортировки

### Использование

1. **Загрузка CVE данных:**
   - Перейдите в раздел "Настройки"
   - Найдите блок "Загрузка базы CVE"
   - Выберите файл JSON или GZ архива
   - Нажмите "Загрузить файл"

2. **Автоматическое скачивание:**
   - Нажмите "Скачать с NVD" для загрузки данных за все годы
   - Или используйте "Ссылки для скачивания" для offline загрузки

3. **Сортировка хостов:**
   - В разделе "Анализ" выберите критерий сортировки
   - Доступны сортировки по риску, CVSS, EPSS, количеству эксплойтов

### Технические детали

#### Парсинг CVE JSON
Система парсит JSON файлы NVD и извлекает:
- CVE ID
- Описание уязвимости
- CVSS v3.1 и v3.0 оценки
- CVSS v2 оценки
- Exploitability и Impact scores
- Даты публикации и модификации

#### Приоритет CVSS оценок
При импорте хостов система использует следующий приоритет:
1. CVSS v3 из базы CVE
2. CVSS v2 из базы CVE (с пометкой)
3. CVSS из EPSS
4. Исходный CVSS хоста

### Требования
- Python 3.11+
- PostgreSQL 13+
- Docker и Docker Compose

### Установка и запуск
```bash
# Клонирование репозитория
git clone <repository-url>
cd STools

# Запуск с Docker Compose
docker-compose up -d

# Доступ к приложению
https://localhost/vulnanalizer/
```

### Лицензия
MIT License
