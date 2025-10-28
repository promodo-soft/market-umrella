import logging
import os
from telegram_bot import send_message, load_chat_id

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_send_message():
    """
    Тестирует отправку сообщений с использованием параметра test_mode
    """
    logger.info("Тестування відправки повідомлень в тестовому режимі")
    
    # Загружаем ID чатов
    load_chat_id()
    
    # Тестовое сообщение
    message = ("📊 *Тестове повідомлення для перевірки функціональності*\n\n"
              "Це повідомлення відправляється тільки в тестові чати, виключаючи робочі чати з великою кількістю людей.\n\n"
              "✅ Тест успішно виконано!")
    
    # Отправляем сообщение только в тестовые чаты
    result = send_message(message, parse_mode="Markdown", test_mode=True)
    
    if result:
        logger.info("Повідомлення успішно відправлено в тестові чати")
    else:
        logger.error("Помилка при відправці повідомлення")
    
    return result

if __name__ == "__main__":
    if os.getenv('TELEGRAM_BOT_TOKEN'):
        logger.info("Токен Telegram знайдений в змінних середовища")
    else:
        logger.warning("Токен Telegram не знайдений в змінних середовища")
    
    test_send_message() 