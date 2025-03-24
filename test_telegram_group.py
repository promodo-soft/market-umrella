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

# ID чатов, куда не следует отправлять тестовые сообщения
EXCLUDED_CHAT_IDS = ["-1001930136015"]  # SEO & CSD - рабочий чат с большим количеством людей

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
        group_chats = {cid: name for cid, name in chats.items() if cid.startswith('-') and cid not in EXCLUDED_CHAT_IDS}
        
        # Выводим информацию о всех чатах, включая исключенные
        all_group_chats = {cid: name for cid, name in chats.items() if cid.startswith('-')}
        logger.info(f"Найдено {len(all_group_chats)} групповых чатов: {all_group_chats}")
        logger.info(f"Исключено из тестирования: {[chats.get(cid, cid) for cid in EXCLUDED_CHAT_IDS]}")
        logger.info(f"Для тестирования выбрано {len(group_chats)} чатов: {group_chats}")
        
        if not all_group_chats:
            logger.error("Групповые чаты не найдены")
            return False
            
        if not group_chats:
            logger.info("Все найденные групповые чаты исключены из тестирования")
            logger.info("Проверка доступности чатов без отправки сообщений:")
            
            # Проверяем доступ к чатам без отправки сообщений
            for chat_id, chat_name in all_group_chats.items():
                try:
                    logger.info(f"Получение информации о чате {chat_name} (ID: {chat_id})")
                    chat_info = get_updater().bot.get_chat(chat_id=int(chat_id))
                    logger.info(f"Чат доступен: {chat_info.title} ({chat_info.type})")
                except Exception as e:
                    logger.error(f"Ошибка при проверке чата {chat_name} (ID: {chat_id}): {str(e)}")
            
            return True
        
        # Отправляем тестовое сообщение только в не исключенные чаты
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