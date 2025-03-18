import logging
import os
import json
import pandas as pd
from datetime import datetime, timedelta
from google.oauth2 import service_account
from googleapiclient.discovery import build
from telegram_bot import send_message
from ahrefs_api import get_organic_traffic

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
            logger.info(f"Загружено {len(domains)} доменов из файла")
        except Exception as e:
            logger.error(f"Ошибка при чтении файла domains.txt: {str(e)}")
            raise

        # Проверяем, есть ли уже данные за сегодня
        headers = values[0] if values else []
        if len(headers) > 1 and headers[1] == current_date:
            logger.info(f"Данные уже обновлены сегодня ({current_date}). Проверяем изменения трафика.")
            
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
            logger.info(f"Результат отправки в Telegram: {'успешно' if telegram_result else 'ошибка'}")
            
            return True

        # Если данных за сегодня нет, добавляем новый столбец
        logger.info(f"Добавляем данные за {current_date}")
        
        # Создаем словарь с текущими данными по доменам
        existing_domains = {row[0]: row[1:] for row in values[1:]} if len(values) > 1 else {}
        
        # Подготавливаем новые данные
        new_values = [['Domain', current_date] + headers[1:] if headers else ['Domain', current_date]]
        
        # Обрабатываем каждый домен
        for domain in domains:
            # Получаем текущий трафик из Ahrefs
            current_traffic = get_organic_traffic(domain)
            logger.info(f"Домен {domain}: трафик = {current_traffic}")
            
            domain_row = [domain, str(current_traffic)]
            
            # Добавляем исторические данные
            if domain in existing_domains:
                domain_row.extend(existing_domains[domain])
            
            new_values.append(domain_row)
        
        # Очищаем весь лист и записываем новые данные
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
        
        logger.info(f"Данные успешно сохранены в Google Sheets: {result.get('updatedCells')} ячеек обновлено")
        
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
        
        # Отправляем уведомление об изменениях
        has_changes, message = analyze_traffic_changes(domains_data)
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