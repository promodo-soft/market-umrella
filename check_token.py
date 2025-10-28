import os
import requests
import json
import traceback
from dotenv import load_dotenv

# Завантажуємо змінні середовища з файлу .env
load_dotenv()

try:
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not token:
        print("TELEGRAM_BOT_TOKEN не знайдено в змінних середовища")
        exit(1)
    
    print(f"Перевірка токена: {token[:5]}...{token[-5:]}")
    
    response = requests.get(f'https://api.telegram.org/bot{token}/getMe')
    result = response.json()
    
    print(f"Відповідь API: {json.dumps(result, indent=2, ensure_ascii=False)}")
    
    if result.get('ok'):
        print(f"✅ Токен валідний! Бот: {result['result']['first_name']} (@{result['result'].get('username', 'немає юзернейму')})")
    else:
        print(f"❌ Токен невалідний! Помилка: {result.get('description', 'Невідома помилка')}")
        
    # Перевірка доступу до тестового чату
    test_chat_id = "292222416"  # TrishkinVlad (тестовий чат)
    print(f"\nПеревірка доступу до тестового чату {test_chat_id}...")
    
    try:
        chat_response = requests.get(f'https://api.telegram.org/bot{token}/getChat?chat_id={test_chat_id}')
        chat_result = chat_response.json()
        
        if chat_result.get('ok'):
            print(f"✅ Доступ до тестового чату {test_chat_id} є! Назва чату: {chat_result['result'].get('title', 'Приватний чат')}")
        else:
            print(f"❌ Немає доступу до тестового чату {test_chat_id}! Помилка: {chat_result.get('description', 'Невідома помилка')}")
    except Exception as e:
        print(f"❌ Помилка при перевірці доступу до тестового чату: {str(e)}")
    
    # Спроба відправити повідомлення в тестовий чат
    print(f"\nСпроба відправити повідомлення в тестовий чат {test_chat_id}...")
    
    try:
        message = "🔍 Це тестове повідомлення для перевірки функціональності бота"
        send_response = requests.post(
            f'https://api.telegram.org/bot{token}/sendMessage',
            json={
                'chat_id': test_chat_id,
                'text': message,
                'parse_mode': 'Markdown'
            }
        )
        send_result = send_response.json()
        
        print(f"Відповідь API на відправку повідомлення: {json.dumps(send_result, indent=2, ensure_ascii=False)}")
        
        if send_result.get('ok'):
            print(f"✅ Повідомлення успішно відправлено в тестовий чат {test_chat_id}!")
        else:
            print(f"❌ Не вдалося відправити повідомлення в тестовий чат {test_chat_id}! Помилка: {send_result.get('description', 'Невідома помилка')}")
    except Exception as e:
        print(f"❌ Помилка при відправці повідомлення в тестовий чат: {str(e)}")
        
    # Перевірка робочого чату
    working_chat_id = "-1001930136015"  # Робочий чат SEO & CSD
    print(f"\nПеревірка доступу до робочого чату {working_chat_id}...")
    
    try:
        chat_response = requests.get(f'https://api.telegram.org/bot{token}/getChat?chat_id={working_chat_id}')
        chat_result = chat_response.json()
        
        if chat_result.get('ok'):
            print(f"✅ Доступ до робочого чату {working_chat_id} є! Назва чату: {chat_result['result'].get('title', 'Невідомо')}")
        else:
            print(f"❌ Немає доступу до робочого чату {working_chat_id}! Помилка: {chat_result.get('description', 'Невідома помилка')}")
    except Exception as e:
        print(f"❌ Помилка при перевірці доступу до робочого чату: {str(e)}")
        print(f"Деталі: {traceback.format_exc()}")
        
except Exception as e:
    print(f"❌ Загальна помилка: {str(e)}")
    print(f"Деталі: {traceback.format_exc()}") 