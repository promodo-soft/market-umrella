#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для локального тестування API Ahrefs без підключення до Google Sheets
"""
import os
import sys
import logging
from datetime import datetime

# Додаємо патч для AHREFS_API_TOKEN
try:
    import monkey_patch  # noqa
except ImportError:
    pass

from telegram_bot import send_message
from ahrefs_api import check_api_availability, get_organic_traffic

# Налаштування логування
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def check_env_variables():
    """Перевіряє наявність необхідних змінних середовища"""
    logger.info("=== Перевірка змінних середовища ===")
    
    # Перевіряємо необхідні змінні
    variables = {
        'TELEGRAM_BOT_TOKEN': os.getenv('TELEGRAM_BOT_TOKEN'),
        'AHREFS_API_KEY': os.getenv('AHREFS_API_KEY')
    }
    
    for name, value in variables.items():
        if value:
            logger.info(f"{name}: знайдений (довжина: {len(value)})")
        else:
            logger.error(f"{name}: не знайдений")
    
    return all(variables.values())

def test_api():
    """Тестує доступність API Ahrefs"""
    logger.info("=== Перевірка доступності API Ahrefs ===")
    
    if check_api_availability():
        logger.info("✅ API Ahrefs доступний")
        return True
    else:
        logger.error("❌ API Ahrefs недоступний")
        return False

def test_domains():
    """Тестує отримання трафіку для тестових доменів"""
    logger.info("=== Тестування отримання трафіку ===")
    
    # Тестові домени
    test_domains = ['ahrefs.com', 'example.com', 'google.com']
    
    results = {}
    for domain in test_domains:
        logger.info(f"Запит трафіку для {domain}...")
        traffic = get_organic_traffic(domain)
        results[domain] = traffic
        logger.info(f"{domain}: трафік = {traffic}")
    
    return results

def main():
    """Основна функція"""
    logger.info("=== Початок локального тестування ===")
    
    # Перевірка змінних середовища
    if not check_env_variables():
        logger.error("Відсутні необхідні змінні середовища")
        return False
    
    # Перевірка API
    if not test_api():
        error_message = "❌ Помилка: API Ahrefs недоступний або невірний ключ API"
        logger.error(error_message)
        send_message(error_message, test_mode=True)
        return False
    
    # Тестування доменів
    results = test_domains()
    
    # Формування повідомлення
    if results:
        message = "✅ Тестування API Ahrefs пройшло успішно\n\n"
        message += "📊 Результати трафіку:\n"
        for domain, traffic in results.items():
            message += f"{domain}: {traffic:,}\n"
        
        # Додаємо відмітку часу
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        message += f"\nДата: {now}"
        
        # Відправка повідомлення в Telegram
        if send_message(message, test_mode=True):
            logger.info("Повідомлення про успішне тестування відправлено в Telegram")
        
        logger.info("=== Тестування завершено успішно ===")
        return True
    else:
        error_message = "❌ Помилка: Не вдалося отримати трафік для тестових доменів"
        logger.error(error_message)
        send_message(error_message, test_mode=True)
        logger.info("=== Тестування завершено з помилками ===")
        return False

if __name__ == "__main__":
    success = main()
    if not success:
        sys.exit(1) 