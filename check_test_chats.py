import requests
import json
import os
from dotenv import load_dotenv
import time

# Завантажуємо змінні з .env файлу
load_dotenv()

# Отримуємо токен бота
token = os.getenv('TELEGRAM_BOT_TOKEN')
if not token:
    print("Помилка: TELEGRAM_BOT_TOKEN не знайдено")
    exit(1)

print(f"Використовую токен: {token[:5]}...{token[-5:]}")

# Перевіряємо інформацію про бота
print("\nОтримую інформацію про бота...")
try:
    bot_info = requests.get(f'https://api.telegram.org/bot{token}/getMe').json()
    if bot_info.get('ok'):
        bot = bot_info['result']
        print(f"Бот: {bot['first_name']} (@{bot.get('username')}), ID: {bot['id']}")
    else:
        print(f"❌ Помилка отримання інформації про бота: {bot_info}")
except Exception as e:
    print(f"❌ Виникла помилка при отриманні інформації про бота: {str(e)}")

# Отримуємо оновлення для пошуку нового тестового чату
print("\nШукаю нові тестові чати...")
try:
    updates = requests.get(f'https://api.telegram.org/bot{token}/getUpdates').json()
    new_test_chat = None
    
    if updates.get('ok'):
        print(f"Отримано {len(updates.get('result', []))} оновлень")
        for update in updates.get('result', []):
            if 'message' in update and 'chat' in update['message']:
                chat = update['message']['chat']
                chat_id = chat['id']
                
                # Шукаємо особисті чати (не групи)
                if chat.get('type') == 'private' and 'first_name' in chat:
                    print(f"Знайдено особистий чат: {chat.get('first_name')} (ID: {chat_id})")
                    
                    # Перевіряємо, чи це новий чат (перевіряємо текст повідомлення)
                    if 'text' in update['message'] and update['message']['text'].startswith('/start'):
                        new_test_chat = {
                            'id': str(chat_id),
                            'name': f"{chat.get('first_name')} {chat.get('last_name', '')}".strip()
                        }
    else:
        print(f"❌ Помилка отримання оновлень: {updates}")
        
    if new_test_chat:
        print(f"✅ Знайдено новий тестовий чат: {new_test_chat['name']} (ID: {new_test_chat['id']})")
        
        # Оновлюємо файл чатів
        try:
            with open('telegram_chats.json', 'r') as f:
                chats = json.load(f)
                
            # Додаємо новий тестовий чат
            chats[new_test_chat['id']] = new_test_chat['name']
            
            with open('telegram_chats.json', 'w') as f:
                json.dump(chats, f, indent=2)
                
            print(f"✅ Тестовий чат додано до файлу telegram_chats.json")
            
            # Надсилаємо тестове повідомлення
            test_message = f"✅ Вітаю! Цей чат тепер налаштований як тестовий чат для бота Market Umbrella."
            
            response = requests.post(
                f'https://api.telegram.org/bot{token}/sendMessage',
                json={
                    'chat_id': new_test_chat['id'],
                    'text': test_message
                }
            )
            
            if response.status_code == 200 and response.json().get('ok'):
                print(f"✅ Тестове повідомлення надіслано в чат {new_test_chat['name']}")
            else:
                print(f"❌ Помилка надсилання тестового повідомлення: {response.text}")
                
        except Exception as e:
            print(f"❌ Помилка при оновленні файлу чатів: {str(e)}")
    else:
        print("❌ Нових тестових чатів не знайдено. Будь ласка, додайте бота в особистий чат і відправте команду /start")
        
except Exception as e:
    print(f"❌ Виникла помилка при пошуку нових чатів: {str(e)}") 