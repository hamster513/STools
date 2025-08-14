# STools CSS Architecture

## 🎯 Обзор

Новая модульная CSS архитектура для проекта STools, построенная на принципах:
- **Модульность** - каждый файл отвечает за свою область
- **Переиспользование** - общие компоненты не дублируются
- **CSS Grid** - современная система разметки
- **CSS Variables** - централизованное управление стилями
- **Responsive Design** - адаптивность для всех устройств

## 📁 Структура файлов

```
static/css/
├── 📁 base/                    # Базовые стили
│   ├── variables.css          # CSS переменные и темы
│   ├── reset.css              # Сброс стилей браузера
│   └── layout.css             # Система разметки на CSS Grid
├── 📁 components/              # Переиспользуемые компоненты
│   ├── buttons.css            # Кнопки всех типов
│   ├── forms.css              # Формы и поля ввода
│   └── tables.css             # Таблицы и их элементы
├── 📁 pages/                   # Стили конкретных страниц
│   ├── auth.css               # Страницы авторизации
│   ├── vulnanalizer.css       # VulnAnalizer интерфейс
│   └── loganalizer.css        # LogAnalizer интерфейс
└── main.css                   # Главный файл (импорты)
```

## 🎨 CSS Variables

### Цветовая палитра
```css
:root {
    /* Основные цвета */
    --primary-color: #2563eb;
    --primary-hover: #1d4ed8;
    --secondary-color: #64748b;
    
    /* Фоновые цвета */
    --background-color: #ffffff;
    --surface-color: #f8fafc;
    
    /* Текстовые цвета */
    --text-primary: #1e293b;
    --text-secondary: #64748b;
    
    /* Статусные цвета */
    --success-color: #10b981;
    --error-color: #ef4444;
    --warning-color: #f59e0b;
    --danger-color: #dc3545;
    --info-color: #3b82f6;
}
```

### Размеры и отступы
```css
:root {
    /* Типографика */
    --font-size-xs: 0.75rem;
    --font-size-sm: 0.875rem;
    --font-size-base: 1rem;
    --font-size-lg: 1.125rem;
    --font-size-xl: 1.25rem;
    --font-size-2xl: 1.5rem;
    
    /* Отступы */
    --spacing-xs: 0.25rem;
    --spacing-sm: 0.5rem;
    --spacing-md: 1rem;
    --spacing-lg: 1.5rem;
    --spacing-xl: 2rem;
    --spacing-2xl: 3rem;
}
```

## 🏗️ CSS Grid Layout

### Основная разметка
```css
.app-container {
    display: grid;
    grid-template-areas: 
        "sidebar header"
        "sidebar main";
    grid-template-columns: var(--sidebar-width) 1fr;
    grid-template-rows: var(--top-bar-height) 1fr;
    min-height: 100vh;
}
```

### Утилиты Grid
```css
.grid { display: grid; }
.grid-cols-1 { grid-template-columns: repeat(1, 1fr); }
.grid-cols-2 { grid-template-columns: repeat(2, 1fr); }
.grid-cols-3 { grid-template-columns: repeat(3, 1fr); }
.grid-cols-4 { grid-template-columns: repeat(4, 1fr); }

.gap-xs { gap: var(--spacing-xs); }
.gap-sm { gap: var(--spacing-sm); }
.gap-md { gap: var(--spacing-md); }
.gap-lg { gap: var(--spacing-lg); }
```

## 🧩 Компоненты

### Кнопки
```html
<!-- Основная кнопка -->
<button class="btn btn-primary">Primary Button</button>

<!-- Кнопка с иконкой -->
<button class="btn btn-primary btn-icon">
    <i class="fas fa-plus"></i>
</button>

<!-- Группа кнопок -->
<div class="btn-group">
    <button class="btn btn-secondary">Left</button>
    <button class="btn btn-secondary">Center</button>
    <button class="btn btn-secondary">Right</button>
</div>
```

### Формы
```html
<!-- Группа полей -->
<div class="form-group">
    <label class="form-label required">Email</label>
    <input type="email" class="form-input" required>
</div>

<!-- Строка полей -->
<div class="form-row">
    <div class="form-group">
        <label class="form-label">First Name</label>
        <input type="text" class="form-input">
    </div>
    <div class="form-group">
        <label class="form-label">Last Name</label>
        <input type="text" class="form-input">
    </div>
</div>
```

