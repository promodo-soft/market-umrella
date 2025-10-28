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
            logger.error("Файл telegram_chats.json не знайдений")
            return False
        
        # Загружаем чаты из файла
        with open('telegram_chats.json', 'r') as f:
            chats = json.load(f)
        
        logger.info(f"Завантажено {len(chats)} чатів з файлу")
        
        # Находим групповые чаты (ID начинается с минуса)
        group_chats = {cid: name for cid, name in chats.items() if cid.startswith('-') and cid not in EXCLUDED_CHAT_IDS}
        
        # Выводим информацию о всех чатах, включая исключенные
        all_group_chats = {cid: name for cid, name in chats.items() if cid.startswith('-')}
        logger.info(f"Знайдено {len(all_group_chats)} групових чатів: {all_group_chats}")
        logger.info(f"Виключено з тестування: {[chats.get(cid, cid) for cid in EXCLUDED_CHAT_IDS]}")
        logger.info(f"Для тестування обрано {len(group_chats)} чатів: {group_chats}")
        
        if not all_group_chats:
            logger.error("Групові чати не знайдені")
            return False
            
        if not group_chats:
            logger.info("Всі знайдені групові чати виключені з тестування")
            logger.info("Перевірка доступності чатів без відправки повідомлень:")
            
            # Проверяем доступ к чатам без отправки сообщений
            for chat_id, chat_name in all_group_chats.items():
                try:
                    logger.info(f"Отримання інформації про чат {chat_name} (ID: {chat_id})")
                    chat_info = get_updater().bot.get_chat(chat_id=int(chat_id))
                    logger.info(f"Чат доступний: {chat_info.title} ({chat_info.type})")
                except Exception as e:
                    logger.error(f"Помилка при перевірці чату {chat_name} (ID: {chat_id}): {str(e)}")
            
            return True
        
        # Отправляем тестовое сообщение только в не исключенные чаты
        for chat_id, chat_name in group_chats.items():
            try:
                message = f"📊 Тестове повідомлення в груповий чат '{chat_name}' (ID: {chat_id}).\n\n"
                message += "Якщо ви бачите це повідомлення, значить бот налаштований правильно і може відправляти сповіщення в цей чат."
                
                logger.info(f"Відправка тестового повідомлення в чат {chat_name} (ID: {chat_id})")
                get_updater().bot.send_message(chat_id=int(chat_id), text=message)
                logger.info(f"Повідомлення успішно відправлено в чат {chat_name}")
            except Exception as e:
                logger.error(f"Помилка при відправці в чат {chat_name} (ID: {chat_id}): {str(e)}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
        
        return True
    
    except Exception as e:
        logger.error(f"Помилка при тестуванні відправки в групу: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False

if __name__ == "__main__":
    logger.info("Починаємо тест відправки повідомлень в групові чати")
    result = test_send_to_group()
    if result:
        logger.info("Тест завершено успішно")
    else:
        logger.error("Тест завершено з помилками") 