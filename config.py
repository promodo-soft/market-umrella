import os
from dotenv import load_dotenv
import pytz

# Загрузка переменных окружения из .env файла
load_dotenv()

# Ahrefs API
AHREFS_API_KEY = os.getenv('AHREFS_API_KEY', 'CxSe8somAMpahxIBAcX0vEv-AQsWbl_fqrcJbfIp')
AHREFS_API_URL = 'https://api.ahrefs.com'  # Базовый URL без версии API

# Telegram Bot
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '7893839978:AAGGMxnFq3idN_JGn-D2808eGeLMHJCIeAs')

# Файлы
DOMAINS_FILE = 'domains.txt'
DATA_FILE = 'traffic_data.xlsx'

# Расписание
SCHEDULE_DAY = os.getenv('SCHEDULE_DAY', 'sunday')  # monday, tuesday, wednesday, thursday, friday, saturday, sunday
SCHEDULE_TIME = os.getenv('SCHEDULE_TIME', '03:00')  # HH:MM в 24-часовом формате
TIMEZONE = pytz.timezone('Europe/Kiev')  # GMT+2

# Пороговое значение для оповещений (в процентах)
TRAFFIC_DECREASE_THRESHOLD = 10

# Режимы работы
class Mode:
    PRODUCTION = 'production'  # Штатный режим
    TEST = 'test'  # Тестовый режим
    MESSAGE_ONLY = 'message_only' 