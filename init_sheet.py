from sheets_manager import SheetsManager
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def init_sheet():
    try:
        manager = SheetsManager()
        
        # Создаем заголовки
        headers = [['Domain', 'Current Traffic', 'Previous Traffic', 'Date']]
        
        body = {
            'values': headers
        }
        
        # Записываем заголовки
        result = manager.sheet.values().update(
            spreadsheetId=manager.sheet_id,
            range='Traffic!A1',
            valueInputOption='RAW',
            body=body
        ).execute()
        
        logger.info("Headers initialized successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error initializing sheet: {str(e)}")
        return False

if __name__ == '__main__':
    init_sheet() 