import logging
from telegram import Update, ParseMode
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
from config import TELEGRAM_BOT_TOKEN
from typing import Dict, Any, List, Union
import json
import os

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("telegram_bot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Файлы для хранения chat_id
CHAT_ID_FILE = 'chat_id.json'
CHATS_FILE = 'telegram_chats.json'

# Глобальные переменные
chat_id = None
chat_ids = []
updater_instance = None

def get_updater():
    """Возвращает глобальный экземпляр updater."""
    global updater_instance
    if updater_instance is None:
        updater_instance = Updater(TELEGRAM_BOT_TOKEN)
    return updater_instance

def load_chat_id():
    """Загружает chat_id из файла."""
    global chat_id, chat_ids
    try:
        # Загружаем основной chat_id
        if os.path.exists(CHAT_ID_FILE):
            with open(CHAT_ID_FILE, 'r') as f:
                data = json.load(f)
                chat_id = data.get('chat_id')
                if chat_id:
                    logger.info(f"Загружен основной chat_id: {chat_id}")
                    
        # Загружаем все чаты из файла
        if os.path.exists(CHATS_FILE):
            with open(CHATS_FILE, 'r') as f:
                chats_data = json.load(f)
                chat_ids = [int(cid) for cid in chats_data.keys()]
                logger.info(f"Загружено {len(chat_ids)} дополнительных чатов")
                
        # Если основной chat_id есть, но его нет в списке всех чатов, добавляем
        if chat_id and chat_id not in chat_ids:
            chat_ids.append(chat_id)
            
        # Удаляем дубликаты
        chat_ids = list(set(chat_ids))
            
    except Exception as e:
        logger.error(f"Ошибка при загрузке chat_id: {str(e)}")

def save_chat_id():
    """Сохраняет chat_id в файл."""
    try:
        with open(CHAT_ID_FILE, 'w') as f:
            json.dump({'chat_id': chat_id}, f)
        logger.info(f"Сохранен chat_id: {chat_id}")
        
        # Добавляем новый chat_id в список всех чатов
        if os.path.exists(CHATS_FILE):
            with open(CHATS_FILE, 'r') as f:
                chats_data = json.load(f)
        else:
            chats_data = {}
            
        # Добавляем новый чат с названием 'Новый чат'
        chats_data[str(chat_id)] = "Новый чат"
        
        # Сохраняем обновленный список чатов
        with open(CHATS_FILE, 'w') as f:
            json.dump(chats_data, f, indent=2)
            
    except Exception as e:
        logger.error(f"Ошибка при сохранении chat_id: {str(e)}")

def start(update: Update, context: CallbackContext) -> None:
    """Обработчик команды /start."""
    global chat_id
    chat_id = update.effective_chat.id
    
    user = update.effective_user
    update.message.reply_text(
        f'Привіт, {user.first_name}! Я бот для моніторингу органічного трафіку сайтів через Ahrefs API. '
        f'Я буду відправляти повідомлення про оновлення даних та зниження трафіку в цей чат.'
    )
    logger.info(f"Бот запущен пользователем {user.first_name} (ID: {user.id}). Chat ID: {chat_id}")
    
    # Сохраняем chat_id
    save_chat_id()
    # После сохранения перезагружаем список чатов
    load_chat_id()

def help_command(update: Update, context: CallbackContext) -> None:
    """Обработчик команды /help."""
    update.message.reply_text(
        'Доступні команди:\n'
        '/start - Запустити бота\n'
        '/help - Показати цю довідку\n'
        '/status - Перевірити статус бота\n'
    )

def status(update: Update, context: CallbackContext) -> None:
    """Обработчик команды /status."""
    load_chat_id()
    
    response = 'Бот активний і готовий до роботи.\n\n'
    response += f'Основной чат ID: {chat_id}\n'
    response += f'Всего чатов для отправки: {len(chat_ids)}\n'
    response += f'ID чатов: {", ".join([str(cid) for cid in chat_ids])}'
    
    update.message.reply_text(response)

def format_traffic_message(domain: str, traffic: int, previous_traffic: int = None) -> str:
    """
    Форматирует сообщение о трафике для домена.
    
    Args:
        domain (str): Домен
        traffic (int): Текущий трафик
        previous_traffic (int, optional): Предыдущее значение трафика
        
    Returns:
        str: Отформатированное сообщение
    """
    message = f"🌐 *{domain}*\n"
    message += f"📊 Трафик: {traffic:,}\n"
    
    if previous_traffic is not None and previous_traffic > 0:
        change = ((traffic - previous_traffic) / previous_traffic) * 100
        emoji = "📈" if change >= 0 else "📉"
        message += f"{emoji} Изменение: {change:+.1f}%\n"
        
    return message

def notify_traffic_update(domains_data, mode='production'):
    """
    Отправляет уведомление об обновлении данных о трафике.
    Условия отправки:
    1. Падение трафика более 5% в двух последних измерениях подряд
    2. Падение трафика более 11% при последнем съеме
    
    Значения трафика меньше 1000 считаются некорректными и игнорируются.
    
    Args:
        domains_data (dict): Словарь с данными о трафике по доменам
        mode (str): Режим работы ('production' или 'test')
    """
    logger.info("Загружен chat_id: %s", chat_id)
    
    # Формируем список доменов для уведомления
    domains_to_notify = []
    for domain, data in domains_data.items():
        history = data.get('history', [])
        if len(history) >= 2:  # Нужно минимум 2 записи для проверки
            # Получаем последние записи
            last_entries = sorted(history, key=lambda x: x['date'])
            
            # Получаем значения трафика
            traffic_current = last_entries[-1]['traffic']  # Последнее измерение
            traffic_previous = last_entries[-2]['traffic']  # Предыдущее измерение
            
            # Проверяем, что значения трафика корректные (больше 1000)
            if traffic_current < 1000 or traffic_previous < 1000:
                logger.info(f"Пропускаем домен {domain} из-за некорректных значений трафика: текущий={traffic_current}, предыдущий={traffic_previous}")
                continue
            
            # Вычисляем изменение для последнего съема
            last_change = ((traffic_current - traffic_previous) / traffic_previous) * 100
            
            should_notify = False
            previous_change = None
            
            # Проверяем условие падения на 11% при последнем съеме
            if last_change <= -11:
                should_notify = True
            
            # Проверяем условие двух последовательных падений по 5%
            elif len(history) >= 3:
                traffic_before_previous = last_entries[-3]['traffic']  # Измерение перед предыдущим
                
                # Проверяем, что предыдущее значение тоже корректное
                if traffic_before_previous >= 1000:
                    previous_change = ((traffic_previous - traffic_before_previous) / traffic_before_previous) * 100
                    
                    if previous_change <= -5 and last_change <= -5:
                        should_notify = True
            
            if mode == 'test' or should_notify:
                notify_data = {
                    'domain': domain,
                    'traffic': traffic_current,
                    'previous_traffic': traffic_previous,
                    'change': last_change,
                    'previous_change': previous_change if previous_change is not None else 0
                }
                domains_to_notify.append(notify_data)
    
    if not domains_to_notify:
        if mode == 'test':
            message = "🔄 Обновление данных о трафике\n\nНет доменов с критическим падением трафика (или значения трафика некорректны)."
            try:
                get_updater().bot.send_message(chat_id=chat_id, text=message)
            except Exception as e:
                logger.error("Ошибка при отправке сообщения в Telegram: %s", str(e))
        return
    
    # Сортируем домены по величине последнего падения (от большего к меньшему)
    domains_to_notify.sort(key=lambda x: x['change'])
    
    # Разбиваем домены на группы по 15 доменов
    chunk_size = 15
    domain_chunks = [domains_to_notify[i:i + chunk_size] for i in range(0, len(domains_to_notify), chunk_size)]
    
    # Отправляем сообщения по частям
    for i, chunk in enumerate(domain_chunks):
        if mode == 'test':
            message = "🔄 Обновление данных о трафике\n\n" if i == 0 else "🔄 Продолжение обновления данных о трафике\n\n"
        else:
            message = "⚠️ Обнаружено критическое падение трафика\n\n" if i == 0 else "⚠️ Продолжение отчета о падении трафика\n\n"
        
        for domain_data in chunk:
            domain = domain_data['domain']
            traffic = domain_data['traffic']
            change = domain_data['change']
            prev_change = domain_data['previous_change']
            
            # Формируем сообщение в зависимости от типа падения
            if change <= -11:
                message += f"{domain}: {traffic:,} (📉 {change:.1f}% - резкое падение)\n"
            else:
                message += f"{domain}: {traffic:,} (📉 {change:.1f}%, пред. {prev_change:.1f}%)\n"
        
        try:
            get_updater().bot.send_message(
                chat_id=chat_id,
                text=message,
                parse_mode='HTML'
            )
        except Exception as e:
            logger.error("Ошибка при отправке сообщения в Telegram: %s", str(e))
            # Пробуем отправить без форматирования
            try:
                get_updater().bot.send_message(chat_id=chat_id, text=message)
            except Exception as e:
                logger.error("Повторная ошибка при отправке сообщения в Telegram: %s", str(e))

def send_message_to_chats(message: str, parse_mode: str = None) -> bool:
    """
    Отправляет сообщение во все сохраненные чаты.
    
    Args:
        message (str): Текст сообщения
        parse_mode (str, optional): Режим форматирования текста
        
    Returns:
        bool: True, если сообщение отправлено хотя бы в один чат, иначе False
    """
    logger.info("Отправка сообщения во все чаты")
    
    if not TELEGRAM_BOT_TOKEN:
        logger.error("Токен Telegram бота не настроен")
        return False
    
    # Загружаем ID чатов
    load_chat_id()
    
    if not chat_ids:
        logger.error("Нет сохраненных чатов для отправки")
        return False
    
    logger.info(f"Найдено {len(chat_ids)} чатов для отправки")
    
    success = False
    for cid in chat_ids:
        try:
            logger.info(f"Отправка сообщения в чат {cid}")
            get_updater().bot.send_message(
                chat_id=cid,
                text=message,
                parse_mode=parse_mode
            )
            success = True
            logger.info(f"Сообщение успешно отправлено в чат {cid}")
        except Exception as e:
            logger.error(f"Ошибка при отправке сообщения в чат {cid}: {str(e)}")
            try:
                # Пробуем отправить без форматирования
                get_updater().bot.send_message(chat_id=cid, text=message)
                success = True
                logger.info(f"Сообщение успешно отправлено без форматирования в чат {cid}")
            except Exception as e2:
                logger.error(f"Повторная ошибка при отправке сообщения в чат {cid}: {str(e2)}")
    
    return success

def send_message(message: str, parse_mode: str = None) -> bool:
    """
    Отправляет сообщение в чат Telegram.
    Совместимость со старым кодом + отправка во все чаты.
    
    Args:
        message (str): Текст сообщения
        parse_mode (str, optional): Режим форматирования текста
        
    Returns:
        bool: True, если сообщение отправлено успешно, иначе False
    """
    logger.info("Начинаем отправку сообщения в Telegram")
    
    if not TELEGRAM_BOT_TOKEN:
        logger.error("Токен Telegram бота не настроен")
        return False
    
    logger.info(f"Токен бота найден, длина: {len(TELEGRAM_BOT_TOKEN)}")
    
    # Отправляем сообщение во все чаты
    return send_message_to_chats(message, parse_mode)

def run_bot():
    """Запускает Telegram бота."""
    if not TELEGRAM_BOT_TOKEN:
        logger.error("Токен Telegram бота не настроен")
        return
        
    try:
        # Загружаем сохраненный chat_id при запуске
        load_chat_id()
        
        updater = get_updater()
        dispatcher = updater.dispatcher
        
        # Регистрация обработчиков команд
        dispatcher.add_handler(CommandHandler("start", start))
        dispatcher.add_handler(CommandHandler("help", help_command))
        dispatcher.add_handler(CommandHandler("status", status))
        
        # Запуск бота
        updater.start_polling()
        logger.info("Telegram бот запущен")
        
        # Запуск бота до нажатия Ctrl+C
        updater.idle()
    except Exception as e:
        logger.error(f"Ошибка при запуске Telegram бота: {str(e)}")

if __name__ == "__main__":
    run_bot() 