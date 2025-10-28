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

# ID чатов, куда не следует отправлять тестовые сообщения
PRODUCTION_CHAT_IDS = ["-1001930136015", "-387031049", "-1001177341323"]  # Три робочих чати: SEO & CSD, Promodo Sales & SEO та Promodo SEO
# Тестовий чат "Кря_Team - Dream Team🤗" з ID -600437720 буде отримувати всі повідомлення

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
                    logger.info(f"Загружен основний chat_id: {chat_id}")
                    
        # Загружаем все чаты из файла
        if os.path.exists(CHATS_FILE):
            with open(CHATS_FILE, 'r') as f:
                chats_data = json.load(f)
                chat_ids = []
                
                for cid_str, name in chats_data.items():
                    try:
                        # Корректно обрабатываем отрицательные ID групп
                        cid = int(cid_str)
                        chat_ids.append(cid)
                        logger.info(f"Загружен chat_id: {cid} ({name})")
                    except ValueError:
                        logger.error(f"Некорректний chat_id в файлі: {cid_str}")
                
                logger.info(f"Загружено {len(chat_ids)} чатів")
            
        # Удаляем дубликаты
        chat_ids = list(set(chat_ids))
        
        logger.info(f"Всього унікальних чатів: {len(chat_ids)}")
            
    except Exception as e:
        logger.error(f"Ошибка при загрузці chat_id: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")

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
            
        # Добавляем новый чат з названням 'Новий чат'
        chats_data[str(chat_id)] = "Новий чат"
        
        # Сохраняем обновленный список чатов
        with open(CHATS_FILE, 'w') as f:
            json.dump(chats_data, f, indent=2)
            
    except Exception as e:
        logger.error(f"Ошибка при сохранении chat_id: {str(e)}")

