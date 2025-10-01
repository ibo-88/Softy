#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Telegram Mass Account Management Platform
Платформа для Массового Управления Аккаунтами Telegram
"""

import os
import sys
import json
import sqlite3
import threading
import asyncio
import time
import random
import logging
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_from_directory
from telethon import TelegramClient
from telethon.errors import FloodWaitError, UserBannedError, ChatWriteForbiddenError
import requests

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('telegram_platform.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'telegram_mass_platform_2024'

# Глобальные переменные
accounts_pool = []
proxy_pool = []
blacklist = set()
active_tasks = {}
task_logs = {}

class DatabaseManager:
    def __init__(self, db_path='telegram_platform.db'):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Инициализация базы данных"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Таблица аккаунтов
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                phone TEXT UNIQUE,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                status TEXT DEFAULT 'offline',
                proxy_id INTEGER,
                geo_country TEXT,
                session_file TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_check TIMESTAMP,
                FOREIGN KEY (proxy_id) REFERENCES proxies (id)
            )
        ''')
        
        # Таблица прокси
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS proxies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ip TEXT,
                port INTEGER,
                username TEXT,
                password TEXT,
                country TEXT,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Таблица blacklist
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS blacklist (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                username TEXT,
                reason TEXT,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Таблица задач парсинга
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS parsing_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                source_type TEXT,
                source_data TEXT,
                status TEXT DEFAULT 'pending',
                results_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP
            )
        ''')
        
        # Таблица рассылок
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS campaigns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                message TEXT,
                media_path TEXT,
                target_count INTEGER,
                sent_count INTEGER DEFAULT 0,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                started_at TIMESTAMP,
                completed_at TIMESTAMP
            )
        ''')
        
        # Таблица логов
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_id INTEGER,
                action TEXT,
                target TEXT,
                status TEXT,
                message TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (account_id) REFERENCES accounts (id)
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("База данных инициализирована")

class ProxyManager:
    def __init__(self, db_manager):
        self.db = db_manager
        self.good_proxy_api_key = None
    
    def load_proxies_from_file(self, file_path):
        """Загрузка прокси из файла"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            conn = sqlite3.connect(self.db.db_path)
            cursor = conn.cursor()
            
            loaded_count = 0
            for line in lines:
                line = line.strip()
                if ':' in line:
                    parts = line.split(':')
                    if len(parts) >= 2:
                        ip = parts[0]
                        port = int(parts[1])
                        username = parts[2] if len(parts) > 2 else ''
                        password = parts[3] if len(parts) > 3 else ''
                        
                        cursor.execute('''
                            INSERT OR IGNORE INTO proxies (ip, port, username, password)
                            VALUES (?, ?, ?, ?)
                        ''', (ip, port, username, password))
                        loaded_count += 1
            
            conn.commit()
            conn.close()
            logger.info(f"Загружено {loaded_count} прокси из файла")
            return loaded_count
        except Exception as e:
            logger.error(f"Ошибка загрузки прокси из файла: {e}")
            return 0
    
    def get_proxies_from_api(self, api_key):
        """Получение прокси через API good proxy"""
        try:
            # Здесь должен быть реальный API запрос к good proxy
            # Для демонстрации возвращаем тестовые данные
            self.good_proxy_api_key = api_key
            
            # Имитация API запроса
            test_proxies = [
                {"ip": "192.168.1.1", "port": 8080, "username": "user1", "password": "pass1", "country": "DE"},
                {"ip": "192.168.1.2", "port": 8080, "username": "user2", "password": "pass2", "country": "US"},
                {"ip": "192.168.1.3", "port": 8080, "username": "user3", "password": "pass3", "country": "RU"},
            ]
            
            conn = sqlite3.connect(self.db.db_path)
            cursor = conn.cursor()
            
            for proxy in test_proxies:
                cursor.execute('''
                    INSERT OR IGNORE INTO proxies (ip, port, username, password, country)
                    VALUES (?, ?, ?, ?, ?)
                ''', (proxy["ip"], proxy["port"], proxy["username"], 
                      proxy["password"], proxy["country"]))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Получено {len(test_proxies)} прокси из API good proxy")
            return len(test_proxies)
        except Exception as e:
            logger.error(f"Ошибка получения прокси из API: {e}")
            return 0

