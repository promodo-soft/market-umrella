#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import sys
import logging
import re
from unittest.mock import patch

# Оригінальний метод error з логгера
original_error = logging.Logger.error

# Перехоплювач повідомлень про помилки
def error_interceptor(self, msg, *args, **kwargs):
    if isinstance(msg, str) and 'AHREFS_API_TOKEN' in msg:
        # Заміняємо AHREFS_API_TOKEN на AHREFS_API_KEY в повідомленні
        modified_msg = msg.replace('AHREFS_API_TOKEN', 'AHREFS_API_KEY')
        print(f"[INTERCEPTOR] Заміна повідомлення про помилку:\nСтаре: {msg}\nНове: {modified_msg}")
        
        # Викликаємо оригінальний метод з модифікованим повідомленням
        return original_error(self, modified_msg, *args, **kwargs)
    
    # Якщо повідомлення не містить AHREFS_API_TOKEN, викликаємо оригінальний метод
    return original_error(self, msg, *args, **kwargs)

def patch_logger():
    """Замінює метод error у всіх логерах"""
    # Патчимо клас Logger
    logging.Logger.error = error_interceptor
    print("[INTERCEPTOR] Логер успішно перехоплений")

def run_test_runner():
    """Запускає test_runner.py з перехопленням помилок"""
    # Патчимо логер
    patch_logger()
    
    # Додаємо змінну середовища, щоб відслідковувати запуск через нашу обгортку
    os.environ['RUNNER_PATCHED'] = 'true'
    
    # Запускаємо test_runner як модуль
    print("[INTERCEPTOR] Запускаємо test_runner.py з перехопленням помилок")
    
    # Імпортуємо і запускаємо test_runner
    try:
        # Додаємо поточну директорію до шляху пошуку модулів
        sys.path.insert(0, os.getcwd())
        
        # Імпортуємо модуль
        import test_runner
        
        # Якщо у модулі є функція run_test, запускаємо її
        if hasattr(test_runner, 'run_test'):
            print("[INTERCEPTOR] Викликаємо test_runner.run_test()")
            result = test_runner.run_test()
            print(f"[INTERCEPTOR] Результат виконання test_runner.run_test(): {result}")
        elif hasattr(test_runner, 'main'):
            print("[INTERCEPTOR] Викликаємо test_runner.main()")
            result = test_runner.main()
            print(f"[INTERCEPTOR] Результат виконання test_runner.main(): {result}")
        else:
            print("[INTERCEPTOR] Скрипт test_runner.py не містить функцій run_test() або main()")
            print("[INTERCEPTOR] Виконуємо скрипт напряму:")
            
            # Запускаємо скрипт напряму
            with open('test_runner.py', 'r', encoding='utf-8') as f:
                exec(f.read(), {'__name__': '__main__'})
    
    except Exception as e:
        print(f"[INTERCEPTOR] Помилка при виконанні test_runner.py: {str(e)}")
        import traceback
        print(f"[INTERCEPTOR] Traceback: {traceback.format_exc()}")
        sys.exit(1)

if __name__ == "__main__":
    print("[INTERCEPTOR] Початок виконання fix_runner.py")
    run_test_runner()
    print("[INTERCEPTOR] Завершення fix_runner.py") 