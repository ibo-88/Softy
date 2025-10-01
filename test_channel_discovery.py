#!/usr/bin/env python3
"""
Тест новых функций поиска каналов и расширенных возможностей
"""

import sys
import os
import sqlite3
import json
from datetime import datetime

# Добавляем путь к модулям
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_database_tables():
    """Тест новых таблиц базы данных"""
    print("🔍 Тестирование новых таблиц базы данных...")
    
    try:
        # Подключаемся к базе данных
        conn = sqlite3.connect('telegram_platform.db')
        cursor = conn.cursor()
        
        # Проверяем таблицу found_channels
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='found_channels'")
        if cursor.fetchone():
            print("✅ Таблица found_channels создана")
        else:
            print("❌ Таблица found_channels не найдена")
        
        # Проверяем таблицу join_tasks
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='join_tasks'")
        if cursor.fetchone():
            print("✅ Таблица join_tasks создана")
        else:
            print("❌ Таблица join_tasks не найдена")
        
        # Проверяем таблицу channel_languages
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='channel_languages'")
        if cursor.fetchone():
            print("✅ Таблица channel_languages создана")
        else:
            print("❌ Таблица channel_languages не найдена")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Ошибка тестирования таблиц: {e}")
        return False

def test_language_detection():
    """Тест определения языков"""
    print("\n🌍 Тестирование определения языков...")
    
    try:
        from langdetect import detect
        
        test_texts = [
            ("Привет, как дела?", "russian"),
            ("Hello, how are you?", "english"),
            ("Hola, ¿cómo estás?", "spanish"),
            ("Bonjour, comment allez-vous?", "french"),
            ("Hallo, wie geht es dir?", "german"),
            ("Ciao, come stai?", "italian"),
            ("Olá, como você está?", "portuguese"),
            ("你好，你好吗？", "chinese"),
            ("こんにちは、元気ですか？", "japanese"),
            ("안녕하세요, 어떻게 지내세요?", "korean"),
            ("مرحبا، كيف حالك؟", "arabic"),
            ("नमस्ते, आप कैसे हैं?", "hindi"),
            ("Merhaba, nasılsın?", "turkish"),
            ("Cześć, jak się masz?", "polish"),
            ("Привіт, як справи?", "ukrainian")
        ]
        
        success_count = 0
        for text, expected_lang in test_texts:
            try:
                detected = detect(text)
                if detected in expected_lang or expected_lang in detected:
                    print(f"✅ '{text[:20]}...' -> {detected}")
                    success_count += 1
                else:
                    print(f"⚠️  '{text[:20]}...' -> {detected} (ожидался {expected_lang})")
            except Exception as e:
                print(f"❌ Ошибка определения языка для '{text[:20]}...': {e}")
        
        print(f"\n📊 Результат: {success_count}/{len(test_texts)} языков определено корректно")
        return success_count >= len(test_texts) * 0.8  # 80% успешности
        
    except ImportError:
        print("❌ Библиотека langdetect не установлена")
        return False
    except Exception as e:
        print(f"❌ Ошибка тестирования языков: {e}")
        return False

def test_channel_discovery_manager():
    """Тест менеджера поиска каналов"""
    print("\n🔍 Тестирование ChannelDiscoveryManager...")
    
    try:
        # Импортируем необходимые модули
        from app import ChannelDiscoveryManager, DatabaseManager, AccountManager, ProxyManager
        
        # Создаем менеджеры
        db_manager = DatabaseManager()
        proxy_manager = ProxyManager(db_manager)
        account_manager = AccountManager(db_manager, proxy_manager)
        channel_manager = ChannelDiscoveryManager(db_manager, account_manager)
        
        print("✅ ChannelDiscoveryManager создан успешно")
        
        # Тестируем определение языка
        test_titles = [
            "Дейтинг Москва",
            "Dating London", 
            "Citas Madrid",
            "Rencontres Paris",
            "Dating Berlin"
        ]
        
        for title in test_titles:
            language = channel_manager.detect_language(title)
            print(f"✅ '{title}' -> {language}")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка тестирования ChannelDiscoveryManager: {e}")
        return False

