# Робота з Google Sheets

## Оновлення: дані тепер зберігаються в Google Sheets

Система була оновлена для роботи з Google Sheets замість локальних Excel файлів.

### ID таблиці Google Sheets

**Основна таблиця**: `1iwr3qku-JcMMqEBTYdWeWRUXfmC9sLp_s-q-Ruxj5xs`
**Посилання**: https://docs.google.com/spreadsheets/d/1iwr3qku-JcMMqEBTYdWeWRUXfmC9sLp_s-q-Ruxj5xs/edit?gid=0#gid=0

### Оновлені файли

1. **test_runner.py** - основний скрипт для збору даних
2. **send_real_traffic_from_sheets.py** - відправка реальних повідомлень
3. **test_enhanced_logic.py** - тестування логіки
4. **show_full_message.py** - показ повних повідомлень
5. **test_google_sheets.py** - тестування підключення

### Структура таблиці

- **Стовпець A**: Домени
- **Стовпці B і далі**: Дані трафіку за різні періоди
- **Рядок 1**: Заголовки (Domain, дати збору даних)

### Змінні середовища

Для роботи з Google Sheets потрібна змінна:
- `GOOGLE_SHEETS_CREDENTIALS` - JSON credentials для Service Account

### Функції для роботи з Google Sheets

#### get_real_traffic_data_from_sheets()
Отримує дані трафіку з Google Sheets та формує структуру для аналізу.

```python
def get_real_traffic_data_from_sheets():
    """Отримує реальні дані трафіку з Google Sheets"""
```

#### test_google_sheets_connection()
Тестує підключення до Google Sheets.

```python
def test_google_sheets_connection():
    """Тестує підключення до Google Sheets"""
```

### Логіка роботи

1. **Автентифікація**: Використання Service Account credentials
2. **Читання даних**: Отримання всіх стовпців з таблиці
3. **Обробка**: Перетворення у формат для аналізу
4. **Аналіз**: Використання існуючої функції `analyze_traffic_changes()`

### Тестування

Для тестування підключення до Google Sheets:
```bash
python test_google_sheets.py
```

Для відправки реального повідомлення з Google Sheets:
```bash
python send_real_traffic_from_sheets.py
```

### Переваги нового підходу

- ✅ Централізоване зберігання даних
- ✅ Можливість колаборації
- ✅ Автоматична синхронізація
- ✅ Доступ з будь-якого місця
- ✅ Версіонування змін
- ✅ Резервне копіювання Google

### Міграція даних

Якщо у вас є локальний файл `traffic_data.xlsx`, дані потрібно перенести в Google Sheets:

1. Відкрити Google Sheets за посиланням
2. Імпортувати дані з Excel файлу
3. Перевірити структуру (домен у стовпці A, трафік у наступних стовпцях)
4. Запустити тест: `python test_google_sheets.py`

### Вимоги

```
google-auth==2.17.3
google-auth-oauthlib==1.0.0
google-auth-httplib2==0.1.0
google-api-python-client==2.88.0
```

### Логіка аналізу залишається незмінною

Система все ще підтримує:
- ✅ Різке падіння ≥ -11%
- ✅ Два послідовних падіння ≥ -5%
- ✅ Три послідовних падіння ≥ -3%
- ❌ ~~Чотири послідовних падіння ≥ -2%~~ (видалено) 