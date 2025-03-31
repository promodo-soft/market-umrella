import logging
import os
import json
import pandas as pd
from datetime import datetime, timedelta
from google.oauth2 import service_account
from googleapiclient.discovery import build
from telegram_bot import send_message
from ahrefs_api import get_organic_traffic, check_api_availability

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Проверка наличия токенов
telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
ahrefs_token = os.getenv('AHREFS_API_KEY')
logger.info(f"Telegram token {'знайдений' if telegram_token else 'не знайдений'} в змінних середовища")
logger.info(f"Ahrefs token {'знайдений' if ahrefs_token else 'не знайдений'} в змінних середовища")

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
        tuple: (bool, str) - (есть ли критические изменения, текст сообщения)
    """
    critical_changes = []
    consecutive_drops = []
    
    logger.info(f"Аналізуємо зміни трафіку для {len(domains_data)} доменів")
    
    for domain, data in domains_data.items():
        history = data.get('history', [])
        if len(history) >= 2:
            current_traffic = history[0]['traffic']  # Текущий трафик теперь первый в истории
            previous_traffic = history[1]['traffic']  # Предыдущий - второй
            
            # Логируем все изменения трафика для диагностики
            change_percent = ((current_traffic - previous_traffic) / previous_traffic) * 100 if previous_traffic > 0 else 0
            logger.info(f"Домен {domain}: поточний трафік {current_traffic}, попередній {previous_traffic}, зміна {change_percent:.1f}%")
            
            # Пропускаем домены с трафиком меньше 1000
            if current_traffic < 1000 or previous_traffic < 1000:
                logger.info(f"Пропускаємо домен {domain} через недостатній трафік")
                continue
            
            # Вычисляем изменение в процентах
            change = ((current_traffic - previous_traffic) / previous_traffic) * 100
            
            # Проверяем условия падения трафика
            if change <= -11:  # Резкое падение более 11%
                logger.info(f"Виявлено різке падіння для {domain}: {change:.1f}%")
                critical_changes.append({
                    'domain': domain,
                    'traffic': current_traffic,
                    'change': change,
                    'type': 'sharp'
                })
            elif len(history) >= 3:  # Проверяем два последовательных падения
                traffic_before_previous = history[2]['traffic']  # Третий в истории
                if traffic_before_previous >= 1000:
                    previous_change = ((previous_traffic - traffic_before_previous) / traffic_before_previous) * 100
                    if previous_change <= -5 and change <= -5:  # Два последовательных падения по 5%
                        logger.info(f"Виявлено послідовне падіння для {domain}: поточне {change:.1f}%, попереднє {previous_change:.1f}%")
                        consecutive_drops.append({
                            'domain': domain,
                            'traffic': current_traffic,
                            'change': change,
                            'prev_change': previous_change
                        })
    
    # Логирование результатов
    logger.info(f"Виявлено різких падінь: {len(critical_changes)}")
    logger.info(f"Виявлено послідовних падінь: {len(consecutive_drops)}")
    
    # Формируем сообщение
    if not critical_changes and not consecutive_drops:
        return False, "✅ Критичних змін трафіку не виявлено"
    
    message = "⚠️ Виявлено падіння трафіку:\n\n"
    
    # Сначала выводим резкие падения
    if critical_changes:
        message += "📉 Різке падіння:\n"
        for change in sorted(critical_changes, key=lambda x: x['change']):
            message += f"{change['domain']}: {change['traffic']:,} (падіння {abs(change['change']):.1f}%)\n"
        message += "\n"
    
    # Затем выводим последовательные падения
    if consecutive_drops:
        message += "📉 Послідовне падіння:\n"
        for drop in sorted(consecutive_drops, key=lambda x: x['change']):
            message += f"{drop['domain']}: {drop['traffic']:,} (падіння {abs(drop['change']):.1f}%, попер. {abs(drop['prev_change']):.1f}%)\n"
    
    return True, message

def run_test():
    """
    Основная функция, которая выполняет проверку и обновление данных
    """
    try:
        # Проверяем наличие токена
        if not os.getenv('AHREFS_API_KEY'):
            logger.error("AHREFS_API_KEY не знайдений в змінних середовища")
            if send_message("❌ Помилка: AHREFS_API_KEY не знайдений в змінних середовища", test_mode=True):
                logger.info("Повідомлення про помилку відправлено в Telegram")
            return False
        
        # Загружаем данные из Google Sheets
        logger.info("Запуск тестового режима")
        
        # Настройка доступа к Google Sheets
        sheet_id = os.getenv('SHEET_ID')
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
            telegram_result = send_message(message)
            logger.info(f"Результат відправки в Telegram: {'успішно' if telegram_result else 'помилка'}")
            
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
        
        # Отправляем сообщение в Telegram
        message = f"✅ Дані про трафік успішно оновлено для {len(domains)} доменів."
        if send_message(message, test_mode=True):
            logger.info("Повідомлення про успішне оновлення відправлено в Telegram")
            
        # Анализируем изменения трафика
        has_changes, traffic_message = analyze_traffic_changes(domains_data)
        if has_changes:
            # Отправляем результаты анализа в Telegram
            if send_message(traffic_message, parse_mode="HTML", test_mode=False):  # Важные уведомления отправляем во все чаты
                logger.info("Повідомлення про зміни трафіку відправлено в Telegram")
        
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

if __name__ == "__main__":
    success = run_test()
    if not success:
        logger.error("Тест завершився з помилкою")
        exit(1) 