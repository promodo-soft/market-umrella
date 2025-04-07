#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для отправки сообщения о последних изменениях трафика в рабочий чат,
используя уже собранные данные.
"""
import os
import logging
import json
from datetime import datetime
from telegram_bot import send_message
from google.oauth2 import service_account
from googleapiclient.discovery import build

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def analyze_traffic_changes(domains_data):
    """
    Анализирует изменения трафика и формирует сообщение для Telegram.
    
    Args:
        domains_data (dict): Словарь с данными о трафике по доменам
        
    Returns:
        tuple: (есть ли критические изменения, текст сообщения)
    """
    critical_changes = []
    consecutive_drops = []
    
    logger.info(f"Анализируем изменения трафика для {len(domains_data)} доменов")
    
    for domain, data in domains_data.items():
        history = data.get('history', [])
        if len(history) >= 2:
            current_traffic = history[0]['traffic']  # Текущий трафик
            previous_traffic = history[1]['traffic']  # Предыдущий трафик
            
            # Логируем все изменения трафика для диагностики
            change_percent = ((current_traffic - previous_traffic) / previous_traffic) * 100 if previous_traffic > 0 else 0
            logger.info(f"Домен {domain}: текущий трафик {current_traffic}, предыдущий {previous_traffic}, изменение {change_percent:.1f}%")
            
            # Пропускаем домены с трафиком меньше 1000
            if current_traffic < 1000 or previous_traffic < 1000:
                logger.info(f"Пропускаем домен {domain} из-за недостаточного трафика")
                continue
            
            # Вычисляем изменение в процентах
            change = ((current_traffic - previous_traffic) / previous_traffic) * 100
            
            # Проверяем условия падения трафика
            if change <= -11:  # Резкое падение более 11%
                logger.info(f"Обнаружено резкое падение для {domain}: {change:.1f}%")
                critical_changes.append({
                    'domain': domain,
                    'traffic': current_traffic,
                    'change': change,
                    'type': 'sharp'
                })
            elif len(history) >= 3:  # Проверяем два последовательных падения
                traffic_before_previous = history[2]['traffic']  # Трафик перед предыдущим
                if traffic_before_previous >= 1000:
                    previous_change = ((previous_traffic - traffic_before_previous) / traffic_before_previous) * 100
                    if previous_change <= -5 and change <= -5:  # Два последовательных падения по 5%
                        logger.info(f"Обнаружено последовательное падение для {domain}: текущее {change:.1f}%, предыдущее {previous_change:.1f}%")
                        consecutive_drops.append({
                            'domain': domain,
                            'traffic': current_traffic,
                            'change': change,
                            'prev_change': previous_change
                        })
    
    # Добавляем форматирование HTML для отправки через Telegram
    if not critical_changes and not consecutive_drops:
        regular_message = "<b>📊 Результати моніторингу трафіку:</b>\n\n"
        regular_message += "✅ <b>Критичних змін трафіку не виявлено.</b>\n\n"
        regular_message += "Моніторинг проведено для всіх доменів.\n"
        regular_message += "Всі показники трафіку в межах норми."
        return False, regular_message
    
    message = "<b>⚠️ Виявлено падіння трафіку:</b>\n\n"
    
    # Сначала выводим резкие падения
    if critical_changes:
        message += "<b>📉 Різке падіння:</b>\n"
        for change in sorted(critical_changes, key=lambda x: x['change']):
            message += f"<code>{change['domain']}</code>: {change['traffic']:,} (падіння {abs(change['change']):.1f}%)\n"
        message += "\n"
    
    # Затем выводим последовательные падения
    if consecutive_drops:
        message += "<b>📉 Послідовне падіння:</b>\n"
        for drop in sorted(consecutive_drops, key=lambda x: x['change']):
            message += f"<code>{drop['domain']}</code>: {drop['traffic']:,} (падіння {abs(drop['change']):.1f}%, попер. {abs(drop['prev_change']):.1f}%)\n"
    
    return True, message

def main():
    """Основная функция для отправки сообщения"""
    logger.info("=== Начало отправки сообщения о трафике ===")
    
    # Проверяем наличие токена бота
    if not os.getenv('TELEGRAM_BOT_TOKEN'):
        logger.error("TELEGRAM_BOT_TOKEN не найден в переменных окружения")
        return False
        
    # Настройка доступа к Google Sheets
    sheet_id = os.getenv('SHEET_ID')
    if not sheet_id:
        logger.error("SHEET_ID не найден в переменных окружения")
        return False
    
    logger.info(f"Sheet ID: {sheet_id}")
    
    # Настройка учетных данных для Google Sheets API
    try:
        logger.info("Настройка учетных данных")
        creds_json = os.getenv('GOOGLE_SHEETS_CREDENTIALS')
        if not creds_json:
            logger.error("GOOGLE_SHEETS_CREDENTIALS не найден в переменных окружения")
            
            # Если не можем получить данные из Google Sheets, 
            # отправляем тестовое сообщение с примером данных
            logger.info("Формируем тестовое сообщение с примером данных")
            
            # Создаем пример данных
            domains_data = {
                "example.com": {
                    "traffic": 15000,
                    "history": [
                        {"date": "2025-04-07", "traffic": 15000},
                        {"date": "2025-04-01", "traffic": 18000}
                    ]
                },
                "sample-site.org": {
                    "traffic": 8500,
                    "history": [
                        {"date": "2025-04-07", "traffic": 8500},
                        {"date": "2025-04-01", "traffic": 10000}
                    ]
                },
                "test-domain.net": {
                    "traffic": 25000,
                    "history": [
                        {"date": "2025-04-07", "traffic": 25000},
                        {"date": "2025-04-01", "traffic": 30000},
                        {"date": "2025-03-25", "traffic": 32000}
                    ]
                }
            }
            
            has_changes, traffic_message = analyze_traffic_changes(domains_data)
            
            # Добавляем примечание о тестовом характере данных
            traffic_message += "\n\n<i>Примітка: Це тестове повідомлення з тестовими даними, оскільки не вдалося отримати реальні дані з Google Sheets.</i>"
            
            # Отправляем сообщение в Telegram (test_mode=False для отправки во все чаты)
            logger.info("Отправка тестового сообщения о трафике")
            if send_message(traffic_message, parse_mode="HTML", test_mode=False):
                logger.info("Сообщение о трафике успешно отправлено")
                return True
            else:
                logger.error("Ошибка при отправке сообщения о трафике")
                return False
        
        creds_dict = json.loads(creds_json)
        logger.info("Учетные данные успешно загружены")
        
        creds = service_account.Credentials.from_service_account_info(
            creds_dict,
            scopes=['https://www.googleapis.com/auth/spreadsheets']
        )
        logger.info("Учетные данные успешно настроены")
        
        # Создание сервиса Google Sheets
        service = build('sheets', 'v4', credentials=creds)
        sheet = service.spreadsheets()
        
        # Получаем данные из таблицы
        result = sheet.values().get(
            spreadsheetId=sheet_id,
            range='Traffic!A1:ZZ'  # Получаем всю таблицу
        ).execute()
        
        values = result.get('values', [])
        if not values:
            logger.error("Данные не найдены в таблице")
            
            # Отправляем сообщение об отсутствии данных
            error_message = "❌ Не вдалося отримати дані про трафік з Google Sheets. Таблиця порожня."
            if send_message(error_message, test_mode=False):
                logger.info("Сообщение об ошибке успешно отправлено")
                return True
            else:
                logger.error("Ошибка при отправке сообщения об ошибке")
                return False
        
        # Обрабатываем данные из таблицы
        headers = values[0] if values else []
        domains_data = {}
        
        for row in values[1:]:  # Пропускаем заголовки
            if len(row) >= 2:
                domain = row[0]
                history = []
                
                # Собираем историю трафика
                for i in range(1, len(row)):
                    if i < len(headers):  # Проверяем, что у нас есть соответствующая дата в заголовках
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
                        'traffic': history[0]['traffic'],  # Текущий трафик в первом элементе истории
                        'history': history
                    }
        
        logger.info(f"Загружены данные для {len(domains_data)} доменов")
        
        # Анализируем изменения трафика
        has_changes, traffic_message = analyze_traffic_changes(domains_data)
        
        # Отправляем результаты анализа в Telegram
        logger.info("Отправка сообщения о трафике во все чаты, включая рабочий")
        if send_message(traffic_message, parse_mode="HTML", test_mode=False):
            logger.info("Сообщение о трафике успешно отправлено")
            return True
        else:
            logger.error("Ошибка при отправке сообщения о трафике")
            return False
        
    except Exception as e:
        logger.error(f"Ошибка при обработке данных: {str(e)}")
        import traceback
        error_details = traceback.format_exc()
        logger.error(error_details)
        
        # Отправляем сообщение об ошибке
        error_message = f"❌ Помилка при формуванні повідомлення про трафік: {str(e)}"
        if send_message(error_message, test_mode=False):
            logger.info("Сообщение об ошибке успешно отправлено")
        
        return False

if __name__ == "__main__":
    success = main()
    if not success:
        logger.error("Отправка сообщения завершилась с ошибкой")
        exit(1)
    else:
        logger.info("Отправка сообщения завершена успешно") 