#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Скрипт для отправки тестового сообщения с данными о трафике
"""

import sys
import os
import logging
from datetime import datetime

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def send_message(message, parse_mode="HTML", test_mode=True):
    """Простая функция отправки сообщения"""
    try:
        import requests
        
        # Токен бота
        bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        if not bot_token:
            logger.error("TELEGRAM_BOT_TOKEN не найден")
            return False
            
        # ID тестового чата
        test_chat_id = "-600437720"  # Тестовый чат
        
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        
        data = {
            'chat_id': test_chat_id,
            'text': message,
            'parse_mode': parse_mode
        }
        
        response = requests.post(url, data=data, timeout=30)
        
        if response.status_code == 200:
            logger.info(f"✅ Сообщение отправлено в тестовый чат {test_chat_id}")
            return True
        else:
            logger.error(f"❌ Ошибка отправки: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Ошибка при отправке сообщения: {str(e)}")
        return False

def create_test_traffic_message():
    """Создает тестовое сообщение с данными о трафике"""
    
    current_date = datetime.now().strftime('%Y-%m-%d')
    
    # Пример данных о трафике (симуляция реальных данных)
    test_domains_data = {
        'example1.com': {
            'traffic': 15420,
            'history': [
                {'date': '2025-06-02', 'traffic': 14850},
                {'date': '2025-06-16', 'traffic': 15420}
            ]
        },
        'example2.com': {
            'traffic': 8930,
            'history': [
                {'date': '2025-06-02', 'traffic': 9200},
                {'date': '2025-06-16', 'traffic': 8930}
            ]
        },
        'example3.com': {
            'traffic': 25600,
            'history': [
                {'date': '2025-06-02', 'traffic': 24100},
                {'date': '2025-06-16', 'traffic': 25600}
            ]
        }
    }
    
    # Анализ изменений
    significant_changes = []
    small_changes = []
    no_changes = []
    
    for domain, data in test_domains_data.items():
        if len(data['history']) >= 2:
            current = data['history'][-1]['traffic']
            previous = data['history'][-2]['traffic']
            
            if previous > 0:
                change_percent = ((current - previous) / previous) * 100
                change_abs = current - previous
                
                if abs(change_percent) >= 10:  # Значительные изменения
                    change_emoji = "📈" if change_percent > 0 else "📉"
                    significant_changes.append(
                        f"{change_emoji} <b>{domain}</b>: {previous:,} → {current:,} "
                        f"({change_abs:+,}, {change_percent:+.1f}%)"
                    )
                elif abs(change_percent) >= 5:  # Небольшие изменения
                    change_emoji = "↗️" if change_percent > 0 else "↘️"
                    small_changes.append(
                        f"{change_emoji} {domain}: {previous:,} → {current:,} "
                        f"({change_abs:+,}, {change_percent:+.1f}%)"
                    )
                else:  # Без изменений
                    no_changes.append(f"🔹 {domain}: {current:,}")
    
    # Формируем сообщение
    message = f"🧪 <b>ТЕСТОВЕ ПОВІДОМЛЕННЯ</b>\n"
    message += f"📊 <b>Звіт про трафік на {current_date}</b>\n\n"
    
    if significant_changes:
        message += "<b>🎯 Значні зміни (≥10%):</b>\n"
        message += "\n".join(significant_changes) + "\n\n"
    
    if small_changes:
        message += "<b>📈 Невеликі зміни (5-10%):</b>\n"
        message += "\n".join(small_changes) + "\n\n"
    
    if no_changes:
        message += "<b>🔹 Без значних змін (<5%):</b>\n"
        message += "\n".join(no_changes[:5])  # Показываем только первые 5
        if len(no_changes) > 5:
            message += f"\n... та ще {len(no_changes) - 5} доменів"
        message += "\n\n"
    
    # Статистика
    total_domains = len(test_domains_data)
    total_traffic = sum(data['traffic'] for data in test_domains_data.values())
    
    message += f"📋 <b>Загальна статистика:</b>\n"
    message += f"• Всього доменів: {total_domains}\n"
    message += f"• Загальний трафік: {total_traffic:,}\n"
    message += f"• Значних змін: {len(significant_changes)}\n"
    message += f"• Невеликих змін: {len(small_changes)}\n"
    message += f"• Без змін: {len(no_changes)}\n\n"
    
    message += f"⏰ <i>Останнє оновлення: {datetime.now().strftime('%H:%M:%S')}</i>\n"
    message += f"🧪 <i>Це тестове повідомлення з прикладом даних</i>"
    
    return message

def main():
    """Основная функция"""
    print("=== Отправка тестового сообщения с данными о трафике ===")
    
    # Проверяем токен
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not bot_token:
        print("❌ TELEGRAM_BOT_TOKEN не найден в переменных окружения")
        return False
    
    print(f"✅ Токен найден (длина: {len(bot_token)})")
    
    # Создаем тестовое сообщение
    message = create_test_traffic_message()
    
    print("\n=== Содержимое сообщения ===")
    # Выводим сообщение без HTML тегов для предварительного просмотра
    import re
    preview = re.sub(r'<[^>]+>', '', message)
    print(preview)
    
    print("\n=== Отправка сообщения ===")
    
    # Отправляем сообщение
    result = send_message(message, parse_mode="HTML", test_mode=True)
    
    if result:
        print("✅ Тестовое сообщение успешно отправлено!")
    else:
        print("❌ Ошибка при отправке тестового сообщения")
    
    return result

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 