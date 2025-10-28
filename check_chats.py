import requests
import json
import os
from dotenv import load_dotenv

# Завантажуємо змінні з .env файлу
load_dotenv()

# Отримуємо токен бота
token = os.getenv('TELEGRAM_BOT_TOKEN')
if not token:
    print("Помилка: TELEGRAM_BOT_TOKEN не знайдено")
    exit(1)

# Завантажуємо список чатів
with open('telegram_chats.json', 'r') as f:
    chats = json.load(f)

print(f"Знайдено {len(chats)} чатів:")
for chat_id, name in chats.items():
    print(f"ID: {chat_id}, Назва: {name}")

print("\nПочинаю надсилати тестові повідомлення...")

# Надсилаємо повідомлення в кожен чат
for chat_id, name in chats.items():
    print(f"\nНадсилаю повідомлення до чату {name} (ID: {chat_id}):")
    
    message = f"Тестове повідомлення для перевірки чату '{name}' (ID: {chat_id}). Будь ласка, підтвердіть отримання."
    
    try:
        response = requests.post(
            f'https://api.telegram.org/bot{token}/sendMessage',
            json={
                'chat_id': chat_id,
                'text': message
            }
        )
        
        if response.status_code == 200 and response.json().get('ok'):
            print(f"✅ Повідомлення успішно надіслано в чат '{name}'")
        else:
            print(f"❌ Помилка надсилання повідомлення: {response.text[:100]}...")
    except Exception as e:
        print(f"❌ Виникла помилка: {str(e)}")
        
print("\nПеревірка завершена. Перевірте отримані повідомлення в кожному чаті.") 