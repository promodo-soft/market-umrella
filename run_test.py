import logging
from data_manager import load_traffic_data, save_traffic_data

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    logger.info("Запуск корректировки данных для work.ua и pumb.ua")
    
    # Загрузка текущих данных
    domains_data = load_traffic_data()
    if not domains_data:
        logger.error("Не удалось загрузить данные из базы")
        exit(1)
    
    # Исправляем некорректные данные
    corrections = {
        'work.ua': 3900000,  # Исправляем на 3.9M
        'pumb.ua': 305000    # Исправляем на 305k
    }
    
    for domain, correct_traffic in corrections.items():
        if domain in domains_data:
            old_traffic = domains_data[domain]['traffic']
            # Обновляем только текущее значение трафика, оставляя previous_traffic без изменений
            domains_data[domain]['traffic'] = correct_traffic
            logger.info(f"Домен {domain}: исправлено значение трафика с {old_traffic:,} на {correct_traffic:,}")
        else:
            logger.warning(f"Домен {domain} не найден в базе данных")
    
    # Сохраняем исправленные данные
    save_traffic_data(domains_data)
    logger.info("Корректировка данных завершена. Следующие обновления будут получены через API Ahrefs") 