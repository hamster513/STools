"""
Системные роуты (health, version, settings, system status)
"""
import os
import psutil
import re
from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.responses import HTMLResponse
from database import get_db

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def read_root():
    """Главная страница"""
    with open("templates/index.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())


@router.get("/api/background-tasks/status")
async def get_background_tasks_status():
    """Получить статус всех фоновых задач"""
    try:
        db = get_db()
        conn = await db.get_connection()
        
        # Получаем все активные задачи
        query = """
            SELECT id, task_type, status, current_step, total_items, processed_items,
                   total_records, processed_records, updated_records, progress_percent, start_time, end_time, error_message, 
                   cancelled, parameters, description, created_at, updated_at
            FROM vulnanalizer.background_tasks 
            WHERE status IN ('processing', 'running', 'initializing', 'idle')
            ORDER BY created_at DESC
        """
        active_tasks = await conn.fetch(query)
        
        # Получаем последние завершенные задачи
        query_completed = """
            SELECT id, task_type, status, current_step, total_items, processed_items,
                   total_records, processed_records, updated_records, progress_percent, start_time, end_time, error_message, 
                   cancelled, parameters, description, created_at, updated_at
            FROM vulnanalizer.background_tasks 
            WHERE status IN ('completed', 'error', 'cancelled')
            ORDER BY created_at DESC
            LIMIT 10
        """
        completed_tasks = await conn.fetch(query_completed)
        
        # Форматируем результаты
        def format_task(task):
            return {
                'id': task['id'],
                'task_type': task['task_type'],
                'status': task['status'],
                'current_step': task['current_step'],
                'total_items': task['total_items'],
                'processed_items': task['processed_items'],
                'total_records': task['total_records'],
                'processed_records': task['processed_records'],
                'updated_records': task['updated_records'],
                'start_time': task['start_time'].isoformat() if task['start_time'] else None,
                'end_time': task['end_time'].isoformat() if task['end_time'] else None,
                'error_message': task['error_message'],
                'cancelled': task['cancelled'],
                'parameters': task['parameters'],
                'description': task['description'],
                'created_at': task['created_at'].isoformat() if task['created_at'] else None,
                'updated_at': task['updated_at'].isoformat() if task['updated_at'] else None,
                'progress_percent': calculate_task_progress(task)
            }
        
        return {
            "success": True,
            "active_tasks": [format_task(task) for task in active_tasks],
            "recent_completed_tasks": [format_task(task) for task in completed_tasks],
            "total_active": len(active_tasks),
            "total_completed": len(completed_tasks)
        }
        
    except Exception as e:
        print(f"Error getting background tasks status: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await db.release_connection(conn)


def calculate_task_progress(task):
    """Рассчитать прогресс задачи с учетом типа задачи"""
    if task['task_type'] in ['hosts_import', 'vm_manual_import']:
        # Для задач импорта хостов и ручного импорта VM используем processed_records и total_records
        if task['status'] == 'processing':
            current_step = task['current_step'] or ''
            
            # Если есть данные о записях, используем их для расчета прогресса
            if task['total_records'] and task['total_records'] > 0:
                processed = task['processed_records'] or 0
                total = task['total_records']
                base_progress = (processed / total) * 80  # 80% за импорт
                
                # Для больших чисел показываем более детальный прогресс
                if total > 100000:  # Для больших импортов
                    # Используем более точный расчет
                    base_progress = (processed / total) * 100
                
                # Если идет расчет рисков, добавляем дополнительный прогресс
                if 'Расчет рисков' in current_step:
                    # Извлекаем прогресс из строки "Расчет рисков (200/845 CVE)"
                    match = re.search(r'\((\d+)/(\d+)\)', current_step)
                    if not match:
                        # Попробуем другой паттерн
                        match = re.search(r'(\d+)/(\d+)', current_step)
                    if match:
                        processed_cve = int(match.group(1))
                        total_cve = int(match.group(2))
                        risk_progress = (processed_cve / total_cve) * 20  # 20% за расчет рисков
                        return int(min(100, base_progress + risk_progress))
                    else:
                        return int(min(100, base_progress + 10))  # Импорт завершен, расчет рисков начался
                else:
                    return int(min(100, base_progress))  # Только импорт
            else:
                # Fallback на старую логику, если нет данных о записях
                if 'Расчет рисков' in current_step:
                    match = re.search(r'\((\d+)/(\d+)\)', current_step)
                    if not match:
                        match = re.search(r'(\d+)/(\d+)', current_step)
                    if match:
                        processed_cve = int(match.group(1))
                        total_cve = int(match.group(2))
                        risk_progress = (processed_cve / total_cve) * 50
                        return int(50 + risk_progress)
                    else:
                        return 50
                else:
                    return 50
        elif task['status'] == 'completed':
            return 100
        else:
            return 0
    elif task['task_type'] == 'hosts_update':
        # Для задач обновления хостов используем processed_items и total_items
        if task['status'] == 'processing':
            current_step = task['current_step'] or ''
            
            # Извлекаем прогресс из строки "Обработка CVE 2763/6807: CVE-2020-1102"
            match = re.search(r'(\d+)/(\d+)', current_step)
            if match:
                processed_cve = int(match.group(1))
                total_cve = int(match.group(2))
                progress = (processed_cve / total_cve) * 100
                return int(progress)
            else:
                return 0
        elif task['status'] == 'completed':
            return 100
        else:
            return 0
    elif task['task_type'] == 'cve_download':
        # Для задач загрузки CVE используем поле progress_percent из базы данных
        if task['progress_percent'] is not None:
            return int(task['progress_percent'])
        else:
            # Fallback на стандартную формулу
            if task['total_items'] and task['total_items'] > 0:
                return int(task['processed_items'] / task['total_items'] * 100)
            else:
                return 0
    elif task['task_type'] == 'epss_download':
        # Для задач загрузки EPSS используем поле progress_percent из базы данных
        if task['progress_percent'] is not None:
            return int(task['progress_percent'])
        else:
            # Fallback на стандартную формулу
            if task['total_items'] and task['total_items'] > 0:
                return int(task['processed_items'] / task['total_items'] * 100)
            else:
                return 0
    else:
        # Для других задач используем стандартную формулу
        if task['total_items'] and task['total_items'] > 0:
            return int(task['processed_items'] / task['total_items'] * 100)
        else:
            return 0

@router.post("/api/background-tasks/{task_id}/update-status")
async def update_background_task_status(
    task_id: int, 
    status: str = None, 
    current_step: str = None,
    processed_records: int = None,
    total_records: int = None
):
    """Обновить статус фоновой задачи"""
    try:
        db = get_db()
        
        updates = {}
        if status:
            updates['status'] = status
        if current_step:
            updates['current_step'] = current_step
        if processed_records is not None:
            updates['processed_records'] = processed_records
        if total_records is not None:
            updates['total_records'] = total_records
            
        await db.update_background_task(task_id, **updates)
        
        return {"success": True, "message": f"Статус задачи {task_id} обновлен"}
        
    except Exception as e:
        print(f"Error updating background task {task_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/background-tasks/{task_id}")
async def get_background_task(task_id: int):
    """Получить информацию о конкретной фоновой задаче"""
    try:
        db = get_db()
        conn = await db.get_connection()
        
        # Устанавливаем схему
        query = """
            SELECT id, task_type, status, current_step, total_items, processed_items,
                   total_records, processed_records, updated_records, start_time, end_time, error_message, 
                   cancelled, parameters, description, created_at, updated_at
            FROM vulnanalizer.background_tasks 
            WHERE id = $1
        """
        task = await conn.fetchrow(query, task_id)
        
        if not task:
            raise HTTPException(status_code=404, detail="Задача не найдена")
        
        # Форматируем результат
        result = {
            'id': task['id'],
            'task_type': task['task_type'],
            'status': task['status'],
            'current_step': task['current_step'],
            'total_items': task['total_items'],
            'processed_items': task['processed_items'],
            'total_records': task['total_records'],
            'processed_records': task['processed_records'],
            'updated_records': task['updated_records'],
            'start_time': task['start_time'].isoformat() if task['start_time'] else None,
            'end_time': task['end_time'].isoformat() if task['end_time'] else None,
            'error_message': task['error_message'],
            'cancelled': task['cancelled'],
            'parameters': task['parameters'],
            'description': task['description'],
            'created_at': task['created_at'].isoformat() if task['created_at'] else None,
            'updated_at': task['updated_at'].isoformat() if task['updated_at'] else None,
            'progress_percent': calculate_task_progress(task)
        }
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error getting background task {task_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await db.release_connection(conn)


@router.post("/api/background-tasks/{task_id}/cancel")
async def cancel_background_task_by_id(task_id: int):
    """Отменить фоновую задачу по ID"""
    try:
        db = get_db()
        conn = await db.get_connection()
        
        # Получаем информацию о задаче
        task_query = """
            SELECT id, task_type, status FROM vulnanalizer.background_tasks 
            WHERE id = $1 AND status IN ('running', 'processing', 'initializing')
        """
        task = await conn.fetchrow(task_query, task_id)
        
        if not task:
            return {"success": False, "message": f"Задача {task_id} не найдена или не активна"}
        
        # Отменяем задачу
        cancelled = await db.cancel_background_task(task['task_type'])
        
        if cancelled:
            return {"success": True, "message": f"Задача {task_id} ({task['task_type']}) отменена"}
        else:
            return {"success": False, "message": f"Не удалось отменить задачу {task_id}"}
    except Exception as e:
        print(f"Error cancelling background task {task_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await db.release_connection(conn)


@router.post("/api/background-tasks/{task_type}/cancel")
async def cancel_background_task(task_type: str):
    """Отменить фоновую задачу по типу"""
    try:
        db = get_db()
        cancelled = await db.cancel_background_task(task_type)
        
        if cancelled:
            return {"success": True, "message": f"Задача {task_type} отменена"}
        else:
            return {"success": False, "message": f"Нет активной задачи типа {task_type}"}
    except Exception as e:
        print(f"Error cancelling background task {task_type}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/background-tasks/clear")
async def clear_background_tasks():
    """Очистить все завершенные фоновые задачи"""
    try:
        db = get_db()
        conn = await db.get_connection()
        
        try:
            # Удаляем все завершенные задачи (completed, error, cancelled)
            query = """
                DELETE FROM vulnanalizer.background_tasks 
                WHERE status IN ('completed', 'error', 'cancelled')
            """
            result = await conn.execute(query)
            
            # Получаем количество удаленных записей
            deleted_count = int(result.split()[-1]) if result.split()[-1].isdigit() else 0
            
            return {
                "success": True, 
                "message": f"Удалено {deleted_count} завершенных задач",
                "deleted_count": deleted_count
            }
        finally:
            await db.release_connection(conn)
            
    except Exception as e:
        print(f"Error clearing background tasks: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/settings")
@router.get("/api/system/settings")  # Алиас для совместимости с frontend
async def get_settings(request: Request):
    """Получить настройки приложения"""
    # Проверяем права администратора
    # TODO: Добавить проверку аутентификации
    # await require_admin(request)
    
    try:
        from database import Database
        db = Database()
        settings = await db.get_settings()
        return settings
    except Exception as e:
        print(f"Error loading settings: {e}")
        # Возвращаем настройки по умолчанию
        return {
            "risk_threshold": 75,
            "max_concurrent_requests": 3,
            # Impact настройки
            "impact_resource_criticality_critical": 0.33,
            "impact_resource_criticality_high": 0.25,
            "impact_resource_criticality_medium": 0.2,
            "impact_resource_criticality_none": 0.2,
            "impact_confidential_data_yes": 0.33,
            "impact_confidential_data_no": 0.2,
            "impact_internet_access_yes": 0.33,
            "impact_internet_access_no": 0.2,
            # ExploitDB настройки (загружаются из базы данных)
            # Metasploit настройки (загружаются из базы данных)
            "database_host": "",
            "database_port": "",
            "database_name": "",
            "database_user": "",
            "database_password": "",
            # CVSS v3 настройки
            "cvss_v3_attack_vector_network": 1.20,
            "cvss_v3_attack_vector_adjacent": 1.10,
            "cvss_v3_attack_vector_local": 0.95,
            "cvss_v3_attack_vector_physical": 0.85,
            "cvss_v3_privileges_required_none": 1.20,
            "cvss_v3_privileges_required_low": 1.00,
            "cvss_v3_privileges_required_high": 0.85,
            "cvss_v3_user_interaction_none": 1.15,
            "cvss_v3_user_interaction_required": 0.90,
            # CVSS v2 настройки
            "cvss_v2_access_vector_network": 1.20,
            "cvss_v2_access_vector_adjacent_network": 1.10,
            "cvss_v2_access_vector_local": 0.95,
            "cvss_v2_access_complexity_low": 1.10,
            "cvss_v2_access_complexity_medium": 1.00,
            "cvss_v2_access_complexity_high": 0.90,
            "cvss_v2_authentication_none": 1.15,
            "cvss_v2_access_complexity_medium": 1.00,
            "cvss_v2_access_complexity_high": 0.90,
            "cvss_v2_authentication_none": 1.15,
            "cvss_v2_authentication_single": 1.00,
            "cvss_v2_authentication_multiple": 0.90
        }


@router.post("/api/settings")
async def update_settings(settings: dict, request: Request):
    """Обновить настройки приложения"""
    # Проверяем права администратора
    # TODO: Добавить проверку аутентификации
    # await require_admin(request)
    
    try:
        print(f"DEBUG: Received settings: {settings}")
        
        from database import Database
        db = Database()
        await db.update_settings(settings)
        
        print(f"DEBUG: Settings saved successfully")
        return {"success": True, "message": "Настройки обновлены"}
    except Exception as e:
        print(f"DEBUG: Error saving settings: {e}")
        import traceback
        print(f"DEBUG: Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Ошибка сохранения настроек: {str(e)}")


@router.get("/api/health")
async def health_check():
    """Проверка здоровья приложения"""
    try:
        # Простая проверка без обращения к базе данных
        return {
            "status": "healthy",
            "service": "vulnanalizer",
            "timestamp": "2024-01-01T00:00:00Z"
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Service unhealthy: {str(e)}")


@router.get("/api/version")
async def get_version():
    """Получить версию приложения"""
    try:
        with open("/app/VERSION", "r") as f:
            version = f.read().strip()
        return {"version": version}
    except FileNotFoundError:
        return {"version": "unknown"}


@router.get("/api/system/status")
async def get_system_status():
    """Получить статус системы и использование ресурсов"""
    try:
        # Получаем информацию о памяти
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Получаем информацию о процессе
        process = psutil.Process(os.getpid())
        
        return {
            "memory": {
                "total_mb": memory.total // (1024 * 1024),
                "available_mb": memory.available // (1024 * 1024),
                "used_mb": memory.used // (1024 * 1024),
                "percent": memory.percent
            },
            "disk": {
                "total_gb": disk.total // (1024 * 1024 * 1024),
                "free_gb": disk.free // (1024 * 1024 * 1024),
                "used_gb": disk.used // (1024 * 1024 * 1024),
                "percent": (disk.used / disk.total) * 100
            },
            "process": {
                "memory_mb": process.memory_info().rss // (1024 * 1024),
                "cpu_percent": process.cpu_percent(),
                "threads": process.num_threads()
            }
        }
    except Exception as e:
        return {"error": str(e)}

@router.get("/api/dashboard/stats")
async def get_dashboard_stats():
    """Получить статистику для дашборда"""
    try:
        db = get_db()
        
        # Получаем базовую статистику
        conn = await db.get_connection()
        total_hosts = await conn.fetchval("SELECT COUNT(*) FROM vulnanalizer.hosts")
        total_cves = await conn.fetchval("SELECT COUNT(DISTINCT cve) FROM vulnanalizer.hosts WHERE cve IS NOT NULL")
        
        # Хосты с высоким риском
        high_risk_hosts = await conn.fetchval(
            "SELECT COUNT(*) FROM vulnanalizer.hosts WHERE risk_score > 50"
        )
        
        # Критические хосты
        critical_hosts = await conn.fetchval(
            "SELECT COUNT(*) FROM vulnanalizer.hosts WHERE criticality = 'Critical'"
        )
        
        # Хосты с эксплойтами
        hosts_with_exploits = await conn.fetchval(
            "SELECT COUNT(*) FROM vulnanalizer.hosts WHERE has_exploits = TRUE"
        )
        
        # Средний риск
        avg_risk_score = await conn.fetchval(
            "SELECT AVG(risk_score) FROM vulnanalizer.hosts WHERE risk_score IS NOT NULL"
        ) or 0.0
        
        # Последнее обновление
        last_update = await conn.fetchval(
            "SELECT MAX(GREATEST(epss_updated_at, exploits_updated_at, risk_updated_at)) FROM vulnanalizer.hosts"
        )
        
        return {
            "success": True,
            "stats": {
                "total_hosts": total_hosts,
                "total_cves": total_cves,
                "high_risk_hosts": high_risk_hosts,
                "critical_hosts": critical_hosts,
                "hosts_with_exploits": hosts_with_exploits,
                "avg_risk_score": round(avg_risk_score, 2),
                "recent_alerts": 0,  # Пока не реализовано
                "last_update": last_update.isoformat() if last_update else None
            }
        }
    except Exception as e:
        print(f"Error getting dashboard stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/dashboard/risk-distribution")
async def get_risk_distribution():
    """Получить распределение рисков"""
    try:
        db = get_db()
        conn = await db.get_connection()
        
        # Распределение по уровням риска
        risk_distribution = await conn.fetch("""
            SELECT risk_level, COUNT(*) as count
            FROM (
                SELECT 
                    CASE 
                        WHEN risk_score >= 80 THEN 'Critical'
                        WHEN risk_score >= 60 THEN 'High'
                        WHEN risk_score >= 40 THEN 'Medium'
                        WHEN risk_score >= 20 THEN 'Low'
                        ELSE 'Very Low'
                    END as risk_level
                FROM vulnanalizer.hosts 
                WHERE risk_score IS NOT NULL
            ) subquery
            GROUP BY risk_level
            ORDER BY 
                CASE risk_level
                    WHEN 'Critical' THEN 1
                    WHEN 'High' THEN 2
                    WHEN 'Medium' THEN 3
                    WHEN 'Low' THEN 4
                    WHEN 'Very Low' THEN 5
                END
        """)
        
        # Распределение по CVSS
        cvss_distribution = await conn.fetch("""
            SELECT cvss_level, COUNT(*) as count
            FROM (
                SELECT 
                    CASE 
                        WHEN cvss >= 9.0 THEN 'Critical (9.0-10.0)'
                        WHEN cvss >= 7.0 THEN 'High (7.0-8.9)'
                        WHEN cvss >= 4.0 THEN 'Medium (4.0-6.9)'
                        WHEN cvss >= 0.1 THEN 'Low (0.1-3.9)'
                        ELSE 'None'
                    END as cvss_level
                FROM vulnanalizer.hosts 
                WHERE cvss IS NOT NULL
            ) subquery
            GROUP BY cvss_level
            ORDER BY 
                CASE cvss_level
                    WHEN 'Critical (9.0-10.0)' THEN 1
                    WHEN 'High (7.0-8.9)' THEN 2
                    WHEN 'Medium (4.0-6.9)' THEN 3
                    WHEN 'Low (0.1-3.9)' THEN 4
                    WHEN 'None' THEN 5
                END
        """)
        
        return {
            "success": True,
            "risk_distribution": [dict(row) for row in risk_distribution],
            "cvss_distribution": [dict(row) for row in cvss_distribution]
        }
    except Exception as e:
        print(f"Error getting risk distribution: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/dashboard/top-cves")
async def get_top_cves(limit: int = 10):
    """Получить топ CVE по количеству хостов"""
    try:
        db = get_db()
        conn = await db.get_connection()
        
        top_cves = await conn.fetch("""
            SELECT 
                cve,
                COUNT(*) as host_count,
                AVG(risk_score) as avg_risk,
                AVG(cvss) as avg_cvss,
                SUM(CASE WHEN has_exploits THEN 1 ELSE 0 END) as hosts_with_exploits
            FROM vulnanalizer.hosts 
            WHERE cve IS NOT NULL
            GROUP BY cve
            ORDER BY host_count DESC
            LIMIT $1
        """, limit)
        
        return {
            "success": True,
            "top_cves": [dict(row) for row in top_cves]
        }
    except Exception as e:
        print(f"Error getting top CVEs: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/performance/database-stats")
async def get_database_performance_stats():
    """Получить статистику производительности базы данных"""
    try:
        from services.performance_monitor import performance_monitor
        stats = await performance_monitor.get_database_stats()
        return {"success": True, "stats": stats}
    except Exception as e:
        print(f"Error getting database performance stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/performance/query-stats")
async def get_query_performance_stats():
    """Получить статистику производительности запросов"""
    try:
        from services.performance_monitor import performance_monitor
        stats = await performance_monitor.get_query_performance_stats()
        return {"success": True, "stats": stats}
    except Exception as e:
        print(f"Error getting query performance stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/performance/index-usage")
async def get_index_usage_stats():
    """Получить статистику использования индексов"""
    try:
        from services.performance_monitor import performance_monitor
        stats = await performance_monitor.get_index_usage_stats()
        return {"success": True, "stats": stats}
    except Exception as e:
        print(f"Error getting index usage stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/performance/report")
async def get_performance_report():
    """Получить полный отчет о производительности"""
    try:
        from services.performance_monitor import performance_monitor
        report = await performance_monitor.generate_performance_report()
        return {"success": True, "report": report}
    except Exception as e:
        print(f"Error generating performance report: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/performance/optimize")
async def optimize_database():
    """Выполнить оптимизацию базы данных"""
    try:
        from services.performance_monitor import performance_monitor
        await performance_monitor.optimize_database()
        return {"success": True, "message": "Database optimization completed"}
    except Exception as e:
        print(f"Error optimizing database: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Cache API endpoints temporarily disabled due to import issues
# TODO: Fix imports and re-enable
