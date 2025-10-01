// Telegram Mass Platform - Основной JavaScript

// Глобальные переменные
let notifications = [];
let currentUser = null;

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
});

function initializeApp() {
    // Инициализация уведомлений
    initializeNotifications();
    
    // Инициализация модальных окон
    initializeModals();
    
    // Инициализация таблиц
    initializeTables();
    
    console.log('Telegram Mass Platform инициализирована');
}

// Система уведомлений
function initializeNotifications() {
    const container = document.getElementById('notifications');
    if (!container) return;
    
    // Создаем контейнер для уведомлений если его нет
    if (!container.querySelector('.notifications-container')) {
        container.innerHTML = '<div class="notifications-container"></div>';
    }
}

function showNotification(message, type = 'info', duration = 5000) {
    const container = document.getElementById('notifications');
    if (!container) return;
    
    const notificationContainer = container.querySelector('.notifications-container') || container;
    
    const notification = document.createElement('div');
    notification.className = `alert alert-${type} alert-dismissible fade show notification-item`;
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        z-index: 9999;
        min-width: 300px;
        max-width: 500px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        animation: slideInRight 0.3s ease-out;
    `;
    
    notification.innerHTML = `
        <i class="fas ${getNotificationIcon(type)}"></i>
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    notificationContainer.appendChild(notification);
    
    // Автоматическое удаление
    if (duration > 0) {
        setTimeout(() => {
            if (notification.parentNode) {
                notification.remove();
            }
        }, duration);
    }
    
    // Добавляем анимацию появления
    setTimeout(() => {
        notification.style.transform = 'translateX(0)';
    }, 10);
}

function getNotificationIcon(type) {
    const icons = {
        'success': 'fa-check-circle',
        'error': 'fa-exclamation-circle',
        'warning': 'fa-exclamation-triangle',
        'info': 'fa-info-circle'
    };
    return icons[type] || 'fa-info-circle';
}

// Модальные окна
function initializeModals() {
    // Инициализация всех модальных окон Bootstrap
    const modals = document.querySelectorAll('.modal');
    modals.forEach(modal => {
        new bootstrap.Modal(modal);
    });
}

function showLoadingModal() {
    const modal = document.getElementById('loadingModal');
    if (modal) {
        const bsModal = new bootstrap.Modal(modal, { backdrop: 'static', keyboard: false });
        bsModal.show();
    }
}

function hideLoadingModal() {
    const modal = document.getElementById('loadingModal');
    if (modal) {
        const bsModal = bootstrap.Modal.getInstance(modal);
        if (bsModal) {
            bsModal.hide();
        }
    }
}

// Таблицы
function initializeTables() {
    // Инициализация всех таблиц с сортировкой
    const tables = document.querySelectorAll('table[data-sortable]');
    tables.forEach(table => {
        makeTableSortable(table);
    });
}

function makeTableSortable(table) {
    const headers = table.querySelectorAll('th[data-sort]');
    headers.forEach(header => {
        header.style.cursor = 'pointer';
        header.innerHTML += ' <i class="fas fa-sort text-muted"></i>';
        
        header.addEventListener('click', () => {
            const column = header.dataset.sort;
            const isAscending = header.classList.contains('sort-asc');
            
            // Убираем классы сортировки со всех заголовков
            headers.forEach(h => {
                h.classList.remove('sort-asc', 'sort-desc');
                h.querySelector('i').className = 'fas fa-sort text-muted';
            });
            
            // Добавляем класс сортировки к текущему заголовку
            if (isAscending) {
                header.classList.add('sort-desc');
                header.querySelector('i').className = 'fas fa-sort-down text-primary';
            } else {
                header.classList.add('sort-asc');
                header.querySelector('i').className = 'fas fa-sort-up text-primary';
            }
            
            // Сортируем таблицу
            sortTable(table, column, !isAscending);
        });
    });
}

