#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Тестування підключення до Google Sheets та отримання даних
"""

import logging
import os
import json
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from config import MAIN_SHEET_ID

# Налаштування логування
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_google_sheets_connection():
    """Тестує підключення до Google Sheets"""
    try:
        # ID таблицы из конфигурации
        SPREADSHEET_ID = MAIN_SHEET_ID
        
        logger.info(f"🔗 Тестуємо підключення до Google Sheets")
        logger.info(f"📊 ID таблиці: {SPREADSHEET_ID}")
        
        # Перевірка наявності credentials
        credentials_json = os.getenv('GOOGLE_SHEETS_CREDENTIALS')
        if not credentials_json:
            logger.error("❌ GOOGLE_SHEETS_CREDENTIALS не знайдений у змінних середовища")
            return False
        
        logger.info("✅ GOOGLE_SHEETS_CREDENTIALS знайдений")
        
        # Парсинг credentials
        try:
            credentials_dict = json.loads(credentials_json)
            logger.info("✅ Credentials успішно розпарсений")
        except json.JSONDecodeError as e:
            logger.error(f"❌ Помилка парсингу credentials: {e}")
            return False
        
        # Аутентифікація
        credentials = Credentials.from_service_account_info(
            credentials_dict,
            scopes=['https://www.googleapis.com/auth/spreadsheets']
        )
        logger.info("✅ Аутентифікація успішна")
        
        # Створення сервісу
        service = build('sheets', 'v4', credentials=credentials)
        logger.info("✅ Google Sheets API сервіс створений")
        
        # Читання даних з таблиці
        logger.info("📖 Читаємо дані з таблиці...")
        range_name = 'A1:Z1000'  # Читаємо широкий діапазон
        result = service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID,
            range=range_name
        ).execute()
        
        values = result.get('values', [])
        logger.info(f"✅ Успішно прочитано {len(values)} рядків")
        
        if not values:
            logger.warning("⚠️ Таблиця порожня або немає даних")
            return True
        
        # Показуємо інформацію про структуру даних
        header_row = values[0] if values else []
        logger.info(f"📋 Заголовки ({len(header_row)} стовпців): {header_row[:10]}{'...' if len(header_row) > 10 else ''}")
        
        # Показуємо кілька перших рядків даних
        data_rows = values[1:6] if len(values) > 1 else []
        logger.info(f"📊 Перші {len(data_rows)} рядків даних:")
        for i, row in enumerate(data_rows, 1):
            domain = row[0] if len(row) > 0 else 'N/A'
            traffic_values = []
            for col_index in range(1, min(len(row), 6)):
                try:
                    if row[col_index]:
                        traffic_values.append(int(row[col_index]))
                except (ValueError, TypeError):
                    continue
            logger.info(f"   {i}. {domain}: {traffic_values}")
        
        # Підрахунок валідних доменів
        valid_domains = 0
        for row in values[1:]:
            if len(row) > 0 and row[0]:  # Є домен
                # Перевіряємо, чи є хоча б два числових значення
                traffic_count = 0
                for col_index in range(1, len(row)):
                    try:
                        if row[col_index]:
                            int(row[col_index])
                            traffic_count += 1
                    except (ValueError, TypeError):
                        continue
                if traffic_count >= 2:
                    valid_domains += 1
        
        logger.info(f"✅ Знайдено {valid_domains} доменів з достатньою кількістю даних для аналізу")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Помилка при тестуванні Google Sheets: {e}")
        import traceback
        logger.error(f"Детальна помилка: {traceback.format_exc()}")
        return False

def main():
    """Основна функція тестування"""
    logger.info("🚀 Запуск тестування Google Sheets")
    
    success = test_google_sheets_connection()
    
    if success:
        logger.info("🎉 Тестування завершено успішно!")
        print("🎉 Підключення до Google Sheets працює!")
    else:
        logger.error("💥 Тестування завершилось з помилками")
        print("💥 Виникли проблеми з підключенням до Google Sheets")

if __name__ == "__main__":
    main() 