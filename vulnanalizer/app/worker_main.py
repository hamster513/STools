"""
Главный файл для Worker контейнера
Отдельный контейнер для обработки фоновых задач
"""
import asyncio
import signal
import sys
from database import get_db
from services.scheduler_service import scheduler_service

class WorkerApp:
    def __init__(self):
        self.running = False
        self.db = get_db()
    
    async def start(self):
        """Запуск worker приложения"""
        print("🚀 Запуск Worker контейнера...")
        
        try:
            # Проверяем соединение с базой данных
            conn = await self.db.get_connection()
            await conn.execute("SELECT 1")
            await self.db.release_connection(conn)
            print("✅ База данных подключена")
            
            # Запускаем планировщик
            await scheduler_service.start_scheduler()
            print("✅ Планировщик фоновых задач запущен")
            
            self.running = True
            
            # Основной цикл
            while self.running:
                await asyncio.sleep(1)
                
        except Exception as e:
            print(f"❌ Ошибка запуска Worker: {e}")
            sys.exit(1)
    
    async def stop(self):
        """Остановка worker приложения"""
        print("🔄 Остановка Worker контейнера...")
        self.running = False
        
        try:
            await scheduler_service.stop_scheduler()
            print("✅ Планировщик остановлен")
        except Exception as e:
            print(f"⚠️ Ошибка остановки планировщика: {e}")
        
        print("🔄 Worker остановлен")

# Глобальный экземпляр
worker_app = WorkerApp()

def signal_handler(signum, frame):
    """Обработчик сигналов для graceful shutdown"""
    print(f"📡 Получен сигнал {signum}, останавливаем Worker...")
    asyncio.create_task(worker_app.stop())

async def main():
    """Главная функция"""
    # Регистрируем обработчики сигналов
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        await worker_app.start()
    except KeyboardInterrupt:
        print("📡 Получен SIGINT, останавливаем...")
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
    finally:
        await worker_app.stop()

if __name__ == "__main__":
    asyncio.run(main())
