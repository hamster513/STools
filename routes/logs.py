"""
Универсальные API роуты для управления логами всех компонентов
"""
from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import FileResponse, HTMLResponse
from pathlib import Path
import os
import json
from datetime import datetime
from typing import Dict, Any, Optional, List

router = APIRouter()

class UniversalLoggingService:
    """Универсальный сервис для логирования всех компонентов"""
    
    def __init__(self):
        self.logs_dir = Path('/app/data/logs')
        try:
            self.logs_dir.mkdir(parents=True, exist_ok=True)
        except PermissionError:
            # Если нет прав на создание директории, используем временную директорию
            import tempfile
            self.logs_dir = Path(tempfile.gettempdir()) / 'stools_logs'
        self.logs_dir.mkdir(parents=True, exist_ok=True)
    
    def get_log_files(self, task_type: str = None, component: str = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Получить список файлов логов"""
        try:
            log_files = []
            
            for log_file in self.logs_dir.glob('*.log'):
                if not log_file.is_file():
                    continue
                
                filename = log_file.name
                if not filename.endswith('.log'):
                    continue
                
                name_without_ext = filename[:-4]
                parts = name_without_ext.split('_')
                
                if len(parts) < 4:
                    continue
                
                # Парсинг: task_type_taskid_YYYYMMDD_HHMMSS
                if len(parts) >= 4:
                    file_date = parts[-2]
                    file_time = parts[-1]
                    file_task_id = parts[-3]
                    file_task_type = '_'.join(parts[:-3])
                else:
                    continue
                
                if task_type and file_task_type != task_type:
                    continue
                
                stat = log_file.stat()
                
                log_files.append({
                    'id': filename,
                    'task_id': int(file_task_id),
                    'task_type': file_task_type,
                    'file_name': filename,
                    'file_path': str(log_file),
                    'file_size': stat.st_size,
                    'file_size_mb': round(stat.st_size / (1024 * 1024), 2),
                    'created_at': datetime.fromtimestamp(stat.st_ctime),
                    'modified_at': datetime.fromtimestamp(stat.st_mtime)
                })
            
            log_files.sort(key=lambda x: x['created_at'], reverse=True)
            return log_files[:limit]
            
        except Exception as e:
            print(f"❌ Ошибка получения файлов логов: {e}")
            return []
    
    def delete_log_file(self, log_file_id: str) -> bool:
        """Удалить файл лога"""
        try:
            file_path = self.logs_dir / log_file_id
            if file_path.exists():
                file_path.unlink()
                return True
            return False
        except Exception as e:
            print(f"❌ Ошибка удаления файла лога: {e}")
            return False
    
    def cleanup_old_logs(self, days: int = 30):
        """Очистка старых логов"""
        try:
            from datetime import timedelta
            cutoff_date = datetime.now() - timedelta(days=days)
            deleted_count = 0
            
            for log_file in self.logs_dir.glob('*.log'):
                if log_file.is_file():
                    file_time = datetime.fromtimestamp(log_file.stat().st_ctime)
                    if file_time < cutoff_date:
                        log_file.unlink()
                        deleted_count += 1
            
            print(f"✅ Очищено {deleted_count} старых файлов логов")
            return deleted_count
        except Exception as e:
            print(f"❌ Ошибка очистки старых логов: {e}")
            return 0

# Глобальный экземпляр сервиса логирования
logging_service = UniversalLoggingService()


@router.get("/users-iframe/", response_class=HTMLResponse)
async def users_iframe_page():
    """Упрощенная страница управления пользователями для iframe"""
    html_content = """
    <!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Управление пользователями - STools</title>
        <link rel="stylesheet" href="/static/css/main.css?v=1.0">
        <link rel="stylesheet" href="/static/css/components/tables.css?v=1.0">
        <link rel="stylesheet" href="/static/css/components/buttons.css?v=1.0">
        <link rel="stylesheet" href="/static/css/components/cards.css?v=1.0">
        <link rel="stylesheet" href="/static/css/fontawesome/all.min.css">
        <style>
            .users-container {
                padding: 1rem;
                max-width: 100%;
                margin: 0;
            }
            .users-header {
                margin-bottom: 1rem;
            }
            .users-actions {
                margin-bottom: 1rem;
            }
            .users-table {
                background: var(--card-bg);
                border-radius: 8px;
                border: 1px solid var(--border-color);
                overflow: hidden;
            }
            .table-header {
                background: var(--bg-secondary);
                padding: 1rem;
                border-bottom: 1px solid var(--border-color);
            }
            .table-content {
                max-height: 300px;
                overflow-y: auto;
            }
            .user-row {
                display: grid;
                grid-template-columns: 1fr auto auto auto;
                gap: 1rem;
                padding: 1rem;
                border-bottom: 1px solid var(--border-color);
                align-items: center;
            }
            .user-row:last-child {
                border-bottom: none;
            }
            .user-info {
                display: flex;
                flex-direction: column;
                gap: 0.25rem;
            }
            .user-name {
                font-weight: 500;
                color: var(--text-primary);
            }
            .user-email {
                font-size: 0.875rem;
                color: var(--text-secondary);
            }
            .user-role {
                font-size: 0.875rem;
                color: var(--text-secondary);
            }
            .user-status {
                font-size: 0.875rem;
                color: var(--text-secondary);
            }
            .user-actions {
                display: flex;
                gap: 0.5rem;
            }
            .btn-sm {
                padding: 0.375rem 0.75rem;
                font-size: 0.875rem;
            }
            .no-users {
                text-align: center;
                padding: 2rem;
                color: var(--text-secondary);
            }
        </style>
    </head>
    <body>
        <div class="users-container">
            <div class="users-header">
                <h3><i class="fas fa-users"></i> Управление пользователями</h3>
                <p>Просмотр и управление пользователями системы</p>
            </div>

            <div class="users-actions">
                <button type="button" id="refresh-users-btn" class="btn btn-secondary btn-sm">
                    <i class="fas fa-sync-alt"></i> Обновить
                </button>
            </div>

            <div class="users-table">
                <div class="table-header">
                    <h4>Пользователи</h4>
                </div>
                <div class="table-content" id="users-table-content">
                    <div class="no-users">
                        <i class="fas fa-spinner fa-spin"></i> Загрузка пользователей...
                    </div>
                </div>
            </div>
        </div>

        <script>
            class UsersIframeManager {
                constructor() {
                    this.init();
                }

                async init() {
                    await this.loadUsers();
                    this.setupEventListeners();
                }

                setupEventListeners() {
                    document.getElementById('refresh-users-btn').addEventListener('click', () => {
                        this.loadUsers();
                    });
                }

                async loadUsers() {
                    try {
                        const response = await fetch('/auth/api/users/public');
                        const data = await response.json();
                        
                        if (data.success) {
                            this.renderUsers(data.users);
                        }
                    } catch (error) {
                        console.error('Ошибка загрузки пользователей:', error);
                        document.getElementById('users-table-content').innerHTML = 
                            '<div class="no-users">Ошибка загрузки пользователей</div>';
                    }
                }

                renderUsers(users) {
                    const tableContent = document.getElementById('users-table-content');
                    
                    if (users.length === 0) {
                        tableContent.innerHTML = '<div class="no-users">Нет пользователей</div>';
                        return;
                    }

                    tableContent.innerHTML = users.map(user => `
                        <div class="user-row">
                            <div class="user-info">
                                <div class="user-name">${user.username}</div>
                                <div class="user-email">${user.email || 'Нет email'}</div>
                            </div>
                            <div class="user-role">${user.is_admin ? 'Администратор' : 'Пользователь'}</div>
                            <div class="user-status">${user.is_active ? 'Активен' : 'Неактивен'}</div>
                            <div class="user-actions">
                                <button class="btn btn-primary btn-sm" onclick="usersIframeManager.editUser(${user.id})">
                                    <i class="fas fa-edit"></i> Редактировать
                                </button>
                            </div>
                        </div>
                    `).join('');
                }

                editUser(userId) {
                    // Открываем редактирование в новом окне
                    window.open(`/users/?edit=${userId}`, '_blank');
                }
            }

            // Инициализация при загрузке страницы
            document.addEventListener('DOMContentLoaded', () => {
                window.usersIframeManager = new UsersIframeManager();
            });
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


@router.get("/logs/", response_class=HTMLResponse)
async def logs_page():
    """Страница управления логами"""
    html_content = """
    <!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Управление логами - STools</title>
        <link rel="stylesheet" href="/static/css/main.css?v=1.0">
        <link rel="stylesheet" href="/static/css/components/tables.css?v=1.0">
        <link rel="stylesheet" href="/static/css/components/buttons.css?v=1.0">
        <link rel="stylesheet" href="/static/css/components/cards.css?v=1.0">
        <link rel="stylesheet" href="/static/css/fontawesome/all.min.css">
        <style>
            .logs-container {
                padding: 2rem;
                max-width: 1200px;
                margin: 0 auto;
            }
            .logs-header {
                margin-bottom: 2rem;
            }
            .logs-stats {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 1rem;
                margin-bottom: 2rem;
            }
            .stat-card {
                background: var(--card-bg);
                padding: 1.5rem;
                border-radius: 8px;
                border: 1px solid var(--border-color);
            }
            .stat-number {
                font-size: 2rem;
                font-weight: bold;
                color: var(--primary-color);
            }
            .stat-label {
                color: var(--text-secondary);
                margin-top: 0.5rem;
            }
            .logs-actions {
                margin-bottom: 2rem;
            }
            .logs-table {
                background: var(--card-bg);
                border-radius: 8px;
                border: 1px solid var(--border-color);
                overflow: hidden;
            }
            .table-header {
                background: var(--bg-secondary);
                padding: 1rem;
                border-bottom: 1px solid var(--border-color);
            }
            .table-content {
                max-height: 400px;
                overflow-y: auto;
            }
            .log-file-row {
                display: grid;
                grid-template-columns: 1fr auto auto auto;
                gap: 1rem;
                padding: 1rem;
                border-bottom: 1px solid var(--border-color);
                align-items: center;
            }
            .log-file-row:last-child {
                border-bottom: none;
            }
            .log-file-info {
                display: flex;
                flex-direction: column;
                gap: 0.25rem;
            }
            .log-file-name {
                font-weight: 500;
                color: var(--text-primary);
            }
            .log-file-meta {
                font-size: 0.875rem;
                color: var(--text-secondary);
            }
            .log-file-size {
                font-size: 0.875rem;
                color: var(--text-secondary);
            }
            .log-file-date {
                font-size: 0.875rem;
                color: var(--text-secondary);
            }
            .log-actions {
                display: flex;
                gap: 0.5rem;
            }
            .btn-sm {
                padding: 0.375rem 0.75rem;
                font-size: 0.875rem;
            }
            .no-logs {
                text-align: center;
                padding: 3rem;
                color: var(--text-secondary);
            }
        </style>
    </head>
    <body>
        <div class="logs-container">
            <div class="logs-header">
                <h1><i class="fas fa-file-alt"></i> Управление логами</h1>
                <p>Просмотр и управление файлами логов системы</p>
            </div>

            <div class="logs-stats" id="logs-stats">
                <!-- Статистика будет загружена динамически -->
            </div>

            <div class="logs-actions">
                <button type="button" id="refresh-logs-btn" class="btn btn-secondary btn-sm">
                    <i class="fas fa-sync-alt"></i> Обновить
                </button>
                <button type="button" id="cleanup-logs-btn" class="btn btn-danger btn-sm" style="margin-left: 10px;">
                    <i class="fas fa-trash"></i> Очистить старые логи
                </button>
            </div>

            <div class="logs-table">
                <div class="table-header">
                    <h3>Файлы логов</h3>
                </div>
                <div class="table-content" id="logs-table-content">
                    <div class="no-logs">
                        <i class="fas fa-spinner fa-spin"></i> Загрузка логов...
                    </div>
                </div>
            </div>
        </div>

        <script>
            class LogsManager {
                constructor() {
                    this.init();
                }

                async init() {
                    await this.loadLogsStats();
                    await this.loadLogs();
                    this.setupEventListeners();
                }

                setupEventListeners() {
                    document.getElementById('refresh-logs-btn').addEventListener('click', () => {
                        this.loadLogs();
                        this.loadLogsStats();
                    });

                    document.getElementById('cleanup-logs-btn').addEventListener('click', () => {
                        this.cleanupOldLogs();
                    });
                }

                async loadLogsStats() {
                    try {
                        const response = await fetch('/api/logs/stats');
                        const data = await response.json();
                        
                        if (data.success) {
                            this.renderLogsStats(data.stats);
                        }
                    } catch (error) {
                        console.error('Ошибка загрузки статистики логов:', error);
                    }
                }

                async loadLogs() {
                    try {
                        const response = await fetch('/api/logs/files');
                        const data = await response.json();
                        
                        if (data.success) {
                            this.renderLogs(data.files);
                        }
                    } catch (error) {
                        console.error('Ошибка загрузки логов:', error);
                        document.getElementById('logs-table-content').innerHTML = 
                            '<div class="no-logs">Ошибка загрузки логов</div>';
                    }
                }

                renderLogsStats(stats) {
                    const statsContainer = document.getElementById('logs-stats');
                    statsContainer.innerHTML = `
                        <div class="stat-card">
                            <div class="stat-number">${stats.total_files}</div>
                            <div class="stat-label">Всего файлов</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-number">${stats.total_size_mb} MB</div>
                            <div class="stat-label">Общий размер</div>
                        </div>
                    `;
                }

                renderLogs(logs) {
                    const tableContent = document.getElementById('logs-table-content');
                    
                    if (logs.length === 0) {
                        tableContent.innerHTML = '<div class="no-logs">Нет файлов логов</div>';
                        return;
                    }

                    tableContent.innerHTML = logs.map(log => `
                        <div class="log-file-row">
                            <div class="log-file-info">
                                <div class="log-file-name">${log.file_name}</div>
                                <div class="log-file-meta">${log.task_type} (ID: ${log.task_id})</div>
                            </div>
                            <div class="log-file-size">${log.file_size_mb} MB</div>
                            <div class="log-file-date">${new Date(log.created_at).toLocaleString()}</div>
                            <div class="log-actions">
                                <button class="btn btn-primary btn-sm" onclick="logsManager.downloadLog('${log.id}')">
                                    <i class="fas fa-download"></i> Скачать
                                </button>
                                <button class="btn btn-danger btn-sm" onclick="logsManager.deleteLog('${log.id}')">
                                    <i class="fas fa-trash"></i> Удалить
                                </button>
                            </div>
                        </div>
                    `).join('');
                }

                async downloadLog(logId) {
                    try {
                        const response = await fetch(`/api/logs/files/${logId}/download`);
                        if (response.ok) {
                            const blob = await response.blob();
                            const url = window.URL.createObjectURL(blob);
                            const a = document.createElement('a');
                            a.href = url;
                            a.download = logId;
                            document.body.appendChild(a);
                            a.click();
                            document.body.removeChild(a);
                            window.URL.revokeObjectURL(url);
                        }
                    } catch (error) {
                        console.error('Ошибка скачивания лога:', error);
                        alert('Ошибка скачивания файла лога');
                    }
                }

                async deleteLog(logId) {
                    if (!confirm('Вы уверены, что хотите удалить этот файл лога?')) {
                        return;
                    }

                    try {
                        const response = await fetch(`/api/logs/files/${logId}`, {
                            method: 'DELETE'
                        });
                        const data = await response.json();
                        
                        if (data.success) {
                            this.loadLogs();
                            this.loadLogsStats();
                        } else {
                            alert('Ошибка удаления файла лога');
                        }
                    } catch (error) {
                        console.error('Ошибка удаления лога:', error);
                        alert('Ошибка удаления файла лога');
                    }
                }

                async cleanupOldLogs() {
                    if (!confirm('Вы уверены, что хотите удалить старые логи (старше 30 дней)?')) {
                        return;
                    }

                    try {
                        const response = await fetch('/api/logs/cleanup', {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json'
                            },
                            body: JSON.stringify({ days: 30 })
                        });
                        const data = await response.json();
                        
                        if (data.success) {
                            alert(`Удалено ${data.deleted_count} старых файлов логов`);
                            this.loadLogs();
                            this.loadLogsStats();
                        } else {
                            alert('Ошибка очистки логов');
                        }
                    } catch (error) {
                        console.error('Ошибка очистки логов:', error);
                        alert('Ошибка очистки логов');
                    }
                }
            }

            // Инициализация при загрузке страницы
            document.addEventListener('DOMContentLoaded', () => {
                window.logsManager = new LogsManager();
            });
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


@router.get("/api/logs/files")
async def get_log_files(task_type: str = None, component: str = None, limit: int = 50):
    """Получить список файлов логов"""
    try:
        log_files = logging_service.get_log_files(task_type, component, limit)
        
        formatted_files = []
        for file_info in log_files:
            formatted_files.append({
                "id": file_info["id"],
                "task_id": file_info["task_id"],
                "task_type": file_info["task_type"],
                "file_name": file_info["file_name"],
                "file_size": file_info["file_size"],
                "file_size_mb": file_info["file_size_mb"],
                "log_level": "INFO",
                "start_time": None,
                "end_time": None,
                "created_at": file_info["created_at"].isoformat() if file_info["created_at"] else None,
                "duration": None
            })
        
        return {
            "success": True,
            "files": formatted_files,
            "total_count": len(formatted_files)
        }
        
    except Exception as e:
        print(f"❌ Ошибка получения файлов логов: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка получения файлов логов: {str(e)}")


@router.get("/api/logs/files/{log_file_id}/download")
async def download_log_file(log_file_id: str):
    """Скачать файл лога"""
    try:
        log_files = logging_service.get_log_files()
        log_file = None
        
        for file_info in log_files:
            if file_info["id"] == log_file_id:
                log_file = file_info
                break
        
        if not log_file:
            raise HTTPException(status_code=404, detail="Файл лога не найден")
        
        file_path = Path(log_file["file_path"])
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="Файл лога не найден на диске")
        
        return FileResponse(
            path=str(file_path),
            filename=log_file["file_name"],
            media_type="text/plain"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Ошибка скачивания файла лога: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка скачивания файла лога: {str(e)}")


@router.delete("/api/logs/files/{log_file_id}")
async def delete_log_file(log_file_id: str):
    """Удалить файл лога"""
    try:
        success = logging_service.delete_log_file(log_file_id)
        
        if success:
            return {
                "success": True,
                "message": "Файл лога удален успешно"
            }
        else:
            raise HTTPException(status_code=404, detail="Файл лога не найден")
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Ошибка удаления файла лога: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка удаления файла лога: {str(e)}")


@router.post("/api/logs/cleanup")
async def cleanup_old_logs(request: Request):
    """Очистка старых логов"""
    try:
        data = await request.json()
        days = data.get("days", 30)
        
        deleted_count = logging_service.cleanup_old_logs(days)
        
        return {
            "success": True,
            "message": f"Удалено {deleted_count} старых файлов логов",
            "deleted_count": deleted_count
        }
        
    except Exception as e:
        print(f"❌ Ошибка очистки логов: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка очистки логов: {str(e)}")


@router.get("/api/logs/stats")
async def get_logs_stats():
    """Получить статистику логов"""
    try:
        all_files = logging_service.get_log_files()
        
        stats_by_type = {}
        total_size = 0
        total_files = len(all_files)
        
        for file_info in all_files:
            task_type = file_info["task_type"]
            file_size = file_info["file_size"] or 0
            
            if task_type not in stats_by_type:
                stats_by_type[task_type] = {
                    "count": 0,
                    "total_size": 0,
                    "total_size_mb": 0
                }
            
            stats_by_type[task_type]["count"] += 1
            stats_by_type[task_type]["total_size"] += file_size
            stats_by_type[task_type]["total_size_mb"] = round(
                stats_by_type[task_type]["total_size"] / (1024 * 1024), 2
            )
            
            total_size += file_size
        
        return {
            "success": True,
            "stats": {
                "total_files": total_files,
                "total_size": total_size,
                "total_size_mb": round(total_size / (1024 * 1024), 2),
                "by_task_type": stats_by_type
            }
        }
        
    except Exception as e:
        print(f"❌ Ошибка получения статистики логов: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка получения статистики логов: {str(e)}")
