import os
import logging
import sys
import traceback
import inspect
import importlib

# Налаштування логування
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Надрукуємо всі змінні середовища
logger.info("=== Перевірка змінних середовища ===")
env_vars = {k: v for k, v in os.environ.items() if 'API' in k or 'TOKEN' in k}
logger.info(f"Змінні середовища з API/TOKEN: {env_vars.keys()}")

# Перевіримо наявність AHREFS_API_KEY
ahrefs_key = os.getenv('AHREFS_API_KEY')
logger.info(f"AHREFS_API_KEY: {'Знайдено' if ahrefs_key else 'Не знайдено'}")
if ahrefs_key:
    logger.info(f"Перші 4 символи: {ahrefs_key[:4]}, довжина: {len(ahrefs_key)}")

# Перевіримо імпорт config.py
try:
    import config
    logger.info("config.py успішно імпортовано")
    # Перевіримо змінні в config.py
    if hasattr(config, 'AHREFS_API_KEY'):
        logger.info(f"config.AHREFS_API_KEY: {'Існує' if config.AHREFS_API_KEY else 'Порожній'}")
        if config.AHREFS_API_KEY:
            logger.info(f"Перші 4 символи: {config.AHREFS_API_KEY[:4]}, довжина: {len(config.AHREFS_API_KEY)}")
    else:
        logger.warning("config.AHREFS_API_KEY не знайдено")
except ImportError as e:
    logger.error(f"Помилка імпорту config.py: {e}")

# Перевіримо імпорт ahrefs_api.py
try:
    import ahrefs_api
    logger.info("ahrefs_api.py успішно імпортовано")
    
    # Перевіримо змінні в ahrefs_api.py
    if hasattr(ahrefs_api, 'AHREFS_API_KEY'):
        logger.info(f"ahrefs_api.AHREFS_API_KEY: {'Існує' if ahrefs_api.AHREFS_API_KEY else 'Порожній'}")
        if ahrefs_api.AHREFS_API_KEY:
            logger.info(f"Перші 4 символи: {ahrefs_api.AHREFS_API_KEY[:4]}, довжина: {len(ahrefs_api.AHREFS_API_KEY)}")
    else:
        logger.warning("ahrefs_api.AHREFS_API_KEY не знайдено")
    
    # Перевіримо функцію check_api_availability
    if hasattr(ahrefs_api, 'check_api_availability'):
        logger.info("Функція check_api_availability знайдена")
        # Перевіримо код функції
        func_source = inspect.getsource(ahrefs_api.check_api_availability)
        logger.info(f"Код функції check_api_availability:\n{func_source}")
        
        # Спробуємо викликати
        try:
            logger.info("Викликаємо check_api_availability()...")
            result = ahrefs_api.check_api_availability()
            logger.info(f"Результат виклику: {result}")
        except Exception as e:
            logger.error(f"Помилка при виклику check_api_availability: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
    else:
        logger.warning("Функція check_api_availability не знайдена")
except ImportError as e:
    logger.error(f"Помилка імпорту ahrefs_api.py: {e}")

# Перевіримо, чи є інші файли, що містять AHREFS_API_TOKEN
logger.info("=== Пошук AHREFS_API_TOKEN у файлах ===")
py_files = [f for f in os.listdir('.') if f.endswith('.py')]
for file_name in py_files:
    try:
        with open(file_name, 'r', encoding='utf-8') as f:
            content = f.read()
            if 'AHREFS_API_TOKEN' in content:
                logger.warning(f"Файл {file_name} містить AHREFS_API_TOKEN")
                # Спробуємо знайти рядки з цією змінною
                lines = content.split('\n')
                for i, line in enumerate(lines):
                    if 'AHREFS_API_TOKEN' in line:
                        logger.warning(f"  Рядок {i+1}: {line.strip()}")
    except Exception as e:
        logger.error(f"Помилка при скануванні файлу {file_name}: {e}")

# Тепер спробуємо імітувати ланцюжок викликів з test_runner.py
logger.info("=== Імітація ланцюжка викликів з test_runner.py ===")

# Крок 1: Перевірка наявності токенів
telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
ahrefs_token = os.getenv('AHREFS_API_KEY')
logger.info(f"Telegram token: {'знайдений' if telegram_token else 'не знайдений'}")
logger.info(f"Ahrefs token: {'знайдений' if ahrefs_token else 'не знайдений'}")

# Крок 2: Перевірка API
if hasattr(ahrefs_api, 'check_api_availability'):
    logger.info("Перевірка доступності API Ahrefs...")
    api_available = ahrefs_api.check_api_availability()
    logger.info(f"API Ahrefs: {'доступний' if api_available else 'недоступний'}")
    
    # Крок 3: Перевірка на наявність AHREFS_API_TOKEN
    logger.info("Перевірка наявності AHREFS_API_TOKEN (хоча це не повинно використовуватися)")
    api_token = os.getenv('AHREFS_API_KEY')
    logger.info(f"AHREFS_API_TOKEN: {'знайдений' if api_token else 'не знайдений'}")
    
    # Тільки якщо ми маємо доступ до джерела, перевіряємо це
    if not api_token:
        try:
            import test_runner
            logger.info("Успішно імпортовано test_runner.py")
            
            # Перевіримо, чи є у ньому код, який перевіряє AHREFS_API_TOKEN
            module_source = inspect.getsource(test_runner)
            if 'AHREFS_API_TOKEN' in module_source:
                logger.warning("test_runner.py містить AHREFS_API_TOKEN")
                # Вивантажимо перший рядок, де він використовується
                lines = module_source.split('\n')
                for i, line in enumerate(lines):
                    if 'AHREFS_API_TOKEN' in line and 'os.getenv' in line:
                        logger.warning(f"  Рядок {i+1}: {line.strip()}")
                        # Якщо це перевірка, давайте спробуємо оцінити цей вираз
                        if 'not os.getenv' in line or 'os.getenv' in line and ' if ' in line:
                            try:
                                # Небезпечно, але для діагностики може бути корисно
                                expr = line.strip()
                                result = None
                                # Спробуємо витягти вираз перевірки
                                if 'if not os.getenv' in expr:
                                    check_expr = expr.split('if ')[1].split(':')[0].strip()
                                    logger.info(f"Оцінюємо вираз: {check_expr}")
                                    result = eval(check_expr)
                                logger.info(f"Результат оцінки: {result}")
                            except Exception as e:
                                logger.error(f"Помилка при оцінці виразу: {e}")
        except ImportError:
            logger.error("Не вдалося імпортувати test_runner.py")
            
if __name__ == "__main__":
    logger.info("=== Тест завершено ===") 