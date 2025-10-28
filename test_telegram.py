import logging
from telegram_bot import send_message
import os

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_telegram():
    """
    Тестирует отправку сообщений в Telegram
    """
    try:
        logger.info("Начинаем тест отправки сообщений в Telegram")
        
        # Проверяем наличие токена
        telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
        logger.info(f"Telegram token {'найден' if telegram_token else 'не найден'} в переменных окружения")
        
        # Пробуем отправить тестовое сообщение
        test_message = "🔄 Тестовое сообщение от Market Umbrella\n\nЕсли вы видите это сообщение, значит отправка работает корректно!"
        
        logger.info("Отправляем тестовое сообщение")
        result = send_message(test_message)
        
        if result:
            logger.info("✅ Сообщение успешно отправлено")
            return True
        else:
            logger.error("❌ Не удалось отправить сообщение")
            return False
            
    except Exception as e:
        logger.error(f"Ошибка при тестировании Telegram: {str(e)}")
        logger.error(f"Тип ошибки: {type(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False

if __name__ == "__main__":
    success = test_telegram()
    if not success:
        logger.error("Тест Telegram завершился с ошибкой")
        exit(1)
    else:
        logger.info("Тест Telegram успешно завершен") 