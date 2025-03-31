import logging
import os
import json
import sys
import traceback
from datetime import datetime, timedelta
from telegram_bot import send_message
from ahrefs_api import get_organic_traffic, check_api_availability

# Налаштування логування
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def check_environment():
    """Перевіряємо змінні середовища"""
    logger.info("=== Перевірка змінних середовища ===")
    
    # Перевіряємо, чи існує змінна AHREFS_API_TOKEN
    
    telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
    ahrefs_token = os.getenv('AHREFS_API_KEY')
    
    logger.info(f"TELEGRAM_BOT_TOKEN {'знайдений' if telegram_token else 'не знайдений'} в змінних середовища")
    logger.info(f"AHREFS_API_KEY {'знайдений' if ahrefs_token else 'не знайдений'} в змінних середовища")
    
    if ahrefs_token:
        logger.info(f"AHREFS_API_KEY перші 4 символи: {ahrefs_token[:4]}..., довжина: {len(ahrefs_token)}")
    
    return telegram_token, ahrefs_token, None

def check_api():
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

def check_ahrefs_key():
    """Імітуємо код, який перевіряє AHREFS_API_KEY"""
    logger.info("=== Перевірка AHREFS_API_KEY ===")
    
    if not os.getenv('AHREFS_API_KEY'):
        logger.error("AHREFS_API_KEY не знайдений в змінних середовища")
        if send_message("❌ Помилка: AHREFS_API_KEY не знайдений в змінних середовища", test_mode=True):
            logger.info("Повідомлення про помилку відправлено в Telegram")
        return False
    
    return True

def monitor_function_calls(target_function, *args, **kwargs):
    """Моніторинг викликів функцій"""
    logger.info(f"=== Виклик функції {target_function.__name__} ===")
    
    try:
        result = target_function(*args, **kwargs)
        logger.info(f"Результат виклику {target_function.__name__}: {result}")
        return result
    except Exception as e:
        logger.error(f"Помилка при виклику {target_function.__name__}: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return None

def main():
    logger.info("=== Початок відлагоджувального скрипта ===")
    
    # Крок 1: Перевірка змінних середовища
    telegram_token, ahrefs_token, _ = check_environment()
    
    # Крок 2: Перевірка API
    is_api_available = monitor_function_calls(check_api)
    
    # Важливо! Спробуємо знайти місце помилки
    # Давайте спробуємо дві перевірки у різному порядку
    
    logger.info("Спроба 1: Перевірка AHREFS_API_KEY, потім API")
    success_key = monitor_function_calls(check_ahrefs_key)
    if success_key:
        logger.info("AHREFS_API_KEY перевірка пройшла успішно")
        is_api_available_2 = monitor_function_calls(check_api)
        if is_api_available_2:
            logger.info("API доступне в Спробі 1")
    
    logger.info("Спроба 2: Перевірка API")
    is_api_available_3 = monitor_function_calls(check_api)
    if is_api_available_3:
        logger.info("API доступне в Спробі 2")
    
    logger.info("=== Кінець відлагоджувального скрипта ===")

if __name__ == "__main__":
    main() 