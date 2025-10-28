import logging
import os
from datetime import datetime
from ahrefs_api import get_organic_traffic, check_api_availability

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_ahrefs_api():
    # Проверка наличия API ключа
    ahrefs_token = os.getenv('AHREFS_API_KEY')
    logger.info(f"Ahrefs token {'найден' if ahrefs_token else 'не найден'} в переменных окружения")
    
    if not ahrefs_token:
        logger.error("AHREFS_API_KEY не найден в переменных окружения")
        return False
    
    # Проверка доступности API
    logger.info("Проверка доступности API Ahrefs...")
    if not check_api_availability():
        logger.error("API Ahrefs недоступно или неверный ключ API")
        return False
    
    logger.info("API Ahrefs доступно, начинаем тестовые запросы")
    
    # Тестовые домены
    test_domains = [
        "ahrefs.com",
        "google.com",
        "bing.com",
        "github.com",
        "facebook.com"
    ]
    
    # Тестирование получения трафика
    for domain in test_domains:
        logger.info(f"Запрашиваем данные для домена: {domain}")
        traffic = get_organic_traffic(domain)
        logger.info(f"Получен трафик для {domain}: {traffic}")
    
    logger.info("Тестирование API Ahrefs завершено")
    return True

if __name__ == "__main__":
    success = test_ahrefs_api()
    if not success:
        logger.error("Тест API Ahrefs завершился с ошибкой")
        exit(1) 