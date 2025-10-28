#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import logging
import platform
import subprocess
import sys
from ahrefs_api import check_api_availability

# Налаштування логування
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("test_ahrefs_key.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def log_system_info():
    """Логування інформації про систему"""
    logger.info(f"Операційна система: {platform.system()} {platform.version()}")
    logger.info(f"Python версія: {sys.version}")
    logger.info(f"Поточна директорія: {os.getcwd()}")
    
    # Список файлів у директорії
    files = os.listdir('.')
    logger.info(f"Файли в директорії: {', '.join(files[:5])}..." if len(files) > 5 else f"Файли в директорії: {', '.join(files)}")
    
    # Значення змінних середовища
    env_vars = ['AHREFS_API_KEY', 'TELEGRAM_BOT_TOKEN']
    for var in env_vars:
        value = os.getenv(var)
        if value:
            # Маскуємо токени для безпеки
            masked_value = value[:4] + '...' + value[-4:] if len(value) > 8 else '****'
            logger.info(f"Змінна середовища {var}: {masked_value} (довжина: {len(value)})")
        else:
            logger.info(f"Змінна середовища {var} не встановлена")

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

def test_ahrefs_key():
    """Перевіряє, чи AHREFS_API_KEY знайдений і доступний"""
    try:
        # Перевіряємо наявність ключа
        api_key = os.getenv('AHREFS_API_KEY')
        if not api_key:
            logger.error("AHREFS_API_KEY не знайдений в змінних середовища")
            return False
        
        logger.info(f"AHREFS_API_KEY знайдений, довжина: {len(api_key)}")
        logger.info(f"Перші 4 символи: {api_key[:4]}...")
        
        # Перевіряємо доступність API
        logger.info("Перевірка доступності API Ahrefs...")
        api_available = check_api_availability()
        
        if api_available:
            logger.info("✅ Тест пройдено успішно! API доступний.")
            return True
        else:
            logger.error("❌ Помилка: API Ahrefs недоступний")
            return False
            
    except Exception as e:
        logger.error(f"❌ Помилка при тестуванні: {str(e)}")
        return False

if __name__ == "__main__":
    logger.info("=== Початок тесту AHREFS_API_KEY ===")
    
    # Логування системної інформації
    log_system_info()
    
    # Перевірка мережевого з'єднання
    logger.info("Перевірка мережевого з'єднання...")
    run_command("ping -c 2 api.ahrefs.com" if platform.system() != "Windows" else "ping -n 2 api.ahrefs.com")
    
    # Виконання тесту
    result = test_ahrefs_key()
    logger.info(f"Результат тесту: {'успішно' if result else 'невдача'}")
    
    if not result:
        # Повертаємо код помилки для використання в CI/CD
        exit(1) 