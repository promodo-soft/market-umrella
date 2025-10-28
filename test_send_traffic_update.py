#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Тестова відправка повідомлення про останні дані трафіку
"""

from test_runner import analyze_traffic_changes
from telegram_bot import send_message
import logging
import json
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
import os

# Налаштування логування
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_domains_list():
    """Завантажує список доменів з файла domains.txt"""
    try:
        with open('domains.txt', 'r', encoding='utf-8') as f:
            domains = [line.strip() for line in f if line.strip()]
        return domains
    except Exception as e:
        logger.error(f"Помилка при читанні файла domains.txt: {e}")
        return []

def get_latest_traffic_data():
    """Отримує останні дані трафіку з Google Sheets"""
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
            return {}
            
        headers = values[0]
        domains_data = {}
        
        # Обробка даних
        for row in values[1:]:
            if len(row) >= 2:
                domain = row[0]
                history = []
                
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
                    domains_data[domain] = {
                        'traffic': history[-1]['traffic'],
                        'history': history
                    }
        
        return domains_data
        
    except Exception as e:
        logger.error(f"Помилка при отриманні даних з Google Sheets: {e}")
        return {}

def test_send_traffic_update():
    """Відправляє тестове повідомлення про останні дані трафіку"""
    
    print("=== Тест відправки оновлення трафіку ===")
    
    try:
        # Загружаємо домени
        print("Завантажуємо домени...")
        domains = get_domains_list()
        print(f"Знайдено доменів: {len(domains)}")
        
        # Отримуємо останні дані трафіку
        print("Отримуємо дані трафіку з Google Sheets...")
        domains_data = get_latest_traffic_data()
        print(f"Отримано дані для {len(domains_data)} доменів")
        
        if not domains_data:
            print("❌ Не вдалося отримати дані трафіку")
            return
            
        # Аналізуємо зміни трафіку
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
        full_message = f"✅ Тестові дані оновлено для {len(domains_data)} доменів\n\n"
        
        # Добавляем сообщение о падениях если есть
        if drops_message:
            full_message += drops_message + "\n\n"
        
        # Добавляем сообщение о росте если есть
        if growth_message:
            full_message += growth_message
        
        logger.info(f"Сообщение для отправки: {full_message}")
        
        # Отправляем сообщение в тестовый чат
        logger.info("Отправка тестового сообщения в Telegram")
        if send_message(full_message, parse_mode="HTML", test_mode=True):
            print("✅ УСПІШНО")
        else:
            print("❌ ПОМИЛКА")
            
    except Exception as e:
        logger.error(f"Помилка під час тестування: {e}")
        print(f"❌ Помилка: {e}")

if __name__ == "__main__":
    test_send_traffic_update() 