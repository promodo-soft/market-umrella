import logging
import time
import schedule
import threading
from datetime import datetime
import pytz

from config import (
    SCHEDULE_DAY, SCHEDULE_TIME, TIMEZONE, 
    TRAFFIC_DECREASE_THRESHOLD, Mode
)
from ahrefs_api import get_organic_traffic, check_api_availability, is_api_limit_reached, get_api_limit_message
from telegram_bot import notify_traffic_update, send_message, run_bot

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("main.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def collect_traffic_data(mode: str = 'production', send_notifications: bool = True):
    """
    Собирает данные о трафике для всех доменов.
    
    Args:
        mode (str): Режим работы ('production' или 'test')
        send_notifications (bool): Отправлять ли уведомления в Telegram
    """
    logger.info(f"Начало сбора данных о трафике (режим: {mode})")
    
    # Проверка доступности API
    if not check_api_availability():
        if send_notifications:
            message = "⚠️ *Ошибка*\nAPI Ahrefs недоступно. Сбор данных невозможен."
            send_message(message, parse_mode='Markdown')
        return
        
    # Загрузка списка доменов
    domains = load_domains()
    if not domains:
        logger.error("Не удалось загрузить список доменов")
        return
        
    # Сбор данных о трафике
    domains_data = {}
    has_traffic_decrease = False
    
    for domain in domains:
        try:
            # Получение трафика через API
            traffic = get_organic_traffic(domain)
            if traffic is None:
                continue
                
            # Получение предыдущего значения трафика
            previous_traffic = previous_data.get(domain, {}).get('traffic', 0) if previous_data else 0
            
            # Сохранение данных
            domains_data[domain] = {
                'traffic': traffic,
                'previous_traffic': previous_traffic
            }
            
            logger.info(f"Домен {domain}: трафик = {traffic}")
            
            # Проверка на падение трафика
            if previous_traffic > 0:
                decrease = ((traffic - previous_traffic) / previous_traffic) * 100
                if decrease <= -TRAFFIC_DECREASE_THRESHOLD:
                    has_traffic_decrease = True
            
        except Exception as e:
            logger.error(f"Ошибка при получении данных для домена {domain}: {str(e)}")
    
    # Отправка уведомлений
    if domains_data and send_notifications:
        if mode == Mode.TEST or has_traffic_decrease:
            notify_traffic_update(domains_data, mode=mode)
            
    # Сохранение данных
    save_traffic_data(domains_data)
    
    logger.info("Сбор данных о трафике завершен")

def run_scheduler():
    """Запускает планировщик для регулярного сбора данных."""
    schedule_time = SCHEDULE_TIME
    
    if SCHEDULE_DAY.lower() == 'everyday':
        schedule.every().day.at(schedule_time).do(collect_traffic_data, mode='production')
    else:
        getattr(schedule.every(), SCHEDULE_DAY.lower()).at(schedule_time).do(
            collect_traffic_data, mode='production'
        )
    
    logger.info(f"Планировщик настроен на выполнение {SCHEDULE_DAY} в {SCHEDULE_TIME}")
    
    while True:
        schedule.run_pending()
        time.sleep(60)

def main():
    """
    Основная функция программы.
    """
    logger.info("Запуск программы мониторинга трафика")
    
    # Запуск Telegram бота в отдельном потоке
    bot_thread = threading.Thread(target=run_bot)
    bot_thread.daemon = True
    bot_thread.start()
    
    # Запуск планировщика в основном потоке
    run_scheduler()

if __name__ == "__main__":
    main() 