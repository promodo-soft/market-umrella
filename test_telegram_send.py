#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Тестовий скрипт для перевірки відправки повідомлень в Telegram
"""

import os
import logging
from telegram_bot import send_message, load_chat_id, TELEGRAM_BOT_TOKEN
try:
    from telegram_bot import PRODUCTION_CHAT_IDS
except ImportError:
    PRODUCTION_CHAT_IDS = ["-1001930136015", "-387031049", "-1001177341323"]

# Налаштування логування
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_telegram_send():
    """Тестує відправку повідомлень в Telegram"""
    
    print("=== Тест відправки повідомлень в Telegram ===")
    
    # Перевіряємо наявність токена
    print(f"TELEGRAM_BOT_TOKEN: {'знайдений' if TELEGRAM_BOT_TOKEN else 'не знайдений'}")
    if TELEGRAM_BOT_TOKEN:
        print(f"Довжина токена: {len(TELEGRAM_BOT_TOKEN)}")
    
    # Завантажуємо чати
    load_chat_id()
    
    # Виводимо інформацію про робочі чати
    print(f"\nРобочі чати (PRODUCTION_CHAT_IDS): {PRODUCTION_CHAT_IDS}")
    
    # Читаємо список всіх чатів
    try:
        import json
        with open('telegram_chats.json', 'r') as f:
            all_chats = json.load(f)
        print(f"\nВсі збережені чати:")
        for chat_id, name in all_chats.items():
            is_production = chat_id in PRODUCTION_CHAT_IDS
            print(f"  {chat_id}: {name} ({'робочий' if is_production else 'тестовий'})")
    except Exception as e:
        print(f"Помилка при читанні telegram_chats.json: {e}")
    
    # Тестуємо відправку в тестовому режимі
    print(f"\n=== Тест 1: відправка в тестовому режимі (test_mode=True) ===")
    test_message = "🧪 Тестове повідомлення в тестовому режимі"
    result1 = send_message(test_message, test_mode=True)
    print(f"Результат: {'успішно' if result1 else 'помилка'}")
    
    # Тестуємо відправку з HTML форматуванням (ТІЛЬКИ в тестові чати)
    print(f"\n=== Тест 2: відправка з HTML форматуванням (ТІЛЬКИ в тестові чати) ===")
    html_message = "<b>🎯 Тестове повідомлення з HTML форматуванням</b>\n\n<i>Курсив</i> та <code>код</code>"
    result2 = send_message(html_message, parse_mode="HTML", test_mode=True)
    print(f"Результат: {'успішно' if result2 else 'помилка'}")
    
    # Симуляція робочого режиму (БЕЗ відправки повідомлення)
    print(f"\n=== Тест 3: перевірка логіки робочого режиму (БЕЗ відправки) ===")
    print("🔍 Перевіряємо які чати були б вибрані для відправки в робочому режимі...")
    # Тут тільки логування, без відправки
    try:
        import json
        with open('telegram_chats.json', 'r') as f:
            all_chats = json.load(f)
        from telegram_bot import PRODUCTION_CHAT_IDS
        
        production_count = sum(1 for cid in all_chats.keys() if cid in PRODUCTION_CHAT_IDS)
        test_count = len(all_chats) - production_count
        print(f"📊 Всього чатів: {len(all_chats)}")
        print(f"📊 Робочих чатів: {production_count}")
        print(f"📊 Тестових чатів: {test_count}")
        result3 = True  # Завжди успішно, бо не відправляємо
    except Exception as e:
        print(f"❌ Помилка при аналізі чатів: {e}")
        result3 = False
    
    return result1, result2, result3

if __name__ == "__main__":
    results = test_telegram_send()
    print(f"\n=== Підсумок тестів ===")
    print(f"Тестовий режим: {'✅' if results[0] else '❌'}")
    print(f"HTML форматування (тестові чати): {'✅' if results[1] else '❌'}")
    print(f"Перевірка логіки робочого режиму: {'✅' if results[2] else '❌'}")
    
    print(f"\n🔐 Примітка: Відправка тільки в тестові чати для безпеки") 