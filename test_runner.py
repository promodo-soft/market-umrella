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
logger.info(f"Telegram token {'найден' if telegram_token else 'не найден'} в переменных окружения")
logger.info(f"Ahrefs token {'найден' if ahrefs_token else 'не найден'} в переменных окружения")

# Проверка доступности API Ahrefs
if not check_api_availability():
    error_message = "❌ API Ahrefs недоступно или неверный ключ API. Проверьте настройки."
    logger.error(error_message)
    send_message(error_message)
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
        message = f"✅ Таблица успешно инициализирована\nДобавлено доменов: {len(values)}"
        telegram_result = send_message(message)
        logger.info(f"Результат отправки в Telegram: {'успешно' if telegram_result else 'ошибка'}")
        
        return True
    except Exception as e:
        logger.error(f"Error initializing Google Sheet: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        # Отправляем уведомление об ошибке в Telegram
        logger.info("Отправляем уведомление об ошибке в Telegram")
        error_message = f"❌ Ошибка при инициализации таблицы:\n{str(e)}"
        telegram_result = send_message(error_message)
        logger.info(f"Результат отправки ошибки в Telegram: {'успешно' if telegram_result else 'ошибка'}")
        
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
    
    for domain, data in domains_data.items():
        history = data.get('history', [])
        if len(history) >= 2:
            current_traffic = history[-1]['traffic']
            previous_traffic = history[-2]['traffic']
            
            # Пропускаем домены с трафиком меньше 1000
            if current_traffic < 1000 or previous_traffic < 1000:
                continue
            
            # Вычисляем изменение в процентах
            change = ((current_traffic - previous_traffic) / previous_traffic) * 100
            
            # Проверяем условия падения трафика
            if change <= -11:  # Резкое падение более 11%
                critical_changes.append({
                    'domain': domain,
                    'traffic': current_traffic,
                    'change': change,
                    'type': 'sharp'
                })
            elif len(history) >= 3:  # Проверяем два последовательных падения
                traffic_before_previous = history[-3]['traffic']
                if traffic_before_previous >= 1000:
                    previous_change = ((previous_traffic - traffic_before_previous) / traffic_before_previous) * 100
                    if previous_change <= -5 and change <= -5:  # Два последовательных падения по 5%
                        consecutive_drops.append({
                            'domain': domain,
                            'traffic': current_traffic,
                            'change': change,
                            'prev_change': previous_change
                        })
    
    # Формируем сообщение
    if not critical_changes and not consecutive_drops:
        return False, "✅ Критических изменений трафика не обнаружено"
    
    message = "⚠️ Обнаружено падение трафика:\n\n"
    
    # Сначала выводим резкие падения
    if critical_changes:
        message += "📉 Резкое падение:\n"
        for change in critical_changes:
            message += f"{change['domain']}: {change['traffic']:,} (падение {change['change']:.1f}%)\n"
        message += "\n"
    
    # Затем выводим последовательные падения
    if consecutive_drops:
        message += "📉 Последовательное падение:\n"
        for drop in consecutive_drops:
            message += f"{drop['domain']}: {drop['traffic']:,} (падение {drop['change']:.1f}%, пред. {drop['prev_change']:.1f}%)\n"
    
    return True, message

def run_test():
    """
    Запускает тестовый режим с загрузкой и сохранением данных из Google Sheets
    """
    try:
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
        
        # Получаем список доменов из файла
        try:
            with open('domains.txt', 'r', encoding='utf-8') as f:
                domains = [line.strip() for line in f if line.strip()]
            logger.info(f"Загружено {len(domains)} доменов из файла")
        except Exception as e:
            logger.error(f"Ошибка при чтении файла domains.txt: {str(e)}")
            raise

        # Собираем новые данные о трафике
        logger.info("Начинаем сбор данных о трафике...")
        current_date = datetime.now().strftime('%Y-%m-%d')
        
        # Подготавливаем новые данные
        new_data = []
        for domain in domains:
            logger.info(f"Запрашиваем данные для домена: {domain}")
            traffic = get_organic_traffic(domain)
            new_data.append([domain, traffic])
            logger.info(f"Получен трафик для {domain}: {traffic}")
        
        # Очищаем старые данные
        logger.info("Очищаем старые данные в таблице")
        sheet.values().clear(
            spreadsheetId=sheet_id,
            range='Traffic!A1:ZZ'
        ).execute()
        
        # Обновляем данные в таблице
        logger.info("Записываем новые данные в таблицу")
        body = {
            'values': [['Domain', current_date]] + new_data
        }
        
        update_result = sheet.values().update(
            spreadsheetId=sheet_id,
            range='Traffic!A1',
            valueInputOption='RAW',
            body=body
        ).execute()
        
        logger.info(f"Данные успешно обновлены: {update_result.get('updatedCells')} ячеек")
        
        # Отправляем уведомление в Telegram
        message = f"✅ Данные успешно обновлены\nОбработано доменов: {len(domains)}"
        telegram_result = send_message(message)
        logger.info(f"Результат отправки в Telegram: {'успешно' if telegram_result else 'ошибка'}")
        
        return True
            
    except Exception as e:
        logger.error(f"Ошибка при выполнении теста: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        # Отправляем уведомление об ошибке в Telegram
        error_message = f"❌ Ошибка при обновлении данных:\n{str(e)}"
        telegram_result = send_message(error_message)
        logger.info(f"Результат отправки ошибки в Telegram: {'успешно' if telegram_result else 'ошибка'}")
        
        return False

if __name__ == "__main__":
    success = run_test()
    if not success:
        logger.error("Тест завершился с ошибкой")
        exit(1) 