def start(update: Update, context: CallbackContext) -> None:
    """Обработчик команды /start."""
    global chat_id
    chat_id = update.effective_chat.id
    chat_type = update.effective_chat.type
    
    user = update.effective_user
    
    # Разные приветствия для личных чатов и групп
    if chat_type == 'private':
        greeting = f'Привіт, {user.first_name}! Я бот для моніторингу органічного трафіку сайтів через Ahrefs API. '
        greeting += f'Я буду відправляти повідомлення про оновлення даних та зниження трафіку в цей чат.'
    else:
        chat_name = update.effective_chat.title
        greeting = f'Привіт! Я бот для моніторингу органічного трафіку сайтів через Ahrefs API. '
        greeting += f'Я буду відправляти повідомлення про оновлення даних та зниження трафіку в цей чат "{chat_name}".'
    
    update.message.reply_text(greeting)
    
    logger.info(f"Бот запущен в чаті {chat_id} (тип: {chat_type}). Пользователь: {user.first_name} (ID: {user.id})")
    
    # Сохраняем chat_id
    save_chat_id()
    # После сохранения перезагружаем список чатов
    load_chat_id()
    
    # Отправляем тестовое сообщение для проверки
    try:
        test_message = "✅ Бот успішно активовано в цьому чаті. Тепер ви будете отримувати сповіщення про зміни трафіку."
        get_updater().bot.send_message(chat_id=chat_id, text=test_message)
        logger.info(f"Тестовое сообщение успешно отправлено в чат {chat_id}")
    except Exception as e:
        logger.error(f"Ошибка при отправке тестового сообщения в чат {chat_id}: {str(e)}")

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
    response += f'Основний чат ID: {chat_id}\n'
    response += f'Всього чатів для відправки: {len(chat_ids)}\n'
    response += f'ID чатів: {", ".join([str(cid) for cid in chat_ids])}'
    
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
    message += f"📊 Трафік: {traffic:,}\n"
    
    if previous_traffic is not None and previous_traffic > 0:
        change = ((traffic - previous_traffic) / previous_traffic) * 100
        emoji = "📈" if change >= 0 else "📉"
        message += f"{emoji} Зміна: {change:+.1f}%\n"
        
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
    
    # Формируем список доменів для уведомлення
    domains_to_notify = []
    for domain, data in domains_data.items():
        history = data.get('history', [])
        if len(history) >= 2:
            last_entries = sorted(history, key=lambda x: x['date'])
            # Теперь сравниваем с датой двухнедельной давности
            traffic_current = last_entries[-1]['traffic']
            traffic_previous = last_entries[-3]['traffic'] if len(last_entries) >= 3 else last_entries[0]['traffic']
            
            # Проверяем, что значения трафика корректные (больше 1000)
            if traffic_current < 1000 or traffic_previous < 1000:
                logger.info(f"Пропускаем домен {domain} з-за некоректних значень трафика: текучий={traffic_current}, попередній={traffic_previous}")
                continue
            
            # Вычисляем изменение для последнего съема
            last_change = ((traffic_current - traffic_previous) / traffic_previous) * 100
            
            should_notify = False
            previous_change = None
            triple_change = None
            
            # Проверяем условие падения на 16% при последнем съеме
            if last_change <= -16:
                should_notify = True

            # Проверяем условие двух последовательных падений по 11%
            if len(history) >= 3:
                traffic_before_previous = last_entries[-3]['traffic']  # Измерение перед предыдущим
                if traffic_before_previous >= 1000:
                    previous_change = ((traffic_previous - traffic_before_previous) / traffic_before_previous) * 100
                    if previous_change <= -11 and last_change <= -11:
                        should_notify = True

            # Новое условие: падение более 6% в трех последних измерениях подряд
            if len(history) >= 4:
                traffic_3ago = last_entries[-4]['traffic']
                if traffic_3ago >= 1000:
                    change_2 = ((traffic_before_previous - traffic_3ago) / traffic_3ago) * 100
                    if change_2 <= -6 and previous_change is not None and previous_change <= -6 and last_change <= -6:
                        should_notify = True
                        triple_change = change_2
            

            
            if mode == 'test' or should_notify:
                notify_data = {
                    'domain': domain,
                    'traffic': traffic_current,
                    'previous_traffic': traffic_previous,
                    'change': last_change,
                    'previous_change': previous_change if previous_change is not None else 0,
                    'triple_change': triple_change if triple_change is not None else 0
                }
                domains_to_notify.append(notify_data)
    
    if not domains_to_notify:
        if mode == 'test':
            message = "🔄 Оновлення даних про трафік\n\nНемає доменів з критичним падінням трафіку (або значення трафіку некоректні)."
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
            message = "🔄 Оновлення даних про трафік\n\n" if i == 0 else "🔄 Продовження оновлення даних про трафік\n\n"
        else:
            message = "⚠️ Виявлено критичне падіння трафіку\n\n" if i == 0 else "⚠️ Продовження звіту про падіння трафіку\n\n"
        
        for domain_data in chunk:
            domain = domain_data['domain']
            traffic = domain_data['traffic']
            change = domain_data['change']
            prev_change = domain_data['previous_change']
            triple_change = domain_data.get('triple_change', 0)


            # Формируем сообщение в зависимости от типа падения
            if change <= -16:
                message += f"{domain}: {traffic:,} (📉 {change:.1f}% - різке падіння)\n"
            elif prev_change <= -11 and change <= -11:
                message += f"{domain}: {traffic:,} (📉 {change:.1f}%, попер. {prev_change:.1f}%)\n"
            elif triple_change != 0 and triple_change <= -6 and prev_change <= -6 and change <= -6:
                message += f"{domain}: {traffic:,} (📉 {change:.1f}%, три поспіль падіння: {triple_change:.1f}%, {prev_change:.1f}%, {change:.1f}%)\n"
            else:
                message += f"{domain}: {traffic:,} (�� {change:.1f}%)\n"
        
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

