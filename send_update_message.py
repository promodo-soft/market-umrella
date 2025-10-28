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

def is_data_fresh(domains_data, max_days=7):
    """
    Проверяет, насколько свежие данные о трафике.
    
    Args:
        domains_data (dict): Словарь с данными о трафике по доменам
        max_days (int): Максимальное количество дней для считания данных свежими
        
    Returns:
        tuple: (свежие ли данные, количество дней с последнего обновления)
    """
    if not domains_data:
        return False, 999
    
    # Ищем самую свежую дату в данных
    latest_date = None
    for domain, data in domains_data.items():
        history = data.get('history', [])
        if history:
            # Сортируем историю по дате
            sorted_history = sorted(history, key=lambda x: x['date'])
            domain_latest = sorted_history[-1]['date']
            
            try:
                domain_date = datetime.strptime(domain_latest, '%Y-%m-%d')
                if latest_date is None or domain_date > latest_date:
                    latest_date = domain_date
            except ValueError:
                continue
    
    if latest_date is None:
        return False, 999
    
    # Вычисляем разницу в днях
    current_date = datetime.now()
    days_diff = (current_date - latest_date).days
    
    logger.info(f"Остання дата даних: {latest_date.strftime('%Y-%m-%d')}, днів тому: {days_diff}")
    
    return days_diff <= max_days, days_diff

