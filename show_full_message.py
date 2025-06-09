#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Показ полного повідомлення про зміни трафіку
"""

from test_runner import analyze_traffic_changes
import logging
import os
import json
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

# Налаштування логування
logging.basicConfig(level=logging.WARNING)  # Уменьшаем логирование
logger = logging.getLogger(__name__)

def get_real_traffic_data_from_sheets():
    """Отримує реальні дані трафіку з Google Sheets"""
    try:
        # ID таблицы из указанной ссылки
        SPREADSHEET_ID = '1iwr3qku-JcMMqEBTYdWeWRUXfmC9sLp_s-q-Ruxj5xs'
        
        # Аутентифікація
        credentials_json = os.getenv('GOOGLE_SHEETS_CREDENTIALS')
        if not credentials_json:
            logger.error("GOOGLE_SHEETS_CREDENTIALS не знайдений")
            return {}
        
        credentials_dict = json.loads(credentials_json)
        credentials = Credentials.from_service_account_info(
            credentials_dict,
            scopes=['https://www.googleapis.com/auth/spreadsheets']
        )
        
        service = build('sheets', 'v4', credentials=credentials)
        
        # Читаємо дані з таблиці
        range_name = 'A:Z'  # Читаємо всі стовпці
        result = service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID,
            range=range_name
        ).execute()
        
        values = result.get('values', [])
        if not values:
            logger.error("Немає даних в Google Sheets")
            return {}
        
        domains_data = {}
        
        for row_index, row in enumerate(values):
            if row_index == 0:  # Пропускаємо заголовок
                continue
                
            if not row:  # Пропускаємо порожні рядки
                continue
                
            domain = row[0] if len(row) > 0 else None
            if not domain:
                continue
            
            # Збираємо всі значення трафіку з рядка (пропускаємо перший стовпець з доменом)
            traffic_values = []
            for col_index in range(1, len(row)):
                try:
                    if row[col_index]:  # Перевіряємо, що значення не порожнє
                        traffic_val = int(row[col_index])
                        if traffic_val >= 0:  # Допускаємо нулеві значення
                            traffic_values.append(traffic_val)
                except (ValueError, TypeError):
                    continue
            
            if len(traffic_values) >= 2:
                # Створюємо історію з фіктивними датами (припускаємо, що дані йдуть від старих до нових)
                history = []
                for i, traffic in enumerate(traffic_values):
                    history.append({
                        'date': f'2024-{(i%12)+1:02d}-{((i//12)%28)+1:02d}',  # Фіктивні дати
                        'traffic': traffic
                    })
                
                domains_data[domain] = {
                    'history': history
                }
        
        return domains_data
        
    except Exception as e:
        logger.error(f"Помилка при читанні Google Sheets: {e}")
        return {}

def show_full_traffic_message():
    """Показує повне повідомлення про зміни трафіку"""
    
    print("=== Повне повідомлення про зміни трафіку ===\n")
    
    try:
        # Отримуємо дані з Google Sheets
        domains_data = get_real_traffic_data_from_sheets()
        
        if not domains_data:
            print("❌ Не вдалося отримати дані з Google Sheets")
            return
            
        print(f"📊 Проаналізовано {len(domains_data)} доменів\n")
        
        # Аналізуємо зміни трафіку
        has_changes, message = analyze_traffic_changes(domains_data)
        
        print(f"📏 Довжина повідомлення: {len(message)} символів")
        print(f"🔍 Критичні зміни виявлено: {'ТАК' if has_changes else 'НІ'}")
        print(f"📨 Буде розбито на частини: {'ТАК' if len(message) > 4000 else 'НІ'}")
        
        print(f"\n{'='*60}")
        print("ПОВНЕ ПОВІДОМЛЕННЯ:")
        print(f"{'='*60}")
        print(message)
        print(f"{'='*60}")
        
        # Подсчитаем секции
        sharp_count = message.count('падіння') - message.count('Послідовне падіння') - message.count('падіння трафіку')
        sequential_in_message = 'Послідовне падіння' in message
        
        print(f"\n📈 Статистика повідомлення:")
        print(f"   - Містить секцію 'Різке падіння': {'ТАК' if 'Різке падіння' in message else 'НІ'}")
        print(f"   - Містить секцію 'Послідовне падіння': {'ТАК' if sequential_in_message else 'НІ'}")
        
            
    except Exception as e:
        print(f"❌ Помилка: {e}")

if __name__ == "__main__":
    show_full_traffic_message() 