def send_message_to_chats(message: str, parse_mode: str = None, test_mode: bool = False) -> bool:
    """
    Отправляет сообщение во все сохраненные чаты.
    
    Args:
        message (str): Текст сообщения
        parse_mode (str, optional): Режим форматирования текста
        test_mode (bool): Если True, исключает отправку в рабочие чаты
        
    Returns:
        bool: True, если сообщение отправлено хотя бы в один чат, иначе False
    """
    logger.info(f"Відправка повідомлення у всі чати (test_mode={test_mode})")
    
    if not TELEGRAM_BOT_TOKEN:
        logger.error("Токен Telegram бота не налаштований")
        return False
    
    # Загружаем ID чатов
    load_chat_id()
    
    if not chat_ids:
        logger.error("Немає збережених чатів для відправки")
        return False
    
    logger.info(f"Знайдено {len(chat_ids)} чатів у файлі telegram_chats.json")
    
    # Фильтруем чаты в зависимости от режима
    target_chat_ids = []
    logger.info(f"Робочі чати (PRODUCTION_CHAT_IDS): {PRODUCTION_CHAT_IDS}")
    
    for cid in chat_ids:
        cid_str = str(cid)
        # В тестовом режиме пропускаем рабочие чаты
        if test_mode and cid_str in PRODUCTION_CHAT_IDS:
            logger.info(f"Пропускаємо робочий чат {cid} в тестовому режимі")
            continue
        
        # Логируем какой чат добавляем
        is_production = cid_str in PRODUCTION_CHAT_IDS
        logger.info(f"Додаємо чат {cid} для відправки ({'робочий' if is_production else 'тестовий'})")
        target_chat_ids.append(cid)
    
    logger.info(f"Знайдено {len(target_chat_ids)} з {len(chat_ids)} чатів для відправки")
    
    success = False
    
    # Розбиваємо довге повідомлення на частини (макс 4000 символів для безпеки)
    max_length = 4000
    message_parts = []
    
    if len(message) <= max_length:
        message_parts = [message]
    else:
        # Розбиваємо повідомлення по рядках
        lines = message.split('\n')
        current_part = ""
        
        for line in lines:
            if len(current_part + line + '\n') <= max_length:
                current_part += line + '\n'
            else:
                if current_part:
                    message_parts.append(current_part.rstrip())
                    current_part = line + '\n'
                else:
                    # Якщо один рядок довший за максимум, розбиваємо його
                    while len(line) > max_length:
                        message_parts.append(line[:max_length])
                        line = line[max_length:]
                    current_part = line + '\n'
        
        if current_part:
            message_parts.append(current_part.rstrip())
    
    logger.info(f"Повідомлення розбито на {len(message_parts)} частин")
    
    for cid in target_chat_ids:
        chat_success = False
        for i, part in enumerate(message_parts):
            try:
                # Додаємо номер частини якщо їх більше одної
                final_message = part
                if len(message_parts) > 1:
                    final_message = f"📄 Частина {i+1}/{len(message_parts)}\n\n{part}"
                
                logger.info(f"Відправка повідомлення в чат {cid} (частина {i+1}/{len(message_parts)})")
                get_updater().bot.send_message(
                    chat_id=cid,
                    text=final_message,
                    parse_mode=parse_mode
                )
                chat_success = True
                logger.info(f"Частина {i+1}/{len(message_parts)} успішно відправлена в чат {cid}")
            except Exception as e:
                logger.error(f"Помилка при відправці частини {i+1} в чат {cid}: {str(e)}")
                try:
                    # Пробуем отправить без форматирования
                    get_updater().bot.send_message(chat_id=cid, text=final_message)
                    chat_success = True
                    logger.info(f"Частина {i+1} успішно відправлена без форматування в чат {cid}")
                except Exception as e2:
                    logger.error(f"Повторна помилка при відправці частини {i+1} в чат {cid}: {str(e2)}")
        
        if chat_success:
            success = True
    
    return success

