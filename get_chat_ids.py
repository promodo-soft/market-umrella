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

    # Формируем URL для запроса обновлений с большим лимитом
    url = f"https://api.telegram.org/bot{token}/getUpdates?limit=100&timeout=60"
    
    try:
        # Отправляем запрос
        logger.info(f"Отправляем запрос к API Telegram: {url}")
        response = requests.get(url)
        data = response.json()
        
        # Проверяем успешность запроса
        if not data.get('ok'):
            logger.error(f"Ошибка при получении обновлений: {data.get('description')}")
            return None
        
        # Сохраняем также существующие чаты из файла
        existing_chats = {}
        if os.path.exists('telegram_chats.json'):
            try:
                with open('telegram_chats.json', 'r') as f:
                    existing_chats = json.load(f)
                    logger.info(f"Загружено {len(existing_chats)} существующих чатов из файла")
            except Exception as e:
                logger.error(f"Ошибка при чтении файла чатов: {str(e)}")
        
        # Извлекаем уникальные chat_id из обновлений
        chat_ids = {}
        
        # Сначала добавляем существующие
        for chat_id, chat_name in existing_chats.items():
            chat_ids[int(chat_id)] = chat_name
        
        # Затем добавляем новые из обновлений
        logger.info(f"Получено {len(data.get('result', []))} обновлений")
        for update in data.get('result', []):
            # Проверяем различные типы обновлений, которые могут содержать информацию о чате
            if 'message' in update:
                message = update['message']
                if 'chat' in message:
                    chat = message['chat']
                    chat_id = chat['id']
                    chat_type = chat.get('type', 'unknown')
                    
                    if chat_type == 'private':
                        chat_name = chat.get('username', chat.get('first_name', 'Личный чат'))
                    elif chat_type in ['group', 'supergroup']:
                        chat_name = chat.get('title', f'Группа {chat_id}')
                    else:
                        chat_name = f'Чат {chat_id}'
                    
                    chat_ids[chat_id] = chat_name
                    logger.info(f"Найден чат {chat_name} (ID: {chat_id}, тип: {chat_type})")
        
        # Выводим результаты
        if chat_ids:
            logger.info(f"Всего найдено {len(chat_ids)} чатов:")
            for chat_id, chat_name in chat_ids.items():
                logger.info(f"Chat ID: {chat_id}, Название: {chat_name}")
        else:
            logger.info("Чаты не найдены. Добавьте бота в чат и отправьте сообщение.")
        
        return chat_ids
    
    except Exception as e:
        logger.error(f"Ошибка при получении chat_id: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return None

if __name__ == "__main__":
    chat_ids = get_telegram_chat_ids()
    
    # Сохраняем все chat_id в файл
    if chat_ids:
        all_chats = {str(chat_id): name for chat_id, name in chat_ids.items()}
        with open('telegram_chats.json', 'w') as f:
            json.dump(all_chats, f, indent=2)
        logger.info(f"ID чатов сохранены в файл telegram_chats.json")
    else:
        logger.error("Не удалось получить ID чатов") 