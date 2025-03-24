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
    logger.info("Тестирование отправки сообщений в тестовом режиме")
    
    # Загружаем ID чатов
    load_chat_id()
    
    # Тестовое сообщение
    message = ("📊 *Тестовое сообщение для проверки функциональности*\n\n"
              "Это сообщение отправляется только в тестовые чаты, исключая рабочие чаты с большим количеством людей.\n\n"
              "✅ Тест успешно выполнен!")
    
    # Отправляем сообщение только в тестовые чаты
    result = send_message(message, parse_mode="Markdown", test_mode=True)
    
    if result:
        logger.info("Сообщение успешно отправлено в тестовые чаты")
    else:
        logger.error("Ошибка при отправке сообщения")
    
    return result

if __name__ == "__main__":
    if os.getenv('TELEGRAM_BOT_TOKEN'):
        logger.info("Токен Telegram найден в переменных окружения")
    else:
        logger.warning("Токен Telegram не найден в переменных окружения")
    
    test_send_message() 