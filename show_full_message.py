#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Показ полного повідомлення про зміни трафіку
"""

from test_runner import analyze_traffic_changes
from telegram_bot import send_message
from config import MAIN_SHEET_ID
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
        # ID таблицы из конфигурации
        SPREADSHEET_ID = MAIN_SHEET_ID
        
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
        
        # Читаємо заголовки (перший рядок) для отримання реальних дат
        headers = values[0] if values else []
        date_columns = []
        
        # Збираємо інформацію про колонки з датами (пропускаємо перший стовпець "Domain")
        for col_index in range(1, len(headers)):
            date_str = headers[col_index]
            if date_str:  # Якщо заголовок не пустий
                try:
                    # Пробуємо розпарсити дату
                    from datetime import datetime
                    date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                    date_columns.append({
                        'index': col_index,
                        'date': date_str,
                        'date_obj': date_obj
                    })
                except ValueError:
                    # Якщо не вдалося розпарсити як дату, пропускаємо
                    continue
        
        # Сортуємо колонки за датою (від старих до нових для правильного аналізу)
        date_columns.sort(key=lambda x: x['date_obj'])
        
        domains_data = {}
        
        for row_index, row in enumerate(values):
            if row_index == 0:  # Пропускаємо заголовок
                continue
                
            if not row:  # Пропускаємо порожні рядки
                continue
                
            domain = row[0] if len(row) > 0 else None
            if not domain:
                continue
            
            # Збираємо данні трафіку відповідно до відсортованих дат
            history = []
            for date_col in date_columns:
                col_index = date_col['index']
                if col_index < len(row) and row[col_index]:
                    try:
                        traffic_val = int(row[col_index])
                        if traffic_val >= 0:  # Допускаємо нулеві значення
                            history.append({
                                'date': date_col['date'],
                                'traffic': traffic_val
                            })
                    except (ValueError, TypeError):
                        continue
            
            # Зберігаємо тільки домени з принаймні двома точками даних
            if len(history) >= 2:
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
        
        # Отправляем в тестовый чат
        print(f"\n🚀 Відправляємо повідомлення в тестовий чат...")
        print(f"📏 Довжина повідомлення для відправки: {len(message)} символів")
        
        # Проверяем наличие токена
        import os
        bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        if not bot_token:
            print("❌ TELEGRAM_BOT_TOKEN не знайдений в змінних середовища")
            return
        else:
            print(f"✅ TELEGRAM_BOT_TOKEN знайдений (довжина: {len(bot_token)})")
        
        try:
            result = send_message(message, parse_mode="HTML", test_mode=True)
            
            if result:
                print("✅ Повідомлення успішно відправлено в тестовий чат!")
            else:
                print("❌ Помилка при відправці повідомлення")
        except Exception as e:
            print(f"❌ Виняток при відправці повідомлення: {e}")
            import traceback
            print(f"Детальна помилка: {traceback.format_exc()}")
            
    except Exception as e:
        print(f"❌ Помилка: {e}")

if __name__ == "__main__":
    show_full_traffic_message() 