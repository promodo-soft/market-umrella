import logging
import os
import traceback
import platform
import subprocess
import sys
import inspect
from ahrefs_api import check_api_availability

# Налаштування логування
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("debug_runner_fixed.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def log_system_info():
    """Логування інформації про систему"""
    logger.info(f"Python версія: {sys.version}")
    logger.info(f"Операційна система: {platform.system()} {platform.version()}")
    logger.info(f"Поточна директорія: {os.getcwd()}")
    
    # Список файлів у директорії
    files = os.listdir('.')
    logger.info(f"Список файлів в директорії: {', '.join(files[:10])}..." if len(files) > 10 else f"Список файлів в директорії: {', '.join(files)}")
    
    # Значення змінних середовища
    env_vars = ['TELEGRAM_BOT_TOKEN', 'AHREFS_API_KEY', 'AHREFS_API_TOKEN']
    for var in env_vars:
        value = os.getenv(var)
        if value:
            # Маскуємо токени для безпеки
            masked_value = value[:4] + '...' + value[-4:] if len(value) > 8 else '****'
            logger.info(f"{var}: {'знайдений' if value else 'не знайдений'} (довжина: {len(value)})")
        else:
            logger.info(f"{var}: не знайдений в змінних середовища")

def run_command(command):
    """Виконує команду в консолі та повертає результат"""
    try:
        logger.info(f"Виконуємо команду: {command}")
        result = subprocess.run(command, shell=True, capture_output=True, text=True, check=False)
        logger.info(f"Код виходу: {result.returncode}")
        if result.stdout:
            logger.info(f"Вивід: {result.stdout[:200]}..." if len(result.stdout) > 200 else f"Вивід: {result.stdout}")
        if result.stderr:
            logger.warning(f"Помилка: {result.stderr[:200]}..." if len(result.stderr) > 200 else f"Помилка: {result.stderr}")
        return result
    except Exception as e:
        logger.error(f"Помилка при виконанні команди: {str(e)}")
        return None

def check_api():
    """Перевіряє доступність API Ahrefs"""
    logger.info("Перевірка API Ahrefs...")
    result = check_api_availability()
    logger.info(f"Результат перевірки API: {'доступний' if result else 'недоступний'}")
    return result

# Головна функція для запуску діагностики
if __name__ == "__main__":
    logger.info("=== Запуск діагностики API ===")
    
    # Виводимо системну інформацію
    log_system_info()
    
    # Перевіряємо мережеве з'єднання
    logger.info("Перевірка мережевого з'єднання до API...")
    run_command("ping -c 2 api.ahrefs.com" if platform.system() != "Windows" else "ping -n 2 api.ahrefs.com")
    
    # Перевіряємо API
    api_available = check_api()
    
    # Підводимо підсумки
    if api_available:
        logger.info("✅ API Ahrefs доступний")
    else:
        logger.error("❌ API Ahrefs недоступний")
        exit(1) 