function sortTable(table, column, ascending) {
    const tbody = table.querySelector('tbody');
    const rows = Array.from(tbody.querySelectorAll('tr'));
    
    rows.sort((a, b) => {
        const aVal = a.querySelector(`td:nth-child(${getColumnIndex(table, column)})`).textContent.trim();
        const bVal = b.querySelector(`td:nth-child(${getColumnIndex(table, column)})`).textContent.trim();
        
        // Попытка числового сравнения
        const aNum = parseFloat(aVal);
        const bNum = parseFloat(bVal);
        
        if (!isNaN(aNum) && !isNaN(bNum)) {
            return ascending ? aNum - bNum : bNum - aNum;
        }
        
        // Строковое сравнение
        return ascending ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal);
    });
    
    // Перестраиваем таблицу
    rows.forEach(row => tbody.appendChild(row));
}

function getColumnIndex(table, column) {
    const headers = table.querySelectorAll('th');
    for (let i = 0; i < headers.length; i++) {
        if (headers[i].dataset.sort === column) {
            return i + 1;
        }
    }
    return 1;
}

// API функции
async function apiRequest(url, options = {}) {
    const defaultOptions = {
        headers: {
            'Content-Type': 'application/json',
        },
    };
    
    const finalOptions = { ...defaultOptions, ...options };
    
    try {
        const response = await fetch(url, finalOptions);
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'Ошибка сервера');
        }
        
        return data;
    } catch (error) {
        console.error('API Error:', error);
        showNotification(error.message, 'error');
        throw error;
    }
}

// Утилиты для работы с данными
function formatDate(dateString) {
    if (!dateString) return '-';
    
    const date = new Date(dateString);
    return date.toLocaleString('ru-RU', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
    });
}

function formatNumber(number) {
    if (number === null || number === undefined) return '0';
    return number.toLocaleString('ru-RU');
}

function truncateText(text, maxLength = 50) {
    if (!text) return '-';
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength) + '...';
}

// Функции для работы с файлами
function selectFile(callback, accept = '*') {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = accept;
    input.style.display = 'none';
    
    input.addEventListener('change', (e) => {
        const file = e.target.files[0];
        if (file && callback) {
            callback(file);
        }
    });
    
    document.body.appendChild(input);
    input.click();
    document.body.removeChild(input);
}

function downloadFile(data, filename, type = 'text/plain') {
    const blob = new Blob([data], { type });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
}

// Функции для работы с формой
function serializeForm(form) {
    const formData = new FormData(form);
    const data = {};
    
    for (let [key, value] of formData.entries()) {
        data[key] = value;
    }
    
    return data;
}

function clearForm(form) {
    form.reset();
    // Очищаем все кастомные элементы
    const customElements = form.querySelectorAll('.form-control, .form-select');
    customElements.forEach(element => {
        element.classList.remove('is-valid', 'is-invalid');
    });
}

// Валидация форм
function validateForm(form) {
    let isValid = true;
    const requiredFields = form.querySelectorAll('[required]');
    
    requiredFields.forEach(field => {
        if (!field.value.trim()) {
            field.classList.add('is-invalid');
            isValid = false;
        } else {
            field.classList.remove('is-invalid');
            field.classList.add('is-valid');
        }
    });
    
    return isValid;
}

// Функции для работы с аккаунтами
function getAccountStatusBadge(status) {
    const statuses = {
        'online': { class: 'bg-success', text: '🟢 Онлайн' },
        'banned': { class: 'bg-danger', text: '🔴 Забанен' },
        'checking': { class: 'bg-warning', text: '🟡 Проверка' },
        'offline': { class: 'bg-secondary', text: '⚫ Офлайн' }
    };
    
    return statuses[status] || statuses['offline'];
}

function getCountryFlag(country) {
    const flags = {
        'DE': '🇩🇪',
        'US': '🇺🇸',
        'RU': '🇷🇺',
        'GB': '🇬🇧',
        'FR': '🇫🇷',
        'IT': '🇮🇹',
        'ES': '🇪🇸',
        'NL': '🇳🇱',
        'PL': '🇵🇱',
        'UA': '🇺🇦'
    };
    return flags[country] || '🌍';
}