class AccountManager:
    def __init__(self, db_manager, proxy_manager):
        self.db = db_manager
        self.proxy_manager = proxy_manager
        self.accounts = {}
    
    def load_sessions_from_folder(self, folder_path):
        """Массовая загрузка сессий из папки"""
        try:
            session_files = []
            for file in os.listdir(folder_path):
                if file.endswith('.session'):
                    session_files.append(os.path.join(folder_path, file))
            
            conn = sqlite3.connect(self.db.db_path)
            cursor = conn.cursor()
            
            loaded_count = 0
            for session_file in session_files:
                try:
                    # Извлекаем номер телефона из имени файла
                    phone = os.path.basename(session_file).replace('.session', '')
                    
                    cursor.execute('''
                        INSERT OR IGNORE INTO accounts (phone, session_file)
                        VALUES (?, ?)
                    ''', (phone, session_file))
                    loaded_count += 1
                except Exception as e:
                    logger.error(f"Ошибка загрузки сессии {session_file}: {e}")
            
            conn.commit()
            conn.close()
            
            logger.info(f"Загружено {loaded_count} сессий из папки")
            return loaded_count
        except Exception as e:
            logger.error(f"Ошибка загрузки сессий: {e}")
            return 0
    
    def assign_geo_proxies(self, country):
        """Назначение прокси по геолокации"""
        try:
            conn = sqlite3.connect(self.db.db_path)
            cursor = conn.cursor()
            
            # Получаем прокси из указанной страны
            cursor.execute('SELECT id FROM proxies WHERE country = ? AND is_active = 1', (country,))
            proxy_ids = [row[0] for row in cursor.fetchall()]
            
            if not proxy_ids:
                logger.warning(f"Не найдены прокси для страны {country}")
                return 0
            
            # Получаем аккаунты без назначенных прокси
            cursor.execute('SELECT id FROM accounts WHERE proxy_id IS NULL')
            account_ids = [row[0] for row in cursor.fetchall()]
            
            assigned_count = 0
            for i, account_id in enumerate(account_ids):
                proxy_id = proxy_ids[i % len(proxy_ids)]
                cursor.execute('''
                    UPDATE accounts SET proxy_id = ?, geo_country = ?
                    WHERE id = ?
                ''', (proxy_id, country, account_id))
                assigned_count += 1
            
            conn.commit()
            conn.close()
            
            logger.info(f"Назначено {assigned_count} прокси для страны {country}")
            return assigned_count
        except Exception as e:
            logger.error(f"Ошибка назначения гео-прокси: {e}")
            return 0
    
    def mass_check_accounts(self):
        """Массовая проверка аккаунтов (ТП)"""
        def check_account(account_id, session_file, proxy_data):
            try:
                # Создаем клиент с прокси
                client = TelegramClient(session_file, api_id, api_hash)
                
                if proxy_data:
                    proxy = {
                        'proxy_type': 'http',
                        'addr': proxy_data['ip'],
                        'port': proxy_data['port'],
                        'username': proxy_data['username'],
                        'password': proxy_data['password']
                    }
                    client.set_proxy(proxy)
                
                # Проверяем подключение
                with client:
                    me = client.get_me()
                    status = 'online'
                    username = me.username or ''
                    first_name = me.first_name or ''
                    last_name = me.last_name or ''
                
                # Обновляем статус в БД
                conn = sqlite3.connect(self.db.db_path)
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE accounts SET status = ?, username = ?, first_name = ?, last_name = ?, last_check = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (status, username, first_name, last_name, account_id))
                conn.commit()
                conn.close()
                
                logger.info(f"Аккаунт {account_id}: ТП пройдена, статус 🟢 Онлайн")
                
            except Exception as e:
                # Обновляем статус на ошибку
                conn = sqlite3.connect(self.db.db_path)
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE accounts SET status = 'banned', last_check = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (account_id,))
                conn.commit()
                conn.close()
                
                logger.error(f"Аккаунт {account_id}: Ошибка проверки - {e}")
        
        # Запускаем проверку в отдельных потоках
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT a.id, a.session_file, p.ip, p.port, p.username, p.password
            FROM accounts a
            LEFT JOIN proxies p ON a.proxy_id = p.id
            WHERE a.status != 'banned'
        ''')
        
        accounts_to_check = cursor.fetchall()
        conn.close()
        
        threads = []
        for account_data in accounts_to_check:
            account_id, session_file, ip, port, username, password = account_data
            proxy_data = None
            if ip:
                proxy_data = {'ip': ip, 'port': port, 'username': username, 'password': password}
            
            thread = threading.Thread(target=check_account, args=(account_id, session_file, proxy_data))
            thread.start()
            threads.append(thread)
        
        logger.info(f"Запущена проверка {len(accounts_to_check)} аккаунтов")
        return len(accounts_to_check)

# Инициализация менеджеров
db_manager = DatabaseManager()
proxy_manager = ProxyManager(db_manager)
account_manager = AccountManager(db_manager, proxy_manager)

# Импорт конфигурации
from config import config

# Получение конфигурации
config_name = os.environ.get('FLASK_ENV', 'default')
app_config = config[config_name]

# API ключи Telegram (настройте в config.py или через переменные окружения)
api_id = app_config.API_ID
api_hash = app_config.API_HASH

@app.route('/')
def index():
    """Главная страница - дашборд"""
    return render_template('index.html')

@app.route('/accounts')
def accounts_page():
    """Страница управления аккаунтами"""
    return render_template('accounts.html')

@app.route('/parsing')
def parsing_page():
    """Страница парсинга"""
    return render_template('parsing.html')

@app.route('/campaigns')
def campaigns_page():
    """Страница рассылок"""
    return render_template('campaigns.html')

@app.route('/blacklist')
def blacklist_page():
    """Страница blacklist"""
    return render_template('blacklist.html')

@app.route('/settings')
def settings_page():
    """Страница настроек"""
    return render_template('settings.html')

# API endpoints
@app.route('/api/accounts', methods=['GET'])
def get_accounts():
    """Получение списка аккаунтов"""
    try:
        conn = sqlite3.connect(db_manager.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT a.id, a.phone, a.username, a.first_name, a.last_name, 
                   a.status, a.geo_country, p.ip, p.port
            FROM accounts a
            LEFT JOIN proxies p ON a.proxy_id = p.id
            ORDER BY a.id
        ''')
        
        accounts = []
        for row in cursor.fetchall():
            accounts.append({
                'id': row[0],
                'phone': row[1],
                'username': row[2] or '',
                'first_name': row[3] or '',
                'last_name': row[4] or '',
                'status': row[5],
                'geo_country': row[6] or '',
                'proxy': f"{row[7]}:{row[8]}" if row[7] else ''
            })
        
        conn.close()
        return jsonify(accounts)
    except Exception as e:
        logger.error(f"Ошибка получения аккаунтов: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/upload-sessions', methods=['POST'])
def upload_sessions():
    """Загрузка сессий из папки"""
    try:
        folder_path = request.json.get('folder_path')
        if not folder_path or not os.path.exists(folder_path):
            return jsonify({'error': 'Неверный путь к папке'}), 400
        
        count = account_manager.load_sessions_from_folder(folder_path)
        return jsonify({'success': True, 'count': count})
    except Exception as e:
        logger.error(f"Ошибка загрузки сессий: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/upload-proxies', methods=['POST'])
def upload_proxies():
    """Загрузка прокси из файла"""
    try:
        file_path = request.json.get('file_path')
        if not file_path or not os.path.exists(file_path):
            return jsonify({'error': 'Неверный путь к файлу'}), 400
        
        count = proxy_manager.load_proxies_from_file(file_path)
        return jsonify({'success': True, 'count': count})
    except Exception as e:
        logger.error(f"Ошибка загрузки прокси: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/get-proxies-api', methods=['POST'])
def get_proxies_api():
    """Получение прокси через API"""
    try:
        api_key = request.json.get('api_key')
        if not api_key:
            return jsonify({'error': 'API ключ не указан'}), 400
        
        count = proxy_manager.get_proxies_from_api(api_key)
        return jsonify({'success': True, 'count': count})
    except Exception as e:
        logger.error(f"Ошибка получения прокси из API: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/assign-geo-proxies', methods=['POST'])
def assign_geo_proxies():
    """Назначение прокси по геолокации"""
    try:
        country = request.json.get('country')
        if not country:
            return jsonify({'error': 'Страна не указана'}), 400
        
        count = account_manager.assign_geo_proxies(country)
        return jsonify({'success': True, 'count': count})
    except Exception as e:
        logger.error(f"Ошибка назначения гео-прокси: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/mass-check', methods=['POST'])
def mass_check():
    """Массовая проверка аккаунтов"""
    try:
        count = account_manager.mass_check_accounts()
        return jsonify({'success': True, 'count': count})
    except Exception as e:
        logger.error(f"Ошибка массовой проверки: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Получение статистики"""
    try:
        conn = sqlite3.connect(db_manager.db_path)
        cursor = conn.cursor()
        
        # Общая статистика аккаунтов
        cursor.execute('SELECT COUNT(*) FROM accounts')
        total_accounts = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM accounts WHERE status = "online"')
        online_accounts = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM accounts WHERE status = "banned"')
        banned_accounts = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM proxies WHERE is_active = 1')
        active_proxies = cursor.fetchone()[0]
        
        conn.close()
        
        return jsonify({
            'total_accounts': total_accounts,
            'online_accounts': online_accounts,
            'banned_accounts': banned_accounts,
            'active_proxies': active_proxies
        })
    except Exception as e:
        logger.error(f"Ошибка получения статистики: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    logger.info("Запуск Telegram Mass Account Management Platform")
    logger.info(f"Платформа доступна по адресу: http://{app_config.HOST}:{app_config.PORT}")
    app.run(host=app_config.HOST, port=app_config.PORT, debug=app_config.DEBUG)