"""
Сервис мониторинга производительности базы данных
"""
import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List
from database import get_db

class PerformanceMonitor:
    def __init__(self):
        self.db = get_db()
        self.query_stats = {}
        self.slow_queries = []
    
    async def monitor_query_performance(self, query_name: str, query_func, *args, **kwargs):
        """Мониторинг производительности запроса"""
        start_time = time.time()
        
        try:
            result = await query_func(*args, **kwargs)
            execution_time = time.time() - start_time
            
            # Сохраняем статистику
            if query_name not in self.query_stats:
                self.query_stats[query_name] = {
                    'count': 0,
                    'total_time': 0,
                    'avg_time': 0,
                    'min_time': float('inf'),
                    'max_time': 0,
                    'last_execution': None
                }
            
            stats = self.query_stats[query_name]
            stats['count'] += 1
            stats['total_time'] += execution_time
            stats['avg_time'] = stats['total_time'] / stats['count']
            stats['min_time'] = min(stats['min_time'], execution_time)
            stats['max_time'] = max(stats['max_time'], execution_time)
            stats['last_execution'] = datetime.now()
            
            # Записываем медленные запросы (> 1 секунды)
            if execution_time > 1.0:
                self.slow_queries.append({
                    'query_name': query_name,
                    'execution_time': execution_time,
                    'timestamp': datetime.now(),
                    'args': args,
                    'kwargs': kwargs
                })
                
                # Ограничиваем список медленных запросов
                if len(self.slow_queries) > 100:
                    self.slow_queries.pop(0)
            
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            print(f"❌ Query {query_name} failed after {execution_time:.3f}s: {e}")
            raise
    
    async def get_database_stats(self) -> Dict[str, Any]:
        """Получить статистику базы данных"""
        try:
            conn = await self.db.get_connection()
            
            # Размер таблиц
            table_sizes = await conn.fetch("""
                SELECT 
                    schemaname,
                    tablename,
                    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size,
                    pg_total_relation_size(schemaname||'.'||tablename) as size_bytes
                FROM pg_tables 
                WHERE schemaname = 'public'
                ORDER BY size_bytes DESC
            """)
            
            # Статистика индексов
            index_stats = await conn.fetch("""
                SELECT 
                    schemaname,
                    tablename,
                    indexname,
                    pg_size_pretty(pg_relation_size(indexrelid)) as index_size
                FROM pg_indexes 
                WHERE schemaname = 'public'
                ORDER BY pg_relation_size(indexrelid) DESC
            """)
            
            # Статистика кэша
            cache_stats = await conn.fetch("""
                SELECT 
                    sum(heap_blks_read) as heap_read,
                    sum(heap_blks_hit) as heap_hit,
                    sum(idx_blks_read) as idx_read,
                    sum(idx_blks_hit) as idx_hit
                FROM pg_statio_user_tables
            """)
            
            # Активные соединения
            active_connections = await conn.fetchval("""
                SELECT count(*) FROM pg_stat_activity 
                WHERE state = 'active'
            """)
            
            # Статистика блокировок
            locks_stats = await conn.fetch("""
                SELECT 
                    locktype,
                    mode,
                    count(*) as count
                FROM pg_locks 
                WHERE locktype != 'relation'
                GROUP BY locktype, mode
                ORDER BY count DESC
            """)
            
            return {
                'table_sizes': [dict(row) for row in table_sizes],
                'index_stats': [dict(row) for row in index_stats],
                'cache_stats': dict(cache_stats[0]) if cache_stats else {},
                'active_connections': active_connections,
                'locks_stats': [dict(row) for row in locks_stats]
            }
            
        except Exception as e:
            print(f"❌ Error getting database stats: {e}")
            return {}
    
    async def get_query_performance_stats(self) -> Dict[str, Any]:
        """Получить статистику производительности запросов"""
        return {
            'query_stats': self.query_stats,
            'slow_queries_count': len(self.slow_queries),
            'recent_slow_queries': self.slow_queries[-10:] if self.slow_queries else []
        }
    
    async def get_index_usage_stats(self) -> Dict[str, Any]:
        """Получить статистику использования индексов"""
        try:
            conn = await self.db.get_connection()
            
            # Статистика сканирования индексов
            index_usage = await conn.fetch("""
                SELECT 
                    schemaname,
                    tablename,
                    indexname,
                    idx_scan,
                    idx_tup_read,
                    idx_tup_fetch
                FROM pg_stat_user_indexes 
                ORDER BY idx_scan DESC
            """)
            
            # Неиспользуемые индексы
            unused_indexes = await conn.fetch("""
                SELECT 
                    schemaname,
                    tablename,
                    indexname
                FROM pg_stat_user_indexes 
                WHERE idx_scan = 0
                ORDER BY tablename, indexname
            """)
            
            return {
                'index_usage': [dict(row) for row in index_usage],
                'unused_indexes': [dict(row) for row in unused_indexes]
            }
            
        except Exception as e:
            print(f"❌ Error getting index usage stats: {e}")
            return {}
    
    async def get_table_bloat_stats(self) -> Dict[str, Any]:
        """Получить статистику фрагментации таблиц"""
        try:
            conn = await self.db.get_connection()
            
            # Фрагментация таблиц
            table_bloat = await conn.fetch("""
                SELECT 
                    schemaname,
                    tablename,
                    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as total_size,
                    pg_size_pretty(pg_relation_size(schemaname||'.'||tablename)) as table_size,
                    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename) - pg_relation_size(schemaname||'.'||tablename)) as index_size
                FROM pg_tables 
                WHERE schemaname = 'public'
                ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
            """)
            
            return {
                'table_bloat': [dict(row) for row in table_bloat]
            }
            
        except Exception as e:
            print(f"❌ Error getting table bloat stats: {e}")
            return {}
    
    async def optimize_database(self):
        """Выполнить оптимизацию базы данных"""
        try:
            conn = await self.db.get_connection()
            
            print("🔄 Starting database optimization...")
            
            # VACUUM для очистки мертвых строк
            print("🧹 Running VACUUM...")
            await conn.execute("VACUUM ANALYZE hosts")
            await conn.execute("VACUUM ANALYZE cve")
            await conn.execute("VACUUM ANALYZE epss")
            await conn.execute("VACUUM ANALYZE exploitdb")
            
            # REINDEX для пересоздания индексов
            print("🔧 Rebuilding indexes...")
            await conn.execute("REINDEX INDEX CONCURRENTLY idx_hosts_cve")
            await conn.execute("REINDEX INDEX CONCURRENTLY idx_hosts_risk_score")
            
            print("✅ Database optimization completed")
            
        except Exception as e:
            print(f"❌ Error optimizing database: {e}")
    
    async def generate_performance_report(self) -> Dict[str, Any]:
        """Сгенерировать отчет о производительности"""
        try:
            db_stats = await self.get_database_stats()
            query_stats = await self.get_query_performance_stats()
            index_stats = await self.get_index_usage_stats()
            bloat_stats = await self.get_table_bloat_stats()
            
            # Анализ производительности
            performance_analysis = {
                'slow_queries_detected': len(self.slow_queries),
                'avg_query_time': sum(stats['avg_time'] for stats in self.query_stats.values()) / len(self.query_stats) if self.query_stats else 0,
                'cache_hit_ratio': self._calculate_cache_hit_ratio(db_stats.get('cache_stats', {})),
                'recommendations': self._generate_recommendations(db_stats, query_stats, index_stats)
            }
            
            return {
                'timestamp': datetime.now().isoformat(),
                'database_stats': db_stats,
                'query_performance': query_stats,
                'index_usage': index_stats,
                'table_bloat': bloat_stats,
                'performance_analysis': performance_analysis
            }
            
        except Exception as e:
            print(f"❌ Error generating performance report: {e}")
            return {}
    
    def _calculate_cache_hit_ratio(self, cache_stats: Dict[str, Any]) -> float:
        """Рассчитать соотношение попаданий в кэш"""
        try:
            heap_read = cache_stats.get('heap_read', 0)
            heap_hit = cache_stats.get('heap_hit', 0)
            idx_read = cache_stats.get('idx_read', 0)
            idx_hit = cache_stats.get('idx_hit', 0)
            
            total_reads = heap_read + idx_read
            total_hits = heap_hit + idx_hit
            
            if total_reads > 0:
                return (total_hits / total_reads) * 100
            return 0.0
        except:
            return 0.0
    
    def _generate_recommendations(self, db_stats: Dict, query_stats: Dict, index_stats: Dict) -> List[str]:
        """Генерировать рекомендации по оптимизации"""
        recommendations = []
        
        # Рекомендации по медленным запросам
        if query_stats.get('slow_queries_count', 0) > 10:
            recommendations.append("Обнаружено много медленных запросов. Рассмотрите оптимизацию индексов.")
        
        # Рекомендации по кэшу
        cache_ratio = self._calculate_cache_hit_ratio(db_stats.get('cache_stats', {}))
        if cache_ratio < 90:
            recommendations.append(f"Низкое соотношение попаданий в кэш ({cache_ratio:.1f}%). Увеличьте размер shared_buffers.")
        
        # Рекомендации по неиспользуемым индексам
        unused_count = len(index_stats.get('unused_indexes', []))
        if unused_count > 5:
            recommendations.append(f"Обнаружено {unused_count} неиспользуемых индексов. Рассмотрите их удаление.")
        
        # Рекомендации по размеру таблиц
        for table in db_stats.get('table_sizes', []):
            size_mb = table.get('size_bytes', 0) / (1024 * 1024)
            if size_mb > 1000:  # Больше 1GB
                recommendations.append(f"Таблица {table['tablename']} большая ({size_mb:.1f}MB). Рассмотрите партиционирование.")
        
        return recommendations

# Глобальный экземпляр монитора производительности
performance_monitor = PerformanceMonitor()