def send_message_to_specific_chats(message: str, target_chat_ids: List[str], parse_mode: str = None) -> bool:
    """
    Отправляет сообщение в указанные чаты.
    
    Args:
        message (str): Текст сообщения
        target_chat_ids (List[str]): Список ID чатов для отправки
        parse_mode (str, optional): Режим форматирования текста
        
    Returns:
        bool: True, если сообщение отправлено хотя бы в один чат, иначе False
    """
    logger.info(f"Відправка повідомлення в конкретні чати: {target_chat_ids}")
    
    if not TELEGRAM_BOT_TOKEN:
        logger.error("Токен Telegram бота не налаштований")
        return False
    
    success = False
    
    # Розбиваємо довге повідомлення на частини (макс 4000 символов для безпеки)
    max_length = 4000
    message_parts = []
    
    if len(message) <= max_length:
        message_parts = [message]
    else:
        # Розбиваємо повідомлення по рядках
        lines = message.split('\n')
        current_part = ""
        
        for line in lines:
            if len(current_part + line + '\n') <= max_length:
                current_part += line + '\n'
            else:
                if current_part:
                    message_parts.append(current_part.rstrip())
                    current_part = line + '\n'
                else:
                    # Якщо один рядок довший за максимум, розбиваємо його
                    while len(line) > max_length:
                        message_parts.append(line[:max_length])
                        line = line[max_length:]
                    current_part = line + '\n'
        
        if current_part:
            message_parts.append(current_part.rstrip())
    
    logger.info(f"Повідомлення розбито на {len(message_parts)} частин")
    
    for chat_id in target_chat_ids:
        chat_success = False
        for i, part in enumerate(message_parts):
            try:
                # Додаємо номер частини якщо їх більше одної
                final_message = part
                if len(message_parts) > 1:
                    final_message = f"📄 Частина {i+1}/{len(message_parts)}\n\n{part}"
                
                logger.info(f"Відправка повідомлення в чат {chat_id} (частина {i+1}/{len(message_parts)})")
                get_updater().bot.send_message(
                    chat_id=int(chat_id),
                    text=final_message,
                    parse_mode=parse_mode
                )
                chat_success = True
                logger.info(f"Частина {i+1}/{len(message_parts)} успішно відправлена в чат {chat_id}")
            except Exception as e:
                logger.error(f"Помилка при відправці частини {i+1} в чат {chat_id}: {str(e)}")
                try:
                    # Пробуем отправить без форматирования
                    get_updater().bot.send_message(chat_id=int(chat_id), text=final_message)
                    chat_success = True
                    logger.info(f"Частина {i+1} успішно відправлена без форматування в чат {chat_id}")
                except Exception as e2:
                    logger.error(f"Повторна помилка при відправці частини {i+1} в чат {chat_id}: {str(e2)}")
        
        if chat_success:
            success = True
    
    return success

def send_message(message: str, parse_mode: str = None, test_mode: bool = False, target_chat_ids: List[str] = None) -> bool:
    """
    Отправляет сообщение в чат Telegram.
    Совместимость со старым кодом + отправка во все чаты.
    
    Args:
        message (str): Текст сообщения
        parse_mode (str, optional): Режим форматирования текста
        test_mode (bool): Если True, исключает отправку в рабочие чаты
        target_chat_ids (List[str], optional): Список конкретных чатов для отправки
        
    Returns:
        bool: True, если сообщение отправлено успешно, иначе False
    """
    logger.info("Починаємо відправку повідомлення в Telegram")
    
    if not TELEGRAM_BOT_TOKEN:
        logger.error("Токен Telegram бота не налаштований")
        return False
    
    logger.info(f"Токен бота знайдений, довжина: {len(TELEGRAM_BOT_TOKEN)}")
    
    # Если указаны конкретные чаты, отправляем только в них
    if target_chat_ids:
        return send_message_to_specific_chats(message, target_chat_ids, parse_mode)
    
    # Отправляем сообщение во все чаты
    return send_message_to_chats(message, parse_mode, test_mode)

def run_bot():
    """Запускает Telegram бота."""
    if not TELEGRAM_BOT_TOKEN:
        logger.error("Токен Telegram бота не налаштований")
        return
        
    try:
        # Загружаем сохраненный chat_id при запуске
        load_chat_id()
        
        updater = get_updater()
        dispatcher = updater.dispatcher
        
        # Регистрация обработчиков команд
        # Регистрируем обработчики команд с фильтрами для работы и в личных чатах, и в группах
        dispatcher.add_handler(CommandHandler("start", start, filters=Filters.chat_type.private | Filters.chat_type.groups))
        dispatcher.add_handler(CommandHandler("help", help_command, filters=Filters.chat_type.private | Filters.chat_type.groups))
        dispatcher.add_handler(CommandHandler("status", status, filters=Filters.chat_type.private | Filters.chat_type.groups))
        
        # Логируем начало работы
        logger.info("Telegram бот запущен і готов обробляти команди в особистих і групових чатах")
        
        # Запуск бота
        updater.start_polling()
        
        # Запуск бота до нажатия Ctrl+C
        updater.idle()
    except Exception as e:
        logger.error(f"Помилка при запуску Telegram бота: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")

if __name__ == "__main__":
    run_bot() 