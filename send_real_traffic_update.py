#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Відправка реального повідомлення про зміни трафіку без повторного збору даних
"""

from test_runner import analyze_traffic_changes
from telegram_bot import send_message
import logging
import json
import os
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

# Налаштування логування
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_real_traffic_data():
    """Отримує реальні дані трафіку з Google Sheets без нового збору"""
    try:
        # Аутентифікація
        credentials_json = os.getenv('GOOGLE_SHEETS_CREDENTIALS')
        if not credentials_json:
            logger.error("GOOGLE_SHEETS_CREDENTIALS не знайдений")
            return {}
            
        credentials_data = json.loads(credentials_json)
        credentials = Credentials.from_service_account_info(
            credentials_data,
            scopes=['https://www.googleapis.com/auth/spreadsheets']
        )
        
        # Підключення до API
        service = build('sheets', 'v4', credentials=credentials)
        sheet = service.spreadsheets()
        
        # Читання даних
        sheet_id = os.getenv('SHEET_ID')
        result = sheet.values().get(
            spreadsheetId=sheet_id,
            range='Traffic!A1:ZZ'
        ).execute()
        
        values = result.get('values', [])
        if not values:
            logger.info("Дані в таблиці відсутні")
            return {}
            
        headers = values[0]
        domains_data = {}
        
        logger.info(f"Знайдено {len(values)-1} доменів у таблиці")
        logger.info(f"Стовпці дат: {headers[1:] if len(headers) > 1 else 'немає'}")
        
        # Обробка даних - створюємо структуру для analyze_traffic_changes
        for row in values[1:]:
            if len(row) >= 2:
                domain = row[0]
                history = []
                
                # Збираємо історію трафіку (від найновішого до найстарішого)
                for i in range(1, len(row)):
                    if i < len(headers):
                        try:
                            traffic = int(row[i])
                            history.append({
                                'date': headers[i],
                                'traffic': traffic
                            })
                        except (ValueError, TypeError):
                            continue
                
                if history:
                    # Сортуємо по даті (найновіший перший)
                    history.sort(key=lambda x: x['date'], reverse=True)
                    domains_data[domain] = {
                        'traffic': history[0]['traffic'],
                        'history': history
                    }
        
        logger.info(f"Оброблено дані для {len(domains_data)} доменів")
        return domains_data
        
    except Exception as e:
        logger.error(f"Помилка при отриманні даних з Google Sheets: {e}")
        return {}

def send_real_traffic_update():
    """Відправляє реальне повідомлення про зміни трафіку"""
    
    print("=== Відправка реального звіту про трафік ===")
    
    try:
        # Отримуємо реальні дані з Google Sheets
        print("Завантажуємо реальні дані з Google Sheets...")
        domains_data = get_real_traffic_data()
        
        if not domains_data:
            print("❌ Не вдалося отримати дані з Google Sheets")
            print("💡 Можливо відсутні змінні середовища GOOGLE_SHEETS_CREDENTIALS або SHEET_ID")
            return
            
        print(f"✅ Отримано дані для {len(domains_data)} доменів")
        
        # Аналізуємо зміни трафіку за допомогою реальної функції
        print("Аналізуємо зміни трафіку...")
        has_changes, drops_message, growth_message = analyze_traffic_changes(domains_data)
        
        # Если сообщения None (данные устарели), не отправляем ничего
        if drops_message is None and growth_message is None:
            logger.info("Повідомлення не відправляється через застарілість даних.")
            return True
        
        # Проверяем, есть ли реальные изменения (падения или рост)
        # Если есть только сообщение "Критичних змін трафіку не виявлено" и нет роста, не отправляем
        if (not has_changes and 
            drops_message and "Критичних змін трафіку не виявлено" in drops_message and 
            not growth_message):
            logger.info("Повідомлення не відправляється - немає критичних змін трафіку та росту доменів.")
            print("ℹ️ Немає критичних змін трафіку та росту доменів - повідомлення не відправляється")
            return True
        
        # Формируем объединенное сообщение
        full_message = f"✅ Дані про трафік з таблиці для {len(domains_data)} доменів\n\n"
        
        # Добавляем сообщение о падениях если есть
        if drops_message:
            full_message += drops_message + "\n\n"
        
        # Добавляем сообщение о росте если есть
        if growth_message:
            full_message += growth_message
        
        logger.info(f"Сообщение для отправки: {full_message}")
        
        # Відправляємо сообщение в Telegram
        logger.info("Отправка сообщения в Telegram")
        if send_message(full_message, parse_mode="HTML", test_mode=True):
            if has_changes:
                print("⚠️ Відправлено звіт з критичними змінами трафіку")
            else:
                print("✅ Відправлено звіт без критичних змін")
        else:
            print("❌ Виникла помилка при відправці")
            
    except Exception as e:
        logger.error(f"Помилка під час виконання: {e}")
        print(f"❌ Помилка: {e}")

if __name__ == "__main__":
    send_real_traffic_update() 