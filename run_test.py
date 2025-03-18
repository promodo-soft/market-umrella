import logging
import os
import json
from datetime import datetime, timedelta
from google.oauth2 import service_account
from googleapiclient.discovery import build

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def load_traffic_data():
    """
    Загружает данные о трафике из Google Sheets.
    
    Returns:
        dict: Словарь с данными о трафике по доменам
    """
    try:
        logger.info("Загрузка данных из Google Sheets")
        
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
        
        # Загрузка данных из Google Sheets
        logger.info(f"Loading data from sheet {sheet_id}")
        result = sheet.values().get(
            spreadsheetId=sheet_id,
            range='Traffic!A2:D'
        ).execute()
        
        values = result.get('values', [])
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
                    # Извлекаем только дату из строки даты/времени
                    try:
                        # Пробуем разные форматы даты
                        if ' ' in date:  # Если есть пробел, значит есть время
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
                        # Используем текущую дату как запасной вариант
                        date_obj = datetime.now()
                        prev_date = (date_obj - timedelta(days=1)).strftime('%Y-%m-%d')
                        history.append({
                            'date': prev_date,
                            'traffic': previous_traffic
                        })
                
                # Используем только дату без времени для истории
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
        return domains_data
    except Exception as e:
        logger.error(f"Error loading data: {str(e)}")
        logger.error(f"Error type: {type(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return None

def save_traffic_data(domains_data):
    """
    Сохраняет данные о трафике в Google Sheets.
    
    Args:
        domains_data (dict): Словарь с данными о трафике по доменам
    """
    try:
        logger.info("Сохранение данных в Google Sheets")
        
        # Настройка доступа к Google Sheets
        sheet_id = os.getenv('SHEET_ID')
        
        # Настройка учетных данных для Google Sheets API
        creds_json = os.getenv('GOOGLE_SHEETS_CREDENTIALS')
        creds_dict = json.loads(creds_json)
        creds = service_account.Credentials.from_service_account_info(
            creds_dict,
            scopes=['https://www.googleapis.com/auth/spreadsheets']
        )
        
        # Создание сервиса Google Sheets
        service = build('sheets', 'v4', credentials=creds)
        sheet = service.spreadsheets()
        
        current_date = datetime.now().strftime('%Y-%m-%d')
        values = []
        
        for domain, data in domains_data.items():
            history = data.get('history', [])
            current_traffic = data['traffic']
            
            # Получаем предыдущее значение трафика
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
        
        # Очищаем старые данные
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
        return True
    except Exception as e:
        logger.error(f"Ошибка при сохранении данных в Google Sheets: {str(e)}")
        logger.error(f"Error type: {type(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False

if __name__ == "__main__":
    logger.info("Запуск тестового режима")
    
    # Загрузка текущих данных
    domains_data = load_traffic_data()
    if not domains_data:
        logger.error("Не удалось загрузить данные из базы")
        exit(1)
    
    # Вывод информации о загруженных доменах
    logger.info(f"Загружено {len(domains_data)} доменов из базы данных")
    
    # Сохраняем данные
    save_traffic_data(domains_data)
    logger.info("Тест завершен успешно") 