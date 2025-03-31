#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import logging
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
    result = test_ahrefs_key()
    logger.info(f"Результат тесту: {'успішно' if result else 'невдача'}")
    
    if not result:
        # Повертаємо код помилки для використання в CI/CD
        exit(1) 