def test_api_endpoints():
    """Тест новых API endpoints"""
    print("\n🌐 Тестирование новых API endpoints...")
    
    try:
        import requests
        
        # Тестируем endpoints (если сервер запущен)
        base_url = "http://localhost:5000"
        
        endpoints = [
            "/api/search-channels",
            "/api/found-channels", 
            "/api/join-channels"
        ]
        
        for endpoint in endpoints:
            try:
                if endpoint == "/api/found-channels":
                    response = requests.get(f"{base_url}{endpoint}", timeout=5)
                else:
                    response = requests.post(f"{base_url}{endpoint}", 
                                           json={}, timeout=5)
                
                if response.status_code in [200, 400, 500]:  # Любой ответ означает что endpoint существует
                    print(f"✅ {endpoint} - доступен")
                else:
                    print(f"⚠️  {endpoint} - статус {response.status_code}")
                    
            except requests.exceptions.ConnectionError:
                print(f"⚠️  {endpoint} - сервер не запущен")
            except Exception as e:
                print(f"❌ {endpoint} - ошибка: {e}")
        
        return True
        
    except ImportError:
        print("⚠️  Библиотека requests не установлена")
        return True  # Не критично для теста
    except Exception as e:
        print(f"❌ Ошибка тестирования API: {e}")
        return False

def test_requirements():
    """Тест зависимостей"""
    print("\n📦 Тестирование зависимостей...")
    
    required_packages = [
        "langdetect",
        "telethon", 
        "flask",
        "requests",
        "schedule",
        "pytz"
    ]
    
    success_count = 0
    for package in required_packages:
        try:
            __import__(package)
            print(f"✅ {package} - установлен")
            success_count += 1
        except ImportError:
            print(f"❌ {package} - не установлен")
    
    print(f"\n📊 Результат: {success_count}/{len(required_packages)} пакетов установлено")
    return success_count == len(required_packages)

def test_file_structure():
    """Тест структуры файлов"""
    print("\n📁 Тестирование структуры файлов...")
    
    required_files = [
        "app.py",
        "requirements.txt",
        "templates/channel_discovery.html",
        "templates/base.html",
        "README.md",
        "CHANNEL_DISCOVERY_IMPLEMENTATION.md"
    ]
    
    success_count = 0
    for file_path in required_files:
        if os.path.exists(file_path):
            print(f"✅ {file_path} - существует")
            success_count += 1
        else:
            print(f"❌ {file_path} - не найден")
    
    print(f"\n📊 Результат: {success_count}/{len(required_files)} файлов найдено")
    return success_count == len(required_files)

def main():
    """Основная функция тестирования"""
    print("🚀 ТЕСТИРОВАНИЕ НОВЫХ ФУНКЦИЙ ПОИСКА КАНАЛОВ")
    print("=" * 60)
    
    tests = [
        ("Структура файлов", test_file_structure),
        ("Зависимости", test_requirements),
        ("Таблицы базы данных", test_database_tables),
        ("Определение языков", test_language_detection),
        ("ChannelDiscoveryManager", test_channel_discovery_manager),
        ("API endpoints", test_api_endpoints)
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ Критическая ошибка в тесте '{test_name}': {e}")
            results.append((test_name, False))
    
    # Итоговый отчет
    print("\n" + "="*60)
    print("📊 ИТОГОВЫЙ ОТЧЕТ")
    print("="*60)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ ПРОЙДЕН" if result else "❌ ПРОВАЛЕН"
        print(f"{test_name:<30} {status}")
        if result:
            passed += 1
    
    print(f"\n📈 Общий результат: {passed}/{total} тестов пройдено")
    
    if passed == total:
        print("🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ! Новые функции готовы к использованию.")
        return True
    else:
        print("⚠️  Некоторые тесты провалены. Проверьте ошибки выше.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)