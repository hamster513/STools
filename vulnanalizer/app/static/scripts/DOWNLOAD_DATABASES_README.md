# Скачивание баз данных уязвимостей

Эти скрипты автоматически скачивают все необходимые базы данных для VulnAnalizer:
- **EPSS** - оценки вероятности эксплуатации уязвимостей
- **ExploitDB** - база публичных эксплойтов
- **Metasploit** - модули фреймворка Metasploit
- **CVE** - полная база уязвимостей NVD (2002 - текущий год)

## 📋 Требования

### Linux/macOS
- `bash`
- `curl`
- `zip` (или `tar`)

### Windows
- PowerShell 5.0 или выше
- .NET Framework 4.5 или выше (для создания ZIP)

## 🚀 Использование

### Linux/macOS

```bash
./download_vulnerability_databases.sh
```

### Windows

```powershell
.\download_vulnerability_databases.ps1
```

Или через PowerShell с разрешением выполнения:

```powershell
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process
.\download_vulnerability_databases.ps1
```

## 📦 Результат

После выполнения скрипта будет создан архив:
```
vulnerability_databases_YYYYMMDD_HHMMSS.zip
```

### Структура архива:

```
vulnerability_databases_YYYYMMDD_HHMMSS/
├── epss/
│   └── epss_scores-current.csv.gz
├── exploitdb/
│   └── files_exploits.csv
├── metasploit/
│   └── modules_metadata_base.json
└── cve/
    ├── nvdcve-2.0-2002.json.gz
    ├── nvdcve-2.0-2003.json.gz
    ├── ...
    └── nvdcve-2.0-2025.json.gz
```

## ⏱️ Время выполнения

- **EPSS**: ~10 секунд (~50 MB)
- **ExploitDB**: ~5 секунд (~15 MB)
- **Metasploit**: ~5 секунд (~20 MB)
- **CVE**: ~10-15 минут (~2-3 GB, зависит от скорости интернета)

**Общее время**: ~15-20 минут

**Размер архива**: ~2-3 GB

## 📥 Импорт в VulnAnalizer

После скачивания:

1. Распакуйте архив
2. Откройте VulnAnalizer → **Настройки**
3. Загрузите файлы через соответствующие разделы:
   - **EPSS**: Загрузка базы EPSS → выберите `epss_scores-current.csv.gz`
   - **ExploitDB**: Загрузка базы ExploitDB → выберите `files_exploits.csv`
   - **Metasploit**: (загружается автоматически через API)
   - **CVE**: Загрузка базы CVE → выберите файлы `nvdcve-2.0-*.json.gz` (можно загружать по годам)

## ⚠️ Важные замечания

1. **Скачивание CVE занимает много времени** - NVD ограничивает скорость запросов
2. **Требуется стабильное интернет-соединение** - файлы большие
3. **Архив занимает ~2-3 GB** - убедитесь что есть свободное место
4. **Скрипт добавляет паузы** между запросами к NVD (1 секунда) чтобы не перегружать сервер

## 🔧 Настройка

### Изменение диапазона годов для CVE

В bash скрипте:
```bash
START_YEAR=2002  # Измените начальный год
```

В PowerShell скрипте:
```powershell
$startYear = 2002  # Измените начальный год
```

### Скачивание только определенных годов

Можно вручную отредактировать скрипт, изменив цикл `for` на нужный диапазон.

## 📝 Альтернативные источники

Если основные источники недоступны:

- **EPSS**: https://api.first.org/data/v1/epss (API)
- **ExploitDB**: https://www.exploit-db.com/ (веб-интерфейс)
- **Metasploit**: https://github.com/rapid7/metasploit-framework
- **CVE**: https://nvd.nist.gov/vuln/data-feeds (официальный сайт)

## 🆘 Решение проблем

### Ошибка "curl: command not found" (Linux/macOS)
Установите curl:
```bash
# Ubuntu/Debian
sudo apt-get install curl

# macOS
brew install curl
```

### Ошибка "zip: command not found" (Linux/macOS)
Скрипт автоматически использует `tar` вместо `zip`.

### Ошибка скачивания с NVD
NVD может временно блокировать запросы. Подождите несколько минут и попробуйте снова.

### Ошибка создания ZIP в PowerShell
Убедитесь что установлен .NET Framework 4.5 или выше.

## 📞 Поддержка

При возникновении проблем:
1. Проверьте подключение к интернету
2. Убедитесь что URL-ы источников актуальны
3. Проверьте свободное место на диске (~3-4 GB)
4. Проверьте логи выполнения скрипта

## 📄 Лицензия

Данные скачиваются из публичных источников:
- EPSS: https://www.first.org/epss/
- ExploitDB: https://www.exploit-db.com/
- Metasploit: https://github.com/rapid7/metasploit-framework
- CVE/NVD: https://nvd.nist.gov/

Убедитесь что соблюдаете условия использования каждого источника.

