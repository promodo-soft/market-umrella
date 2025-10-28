#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для автоматичного патчингу функцій, які перевіряють токени.
Достатньо додати імпорт цього модуля перед запуском тестів:

import monkey_patch  # noqa

"""
import logging
import os
import sys
import importlib
import types
import inspect

logger = logging.getLogger("monkey_patch")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

def patch_modules():
    """
    Патчить всі модулі, які містять перевірки AHREFS_API_TOKEN
    """
    logger.info("Початок патчингу функцій для AHREFS_API_TOKEN")
    
    # Патчимо логер для заміни повідомлень про помилки
    original_error = logging.Logger.error
    
    def patched_error(self, msg, *args, **kwargs):
        """Патч для перехоплення повідомлень про AHREFS_API_TOKEN"""
        if isinstance(msg, str) and 'AHREFS_API_TOKEN' in msg:
            # Заміняємо AHREFS_API_TOKEN на AHREFS_API_KEY в повідомленні
            modified_msg = msg.replace('AHREFS_API_TOKEN', 'AHREFS_API_KEY')
            logger.info(f"[PATCH] Заміна повідомлення про помилку:\nСтаре: {msg}\nНове: {modified_msg}")
            return original_error(self, modified_msg, *args, **kwargs)
        return original_error(self, msg, *args, **kwargs)
    
    # Встановлюємо патч
    logging.Logger.error = patched_error
    logger.info("Логер успішно перехоплений")
    
    # Створюємо замінник для функцій, які перевіряють AHREFS_API_TOKEN
    def patched_token_check():
        """Замінник функції, яка перевіряє AHREFS_API_TOKEN"""
        logger.info("[PATCH] Викликана функція перевірки AHREFS_API_TOKEN, використовуємо AHREFS_API_KEY замість неї")
        api_key = os.getenv('AHREFS_API_KEY')
        if not api_key:
            logger.error("AHREFS_API_KEY не знайдений в змінних середовища")
            return False
        return True
    
    # Пошук і патчинг модулів
    for module_name in list(sys.modules.keys()):
        if not module_name.startswith(('_', 'importlib', 'logging', 'types', 'sys', 'os')):
            try:
                module = sys.modules[module_name]
                if hasattr(module, '__file__') and module.__file__:
                    # Перевіряємо, чи це не сам скрипт патчингу
                    if 'monkey_patch.py' in module.__file__:
                        continue
                    
                    # Перевіряємо лише файли в поточній директорії проекту
                    if not module.__file__.startswith(os.getcwd()):
                        continue
                    
                    # Перевіряємо, чи є у модулі функції для патчингу
                    for attr_name in dir(module):
                        if attr_name.startswith('_'):
                            continue
                        
                        try:
                            attr = getattr(module, attr_name)
                            
                            # Перевіряємо, чи це функція
                            if isinstance(attr, types.FunctionType) or isinstance(attr, types.MethodType):
                                try:
                                    # Отримуємо код функції
                                    source = inspect.getsource(attr)
                                    
                                    # Перевіряємо, чи містить функція перевірку AHREFS_API_TOKEN
                                    if 'AHREFS_API_TOKEN' in source and 'os.getenv' in source:
                                        logger.info(f"[PATCH] Знайдена функція {module_name}.{attr_name}, яка містить перевірку AHREFS_API_TOKEN")
                                        
                                        # Створюємо нову функцію, яка змінює поведінку оригінальної
                                        def create_wrapper(original_func):
                                            def wrapper(*args, **kwargs):
                                                logger.info(f"[PATCH] Викликана функція {original_func.__name__}, яка перевіряє AHREFS_API_TOKEN")
                                                
                                                # Тимчасово додаємо AHREFS_API_TOKEN в змінні середовища
                                                if 'AHREFS_API_KEY' in os.environ and 'AHREFS_API_TOKEN' not in os.environ:
                                                    os.environ['AHREFS_API_TOKEN'] = os.environ['AHREFS_API_KEY']
                                                    logger.info("[PATCH] Додано AHREFS_API_TOKEN в змінні середовища на базі AHREFS_API_KEY")
                                                
                                                # Викликаємо оригінальну функцію
                                                result = original_func(*args, **kwargs)
                                                return result
                                            
                                            # Копіюємо атрибути оригінальної функції
                                            wrapper.__name__ = original_func.__name__
                                            wrapper.__doc__ = original_func.__doc__
                                            wrapper.__module__ = original_func.__module__
                                            
                                            return wrapper
                                        
                                        # Замінюємо оригінальну функцію на обгортку
                                        setattr(module, attr_name, create_wrapper(attr))
                                        logger.info(f"[PATCH] Функцію {module_name}.{attr_name} успішно заміненo")
                                
                                except Exception as e:
                                    logger.debug(f"[PATCH] Помилка при аналізі функції {module_name}.{attr_name}: {str(e)}")
                                    continue
                        except Exception as e:
                            logger.debug(f"[PATCH] Помилка при доступі до атрибуту {attr_name} модуля {module_name}: {str(e)}")
                            continue
            
            except Exception as e:
                logger.debug(f"[PATCH] Помилка при обробці модуля {module_name}: {str(e)}")
                continue
    
    logger.info("Патчинг функцій завершений")
    
    # Додаємо AHREFS_API_TOKEN з AHREFS_API_KEY для сумісності
    if 'AHREFS_API_KEY' in os.environ and 'AHREFS_API_TOKEN' not in os.environ:
        os.environ['AHREFS_API_TOKEN'] = os.environ['AHREFS_API_KEY']
        logger.info("Додано AHREFS_API_TOKEN в змінні середовища на базі AHREFS_API_KEY")

# Запускаємо патч при імпорті модуля
patch_modules() 