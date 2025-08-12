"""
Сервис планировщика задач для автоматического обновления данных
"""
import asyncio
import schedule
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from database import get_db

class SchedulerService:
    def __init__(self):
        self.db = get_db()
        self.running = False
        self.tasks = {}
    
    async def start_scheduler(self):
        """Запустить планировщик"""
        if self.running:
            return
        
        self.running = True
        print("🕐 Scheduler started")
        
        # Настраиваем расписание
        schedule.every().day.at("02:00").do(self.daily_update)
        schedule.every().hour.do(self.hourly_check)
        schedule.every(30).minutes.do(self.cleanup_old_data)
        
        # Запускаем в отдельном потоке
        asyncio.create_task(self._run_scheduler())
    
    async def stop_scheduler(self):
        """Остановить планировщик"""
        self.running = False
        schedule.clear()
        print("🕐 Scheduler stopped")
    
    async def _run_scheduler(self):
        """Основной цикл планировщика"""
        while self.running:
            schedule.run_pending()
            await asyncio.sleep(60)  # Проверяем каждую минуту
    
    async def daily_update(self):
        """Ежедневное обновление данных"""
        try:
            print("🔄 Starting daily update")
            
            # Проверяем, не запущено ли уже обновление
            existing_task = await self.db.get_background_task('hosts_update')
            if existing_task and existing_task['status'] in ['processing', 'initializing']:
                print("⚠️ Update already running, skipping daily update")
                return
            
            # Запускаем инкрементальное обновление
            result = await self.db.update_hosts_incremental(days_old=1)
            
            if result['success']:
                print(f"✅ Daily update completed: {result['updated_count']} hosts updated")
            else:
                print(f"❌ Daily update failed: {result['message']}")
                
        except Exception as e:
            print(f"❌ Error in daily update: {e}")
    
    async def hourly_check(self):
        """Ежечасная проверка системы"""
        try:
            print("🔍 Hourly system check")
            
            # Проверяем состояние базы данных
            conn = await self.db.get_connection()
            
            # Проверяем количество хостов без данных
            hosts_without_data = await conn.fetchval("""
                SELECT COUNT(*) FROM hosts 
                WHERE epss_score IS NULL AND exploits_count IS NULL
            """)
            
            if hosts_without_data > 0:
                print(f"⚠️ Found {hosts_without_data} hosts without data")
            
            # Проверяем последнее обновление
            last_update = await conn.fetchval("""
                SELECT MAX(GREATEST(epss_updated_at, exploits_updated_at, risk_updated_at)) 
                FROM hosts
            """)
            
            if last_update:
                hours_since_update = (datetime.now() - last_update).total_seconds() / 3600
                if hours_since_update > 24:
                    print(f"⚠️ Last update was {hours_since_update:.1f} hours ago")
            
        except Exception as e:
            print(f"❌ Error in hourly check: {e}")
    
    async def cleanup_old_data(self):
        """Очистка старых данных"""
        try:
            print("🧹 Cleaning up old data")
            
            conn = await self.db.get_connection()
            
            # Удаляем старые записи фоновых задач (старше 30 дней)
            deleted_tasks = await conn.execute("""
                DELETE FROM background_tasks 
                WHERE created_at < NOW() - INTERVAL '30 days'
            """)
            
            print(f"✅ Cleaned up old background tasks")
            
        except Exception as e:
            print(f"❌ Error in cleanup: {e}")
    
    async def add_custom_schedule(self, task_name: str, schedule_config: Dict[str, Any]):
        """Добавить пользовательское расписание"""
        try:
            frequency = schedule_config.get('frequency', 'daily')
            time_str = schedule_config.get('time', '02:00')
            
            if frequency == 'daily':
                schedule.every().day.at(time_str).do(self._run_custom_task, task_name)
            elif frequency == 'hourly':
                schedule.every().hour.do(self._run_custom_task, task_name)
            elif frequency == 'weekly':
                day = schedule_config.get('day', 'monday')
                schedule.every().monday.at(time_str).do(self._run_custom_task, task_name)
            
            self.tasks[task_name] = schedule_config
            print(f"✅ Added custom schedule for task: {task_name}")
            
        except Exception as e:
            print(f"❌ Error adding custom schedule: {e}")
    
    async def _run_custom_task(self, task_name: str):
        """Выполнить пользовательскую задачу"""
        try:
            print(f"🔄 Running custom task: {task_name}")
            
            if task_name == 'full_update':
                # Полное обновление
                result = await self.db.update_hosts_epss_and_exploits_background_parallel()
            elif task_name == 'incremental_update':
                # Инкрементальное обновление
                days = self.tasks.get(task_name, {}).get('days_old', 1)
                result = await self.db.update_hosts_incremental(days_old=days)
            else:
                print(f"⚠️ Unknown custom task: {task_name}")
                return
            
            print(f"✅ Custom task {task_name} completed")
            
        except Exception as e:
            print(f"❌ Error in custom task {task_name}: {e}")

# Глобальный экземпляр планировщика
scheduler_service = SchedulerService()
