#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Простой тест отправки сообщения в тестовый чат
"""

from telegram_bot import send_message
import logging
from datetime import datetime

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_send_to_test_chat():
    """Тестирует отправку сообщения только в тестовый чат"""
    
    print("=== Тест відправки повідомлення в тестовий чат ===")
    
    # Создаем тестовое сообщение
    test_message = f"""🧪 <b>ТЕСТОВЕ ПОВІДОМЛЕННЯ</b>
📅 Дата: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

📊 <b>Це тест відправки повідомлення з реальних даних</b>

✅ Якщо ви бачите це повідомлення, то:
• Підключення до Telegram API працює
• Функція send_message працює правильно
• test_mode=True коректно відфільтровує робочі чати

🎯 Це повідомлення має прийти ТІЛЬКИ в тестовий чат.

⏰ <i>Час відправки: {datetime.now().strftime('%H:%M:%S')}</i>"""

    print(f"📝 Текст повідомлення:")
    print(test_message)
    print(f"\n📏 Довжина повідомлення: {len(test_message)} символів")
    
    # Отправляем сообщение
    print(f"\n🚀 Відправка повідомлення в тестовий чат...")
    result = send_message(test_message, parse_mode="HTML", test_mode=True)
    
    if result:
        print("✅ Повідомлення успішно відправлено в тестовий чат!")
    else:
        print("❌ Помилка при відправці повідомлення")
    
    return result

if __name__ == "__main__":
    success = test_send_to_test_chat()
    if not success:
        print("\n💡 Можливі причини помилки:")
        print("   1. Відсутній TELEGRAM_BOT_TOKEN")
        print("   2. Проблеми з доступом до Telegram API")
        print("   3. Некоректні ID чатів в telegram_chats.json")
        print("   4. Бот не додано в тестовий чат") 