// Функции для работы с прокси
function formatProxy(proxy) {
    if (!proxy) return '-';
    return `${proxy.ip}:${proxy.port}`;
}

function validateProxyFormat(proxyString) {
    const pattern = /^(\d{1,3}\.){3}\d{1,3}:\d{1,5}(:\w+:\w+)?$/;
    return pattern.test(proxyString);
}

// Функции для работы с логами
function addLogEntry(accountId, action, target, status, message) {
    const logEntry = {
        timestamp: new Date().toISOString(),
        accountId,
        action,
        target,
        status,
        message
    };
    
    // Сохраняем в localStorage для демонстрации
    const logs = JSON.parse(localStorage.getItem('telegram_logs') || '[]');
    logs.unshift(logEntry);
    
    // Ограничиваем количество логов
    if (logs.length > 1000) {
        logs.splice(1000);
    }
    
    localStorage.setItem('telegram_logs', JSON.stringify(logs));
    
    // Обновляем UI если есть элемент для логов
    updateLogsDisplay();
}

function updateLogsDisplay() {
    const logsContainer = document.getElementById('logs-container');
    if (!logsContainer) return;
    
    const logs = JSON.parse(localStorage.getItem('telegram_logs') || '[]');
    const recentLogs = logs.slice(0, 50); // Показываем только последние 50
    
    logsContainer.innerHTML = recentLogs.map(log => `
        <div class="log-entry">
            <span class="log-time">${formatDate(log.timestamp)}</span>
            <span class="log-account">Аккаунт ${log.accountId}</span>
            <span class="log-action">${log.action}</span>
            <span class="log-target">${log.target}</span>
            <span class="log-status badge ${getLogStatusClass(log.status)}">${log.status}</span>
            <span class="log-message">${log.message}</span>
        </div>
    `).join('');
}

function getLogStatusClass(status) {
    const classes = {
        'success': 'bg-success',
        'error': 'bg-danger',
        'warning': 'bg-warning',
        'info': 'bg-info'
    };
    return classes[status] || 'bg-secondary';
}

// Функции для работы с графиками
function createChart(canvasId, type, data, options = {}) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return null;
    
    const defaultOptions = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: {
                position: 'bottom'
            }
        }
    };
    
    const finalOptions = { ...defaultOptions, ...options };
    
    return new Chart(ctx, {
        type,
        data,
        options: finalOptions
    });
}

// Функции для работы с пагинацией
function createPagination(containerId, currentPage, totalPages, onPageChange) {
    const container = document.getElementById(containerId);
    if (!container) return;
    
    let paginationHTML = '';
    
    // Предыдущая страница
    if (currentPage > 1) {
        paginationHTML += `<li class="page-item"><a class="page-link" href="#" onclick="${onPageChange}(${currentPage - 1})">Предыдущая</a></li>`;
    }
    
    // Страницы
    const startPage = Math.max(1, currentPage - 2);
    const endPage = Math.min(totalPages, currentPage + 2);
    
    if (startPage > 1) {
        paginationHTML += `<li class="page-item"><a class="page-link" href="#" onclick="${onPageChange}(1)">1</a></li>`;
        if (startPage > 2) {
            paginationHTML += `<li class="page-item disabled"><span class="page-link">...</span></li>`;
        }
    }
    
    for (let i = startPage; i <= endPage; i++) {
        const activeClass = i === currentPage ? 'active' : '';
        paginationHTML += `<li class="page-item ${activeClass}"><a class="page-link" href="#" onclick="${onPageChange}(${i})">${i}</a></li>`;
    }
    
    if (endPage < totalPages) {
        if (endPage < totalPages - 1) {
            paginationHTML += `<li class="page-item disabled"><span class="page-link">...</span></li>`;
        }
        paginationHTML += `<li class="page-item"><a class="page-link" href="#" onclick="${onPageChange}(${totalPages})">${totalPages}</a></li>`;
    }
    
    // Следующая страница
    if (currentPage < totalPages) {
        paginationHTML += `<li class="page-item"><a class="page-link" href="#" onclick="${onPageChange}(${currentPage + 1})">Следующая</a></li>`;
    }
    
    container.innerHTML = paginationHTML;
}