### Таблицы
```html
<!-- Контейнер таблицы -->
<div class="table-container">
    <!-- Заголовок таблицы -->
    <div class="table-header">
        <div class="table-header-cell">Name</div>
        <div class="table-header-cell">Status</div>
        <div class="table-header-cell">Actions</div>
    </div>
    
    <!-- Тело таблицы -->
    <div class="table-body">
        <div class="table-row">
            <div class="table-cell">John Doe</div>
            <div class="table-cell">Active</div>
            <div class="table-cell">Edit</div>
        </div>
    </div>
</div>
```

## 📱 Responsive Design

### Брейкпоинты
```css
/* Mobile First */
@media (max-width: 640px) {
    /* Стили для мобильных */
}

@media (min-width: 641px) and (max-width: 1024px) {
    /* Стили для планшетов */
}

@media (min-width: 1025px) {
    /* Стили для десктопов */
}
```

### Адаптивные утилиты
```css
/* Скрыть на мобильных */
.sm\:hidden { display: none; }

/* Показать только на мобильных */
.md\:hidden { display: none; }

/* Изменить колонки на мобильных */
@media (max-width: 768px) {
    .grid-cols-4 { grid-template-columns: 1fr; }
}
```

## 🌙 Темная тема

```css
.dark-theme {
    --background-color: #0f172a;
    --surface-color: #1e293b;
    --text-primary: #f1f5f9;
    --text-secondary: #cbd5e1;
    --border-color: #334155;
}
```

## 🚀 Использование

### 1. Подключение в HTML
```html
<link rel="stylesheet" href="/static/css/main.css?v=4.0">
```

### 2. Добавление новых компонентов
1. Создайте файл в `components/` или `pages/`
2. Добавьте импорт в `main.css`
3. Используйте CSS переменные для консистентности

### 3. Создание новых страниц
1. Создайте файл в `pages/`
2. Используйте существующие компоненты
3. Добавьте специфичные стили

## 🔧 Утилиты

### Текстовые утилиты
```css
.text-center { text-align: center; }
.text-left { text-align: left; }
.text-right { text-align: right; }

.font-bold { font-weight: 700; }
.font-semibold { font-weight: 600; }
.font-medium { font-weight: 500; }
```

### Цветовые утилиты
```css
.text-primary { color: var(--text-primary); }
.text-secondary { color: var(--text-secondary); }
.text-success { color: var(--success-color); }
.text-error { color: var(--error-color); }

.bg-primary { background-color: var(--primary-color); }
.bg-surface { background-color: var(--surface-color); }
```

### Отступы
```css
.p-0 { padding: 0; }
.p-sm { padding: var(--spacing-sm); }
.p-md { padding: var(--spacing-md); }
.p-lg { padding: var(--spacing-lg); }

.m-0 { margin: 0; }
.m-sm { margin: var(--spacing-sm); }
.m-md { margin: var(--spacing-md); }
.m-lg { margin: var(--spacing-lg); }
```

## 📋 Best Practices

### ✅ Рекомендуется
- Использовать CSS переменные для цветов и размеров
- Применять CSS Grid для разметки
- Создавать переиспользуемые компоненты
- Следовать принципу Mobile First
- Использовать семантические классы

### ❌ Не рекомендуется
- Использовать инлайн-стили
- Дублировать CSS код
- Использовать фиксированные размеры в пикселях
- Игнорировать доступность
- Создавать слишком специфичные селекторы

## 🔄 Миграция

### Из старой системы
1. Запустите скрипт миграции: `./migrate_css.sh`
2. Проверьте работу приложения
3. Удалите старые CSS файлы при необходимости

### Откат изменений
```bash
# Восстановить из бэкапа
cp css_backup_YYYYMMDD_HHMMSS/* /path/to/restore/
```

## 📚 Дополнительные ресурсы

- [CSS Grid Guide](https://css-tricks.com/snippets/css/complete-guide-grid/)
- [CSS Custom Properties](https://developer.mozilla.org/en-US/docs/Web/CSS/Using_CSS_custom_properties)
- [Responsive Design](https://developer.mozilla.org/en-US/docs/Learn/CSS/CSS_layout/Responsive_Design)
