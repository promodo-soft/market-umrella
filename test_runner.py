import logging
import os
import json
import pandas as pd
from datetime import datetime, timedelta
from google.oauth2 import service_account
from googleapiclient.discovery import build
from telegram_bot import send_message

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Проверка наличия токена
telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
logger.info(f"Telegram token {'найден' if telegram_token else 'не найден'} в переменных окружения")

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
        
        # Проверяем наличие данных в таблице
        result = sheet.values().get(
            spreadsheetId=sheet_id,
            range='Traffic!A2:D'
        ).execute()
        
        values = result.get('values', [])
        
        # Если данных нет, инициализируем таблицу
        if not values:
            logger.info("No data found in sheet, initializing with data from Excel")
            if not init_sheet(service, sheet_id):
                raise Exception("Failed to initialize sheet")
            return True
        
        logger.info(f"Loaded {len(values)} rows from sheet")
        
        domains_data = {}
        
        for row in values:
            if len(row) >= 4:
                domain = row[0]
                current_traffic = int(row[1])
                previous_traffic = int(row[2])
                date = row[3]
                logger.info(f"Processing domain: {domain}, current: {current_traffic}, previous: {previous_traffic}, date: {date}")
                
                history = []
                if previous_traffic > 0:
                    try:
                        if ' ' in date:
                            date_obj = datetime.strptime(date.split(' ')[0], '%Y-%m-%d')
                        else:
                            date_obj = datetime.strptime(date, '%Y-%m-%d')
                        
                        prev_date = (date_obj - timedelta(days=1)).strftime('%Y-%m-%d')
                        history.append({
                            'date': prev_date,
                            'traffic': previous_traffic
                        })
                    except ValueError as e:
                        logger.warning(f"Ошибка при обработке даты '{date}': {str(e)}")
                        date_obj = datetime.now()
                        prev_date = (date_obj - timedelta(days=1)).strftime('%Y-%m-%d')
                        history.append({
                            'date': prev_date,
                            'traffic': previous_traffic
                        })
                
                current_date = date.split(' ')[0] if ' ' in date else date
                history.append({
                    'date': current_date,
                    'traffic': current_traffic
                })
                
                domains_data[domain] = {
                    'traffic': current_traffic,
                    'history': history
                }
        
        logger.info(f"Successfully processed {len(domains_data)} domains")
        
        # Сохранение данных обратно в Google Sheets
        logger.info("Сохранение данных в Google Sheets")
        current_date = datetime.now().strftime('%Y-%m-%d')
        values = []
        
        for domain, data in domains_data.items():
            history = data.get('history', [])
            current_traffic = data['traffic']
            
            previous_traffic = 0
            if len(history) >= 2:
                previous_traffic = history[-2]['traffic']
            
            values.append([
                domain,
                current_traffic,
                previous_traffic,
                current_date
            ])
        
        logger.info(f"Подготовлено {len(values)} доменов для сохранения")
        
        body = {
            'values': values
        }
        
        # Очищаем старые данные (начиная со второй строки, чтобы сохранить заголовки)
        sheet.values().clear(
            spreadsheetId=sheet_id,
            range='Traffic!A2:D',
        ).execute()
        
        # Записываем новые данные
        result = sheet.values().update(
            spreadsheetId=sheet_id,
            range='Traffic!A2',
            valueInputOption='RAW',
            body=body
        ).execute()
        
        logger.info(f"Данные успешно сохранены в Google Sheets: {result.get('updatedCells')} ячеек обновлено")
        logger.info("Тест завершен успешно")
        
        # Отправляем уведомление в Telegram
        logger.info("Отправляем уведомление в Telegram об успешном обновлении")
        message = f"✅ Данные успешно обновлены\nОбработано доменов: {len(values)}"
        telegram_result = send_message(message)
        logger.info(f"Результат отправки в Telegram: {'успешно' if telegram_result else 'ошибка'}")
        
        return True
    except Exception as e:
        logger.error(f"Ошибка при выполнении теста: {str(e)}")
        logger.error(f"Error type: {type(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        # Отправляем уведомление об ошибке в Telegram
        logger.info("Отправляем уведомление об ошибке в Telegram")
        error_message = f"❌ Ошибка при обновлении данных:\n{str(e)}"
        telegram_result = send_message(error_message)
        logger.info(f"Результат отправки ошибки в Telegram: {'успешно' if telegram_result else 'ошибка'}")
        
        return False

if __name__ == "__main__":
    success = run_test()
    if not success:
        logger.error("Тест завершился с ошибкой")
        exit(1) 