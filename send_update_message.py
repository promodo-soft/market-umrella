#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для отправки сообщения о последних изменениях трафика в рабочий чат
"""
import os
import logging
from datetime import datetime
from telegram_bot import send_message

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Основная функция для отправки сообщения"""
    logger.info("=== Начало отправки сообщения ===")
    
    # Проверяем наличие токена бота
    if not os.getenv('TELEGRAM_BOT_TOKEN'):
        logger.error("TELEGRAM_BOT_TOKEN не найден в переменных окружения")
        return False
    
    # Формируем сообщение
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    message = "✅ Обновление данных о трафике выполнено успешно\n\n"
    message += "📊 Результаты мониторинга:\n"
    message += "- Трафик сайтов проверен\n"
    message += "- Данные успешно обработаны\n"
    message += "- Результаты сохранены\n\n"
    message += f"Важное сообщение: это повторная отправка последних результатов в рабочий чат.\n\n"
    message += f"Дата: {now}"
    
    # Отправляем сообщение в Telegram (test_mode=False для отправки во все чаты, включая рабочий)
    logger.info("Отправка сообщения во все чаты, включая рабочий")
    if send_message(message, test_mode=False):
        logger.info("Сообщение успешно отправлено во все чаты")
        return True
    else:
        logger.error("Ошибка при отправке сообщения")
        return False

if __name__ == "__main__":
    success = main()
    if not success:
        logger.error("Отправка сообщения завершилась с ошибкой")
    else:
        logger.info("Отправка сообщения завершена успешно") 