// Функции для работы с фильтрами
function applyTableFilters(tableId, filters) {
    const table = document.getElementById(tableId);
    if (!table) return;
    
    const tbody = table.querySelector('tbody');
    const rows = Array.from(tbody.querySelectorAll('tr'));
    
    rows.forEach(row => {
        let show = true;
        
        Object.keys(filters).forEach(key => {
            const filterValue = filters[key];
            if (!filterValue) return;
            
            const cell = row.querySelector(`[data-filter="${key}"]`);
            if (!cell) return;
            
            const cellValue = cell.textContent.toLowerCase();
            if (!cellValue.includes(filterValue.toLowerCase())) {
                show = false;
            }
        });
        
        row.style.display = show ? '' : 'none';
    });
}

// Функции для работы с экспортом
function exportToCSV(data, filename) {
    if (!data || data.length === 0) {
        showNotification('Нет данных для экспорта', 'warning');
        return;
    }
    
    const headers = Object.keys(data[0]);
    const csvContent = [
        headers.join(','),
        ...data.map(row => headers.map(header => `"${row[header] || ''}"`).join(','))
    ].join('\n');
    
    downloadFile(csvContent, filename, 'text/csv');
    showNotification('Данные экспортированы в CSV', 'success');
}

function exportToJSON(data, filename) {
    if (!data) {
        showNotification('Нет данных для экспорта', 'warning');
        return;
    }
    
    const jsonContent = JSON.stringify(data, null, 2);
    downloadFile(jsonContent, filename, 'application/json');
    showNotification('Данные экспортированы в JSON', 'success');
}

// Функции для работы с загрузкой
function showProgress(containerId, progress) {
    const container = document.getElementById(containerId);
    if (!container) return;
    
    container.innerHTML = `
        <div class="progress">
            <div class="progress-bar" role="progressbar" style="width: ${progress}%" aria-valuenow="${progress}" aria-valuemin="0" aria-valuemax="100">
                ${progress}%
            </div>
        </div>
    `;
}

// Глобальные функции для использования в HTML
window.showNotification = showNotification;
window.showLoadingModal = showLoadingModal;
window.hideLoadingModal = hideLoadingModal;
window.apiRequest = apiRequest;
window.formatDate = formatDate;
window.formatNumber = formatNumber;
window.getAccountStatusBadge = getAccountStatusBadge;
window.getCountryFlag = getCountryFlag;
window.addLogEntry = addLogEntry;
window.exportToCSV = exportToCSV;
window.exportToJSON = exportToJSON;

// Добавляем CSS анимации
const style = document.createElement('style');
style.textContent = `
    @keyframes slideInRight {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    
    .notification-item {
        transform: translateX(100%);
        opacity: 0;
    }
    
    .log-entry {
        padding: 8px 12px;
        border-bottom: 1px solid #e9ecef;
        font-family: 'Courier New', monospace;
        font-size: 0.9rem;
    }
    
    .log-entry:last-child {
        border-bottom: none;
    }
    
    .log-time {
        color: #6c757d;
        margin-right: 10px;
    }
    
    .log-account {
        color: #007bff;
        font-weight: bold;
        margin-right: 10px;
    }
    
    .log-action {
        color: #28a745;
        margin-right: 10px;
    }
    
    .log-target {
        color: #6f42c1;
        margin-right: 10px;
    }
    
    .log-message {
        color: #495057;
    }
`;
document.head.appendChild(style);