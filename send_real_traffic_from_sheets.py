#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Відправка реального повідомлення про зміни трафіку з Google Sheets
"""

from test_runner import analyze_traffic_changes
from telegram_bot import send_message
import logging
import os
import json
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

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
    """Основна функція"""
    logger.info("Запуск відправки реального повідомлення про трафік з Google Sheets")
    
    # Отримуємо дані з Google Sheets
    domains_data = get_real_traffic_data_from_sheets()
    
    if not domains_data:
        logger.error("Не вдалося отримати дані трафіку з Google Sheets")
        return
    
    logger.info(f"Аналізуємо дані для {len(domains_data)} доменів")
    
    # Аналізуємо зміни трафіку
    has_critical_changes, drops_message, growth_message = analyze_traffic_changes(domains_data)
    
    # Если сообщения None (данные устарели), не отправляем ничего
    if drops_message is None and growth_message is None:
        logger.info("Повідомлення не відправляється через застарілість даних.")
        return True
    
    # Проверяем, есть ли реальные изменения (падения или рост)
    # Если есть только сообщение "Критичних змін трафіку не виявлено" и нет роста, не отправляем
    if (not has_critical_changes and 
        drops_message and "Критичних змін трафіку не виявлено" in drops_message and 
        not growth_message):
        logger.info("Повідомлення не відправляється - немає критичних змін трафіку та росту доменів.")
        print("ℹ️ Немає критичних змін трафіку та росту доменів - повідомлення не відправляється")
        return True
    
    # Формируем объединенное сообщение
    full_message = f"✅ Реальні дані з Google Sheets для {len(domains_data)} доменів\n\n"
    
    # Добавляем сообщение о падениях если есть
    if drops_message:
        full_message += drops_message + "\n\n"
    
    # Добавляем сообщение о росте если есть
    if growth_message:
        full_message += growth_message
    
    logger.info(f"Сообщение для отправки: {full_message}")
    
    # Відправляємо повідомлення в тестовий чат
    print(f"🚀 Відправляємо повідомлення про {'критичні зміни' if has_critical_changes else 'стан трафіку'}...")
    result = send_message(full_message, parse_mode="HTML", test_mode=True)

if __name__ == "__main__":
    main() 