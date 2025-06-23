#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для отправки доменов с ростом трафика более 15% в указанный чат
"""

import os
import logging
import json
from datetime import datetime
from telegram_bot import send_message
from google.oauth2 import service_account
from googleapiclient.discovery import build
from config import MAIN_SHEET_ID

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('growth_domains.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def is_data_fresh_for_growth(growth_domains, max_days=7):
    """
    Проверяет, насколько свежие данные о трафике для отчёта о росте.
    
    Args:
        growth_domains (dict): Словарь с данными о доменах с ростом
        max_days (int): Максимальное количество дней для считания данных свежими
        
    Returns:
        tuple: (свежие ли данные, количество дней с последнего обновления)
    """
    if not growth_domains:
        return False, 999
    
    # Ищем самую свежую дату в данных
    latest_date = None
    for domain, data in growth_domains.items():
        current_date_str = data.get('current_date')
        if current_date_str:
            try:
                current_date_obj = datetime.strptime(current_date_str, '%Y-%m-%d')
                if latest_date is None or current_date_obj > latest_date:
                    latest_date = current_date_obj
            except ValueError:
                continue
    
    if latest_date is None:
        return False, 999
    
    # Вычисляем разницу в днях
    current_date = datetime.now()
    days_diff = (current_date - latest_date).days
    
    logger.info(f"Остання дата даних для звіту про ріст: {latest_date.strftime('%Y-%m-%d')}, днів тому: {days_diff}")
    
    return days_diff <= max_days, days_diff

def get_credentials():
    """Получает учетные данные для Google Sheets API"""
    try:
        credentials_json = os.getenv('GOOGLE_SHEETS_CREDENTIALS')
        if not credentials_json:
            logger.error("GOOGLE_SHEETS_CREDENTIALS не найден в переменных окружения")
            return None
        
        credentials_info = json.loads(credentials_json)
        credentials = service_account.Credentials.from_service_account_info(
            credentials_info,
            scopes=['https://www.googleapis.com/auth/spreadsheets.readonly']
        )
        return credentials
    except Exception as e:
        logger.error(f"Ошибка при настройке учетных данных: {e}")
        return None

def get_traffic_data_from_sheets():
    """Получает данные о трафике из Google Sheets и находит домены с ростом более 15%"""
    credentials = get_credentials()
    if not credentials:
        return {}
    
    try:
        service = build('sheets', 'v4', credentials=credentials)
        sheet = service.spreadsheets()
        
        # Читаем данные из листа
        range_name = 'A:ZZ'  # Читаем все доступные колонки
        result = sheet.values().get(spreadsheetId=MAIN_SHEET_ID, range=range_name).execute()
        values = result.get('values', [])
        
        if not values:
            logger.warning("Данные в таблице не найдены")
            return {}
        
        logger.info(f"Прочитано {len(values)} строк из Google Sheets")
        
        # Читаем заголовки (первый ряд) для получения реальных дат
        headers = values[0] if values else []
        date_columns = []
        
        # Собираем информацию о колонках с датами (пропускаем первый столбец "Domain")
        for col_index in range(1, len(headers)):
            date_str = headers[col_index]
            if date_str:  # Если заголовок не пустой
                try:
                    # Пробуем распарсить дату
                    date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                    date_columns.append({
                        'index': col_index,
                        'date': date_str,
                        'date_obj': date_obj
                    })
                except ValueError:
                    # Если не удалось распарсить как дату, пропускаем
                    continue
        
        # Сортируем колонки по дате (от старых к новым для правильного анализа)
        date_columns.sort(key=lambda x: x['date_obj'])
        
        logger.info(f"Найдено {len(date_columns)} колонок с датами")
        
        growth_domains = {}
        
        for row_index, row in enumerate(values):
            if row_index == 0:  # Пропускаем заголовок
                continue
                
            if not row:  # Пропускаем пустые строки
                continue
                
            domain = row[0] if len(row) > 0 else None
            if not domain:
                continue
            
            # Собираем данные трафика согласно отсортированным датам
            history = []
            for date_col in date_columns:
                col_index = date_col['index']
                if col_index < len(row) and row[col_index]:
                    try:
                        traffic_val = int(row[col_index])
                        if traffic_val >= 0:  # Допускаем нулевые значения
                            history.append({
                                'date': date_col['date'],
                                'traffic': traffic_val
                            })
                    except (ValueError, TypeError):
                        continue
            
            # Анализируем только домены с минимум 2 точками данных
            if len(history) >= 2:
                current_traffic = history[-1]['traffic']  # Последний (самый новый)
                previous_traffic = history[-2]['traffic']  # Предпоследний
                
                # Рассчитываем процент роста
                if previous_traffic > 0:  # Избегаем деления на ноль
                    growth_percent = ((current_traffic - previous_traffic) / previous_traffic) * 100
                    
                    # Если рост 15% или более
                    if growth_percent >= 15.0:
                        growth_domains[domain] = {
                            'current_traffic': current_traffic,
                            'previous_traffic': previous_traffic,
                            'growth_percent': growth_percent,
                            'current_date': history[-1]['date'],
                            'previous_date': history[-2]['date']
                        }
        
        logger.info(f"Найдено {len(growth_domains)} доменов с ростом 15%+")
        return growth_domains
        
    except Exception as e:
        logger.error(f"Ошибка при получении данных из Google Sheets: {e}")
        return {}

def format_growth_message(growth_domains):
    """Форматирует сообщение с доменами роста"""
    if not growth_domains:
        return "🔍 Домени з ростом трафіку 15%+ не знайдені"
    
    # Сортируем по проценту роста (убывание)
    sorted_domains = sorted(
        growth_domains.items(), 
        key=lambda x: x[1]['growth_percent'], 
        reverse=True
    )
    
    message_parts = ["🚀 Домени з ростом трафіку 15%+:\n"]
    
    for domain, data in sorted_domains:
        current = data['current_traffic']
        previous = data['previous_traffic']
        growth = data['growth_percent']
        
        # Форматируем числа с разделителями тысяч
        current_formatted = f"{current:,}".replace(',', ' ')
        previous_formatted = f"{previous:,}".replace(',', ' ')
        
        message_parts.append(
            f"📈 {domain}: {current_formatted} (було {previous_formatted}, +{growth:.1f}%)"
        )
    
    message_parts.append(f"\n📊 Всього доменів з ростом 15%+: {len(growth_domains)}")
    message_parts.append(f"📅 Порівняння: {sorted_domains[0][1]['previous_date']} → {sorted_domains[0][1]['current_date']}")
    
    return "\n".join(message_parts)

def send_growth_report():
    """Основная функция отправки отчета о росте"""
    logger.info("=== Початок відправки звіту про домени з ростом 15%+ ===")
    
    try:
        # Получаем данные о доменах с ростом
        growth_domains = get_traffic_data_from_sheets()
        
        if not growth_domains:
            logger.info("Нет доменов с ростом 15%+ или ошибка получения данных")
            message = "🔍 Домени з ростом трафіку 15%+ не знайдені або сталася помилка отримання даних"
        else:
            # Проверяем свежесть данных перед отправкой отчёта о росте
            is_fresh, days_old = is_data_fresh_for_growth(growth_domains, max_days=7)
            
            if not is_fresh:
                logger.warning(f"Дані застарілі на {days_old} днів. Звіт про ріст НЕ відправляється.")
                return True  # Завершаем функцию без отправки сообщений
            else:
                logger.info(f"Дані свіжі ({days_old} днів тому). Формуємо звіт про ріст.")
                message = format_growth_message(growth_domains)
        
        # ID чата для отправки (можно задать через переменную окружения или использовать "Новий чат")
        target_chat_id = os.getenv('GROWTH_REPORT_CHAT_ID', '-1001177341323')  # По умолчанию чат "Новий чат"
        
        logger.info(f"Отправка сообщения в чат {target_chat_id}")
        
        # Отправляем сообщение в указанный чат
        success = send_message(message, test_mode=False, target_chat_ids=[target_chat_id])
        
        if success:
            logger.info("Звіт про домени з ростом успішно відправлений")
        else:
            logger.error("Помилка при відправці звіту")
            
        return success
        
    except Exception as e:
        logger.error(f"Ошибка при отправке отчета о росте: {e}")
        return False

if __name__ == "__main__":
    send_growth_report() 