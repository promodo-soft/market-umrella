import logging
import json
import os
from telegram_bot import load_chat_id, send_message_to_chats, get_updater

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_send_to_group():
    """
    Тестирует отправку сообщения в группу
    """
    try:
        # Загружаем ID чатов
        load_chat_id()
        
        # Проверяем наличие файла с чатами
        if not os.path.exists('telegram_chats.json'):
            logger.error("Файл telegram_chats.json не найден")
            return False
        
        # Загружаем чаты из файла
        with open('telegram_chats.json', 'r') as f:
            chats = json.load(f)
        
        logger.info(f"Загружено {len(chats)} чатов из файла")
        
        # Находим групповые чаты (ID начинается с минуса)
        group_chats = {cid: name for cid, name in chats.items() if cid.startswith('-')}
        logger.info(f"Найдено {len(group_chats)} групповых чатов: {group_chats}")
        
        if not group_chats:
            logger.error("Групповые чаты не найдены")
            return False
        
        # Отправляем тестовое сообщение в каждый групповой чат
        for chat_id, chat_name in group_chats.items():
            try:
                message = f"📊 Тестовое сообщение в групповой чат '{chat_name}' (ID: {chat_id}).\n\n"
                message += "Если вы видите это сообщение, значит бот настроен правильно и может отправлять уведомления в этот чат."
                
                logger.info(f"Отправка тестового сообщения в чат {chat_name} (ID: {chat_id})")
                get_updater().bot.send_message(chat_id=int(chat_id), text=message)
                logger.info(f"Сообщение успешно отправлено в чат {chat_name}")
            except Exception as e:
                logger.error(f"Ошибка при отправке в чат {chat_name} (ID: {chat_id}): {str(e)}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
        
        return True
    
    except Exception as e:
        logger.error(f"Ошибка при тестировании отправки в группу: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False

if __name__ == "__main__":
    logger.info("Начинаем тест отправки сообщений в групповые чаты")
    result = test_send_to_group()
    if result:
        logger.info("Тест завершен успешно")
    else:
        logger.error("Тест завершен с ошибками") 