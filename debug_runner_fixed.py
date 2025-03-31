import logging
import os
import traceback
from ahrefs_api import check_api_availability

# Налаштування логування
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def check_environment():
    """Перевіряємо змінні середовища"""
    logger.info("=== Перевірка змінних середовища ===")
    
    for key in ['TELEGRAM_BOT_TOKEN', 'AHREFS_API_KEY', 'AHREFS_API_TOKEN']:
        value = os.getenv(key)
        logger.info(f"{key}: {'знайдений' if value else 'не знайдений'} в змінних середовища")
        if value and key in ['AHREFS_API_KEY']:
            logger.info(f"{key} перші 4 символи: {value[:4]}..., довжина: {len(value)}")
    
    return True

def test_api_availability():
    """Тестуємо доступність API"""
    logger.info("=== Тестуємо доступність API ===")
    
    try:
        result = check_api_availability()
        logger.info(f"API доступний: {result}")
        return result
    except Exception as e:
        logger.error(f"Помилка при перевірці API: {str(e)}")
        logger.error(traceback.format_exc())
        return False

def main():
    """Основна функція тестування"""
    logger.info("=== Початок тестування ===")
    
    # Перевіряємо змінні середовища
    check_environment()
    
    # Перевіряємо API
    api_available = test_api_availability()
    
    if api_available:
        logger.info("✅ Тест пройдено успішно! API доступний.")
    else:
        logger.error("❌ Тест не пройдено! API недоступний.")
    
    logger.info("=== Кінець тестування ===")

if __name__ == "__main__":
    main() 