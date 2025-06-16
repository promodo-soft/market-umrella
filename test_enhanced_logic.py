#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Тестування оновленої логіки аналізу трафіку з підтримкою всіх 4 типів падінь
"""

from test_runner import analyze_traffic_changes
from telegram_bot import send_message
import logging
import os

# Налаштування логування
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_real_traffic_data_from_sheets():
    """Отримує реальні дані трафіку з Google Sheets"""
    try:
        # ID таблицы из конфигурации
        from config import MAIN_SHEET_ID
        SPREADSHEET_ID = MAIN_SHEET_ID
        
        # Аутентифікація
        credentials_json = os.getenv('GOOGLE_SHEETS_CREDENTIALS')
        if not credentials_json:
            logger.error("GOOGLE_SHEETS_CREDENTIALS не знайдений")
            return {}
        
        import json
        from google.oauth2.service_account import Credentials
        from googleapiclient.discovery import build
        
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
        
        logger.info(f"Завантажено {len(values)} рядків з Google Sheets")
        
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
                
                logger.info(f"Домен {domain}: {len(traffic_values)} значень трафіку")
        
        logger.info(f"Оброблено {len(domains_data)} доменів з Google Sheets")
        return domains_data
        
    except Exception as e:
        logger.error(f"Помилка при читанні Google Sheets: {e}")
        return {}

def main():
    """Основна функція тестування"""
    logger.info("🚀 Запуск тестування оновленої логіки аналізу трафіку")
    
    # Отримуємо дані з Google Sheets
    domains_data = get_real_traffic_data_from_sheets()
    
    if not domains_data:
        logger.error("❌ Не вдалося отримати дані трафіку")
        return
    
    logger.info(f"📊 Аналізуємо дані для {len(domains_data)} доменів")
    
    # Аналізуємо зміни трафіку з оновленою логікою
    has_critical_changes, message = analyze_traffic_changes(domains_data)
    
    logger.info(f"🔍 Результат аналізу: критичні зміни = {has_critical_changes}")
    logger.info(f"📝 Довжина повідомлення: {len(message)} символів")
    
    print("="*80)
    print("📋 ПОВНЕ ПОВІДОМЛЕННЯ ПРО ТРАФІК:")
    print("="*80)
    print(message)
    print("="*80)
    
    if has_critical_changes:
        logger.info("⚠️ Виявлено критичні зміни! Відправляємо повідомлення в тестовий чат...")
        
        # Відправляємо повідомлення в тестовий чат
        test_chat_id = -600437720  # Кря_Team - Dream Team🤗
        
        try:
            result = send_message(test_chat_id, message)
            if result:
                logger.info("✅ Повідомлення успішно відправлено в тестовий чат!")
            else:
                logger.error("❌ Помилка при відправці повідомлення")
        except Exception as e:
            logger.error(f"❌ Помилка при відправці: {e}")
    else:
        logger.info("✅ Критичних змін не виявлено")

if __name__ == "__main__":
    main() 