from sheets_manager import SheetsManager
import logging
from datetime import datetime
import pandas as pd

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def init_sheet():
    try:
        manager = SheetsManager()
        
        # Создаем заголовки
        headers = [['Domain', 'Current Traffic', 'Previous Traffic', 'Date']]
        
        # Читаем данные из Excel файла
        logger.info("Reading data from Excel file")
        df = pd.read_excel('traffic_data.xlsx')
        
        # Подготавливаем данные
        current_date = datetime.now().strftime('%Y-%m-%d')
        initial_data = []
        
        for _, row in df.iterrows():
            domain = row['Domain']
            current_traffic = int(row['Traffic'])
            # Используем текущий трафик как предыдущий (так как это начальные данные)
            initial_data.append([domain, current_traffic, current_traffic, current_date])
        
        logger.info(f"Prepared {len(initial_data)} domains for upload")
        
        # Объединяем заголовки и данные
        values = headers + initial_data
        
        body = {
            'values': values
        }
        
        # Очищаем старые данные
        logger.info("Clearing old data")
        manager.sheet.values().clear(
            spreadsheetId=manager.sheet_id,
            range='Traffic!A1:D1000'
        ).execute()
        
        # Записываем новые данные
        logger.info("Uploading new data")
        result = manager.sheet.values().update(
            spreadsheetId=manager.sheet_id,
            range='Traffic!A1',
            valueInputOption='RAW',
            body=body
        ).execute()
        
        logger.info("Sheet initialized with data from Excel file successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error initializing sheet: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False

if __name__ == '__main__':
    init_sheet() 