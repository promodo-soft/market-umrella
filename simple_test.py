#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Простой тест отправки сообщений в Telegram
"""

import os
from telegram_bot import send_message

print("=== Простой тест Telegram ===")

# Тест отправки в тестовые чаты
print("Тест 1: Отправка в тестовые чаты...")
message = "🧪 Простое тестовое сообщение"
result1 = send_message(message, test_mode=True)
print(f"Результат: {'успешно' if result1 else 'ошибка'}")

print("\nГотово!") 