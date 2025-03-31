import os
import logging
import inspect
import importlib.util
import sys

# Налаштування логування
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def check_modules_for_token_usage():
    """
    Перевіряє всі модулі на використання AHREFS_API_TOKEN та AHREFS_API_KEY
    """
    logger.info("=== Початок пошуку використання токенів API в коді ===")
    
    # Отримуємо список всіх Python файлів у поточній директорії
    files = [f for f in os.listdir('.') if f.endswith('.py')]
    logger.info(f"Знайдено {len(files)} Python файлів у поточній директорії")
    
    for file_name in files:
        logger.info(f"Перевірка файлу: {file_name}")
        try:
            with open(file_name, 'r', encoding='utf-8') as f:
                content = f.read()
                
                # Шукаємо згадки токенів
                if 'AHREFS_API_TOKEN' in content:
                    logger.warning(f"Знайдено використання AHREFS_API_TOKEN у файлі {file_name}")
                    
                    # Вивантажуємо номери рядків, де використовується токен
                    lines = content.split('\n')
                    for i, line in enumerate(lines):
                        if 'AHREFS_API_TOKEN' in line:
                            logger.warning(f"  Рядок {i+1}: {line.strip()}")
                
                if 'AHREFS_API_KEY' in content:
                    logger.info(f"Знайдено використання AHREFS_API_KEY у файлі {file_name}")
        except Exception as e:
            logger.error(f"Помилка при перевірці файлу {file_name}: {str(e)}")
    
    logger.info("=== Перевірка завершена ===")

def test_environment_variables():
    """
    Тестує наявність змінних середовища
    """
    logger.info("=== Перевірка змінних середовища ===")
    
    # Перевіряємо наявність токенів
    ahrefs_token = os.getenv('AHREFS_API_KEY')
    old_token = os.getenv('AHREFS_API_KEY')
    
    logger.info(f"AHREFS_API_KEY: {'знайдений' if ahrefs_token else 'не знайдений'}")
    if ahrefs_token:
        logger.info(f"  Довжина: {len(ahrefs_token)}")
        logger.info(f"  Перші 4 символи: {ahrefs_token[:4]}")
    
    logger.info(f"AHREFS_API_TOKEN: {'знайдений' if old_token else 'не знайдений'}")
    if old_token:
        logger.info(f"  Довжина: {len(old_token)}")
        logger.info(f"  Перші 4 символи: {old_token[:4]}")
    
    logger.info("=== Перевірка завершена ===")

def inspect_ahrefs_api_module():
    """
    Інспектує модуль ahrefs_api для виявлення проблем
    """
    logger.info("=== Інспекція модуля ahrefs_api ===")
    
    try:
        # Завантажуємо модуль ahrefs_api динамічно
        spec = importlib.util.spec_from_file_location("ahrefs_api", "./ahrefs_api.py")
        ahrefs_api = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(ahrefs_api)
        
        # Перевіряємо наявність змінних у модулі
        if hasattr(ahrefs_api, 'AHREFS_API_KEY'):
            logger.info(f"Модуль має змінну AHREFS_API_KEY: {bool(ahrefs_api.AHREFS_API_KEY)}")
        else:
            logger.warning("Модуль не має змінної AHREFS_API_KEY")
        
        # Перевіряємо функцію перевірки доступності API
        if hasattr(ahrefs_api, 'check_api_availability'):
            logger.info("Модуль має функцію check_api_availability")
            func_source = inspect.getsource(ahrefs_api.check_api_availability)
            if 'AHREFS_API_TOKEN' in func_source:
                logger.warning("Функція check_api_availability використовує AHREFS_API_TOKEN!")
            if 'AHREFS_API_KEY' in func_source:
                logger.info("Функція check_api_availability використовує AHREFS_API_KEY")
        else:
            logger.warning("Модуль не має функції check_api_availability")
            
        # Перевіряємо функцію отримання трафіку
        if hasattr(ahrefs_api, 'get_organic_traffic'):
            logger.info("Модуль має функцію get_organic_traffic")
            func_source = inspect.getsource(ahrefs_api.get_organic_traffic)
            if 'AHREFS_API_TOKEN' in func_source:
                logger.warning("Функція get_organic_traffic використовує AHREFS_API_TOKEN!")
            if 'AHREFS_API_KEY' in func_source:
                logger.info("Функція get_organic_traffic використовує AHREFS_API_KEY")
        else:
            logger.warning("Модуль не має функції get_organic_traffic")
    
    except Exception as e:
        logger.error(f"Помилка при інспекції модуля ahrefs_api: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
    
    logger.info("=== Інспекція завершена ===")

if __name__ == "__main__":
    logger.info("=== Запуск діагностики проблеми з AHREFS_API_TOKEN ===")
    
    # Встановлюємо змінну середовища для тестування
    os.environ['AHREFS_API_KEY'] = "test_key_for_diagnostics"
    
    # Перевіряємо змінні середовища
    test_environment_variables()
    
    # Шукаємо використання токенів у коді
    check_modules_for_token_usage()
    
    # Інспектуємо модуль ahrefs_api
    inspect_ahrefs_api_module()
    
    logger.info("=== Діагностика завершена ===") 