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
    
    telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
    ahrefs_token = os.getenv('AHREFS_API_KEY')
    
    logger.info(f"Telegram token {'знайдений' if telegram_token else 'не знайдений'} в змінних середовища")
    logger.info(f"Ahrefs token {'знайдений' if ahrefs_token else 'не знайдений'} в змінних середовища")
    
    # Перевіряємо, чи існує змінна AHREFS_API_TOKEN
    old_token = os.getenv('AHREFS_API_KEY')
    logger.info(f"AHREFS_API_TOKEN {'знайдений' if old_token else 'не знайдений'} в змінних середовища")
    
    # Логуємо всі змінні середовища, які містять API або TOKEN
    env_vars = {k: "[HIDDEN]" for k, v in os.environ.items() if 'API' in k or 'TOKEN' in k}
    logger.info(f"Змінні середовища, пов'язані з API/токенами: {env_vars}")
    
    return telegram_token, ahrefs_token, old_token

def check_api():
    """Перевіряємо доступність API"""
    logger.info("=== Перевірка доступності API ===")
    
    try:
        is_available = check_api_availability()
        logger.info(f"Результат check_api_availability(): {is_available}")
        return is_available
    except Exception as e:
        logger.error(f"Помилка при перевірці доступності API: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False

def check_ahrefs_token():
    """Імітуємо код, який перевіряє AHREFS_API_TOKEN"""
    logger.info("=== Перевірка AHREFS_API_TOKEN ===")
    
    if not os.getenv('AHREFS_API_KEY'):
        logger.error('AHREFS_API_KEY не знайдений в змінних середовища")
        if send_message("❌ Помилка: AHREFS_API_TOKEN не знайдений в змінних середовища", test_mode=True):
            logger.info("Повідомлення про помилку відправлено в Telegram")
        return False
    
    return True

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
    telegram_token, ahrefs_token, old_token = check_environment()
    
    # Крок 2: Перевірка API
    is_api_available = monitor_function_calls(check_api)
    
    # Важливо! Спробуємо знайти місце помилки
    # Давайте спробуємо наші дві перевірки у різному порядку
    
    logger.info("Спроба 1: Перевірка AHREFS_API_KEY, потім API, потім AHREFS_API_TOKEN")
    success_key = monitor_function_calls(check_ahrefs_key)
    if success_key:
        logger.info("AHREFS_API_KEY перевірка пройшла успішно")
        is_api_available_2 = monitor_function_calls(check_api)
        if is_api_available_2:
            logger.info("API доступне в Спробі 1")
            # Тепер перевіряємо AHREFS_API_TOKEN
            success_token = monitor_function_calls(check_ahrefs_token)
            if not success_token:
                logger.error("Спроба 1: Помилка при перевірці AHREFS_API_TOKEN")
    
    logger.info("Спроба 2: Перевірка API, потім AHREFS_API_TOKEN")
    is_api_available_3 = monitor_function_calls(check_api)
    if is_api_available_3:
        logger.info("API доступне в Спробі 2")
        # Відразу перевіряємо AHREFS_API_TOKEN
        success_token_2 = monitor_function_calls(check_ahrefs_token)
        if not success_token_2:
            logger.error("Спроба 2: Помилка при перевірці AHREFS_API_TOKEN")
    
    logger.info("=== Кінець відлагоджувального скрипта ===")

if __name__ == "__main__":
    main() 