def analyze_traffic_changes(domains_data):
    """
    Анализирует изменения трафика и формирует сообщения для Telegram.
    
    Args:
        domains_data (dict): Словарь с данными о трафике по доменам
        
    Returns:
        tuple: (есть ли критические изменения, текст сообщения о падениях, текст сообщения о росте)
    """
    # Проверяем свежесть данных
    is_fresh, days_old = is_data_fresh(domains_data, max_days=7)
    
    if not is_fresh:
        logger.warning(f"Дані застарілі на {days_old} днів. Пропускаємо аналіз змін трафіку. Повідомлення НЕ відправляються.")
        return False, None, None  # Возвращаем None для обоих сообщений
    
    critical_changes = []
    consecutive_drops = []
    triple_drops = []
    growth_domains = {}
    
    logger.info(f"Аналізуємо зміни трафіку для {len(domains_data)} доменів (дані свіжі: {days_old} днів тому)")
    
    for domain, data in domains_data.items():
        history = data.get('history', [])
        if len(history) >= 2:
            # Сортируем историю по дате
            sorted_history = sorted(history, key=lambda x: x['date'])
            
            current_traffic = sorted_history[-1]['traffic']  # Последний (самый новый)
            previous_traffic = sorted_history[-3]['traffic'] if len(sorted_history) >= 3 else sorted_history[0]['traffic']  # Двухнедельной давности для падений
            
            # Логируем все изменения трафика для диагностики
            change_percent = ((current_traffic - previous_traffic) / previous_traffic) * 100 if previous_traffic > 0 else 0
            logger.info(f"Домен {domain}: поточний трафік {current_traffic}, попередній {previous_traffic}, зміна {change_percent:.1f}%")
            
            # Пропускаем домены с трафиком меньше 1000
            if current_traffic < 1000 or previous_traffic < 1000:
                logger.info(f"Пропускаємо домен {domain} через недостатній трафік")
                continue
            
            # Вычисляем изменение в процентах для падений
            change = ((current_traffic - previous_traffic) / previous_traffic) * 100
            
            # Флаг для определения, нужно ли уведомлять о падении
            should_notify = False
            previous_change = None
            triple_change = None
            
            # 1. Проверяем условие резкого падения на 11%
            if change <= -11:
                logger.info(f"Виявлено різке падіння для {domain}: {change:.1f}%")
                critical_changes.append({
                    'domain': domain,
                    'traffic': current_traffic,
                    'change': change,
                    'type': 'sharp'
                })
                should_notify = True
            
            # 2. Проверяем условие двух последовательных падений по 5%
            elif len(sorted_history) >= 3:
                traffic_before_previous = sorted_history[-3]['traffic']  # Измерение перед предыдущим
                if traffic_before_previous >= 1000:
                    previous_change = ((previous_traffic - traffic_before_previous) / traffic_before_previous) * 100
                    if previous_change <= -5 and change <= -5:
                        logger.info(f"Виявлено послідовне падіння для {domain}: поточне {change:.1f}%, попереднє {previous_change:.1f}%")
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
                        logger.info(f"Виявлено потрійне падіння для {domain}: {change_2:.1f}%, {previous_change:.1f}%, {change:.1f}%")
                        triple_drops.append({
                            'domain': domain,
                            'traffic': current_traffic,
                            'change': change,
                            'prev_change': previous_change,
                            'triple_change': change_2
                        })
                        should_notify = True
            
            # Анализ роста (сравниваем соседние периоды)
            if len(sorted_history) >= 2:
                recent_traffic = sorted_history[-2]['traffic']  # Предпоследний для анализа роста
                if recent_traffic >= 1000:
                    growth_percent = ((current_traffic - recent_traffic) / recent_traffic) * 100
                    if growth_percent >= 15.0:
                        growth_domains[domain] = {
                            'current_traffic': current_traffic,
                            'previous_traffic': recent_traffic,
                            'growth_percent': growth_percent,
                            'current_date': sorted_history[-1]['date'],
                            'previous_date': sorted_history[-2]['date']
                        }
                        logger.info(f"Виявлено ріст для {domain}: {growth_percent:.1f}%")
    
    # Текущая дата для отображения в сообщении
    current_date = datetime.now().strftime("%d.%m.%Y")
    
    # Формируем сообщение о падениях
    if not critical_changes and not consecutive_drops and not triple_drops:
        drops_message = f"✅ Критичних змін трафіку не виявлено\n\n📆 Дані порівнюються з показниками двотижневої давнини\n📅 Дата звіту: {current_date}"
    else:
        drops_message = "⚠️ Виявлено падіння трафіку:\n\n"
        
        # Сначала выводим резкие падения
        if critical_changes:
            drops_message += "📉 Різке падіння:\n"
            for change in sorted(critical_changes, key=lambda x: x['change']):
                drops_message += f"• <b>{change['domain']}</b>: {change['traffic']:,} (падіння {abs(change['change']):.1f}% порівняно з двотижневою давниною)\n"
            drops_message += "\n"
        
        # Затем выводим последовательные падения
        if consecutive_drops:
            drops_message += "📉 Послідовне падіння:\n"
            for drop in sorted(consecutive_drops, key=lambda x: x['change']):
                drops_message += f"• <b>{drop['domain']}</b>: {drop['traffic']:,} (падіння {abs(drop['change']):.1f}% порівняно з двотижневою давниною, попер. падіння {abs(drop['prev_change']):.1f}%)\n"
            drops_message += "\n"
        
        # Тройные падения
        if triple_drops:
            drops_message += "📉 Потрійне падіння:\n"
            for drop in sorted(triple_drops, key=lambda x: x['change']):
                drops_message += f"• <b>{drop['domain']}</b>: {drop['traffic']:,} (три поспіль падіння: {abs(drop['triple_change']):.1f}%, {abs(drop['prev_change']):.1f}%, {abs(drop['change']):.1f}%)\n"
            drops_message += "\n"
        
        # Добавляем пояснение и дату
        drops_message += f"📌 Всі показники порівнюються з даними двотижневої давнини\n📅 Дата звіту: {current_date}"
    
    # Формируем сообщение о росте
    growth_message = None
    if growth_domains:
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
                f"📈 <b>{domain}</b>: {current_formatted} (було {previous_formatted}, +{growth:.1f}%)"
            )
        
        message_parts.append(f"\n📊 Всього доменів з ростом 15%+: {len(growth_domains)}")
        message_parts.append(f"📌 Порівняння з попереднім вимірюванням")
        message_parts.append(f"📅 Дата звіту: {current_date}")
        
        growth_message = "\n".join(message_parts)
    
    has_critical_changes = bool(critical_changes or consecutive_drops or triple_drops)
    
    return has_critical_changes, drops_message, growth_message

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
            
            has_changes, traffic_message, growth_message = analyze_traffic_changes(domains_data)
            
            # Если сообщения None (данные устарели), не отправляем ничего
            if traffic_message is None and growth_message is None:
                logger.info("Тестове повідомлення не відправляється через застарілість даних.")
                return True
            
            # Проверяем, есть ли реальные изменения (падения или рост)
            # Если есть только сообщение "Критичних змін трафіку не виявлено" и нет роста, не отправляем
            if (not has_changes and 
                traffic_message and "Критичних змін трафіку не виявлено" in traffic_message and 
                not growth_message):
                logger.info("Тестове повідомлення не відправляється - немає критичних змін трафіку та росту доменів.")
                return True
            
            # Формируем тестовое сообщение
            test_message = f"✅ Тестові дані про трафік для {len(domains_data)} доменів\n\n"
            
            # Добавляем сообщение о падениях если есть
            if traffic_message:
                test_message += traffic_message + "\n\n"
            
            # Добавляем сообщение о росте если есть
            if growth_message:
                test_message += growth_message + "\n\n"
            
            # Добавляем примечание о тестовом характере данных
            test_message += "\n\n<i>Примітка: Це тестове повідомлення з тестовими даними, оскільки не вдалося отримати реальні дані з Google Sheets.</i>"
            
            # Отправляем сообщение в Telegram (test_mode=True только в тестовый чат)
            logger.info("Отправка тестового сообщения о трафике")
            if send_message(test_message, parse_mode="HTML", test_mode=True):
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
        has_changes, traffic_message, growth_message = analyze_traffic_changes(domains_data)
        
        # Если сообщения None (данные устарели), не отправляем ничего
        if traffic_message is None and growth_message is None:
            logger.info("Повідомлення не відправляється через застарілість даних.")
            return True
        
        # Проверяем, есть ли реальные изменения (падения или рост)
        # Если есть только сообщение "Критичних змін трафіку не виявлено" и нет роста, не отправляем
        if (not has_changes and 
            traffic_message and "Критичних змін трафіку не виявлено" in traffic_message and 
            not growth_message):
            logger.info("Повідомлення не відправляється - немає критичних змін трафіку та росту доменів.")
            return True
        
        # Формируем объединенное сообщение
        full_message = f"✅ Дані про трафік успішно оновлено для {len(domains_data)} доменів\n\n"
        
        # Добавляем сообщение о падениях если есть
        if traffic_message:
            full_message += traffic_message + "\n\n"
        
        # Добавляем сообщение о росте если есть
        if growth_message:
            full_message += growth_message
        
        # Отправляем результаты анализа в Telegram
        logger.info("Отправка сообщения о трафике во все чаты, включая рабочий")
        if send_message(full_message, parse_mode="HTML", test_mode=False):
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