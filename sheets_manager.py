import os
import json
import logging
from datetime import datetime, timedelta
import pandas as pd
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google.oauth2 import service_account

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SheetsManager:
    def __init__(self):
        self.sheet_id = os.getenv('SHEET_ID')
        self.creds = None
        self._setup_credentials()
        self.service = build('sheets', 'v4', credentials=self.creds)
        self.sheet = self.service.spreadsheets()

    def _setup_credentials(self):
        """Настраивает учетные данные для Google Sheets API."""
        try:
            creds_json = os.getenv('GOOGLE_SHEETS_CREDENTIALS')
            if not creds_json:
                raise ValueError("GOOGLE_SHEETS_CREDENTIALS not found in environment variables")
            
            creds_dict = json.loads(creds_json)
            self.creds = service_account.Credentials.from_service_account_info(
                creds_dict,
                scopes=['https://www.googleapis.com/auth/spreadsheets']
            )
        except Exception as e:
            logger.error(f"Error setting up credentials: {str(e)}")
            raise

    def load_traffic_data(self):
        """
        Загружает данные о трафике из Google Sheets.
        
        Returns:
            dict: Словарь с данными о трафике по доменам
        """
        try:
            result = self.sheet.values().get(
                spreadsheetId=self.sheet_id,
                range='Traffic!A2:D'
            ).execute()
            
            values = result.get('values', [])
            domains_data = {}
            
            for row in values:
                if len(row) >= 4:
                    domain = row[0]
                    current_traffic = int(row[1])
                    previous_traffic = int(row[2])
                    date = row[3]
                    
                    # Создаем историю из текущего и предыдущего значения
                    history = []
                    if previous_traffic > 0:
                        prev_date = (datetime.strptime(date, '%Y-%m-%d') - timedelta(days=1)).strftime('%Y-%m-%d')
                        history.append({
                            'date': prev_date,
                            'traffic': previous_traffic
                        })
                    
                    history.append({
                        'date': date,
                        'traffic': current_traffic
                    })
                    
                    domains_data[domain] = {
                        'traffic': current_traffic,
                        'history': history
                    }
            
            logger.info("Данные успешно загружены из Google Sheets")
            return domains_data
        except Exception as e:
            logger.error(f"Ошибка при загрузке данных из Google Sheets: {str(e)}")
            return None

    def save_traffic_data(self, domains_data):
        """
        Сохраняет данные о трафике в Google Sheets.
        
        Args:
            domains_data (dict): Словарь с данными о трафике по доменам
        """
        try:
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
            
            body = {
                'values': values
            }
            
            # Очищаем старые данные
            self.sheet.values().clear(
                spreadsheetId=self.sheet_id,
                range='Traffic!A2:D',
            ).execute()
            
            # Записываем новые данные
            self.sheet.values().update(
                spreadsheetId=self.sheet_id,
                range='Traffic!A2',
                valueInputOption='RAW',
                body=body
            ).execute()
            
            logger.info("Данные успешно сохранены в Google Sheets")
            return True
        except Exception as e:
            logger.error(f"Ошибка при сохранении данных в Google Sheets: {str(e)}")
            return False 