import logging
import os
import json
import pandas as pd
import traceback
import sys
import platform
import subprocess

# Імпортуємо модуль-патч для підтримки застарілого AHREFS_API_TOKEN
try:
    import monkey_patch  # noqa
except ImportError:
    # Якщо модуль відсутній, просто продовжуємо роботу
    pass

from datetime import datetime, timedelta
from google.oauth2 import service_account
from googleapiclient.discovery import build
from telegram_bot import send_message
from ahrefs_api import get_organic_traffic, check_api_availability

# Встановлюємо перехоплювач невловлених виключень
def handle_uncaught_exception(exc_type, exc_value, exc_traceback):
    logger.critical("Невловлене виключення", exc_info=(exc_type, exc_value, exc_traceback))
    # Продовжуємо зі стандартною обробкою
    sys.__excepthook__(exc_type, exc_value, exc_traceback)

sys.excepthook = handle_uncaught_exception

# Настройка логирования
logging.basicConfig(
    level=logging.DEBUG,  # Змінено рівень на DEBUG для більше інформації
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Діагностична інформація про поточне середовище
logger.info(f"Python версія: {sys.version}")
logger.info(f"Поточна директорія: {os.getcwd()}")
logger.info(f"Список файлів в директорії: {', '.join(os.listdir('.')[:10])}...")

# Проверка наличия токенов
telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
ahrefs_token = os.getenv('AHREFS_API_KEY')
logger.info(f"Telegram token {'знайдений' if telegram_token else 'не знайдений'} в змінних середовища")
logger.info(f"Ahrefs token {'знайдений' if ahrefs_token else 'не знайдений'} в змінних середовища")

# ДЕБАГ: Виведемо всі змінні середовища (без конфіденційних даних)
for key, value in os.environ.items():
    if 'TOKEN' in key or 'KEY' in key or 'SECRET' in key or 'PASS' in key:
        logger.debug(f"Змінна середовища {key}: {'[знайдена]' if value else '[не знайдена]'}")
    else:
        logger.debug(f"Змінна середовища {key}: {value}")

try:
    logger.info(f"Перевіримо дійсність AHREFS_API_KEY: {ahrefs_token[:4]}... (довжина: {len(ahrefs_token)})")
except (TypeError, IndexError) as e:
    logger.error(f"Помилка при доступі до AHREFS_API_KEY: {str(e)}")

# Трасування виклику функції check_api_availability
logger.info("Викликаємо check_api_availability()...")
try:
    api_available = check_api_availability()
    logger.info(f"Результат check_api_availability(): {api_available}")
except Exception as e:
    logger.error(f"Помилка при перевірці доступності API: {str(e)}")
    logger.error(f"Traceback: {traceback.format_exc()}")

# Проверка доступности API Ahrefs
if not check_api_availability():
    error_message = "❌ API Ahrefs недоступне або невірний ключ API. Перевірте налаштування."
    logger.error(error_message)
    send_message(error_message, test_mode=True)
    raise ValueError(error_message)

def init_sheet(service, sheet_id):
    """
    Инициализирует Google Sheet данными из Excel файла
    """
    try:
        logger.info("Initializing Google Sheet")
        sheet = service.spreadsheets()
        
        # Чтение данных из Excel файла
        logger.info("Reading data from Excel file")
        try:
            df = pd.read_excel('traffic_data.xlsx')
            logger.info(f"Read {len(df)} rows from Excel file")
        except Exception as e:
            logger.error(f"Error reading Excel file: {str(e)}")
            raise
        
        # Подготовка данных для Google Sheets
        headers = [['Domain', 'Current Traffic', 'Previous Traffic', 'Date']]
        values = []
        
        current_date = datetime.now().strftime('%Y-%m-%d')
        
        # Используем данные из Excel
        for _, row in df.iterrows():
            try:
                domain = row['Domain']
                current_traffic = int(row['Traffic'])
                previous_traffic = int(row.get('Previous Traffic', current_traffic))  # Если нет предыдущего трафика, используем текущий
                
                values.append([
                    domain,
                    current_traffic,
                    previous_traffic,
                    current_date
                ])
            except Exception as e:
                logger.warning(f"Error processing row for domain {row.get('Domain', 'unknown')}: {str(e)}")
        
        logger.info(f"Prepared {len(values)} domains for upload")
        
        # Очистка старых данных
        try:
            sheet.values().clear(
                spreadsheetId=sheet_id,
                range='Traffic!A1:D1000',
            ).execute()
            logger.info("Cleared old data")
        except Exception as e:
            logger.error(f"Error clearing old data: {str(e)}")
            raise
        
        # Запись заголовков и данных
        all_values = headers + values
        body = {'values': all_values}
        
        result = sheet.values().update(
            spreadsheetId=sheet_id,
            range='Traffic!A1',
            valueInputOption='RAW',
            body=body
        ).execute()
        
        logger.info(f"Successfully initialized Google Sheet with {len(values)} domains: {result.get('updatedCells')} cells updated")
        
        # Отправляем уведомление в Telegram
        logger.info("Отправляем уведомление в Telegram об инициализации")
        message = f"✅ Таблиця успішно ініціалізована\nДодано доменів: {len(values)}"
        telegram_result = send_message(message)
        logger.info(f"Результат відправки в Telegram: {'успішно' if telegram_result else 'помилка'}")
        
        return True
    except Exception as e:
        logger.error(f"Error initializing Google Sheet: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        # Отправляем уведомление об ошибке в Telegram
        logger.info("Отправляем уведомлення про помилку в Telegram")
        error_message = f"❌ Помилка при ініціалізації таблиці:\n{str(e)}"
        telegram_result = send_message(error_message)
        logger.info(f"Результат відправки помилки в Telegram: {'успішно' if telegram_result else 'помилка'}")
        
        return False

def analyze_traffic_changes(domains_data):
    """
    Анализирует изменения трафика и формирует сообщение для Telegram.
    
    Args:
        domains_data (dict): Словарь с данными о трафике по доменам
        
    Returns:
        tuple: (есть ли критические изменения, текст сообщения)
    """
    critical_changes = []
    consecutive_drops = []
    triple_drops = []
    
    logger.info(f"Аналізуємо зміни трафіку для {len(domains_data)} доменів")
    
    for domain, data in domains_data.items():
        history = data.get('history', [])
        if len(history) >= 2:
            # Сортируем историю по дате
            sorted_history = sorted(history, key=lambda x: x['date'])
            
            current_traffic = sorted_history[-1]['traffic']  # Последний (самый новый)
            previous_traffic = sorted_history[-3]['traffic'] if len(sorted_history) >= 3 else sorted_history[0]['traffic']  # Двухнедельной давности
            
            # Логируем все изменения трафика для диагностики
            change_percent = ((current_traffic - previous_traffic) / previous_traffic) * 100 if previous_traffic > 0 else 0
            logger.info(f"Домен {domain}: поточний трафік {current_traffic}, попередній {previous_traffic}, зміна {change_percent:.1f}%")
            
            # Пропускаем домены с трафиком меньше 1000
            if current_traffic < 1000 or previous_traffic < 1000:
                logger.info(f"Пропускаємо домен {domain} через недостатній трафік")
                continue
            
            # Вычисляем изменение в процентах
            change = ((current_traffic - previous_traffic) / previous_traffic) * 100
            
            # Флаг для определения, нужно ли уведомлять
            should_notify = False
            previous_change = None
            triple_change = None
            
            # 1. Проверяем условие резкого падения на 11%
            if change <= -11:
                logger.info(f"Виявлено різке падіння для {domain}: {change:.1f}%")
                critical_changes.append({
                    'domain': domain,
                    'traffic': current_traffic,
                    'change': change,
                    'type': 'sharp'
                })
                should_notify = True
            
            # 2. Проверяем условие двух последовательных падений по 5%
            elif len(sorted_history) >= 3:
                traffic_before_previous = sorted_history[-3]['traffic']  # Измерение перед предыдущим
                if traffic_before_previous >= 1000:
                    previous_change = ((previous_traffic - traffic_before_previous) / traffic_before_previous) * 100
                    if previous_change <= -5 and change <= -5:
                        logger.info(f"Виявлено послідовне падіння для {domain}: поточне {change:.1f}%, попереднє {previous_change:.1f}%")
                        consecutive_drops.append({
                            'domain': domain,
                            'traffic': current_traffic,
                            'change': change,
                            'prev_change': previous_change
                        })
                        should_notify = True
            
            # 3. Условие: падение более 3% в трех последних измерениях подряд
            if len(sorted_history) >= 4 and not should_notify:
                traffic_3ago = sorted_history[-4]['traffic']
                if traffic_3ago >= 1000 and previous_change is not None:
                    change_2 = ((traffic_before_previous - traffic_3ago) / traffic_3ago) * 100
                    if change_2 <= -3 and previous_change <= -3 and change <= -3:
                        logger.info(f"Виявлено потрійне падіння для {domain}: {change_2:.1f}%, {previous_change:.1f}%, {change:.1f}%")
                        triple_drops.append({
                            'domain': domain,
                            'traffic': current_traffic,
                            'change': change,
                            'prev_change': previous_change,
                            'triple_change': change_2
                        })
                        should_notify = True
    
    # Текущая дата для отображения в сообщении
    current_date = datetime.now().strftime("%d.%m.%Y")
    
    # Формируем сообщение
    if not critical_changes and not consecutive_drops and not triple_drops:
        return False, f"✅ Критичних змін трафіку не виявлено\n\n📆 Дані порівнюються з показниками двотижневої давнини\n📅 Дата звіту: {current_date}"
    
    message = "⚠️ Виявлено падіння трафіку:\n\n"
    
    # Сначала выводим резкие падения
    if critical_changes:
        message += "📉 Різке падіння:\n"
        for change in sorted(critical_changes, key=lambda x: x['change']):
            message += f"{change['domain']}: {change['traffic']:,} (падіння {abs(change['change']):.1f}% порівняно з двотижневою давниною)\n"
        message += "\n"
    
    # Затем выводим последовательные падения
    if consecutive_drops:
        message += "📉 Послідовне падіння:\n"
        for drop in sorted(consecutive_drops, key=lambda x: x['change']):
            message += f"{drop['domain']}: {drop['traffic']:,} (падіння {abs(drop['change']):.1f}% порівняно з двотижневою давниною, попер. падіння {abs(drop['prev_change']):.1f}%)\n"
        message += "\n"
    
    # Тройные падения
    if triple_drops:
        message += "📉 Потрійне падіння:\n"
        for drop in sorted(triple_drops, key=lambda x: x['change']):
            message += f"{drop['domain']}: {drop['traffic']:,} (три поспіль падіння: {abs(drop['triple_change']):.1f}%, {abs(drop['prev_change']):.1f}%, {abs(drop['change']):.1f}%)\n"
        message += "\n"
    
    # Добавляем пояснение и дату
    message += f"📌 Всі показники порівнюються з даними двотижневої давнини\n📅 Дата звіту: {current_date}"
    
    return True, message

def run_test():
    """
    Основная функция, которая выполняет проверку и обновление данных
    """
    try:
        logger.info("=== Початок функції run_test() ===")
        
        # Логуємо системну інформацію
        log_system_info()
        
        # Перевіряємо мережеве з'єднання
        logger.info("Перевірка мережевого з'єднання до API...")
        run_command("ping -c 2 api.ahrefs.com" if platform.system() != "Windows" else "ping -n 2 api.ahrefs.com")
        
        # Проверяем наличие токена
        api_key = os.getenv('AHREFS_API_KEY')
        if not api_key:
            logger.error("AHREFS_API_KEY не знайдений в змінних середовища")
            try:
                if send_message("❌ Помилка: AHREFS_API_KEY не знайдений в змінних середовища", test_mode=True):
                    logger.info("Повідомлення про помилку відправлено в Telegram")
            except Exception as e:
                logger.error(f"Помилка при відправці повідомлення: {str(e)}")
            return False
        
        logger.info(f"У функції run_test() AHREFS_API_KEY знайдений, довжина: {len(api_key)}")
        
        # Загружаем данные из Google Sheets
        logger.info("Запуск тестового режима")
        
        # Настройка доступа к Google Sheets (используем ID из указанной таблицы)
        sheet_id = '1iwr3qku-JcMMqEBTYdWeWRUXfmC9sLp_s-q-Ruxj5xs'
        logger.info(f"Sheet ID: {sheet_id}")
        
        # Настройка учетных данных для Google Sheets API
        try:
            logger.info("Setting up credentials")
            creds_json = os.getenv('GOOGLE_SHEETS_CREDENTIALS')
            if not creds_json:
                logger.error("GOOGLE_SHEETS_CREDENTIALS not found in environment variables")
                raise ValueError("GOOGLE_SHEETS_CREDENTIALS not found in environment variables")
            
            try:
                creds_dict = json.loads(creds_json)
                logger.info("Successfully parsed credentials JSON")
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse credentials JSON: {str(e)}")
                raise
            
            creds = service_account.Credentials.from_service_account_info(
                creds_dict,
                scopes=['https://www.googleapis.com/auth/spreadsheets']
            )
            logger.info("Credentials setup successfully")
        except Exception as e:
            logger.error(f"Error setting up credentials: {str(e)}")
            raise
        
        # Создание сервиса Google Sheets
        service = build('sheets', 'v4', credentials=creds)
        sheet = service.spreadsheets()
        
        # Проверяем наличие данных в таблице
        result = sheet.values().get(
            spreadsheetId=sheet_id,
            range='Traffic!A1:ZZ'  # Расширяем диапазон для чтения всей истории
        ).execute()
        
        values = result.get('values', [])
        current_date = datetime.now().strftime('%Y-%m-%d')
        
        if not values:
            # Если таблица пустая, создаем новую с заголовками
            logger.info("No data found in sheet, initializing with headers")
            headers = [['Domain', current_date]]
            sheet.values().update(
                spreadsheetId=sheet_id,
                range='Traffic!A1',
                valueInputOption='RAW',
                body={'values': headers}
            ).execute()
            values = headers
        
        # Получаем список доменов из файла
        try:
            with open('domains.txt', 'r', encoding='utf-8') as f:
                domains = [line.strip() for line in f if line.strip()]
            logger.info(f"Загружено {len(domains)} доменів з файла")
        except Exception as e:
            logger.error(f"Помилка при читанні файла domains.txt: {str(e)}")
            raise

        # Проверяем, есть ли уже данные за сегодня
        headers = values[0] if values else []
        if len(headers) > 1 and headers[1] == current_date:
            logger.info(f"Дані вже оновлені сьогодні ({current_date}). Перевіряємо зміни трафіку.")
            
            # Анализируем изменения трафика
            domains_data = {}
            for row in values[1:]:  # Пропускаем заголовки
                if len(row) >= 2:
                    domain = row[0]
                    history = []
                    
                    # Собираем историю трафика
                    for i in range(1, len(row)):
                        if i < len(headers):  # Проверяем, что у нас есть соответствующая дата в заголовках
                            try:
                                traffic = int(row[i])
                                history.append({
                                    'date': headers[i],
                                    'traffic': traffic
                                })
                            except (ValueError, TypeError):
                                continue
                    
                    if history:
                        domains_data[domain] = {
                            'traffic': history[-1]['traffic'],
                            'history': history
                        }
            
                    # Анализируем изменения и отправляем уведомление
        has_changes, message = analyze_traffic_changes(domains_data)
        
        # Додаємо інформацію про кількість доменів
        message = f"✅ Дані про трафік успішно оновлено для {len(domains_data)} доменів\n\n" + message
        
        # Відправляємо повідомлення у всі чати (test_mode=False означає відправка у всі чати, включаючи робочі)
        telegram_result = send_message(message, parse_mode="HTML", test_mode=False)
        logger.info(f"Результат відправки в Telegram: {'успішно' if telegram_result else 'помилка'}")
        
        # Додаткове логування для діагностики
        if not telegram_result:
            logger.error("Повідомлення не було відправлено в жоден чат! Перевірте налаштування Telegram.")
        else:
            logger.info("Повідомлення успішно відправлено в Telegram чати.")
            
            return True
        
        # Если данных за сегодня нет, добавляем новый столбец
        logger.info(f"Додаємо дані за {current_date}")
        
        # Создаем словарь с текущими данными по доменам
        existing_domains = {row[0]: row[1:] for row in values[1:]} if len(values) > 1 else {}
        
        # Подготавливаем новые данные
        new_values = [['Domain', current_date] + headers[1:] if headers else ['Domain', current_date]]
        
        # Обрабатываем каждый домен
        for domain in domains:
            # Получаем текущий трафик из Ahrefs
            logger.info(f"Запрашиваем дані для домена: {domain}")
            current_traffic = get_organic_traffic(domain)
            logger.info(f"Домен {domain}: трафік = {current_traffic}")
            
            domain_row = [domain, str(current_traffic)]
            
            # Добавляем исторические данные
            if domain in existing_domains:
                domain_row.extend(existing_domains[domain])
            
            new_values.append(domain_row)
        
        # Очищаем весь лист і записываем новые данные
        sheet.values().clear(
            spreadsheetId=sheet_id,
            range='Traffic!A1:ZZ'
        ).execute()
        
        result = sheet.values().update(
            spreadsheetId=sheet_id,
            range='Traffic!A1',
            valueInputOption='RAW',
            body={'values': new_values}
        ).execute()
        
        logger.info(f"Дані успішно збережені в Google Sheets: {result.get('updatedCells')} ячеек оновлено")
        
        # Анализируем изменения трафика
        domains_data = {}
        for row in new_values[1:]:  # Пропускаем заголовки
            if len(row) >= 2:
                domain = row[0]
                history = []
                
                # Собираем историю трафика
                for i in range(1, len(row)):
                    if i < len(new_values[0]):  # Проверяем, что у нас есть соответствующая дата в заголовках
                        try:
                            traffic = int(row[i])
                            history.append({
                                'date': new_values[0][i],
                                'traffic': traffic
                            })
                        except (ValueError, TypeError):
                            continue
                
                if history:
                    domains_data[domain] = {
                        'traffic': history[0]['traffic'],  # Текущий трафик теперь первый в истории
                        'history': history
                    }
        
        # Анализируем изменения трафика
        has_changes, traffic_message = analyze_traffic_changes(domains_data)
        
        # Додаємо до traffic_message інформацію про кількість оновлених доменів
        traffic_message = f"✅ Дані про трафік успішно оновлено для {len(domains)} доменів\n\n" + traffic_message
        
        # Отправляем результаты анализа в Telegram (test_mode=False означає відправка у всі чати, включаючи робочі)
        telegram_result = send_message(traffic_message, parse_mode="HTML", test_mode=False)
        if telegram_result:
            logger.info("Повідомлення про зміни трафіку відправлено в Telegram")
        else:
            logger.error("Повідомлення про зміни трафіку НЕ БУЛО відправлено в Telegram! Перевірте налаштування.")
        
        return True
    
    except Exception as e:
        logger.error(f"Помилка при виконанні тесту: {str(e)}")
        import traceback
        error_details = traceback.format_exc()
        logger.error(error_details)
        
        # Отправляем сообщение об ошибке в Telegram
        message = f"❌ Помилка: {str(e)}\n\n```\n{error_details[:1900]}```"
        if send_message(message, parse_mode="Markdown", test_mode=True):
            logger.info("Повідомлення про помилку відправлено в Telegram")
            
        return False

def log_system_info():
    """Логування інформації про систему"""
    logger.info(f"Python версія: {sys.version}")
    logger.info(f"Операційна система: {platform.system()} {platform.version()}")
    logger.info(f"Поточна директорія: {os.getcwd()}")
    
    # Список файлів у директорії
    files = os.listdir('.')
    logger.info(f"Список файлів в директорії: {', '.join(files[:10])}..." if len(files) > 10 else f"Список файлів в директорії: {', '.join(files)}")
    
    # Значення змінних середовища
    env_vars = ['TELEGRAM_BOT_TOKEN', 'AHREFS_API_KEY', 'SHEET_ID', 'GOOGLE_SHEETS_CREDENTIALS']
    for var in env_vars:
        value = os.getenv(var)
        if value and var != 'GOOGLE_SHEETS_CREDENTIALS':
            # Маскуємо токени для безпеки
            masked_value = value[:4] + '...' + value[-4:] if len(value) > 8 else '****'
            logger.info(f"{var} {'знайдений' if value else 'не знайдений'} в змінних середовища")
        elif var == 'GOOGLE_SHEETS_CREDENTIALS':
            logger.info(f"{var} {'знайдений' if value else 'не знайдений'} в змінних середовища")
        else:
            logger.info(f"{var} не знайдений в змінних середовища")

def run_command(command):
    """Виконує команду в консолі та повертає результат"""
    try:
        logger.info(f"Виконуємо команду: {command}")
        result = subprocess.run(command, shell=True, capture_output=True, text=True, check=False)
        logger.info(f"Код виходу: {result.returncode}")
        if result.stdout:
            logger.info(f"Вивід: {result.stdout[:200]}..." if len(result.stdout) > 200 else f"Вивід: {result.stdout}")
        if result.stderr:
            logger.warning(f"Помилка: {result.stderr[:200]}..." if len(result.stderr) > 200 else f"Помилка: {result.stderr}")
        return result
    except Exception as e:
        logger.error(f"Помилка при виконанні команди: {str(e)}")
        return None

if __name__ == "__main__":
    success = run_test()
    if not success:
        logger.error("Тест завершився з помилкою")
        exit(1) 