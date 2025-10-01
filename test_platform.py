#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тестовый скрипт для проверки всех функций платформы
"""

import os
import sys
import sqlite3
import requests
import time
from datetime import datetime

def test_database():
    """Тест базы данных"""
    print("🔍 Тестирование базы данных...")
    
    try:
        # Проверяем существование файла БД
        if not os.path.exists('telegram_platform.db'):
            print("❌ База данных не найдена")
            return False
        
        # Подключаемся к БД
        conn = sqlite3.connect('telegram_platform.db')
        cursor = conn.cursor()
        
        # Проверяем таблицы
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        required_tables = ['accounts', 'proxies', 'blacklist', 'parsed_users', 'campaigns']
        missing_tables = [table for table in required_tables if table not in tables]
        
        if missing_tables:
            print(f"❌ Отсутствуют таблицы: {missing_tables}")
            return False
        
        print("✅ База данных работает корректно")
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Ошибка базы данных: {e}")
        return False

def test_web_server():
    """Тест веб-сервера"""
    print("🌐 Тестирование веб-сервера...")
    
    try:
        # Проверяем доступность сервера
        response = requests.get('http://localhost:5000', timeout=5)
        
        if response.status_code == 200:
            print("✅ Веб-сервер работает")
            return True
        else:
            print(f"❌ Веб-сервер вернул код: {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Веб-сервер недоступен")
        return False
    except Exception as e:
        print(f"❌ Ошибка веб-сервера: {e}")
        return False

def test_api_endpoints():
    """Тест API endpoints"""
    print("🔌 Тестирование API endpoints...")
    
    endpoints = [
        '/api/accounts',
        '/api/proxies',
        '/api/blacklist',
        '/api/stats'
    ]
    
    working_endpoints = 0
    
    for endpoint in endpoints:
        try:
            response = requests.get(f'http://localhost:5000{endpoint}', timeout=5)
            if response.status_code == 200:
                print(f"✅ {endpoint} - работает")
                working_endpoints += 1
            else:
                print(f"❌ {endpoint} - код {response.status_code}")
        except Exception as e:
            print(f"❌ {endpoint} - ошибка: {e}")
    
    if working_endpoints == len(endpoints):
        print("✅ Все API endpoints работают")
        return True
    else:
        print(f"⚠️ Работают {working_endpoints}/{len(endpoints)} endpoints")
        return False

def test_file_structure():
    """Тест структуры файлов"""
    print("📁 Тестирование структуры файлов...")
    
    required_files = [
        'app.py',
        'config.py',
        'requirements.txt',
        'static/js/main.js',
        'static/css/style.css',
        'templates/base.html',
        'templates/index.html',
        'templates/accounts.html',
        'templates/parsing.html',
        'templates/campaigns.html',
        'templates/registration.html',
        'templates/invitations.html',
        'templates/subscriptions.html',
        'templates/blacklist.html',
        'templates/settings.html'
    ]
    
    required_dirs = [
        'sessions',
        'uploads',
        'static',
        'static/js',
        'static/css',
        'templates'
    ]
    
    missing_files = []
    missing_dirs = []
    
    # Проверяем файлы
    for file_path in required_files:
        if not os.path.exists(file_path):
            missing_files.append(file_path)
    
    # Проверяем папки
    for dir_path in required_dirs:
        if not os.path.exists(dir_path):
            missing_dirs.append(dir_path)
    
    if missing_files:
        print(f"❌ Отсутствуют файлы: {missing_files}")
        return False
    
    if missing_dirs:
        print(f"❌ Отсутствуют папки: {missing_dirs}")
        return False
    
    print("✅ Структура файлов корректна")
    return True

def test_dependencies():
    """Тест зависимостей"""
    print("📦 Тестирование зависимостей...")
    
    required_modules = [
        'flask',
        'telethon',
        'requests',
        'sqlite3'
    ]
    
    missing_modules = []
    
    for module in required_modules:
        try:
            __import__(module)
        except ImportError:
            missing_modules.append(module)
    
    if missing_modules:
        print(f"❌ Отсутствуют модули: {missing_modules}")
        print("Установите их командой: pip install -r requirements.txt")
        return False
    
    print("✅ Все зависимости установлены")
    return True

def create_test_data():
    """Создание тестовых данных"""
    print("📝 Создание тестовых данных...")
    
    try:
        # Создаем папки если их нет
        os.makedirs('sessions', exist_ok=True)
        os.makedirs('uploads', exist_ok=True)
        
        # Создаем тестовый файл с прокси
        with open('example_proxies.txt', 'w', encoding='utf-8') as f:
            f.write("# Пример файла с прокси\n")
            f.write("192.168.1.1:8080:user:pass\n")
            f.write("192.168.1.2:8080:user:pass\n")
        
        # Создаем тестовый файл с юзернеймами
        with open('example_usernames.txt', 'w', encoding='utf-8') as f:
            f.write("# Пример файла с юзернеймами\n")
            f.write("@username1\n")
            f.write("@username2\n")
            f.write("username3\n")
        
        print("✅ Тестовые данные созданы")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка создания тестовых данных: {e}")
        return False

def main():
    """Основная функция тестирования"""
    print("🚀 Запуск тестирования платформы Telegram Mass Management")
    print("=" * 60)
    
    tests = [
        ("Структура файлов", test_file_structure),
        ("Зависимости", test_dependencies),
        ("База данных", test_database),
        ("Тестовые данные", create_test_data),
        ("Веб-сервер", test_web_server),
        ("API endpoints", test_api_endpoints)
    ]
    
    passed_tests = 0
    total_tests = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n{test_name}:")
        if test_func():
            passed_tests += 1
        time.sleep(0.5)
    
    print("\n" + "=" * 60)
    print(f"📊 Результаты тестирования: {passed_tests}/{total_tests} тестов пройдено")
    
    if passed_tests == total_tests:
        print("🎉 Все тесты пройдены! Платформа готова к работе.")
        print("\n📋 Следующие шаги:")
        print("1. Поместите .session файлы в папку sessions/")
        print("2. Настройте прокси в настройках")
        print("3. Запустите платформу: python app.py")
        print("4. Откройте http://localhost:5000")
    else:
        print("⚠️ Некоторые тесты не пройдены. Проверьте ошибки выше.")
    
    return passed_tests == total_tests

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)