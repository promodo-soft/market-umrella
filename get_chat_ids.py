import os
import logging
import requests
import json

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_telegram_chat_ids():
    """
    Получает все последние чаты бота
    """
    # Получаем токен из переменных окружения
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN не найден в переменных окружения")
        return None

    # Формируем URL для запроса обновлений
    url = f"https://api.telegram.org/bot{token}/getUpdates"
    
    try:
        # Отправляем запрос
        response = requests.get(url)
        data = response.json()
        
        # Проверяем успешность запроса
        if not data.get('ok'):
            logger.error(f"Ошибка при получении обновлений: {data.get('description')}")
            return None
        
        # Извлекаем уникальные chat_id из обновлений
        chat_ids = {}
        for update in data.get('result', []):
            message = update.get('message')
            if message and 'chat' in message:
                chat = message['chat']
                chat_id = chat['id']
                chat_name = chat.get('title', chat.get('username', 'Личный чат'))
                chat_ids[chat_id] = chat_name
        
        # Выводим результаты
        if chat_ids:
            logger.info(f"Найдено {len(chat_ids)} чатов:")
            for chat_id, chat_name in chat_ids.items():
                logger.info(f"Chat ID: {chat_id}, Название: {chat_name}")
        else:
            logger.info("Чаты не найдены. Добавьте бота в чат и отправьте сообщение.")
        
        return chat_ids
    
    except Exception as e:
        logger.error(f"Ошибка при получении chat_id: {str(e)}")
        return None

if __name__ == "__main__":
    chat_ids = get_telegram_chat_ids()
    
    # Сохраняем все chat_id в файл
    if chat_ids:
        all_chats = {str(chat_id): name for chat_id, name in chat_ids.items()}
        with open('telegram_chats.json', 'w') as f:
            json.dump(all_chats, f, indent=2)
        logger.info(f"ID чатов сохранены в файл telegram_chats.json") 