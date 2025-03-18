import logging
from data_manager import load_traffic_data, save_traffic_data

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    logger.info("Запуск тестового режима")
    
    # Загрузка текущих данных
    domains_data = load_traffic_data()
    if not domains_data:
        logger.error("Не удалось загрузить данные из базы")
        exit(1)
    
    # Здесь можно добавить дополнительную логику для тестирования
    logger.info(f"Загружено {len(domains_data)} доменов из базы данных")
    
    # Сохраняем данные
    save_traffic_data(domains_data)
    logger.info("Тест завершен успешно") 