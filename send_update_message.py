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
from config import MAIN_SHEET_ID

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def analyze_traffic_changes(domains_data):
    """Анализирует изменения трафика и формирует сообщение для Telegram"""
    critical_changes = []
    consecutive_drops = []
    triple_drops = []
    
    for domain, data in domains_data.items():
        history = data.get('history', [])
        if len(history) >= 2:
            # Сортируем историю по дате (правильно парсим даты)
            from datetime import datetime
            sorted_history = sorted(history, key=lambda x: datetime.strptime(x['date'], '%Y-%m-%d'))
            
            current_traffic = sorted_history[-1]['traffic']  # Последний (самый новый)
            previous_traffic = sorted_history[-3]['traffic'] if len(sorted_history) >= 3 else sorted_history[0]['traffic']  # Двухнедельной давности
            
            # Пропускаем домены с трафиком меньше 1000
            if current_traffic < 1000 or previous_traffic < 1000:
                continue
            
            # Вычисляем изменение в процентах
            change = ((current_traffic - previous_traffic) / previous_traffic) * 100
            
            # Флаг для определения, нужно ли уведомлять
            should_notify = False
            previous_change = None
            
            # 1. Проверяем условие резкого падения на 11%
            if change <= -11:
                critical_changes.append({
                    'domain': domain,
                    'traffic': current_traffic,
                    'change': change
                })
                should_notify = True
                
            # 2. Проверяем условие двух последовательных падений по 5%
            elif len(sorted_history) >= 3:
                traffic_before_previous = sorted_history[-3]['traffic']  # Измерение перед предыдущим
                if traffic_before_previous >= 1000:
                    previous_change = ((previous_traffic - traffic_before_previous) / traffic_before_previous) * 100
                    if previous_change <= -5 and change <= -5:
                        consecutive_drops.append({
                            'domain': domain,
                            'traffic': current_traffic,
                            'change': change,
                            'prev_change': previous_change
                        })
                        should_notify = True
            
            # 3. Условие: падение более 3% в трех последних измерениях подряд
            if len(sorted_history) >= 4 and not should_notify:
                traffic_3ago = sorted_history[-4]['traffic']
                if traffic_3ago >= 1000 and previous_change is not None:
                    change_2 = ((traffic_before_previous - traffic_3ago) / traffic_3ago) * 100
                    if change_2 <= -3 and previous_change <= -3 and change <= -3:
                        triple_drops.append({
                            'domain': domain,
                            'traffic': current_traffic,
                            'change': change,
                            'prev_change': previous_change,
                            'triple_change': change_2
                        })
                        should_notify = True
    
    # Текущая дата
    current_date = datetime.now().strftime("%d.%m.%Y")
    
    # Проверяем, есть ли критические изменения
    if not critical_changes and not consecutive_drops and not triple_drops:
        return False, f"✅ Критичних змін трафіку не виявлено\n\n📆 Дані порівнюються з показниками двотижневої давнини\n📅 Дата звіту: {current_date}"
    
    message = "⚠️ Виявлено падіння трафіку:\n\n"
    
    # Резкие падения
    if critical_changes:
        message += "📉 <b>Різке падіння:</b>\n"
        for change in sorted(critical_changes, key=lambda x: x['change']):
            message += f"• <b>{change['domain']}</b>: {change['traffic']:,} (падіння {abs(change['change']):.1f}% порівняно з двотижневою давниною)\n"
        message += "\n"
    
    # Последовательные падения
    if consecutive_drops:
        message += "📉 <b>Послідовне падіння:</b>\n"
        for drop in sorted(consecutive_drops, key=lambda x: x['change']):
            message += f"• <b>{drop['domain']}</b>: {drop['traffic']:,} (падіння {abs(drop['change']):.1f}% порівняно з двотижневою давниною, попер. падіння {abs(drop['prev_change']):.1f}%)\n"
        message += "\n"
    
    # Тройные падения
    if triple_drops:
        message += "📉 <b>Потрійне падіння:</b>\n"
        for drop in sorted(triple_drops, key=lambda x: x['change']):
            message += f"• <b>{drop['domain']}</b>: {drop['traffic']:,} (три поспіль падіння: {abs(drop['triple_change']):.1f}%, {abs(drop['prev_change']):.1f}%, {abs(drop['change']):.1f}%)\n"
        message += "\n"
    
    # Пояснение
    message += f"📌 Всі показники порівнюються з даними двотижневої давнини\n📅 Дата звіту: {current_date}"
    
    return True, message

def main():
    """Основная функция для отправки сообщения"""
    logger.info("=== Начало отправки сообщения о трафике ===")
    
    # Проверяем наличие токена бота
    if not os.getenv('TELEGRAM_BOT_TOKEN'):
        logger.error("TELEGRAM_BOT_TOKEN не найден в переменных окружения")
        return False
        
    # Настройка доступа к Google Sheets - используем ID из конфигурации
    sheet_id = MAIN_SHEET_ID
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
            
            # Отправляем сообщение в Telegram (test_mode=True только в тестовый чат)
            logger.info("Отправка тестового сообщения о трафике")
            if send_message(traffic_message, parse_mode="HTML", test_mode=True):
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
                    'traffic': history[-1]['traffic'],  # Текущий трафик - последний (самый новый)
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