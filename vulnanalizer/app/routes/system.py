"""
Системные роуты (health, version, settings, system status)
"""
import os
import psutil
from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from database import get_db

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def read_root():
    """Главная страница"""
    with open("templates/index.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())





@router.get("/api/settings")
async def get_settings():
    """Получить настройки приложения"""
    try:
        import os
        import tempfile
        
        # Ищем файл настроек в возможных местах
        possible_paths = [
            os.path.join(os.getcwd(), "data", "settings.json"),
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "settings.json"),
            os.path.join(tempfile.gettempdir(), "settings.json"),
            "/tmp/settings.json",
        ]
        
        settings_file = None
        for path in possible_paths:
            if os.path.exists(path):
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        import json
                        settings = json.load(f)
                    settings_file = path
                    print(f"DEBUG: Loaded settings from: {settings_file}")
                    break
                except Exception as e:
                    print(f"DEBUG: Cannot read {path}: {e}")
                    continue
        
        if settings_file is None:
            # Возвращаем настройки по умолчанию
            return {
                "impact_resource_criticality": "Medium",
                "impact_confidential_data": "Отсутствуют",
                "impact_internet_access": "Недоступен"
            }
            
        # Проверяем, что все необходимые поля присутствуют
        required_fields = ["impact_resource_criticality", "impact_confidential_data", "impact_internet_access"]
        for field in required_fields:
            if field not in settings:
                # Если какое-то поле отсутствует, возвращаем настройки по умолчанию
                return {
                    "impact_resource_criticality": "Medium",
                    "impact_confidential_data": "Отсутствуют",
                    "impact_internet_access": "Недоступен"
                }
        
        return settings
    except FileNotFoundError:
        # Возвращаем настройки по умолчанию
        return {
            "impact_resource_criticality": "Medium",
            "impact_confidential_data": "Отсутствуют",
            "impact_internet_access": "Недоступен"
        }
    except json.JSONDecodeError as e:
        # Если файл поврежден, возвращаем настройки по умолчанию
        return {
            "impact_resource_criticality": "Medium",
            "impact_confidential_data": "Отсутствуют",
            "impact_internet_access": "Недоступен"
        }


@router.post("/api/settings")
async def update_settings(settings: dict):
    """Обновить настройки приложения"""
    try:
        print(f"DEBUG: Received settings: {settings}")
        
        # Проверяем, что settings содержит необходимые поля Impact
        required_impact_fields = ["impact_resource_criticality", "impact_confidential_data", "impact_internet_access"]
        for field in required_impact_fields:
            if field not in settings:
                print(f"DEBUG: Missing field: {field}")
                raise ValueError(f"Отсутствует обязательное поле Impact: {field}")
        
        print(f"DEBUG: All required fields present")
        
        # Определяем путь для сохранения настроек
        import os
        import tempfile
        
        # Пробуем разные варианты путей
        possible_paths = [
            os.path.join(os.getcwd(), "data"),  # Текущая рабочая директория
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "data"),  # Рядом с файлом
            tempfile.gettempdir(),  # Временная директория
            "/tmp",  # Стандартная временная директория
        ]
        
        data_dir = None
        for path in possible_paths:
            try:
                os.makedirs(path, exist_ok=True)
                test_file = os.path.join(path, "test_write.tmp")
                with open(test_file, "w") as f:
                    f.write("test")
                os.remove(test_file)
                data_dir = path
                print(f"DEBUG: Using data directory: {data_dir}")
                break
            except Exception as e:
                print(f"DEBUG: Cannot use {path}: {e}")
                continue
        
        if data_dir is None:
            raise Exception("Не удалось найти директорию для записи настроек")
        
        settings_file = os.path.join(data_dir, "settings.json")
        print(f"DEBUG: Settings file: {settings_file}")
        
        # Фильтруем только настройки Impact для сохранения
        impact_settings = {
            "impact_resource_criticality": settings["impact_resource_criticality"],
            "impact_confidential_data": settings["impact_confidential_data"],
            "impact_internet_access": settings["impact_internet_access"]
        }
        
        print(f"DEBUG: Impact settings to save: {impact_settings}")
        
        # Сохраняем настройки Impact
        with open(settings_file, "w", encoding="utf-8") as f:
            import json
            json.dump(impact_settings, f, ensure_ascii=False, indent=2)
        
        print(f"DEBUG: Settings saved successfully")
        return {"success": True, "message": "Настройки Impact обновлены"}
    except ValueError as e:
        print(f"DEBUG: ValueError: {e}")
        raise HTTPException(status_code=400, detail=f"Некорректные данные настроек: {str(e)}")
    except PermissionError as e:
        print(f"DEBUG: PermissionError: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка прав доступа при сохранении настроек: {str(e)}")
    except Exception as e:
        print(f"DEBUG: Unexpected error: {e}")
        import traceback
        print(f"DEBUG: Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Ошибка сохранения настроек: {str(e)}")


@router.get("/api/health")
async def health_check():
    """Проверка здоровья приложения"""
    try:
        # Проверяем подключение к базе данных
        from database import get_db
        db = get_db()
        await db.test_connection()
        
        return {
            "status": "healthy",
            "database": "connected",
            "timestamp": "2024-01-01T00:00:00Z"
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Service unhealthy: {str(e)}")


@router.get("/api/version")
async def get_version():
    """Получить версию приложения"""
    try:
        with open("VERSION", "r") as f:
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
        total_hosts = await conn.fetchval("SELECT COUNT(*) FROM hosts")
        total_cves = await conn.fetchval("SELECT COUNT(DISTINCT cve) FROM hosts WHERE cve IS NOT NULL")
        
        # Хосты с высоким риском
        high_risk_hosts = await conn.fetchval(
            "SELECT COUNT(*) FROM hosts WHERE risk_score > 50"
        )
        
        # Критические хосты
        critical_hosts = await conn.fetchval(
            "SELECT COUNT(*) FROM hosts WHERE criticality = 'Critical'"
        )
        
        # Хосты с эксплойтами
        hosts_with_exploits = await conn.fetchval(
            "SELECT COUNT(*) FROM hosts WHERE has_exploits = TRUE"
        )
        
        # Средний риск
        avg_risk_score = await conn.fetchval(
            "SELECT AVG(risk_score) FROM hosts WHERE risk_score IS NOT NULL"
        ) or 0.0
        
        # Последнее обновление
        last_update = await conn.fetchval(
            "SELECT MAX(GREATEST(epss_updated_at, exploits_updated_at, risk_updated_at)) FROM hosts"
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
                FROM hosts 
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
                FROM hosts 
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
            FROM hosts 
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
